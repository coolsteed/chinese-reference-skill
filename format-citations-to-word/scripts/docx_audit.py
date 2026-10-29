#!/usr/bin/env python3
"""Inventory, guarded citation patches, and mechanical DOCX verification.
Requires lxml; use the artifact runtime when available. No network operations.
"""
import argparse
from collections import defaultdict
import copy
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import tempfile
from urllib.parse import unquote
from zipfile import ZipFile
from lxml import etree as E

NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W = '{' + NS + '}'
PART = re.compile(r'word/(document|footnotes|endnotes|header\d+|footer\d+)\.xml$')
PROTECTED = ('fldChar', 'instrText', 'fldSimple', 'bookmarkStart', 'bookmarkEnd',
             'commentRangeStart', 'commentRangeEnd', 'commentReference',
             'ins', 'del', 'sdt', 'drawing', 'object')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    with ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise ValueError('Corrupt ZIP member: ' + bad)
        data = {i.filename: z.read(i) for i in z.infolist()}
        if len(data) != len(z.infolist()):
            raise ValueError('Duplicate ZIP members')
    if 'word/document.xml' not in data:
        raise ValueError('Not a DOCX package')
    parser = E.XMLParser(resolve_entities=False, no_network=True)
    for name, content in data.items():
        if name.endswith(('.xml', '.rels')):
            if b'<!DOCTYPE' in content:
                raise ValueError('Unexpected DTD in Word XML: ' + name)
            E.fromstring(content, parser)
    for name, content in data.items():
        if name.endswith('.rels'):
            base = '' if name == '_rels/.rels' else name.rsplit('/_rels/', 1)[0]
            for rel in E.fromstring(content, parser):
                if rel.get('TargetMode') == 'External':
                    continue
                target = unquote(rel.get('Target', '').split('#')[0])
                if not target:
                    continue
                target = posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join(base, target))
                if target not in data:
                    raise ValueError(f'Broken relationship {name}: {target}')
    return data

def roots(data):
    return {n: E.fromstring(v) for n, v in data.items() if PART.fullmatch(n)}

def paragraphs(root):
    return list(root.iter(W + 'p'))

def text(p):
    return ''.join(t.text or '' for t in p.iter(W + 't'))

def style(p):
    x = p.find(W + 'pPr/' + W + 'pStyle')
    return x.get(W + 'val', '') if x is not None else ''

def protected(root):
    return {n: sum(1 for _ in root.iter(W + n)) for n in PROTECTED}

def inventory(path):
    data = load(path)
    return {'sha256': sha(path), 'parts': {
        name: {'protected': protected(root), 'paragraphs': [
            {'index': i, 'style': style(p), 'text': text(p),
             'protected': {k: v for k, v in protected(p).items() if v}}
            for i, p in enumerate(paragraphs(root))]}
        for name, root in roots(data).items()}}

def plan_groups(path, plan):
    if plan.get('source_sha256') != sha(path):
        raise ValueError('Source SHA-256 mismatch')
    groups = defaultdict(list)
    if not plan.get('edits'):
        raise ValueError('Empty edit plan')
    for edit in plan['edits']:
        if not edit.get('citation_id') or not edit.get('evidence'):
            raise ValueError('Each edit needs citation_id and evidence')
        if edit.get('kind') not in ('span', 'reference'):
            raise ValueError('Unknown patch kind')
        if not PART.fullmatch(edit.get('part', '')):
            raise ValueError('Unsupported Word part')
        if not isinstance(edit.get('paragraph'), int) or edit['paragraph'] < 0:
            raise ValueError('Invalid paragraph index')
        groups[(edit['part'], edit['paragraph'])].append(edit)
    return groups

def expected(old, edits):
    if any(e['kind'] == 'reference' for e in edits):
        if len(edits) != 1 or edits[0]['old'] != old:
            raise ValueError('Whole-reference guard mismatch or conflicting edits')
        segments = edits[0].get('segments')
        if not segments or any(not isinstance(s.get('text'), str) for s in segments):
            raise ValueError('Reference patch needs nonempty text segments')
        if any(not isinstance(s[k], bool) for s in segments for k in ('italic', 'bold') if k in s):
            raise ValueError('Italic/bold values must be JSON booleans')
        return ''.join(s['text'] for s in segments)
    ordered = sorted(edits, key=lambda e: e['start'])
    last = -1
    for e in ordered:
        a, b = e['start'], e['end']
        if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < b <= len(old)):
            raise ValueError('Invalid span offsets')
        if a < last or old[a:b] != e['old'] or not isinstance(e.get('new'), str):
            raise ValueError('Overlapping spans or old-text guard mismatch')
        last = b
    result = old
    for e in reversed(ordered):
        result = result[:e['start']] + e['new'] + result[e['end']:]
    return result

def ensure_plain(p):
    if any(protected(p).values()) or any(q is not p for q in p.iter(W + 'p')):
        raise ValueError('Protected/complex paragraph: use a field-aware editing route')
    if any(c.tag not in (W + 'pPr', W + 'r') for c in p):
        raise ValueError('Paragraph contains hyperlinks, controls, or other complex elements')
    for r in p.findall(W + 'r'):
        if any(c.tag not in (W + 'rPr', W + 't') for c in r):
            raise ValueError('Non-text run cannot be patched with this helper')

def set_text(node, value):
    node.text = value
    node.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')

def patch(p, edits):
    ensure_plain(p)
    old = text(p)
    result = expected(old, edits)
    if edits[0]['kind'] == 'reference':
        for c in list(p):
            if c.tag != W + 'pPr':
                p.remove(c)
        for seg in edits[0]['segments']:
            run = E.SubElement(p, W + 'r')
            if 'italic' in seg or 'bold' in seg:
                pr = E.SubElement(run, W + 'rPr')
                for key, tag in [('italic', 'i'), ('bold', 'b')]:
                    if key in seg:
                        E.SubElement(pr, W + tag).set(W + 'val', '1' if seg[key] else '0')
            set_text(E.SubElement(run, W + 't'), seg['text'])
    else:
        for e in sorted(edits, key=lambda x: x['start'], reverse=True):
            offset = 0
            first = True
            for node in p.iter(W + 't'):
                val = node.text or ''
                a, b = offset, offset + len(val)
                offset = b
                if a < e['end'] and b > e['start']:
                    prefix = val[:max(0, e['start'] - a)]
                    suffix = val[max(0, e['end'] - a):] if e['end'] < b else ''
                    set_text(node, prefix + (e['new'] if first else '') + suffix)
                    first = False
    if text(p) != result:
        raise ValueError('Patch result failed internal text guard')

def apply(source, plan, output):
    if Path(source).resolve() == Path(output).resolve():
        raise ValueError('Output must not overwrite source')
    data = load(source)
    rt = roots(data)
    groups = plan_groups(source, plan)
    for (part, index), edits in groups.items():
        if part not in rt or index >= len(paragraphs(rt[part])):
            raise ValueError('Patch paragraph does not exist')
        patch(paragraphs(rt[part])[index], edits)
    for part in {k[0] for k in groups}:
        data[part] = E.tostring(rt[part], xml_declaration=True, encoding='UTF-8', standalone=True)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, suffix='.docx')
    os.close(fd)
    try:
        with ZipFile(source) as zin, ZipFile(tmp, 'w') as zout:
            for item in zin.infolist():
                zout.writestr(item, data[item.filename])
        load(tmp)
        os.replace(tmp, out)
    finally:
        if Path(tmp).exists():
            Path(tmp).unlink()

def canonical(node):
    return E.tostring(node, method='c14n') if node is not None else b''

def skeleton(p):
    p = copy.deepcopy(p)
    for t in p.iter(W + 't'):
        t.text = ''
        t.attrib.pop('{http://www.w3.org/XML/1998/namespace}space', None)
    return canonical(p)

def preservation(before, after, plan=None):
    a, b = load(before), load(after)
    if set(a) != set(b):
        raise ValueError('Package members added or removed')
    groups = plan_groups(before, plan) if plan else {}
    changed = {part for part, _ in groups}
    for name in a:
        if name not in changed and a[name] != b[name]:
            raise ValueError('Unplanned change to ZIP member: ' + name)
    ra, rb = roots(a), roots(b)
    for name in ra:
        pa, pb = paragraphs(ra[name]), paragraphs(rb[name])
        if len(pa) != len(pb) or protected(ra[name]) != protected(rb[name]):
            raise ValueError('Paragraph/protected structure count changed in ' + name)
        for i, (x, y) in enumerate(zip(pa, pb)):
            edits = groups.get((name, i))
            if not edits:
                if canonical(x) != canonical(y):
                    raise ValueError(f'Unplanned paragraph change: {name}:{i}')
            else:
                ensure_plain(x)
                if text(y) != expected(text(x), edits):
                    raise ValueError(f'Unexpected text outside citation patch: {name}:{i}')
                if edits[0]['kind'] == 'span' and skeleton(x) != skeleton(y):
                    raise ValueError('Span patch changed run formatting/structure')
                if edits[0]['kind'] == 'reference' and canonical(x.find(W + 'pPr')) != canonical(y.find(W + 'pPr')):
                    raise ValueError('Reference patch changed paragraph properties')

def normalize(s):
    return re.sub(r'\s+', ' ', s).strip()

def italic_text(data, rt):
    styles = E.fromstring(data['word/styles.xml']) if 'word/styles.xml' in data else E.Element('none')
    smap = {s.get(W + 'styleId'): s for s in styles.findall(W + 'style')}
    def prop(pr, inherited):
        e = pr.find(W + 'i') if pr is not None else None
        return inherited if e is None else e.get(W + 'val', 'true') not in ('0', 'false', 'off')
    def inherited(sid, seen=None):
        seen = set() if seen is None else seen
        if sid in seen or sid not in smap:
            return False
        seen.add(sid)
        s = smap[sid]
        base = s.find(W + 'basedOn')
        return prop(s.find(W + 'rPr'), inherited(base.get(W + 'val'), seen) if base is not None else False)
    default = prop(styles.find(W + 'docDefaults/' + W + 'rPrDefault/' + W + 'rPr'), False)
    chunks = []
    for root in rt.values():
        for p in paragraphs(root):
            pitalic = inherited(style(p)) if style(p) in smap else default
            for run in p.iter(W + 'r'):
                pr = run.find(W + 'rPr')
                rs = pr.find(W + 'rStyle') if pr is not None else None
                # An unstyled run inherits the paragraph. Explicit character styles are conservative.
                value = inherited(rs.get(W + 'val')) if rs is not None else pitalic
                chunks.append(text(run) if prop(pr, value) else '\0')
            chunks.append('\0')
    return normalize(''.join(chunks))

def check(output, checks, before=None, plan=None):
    errors, passed = [], []
    data = load(output)
    rt = roots(data)
    full = normalize(' '.join(text(p) for r in rt.values() for p in paragraphs(r)))
    sty = set(checks.get('bibliography_styles', ['Bibliography']))
    if 'word/styles.xml' in data:
        for definition in E.fromstring(data['word/styles.xml']).findall(W + 'style'):
            name = definition.find(W + 'name')
            if name is not None and name.get(W + 'val') in sty:
                sty.add(definition.get(W + 'styleId'))
    refs = [normalize(text(p)) for p in paragraphs(rt['word/document.xml']) if style(p) in sty]
    def require(ok, message):
        (passed if ok else errors).append(message)
    if 'reference_count' in checks:
        require(len(refs) == checks['reference_count'], f'Reference count: {len(refs)} expected {checks["reference_count"]}')
    for value in checks.get('required_text', []):
        require(normalize(value) in full, 'Required text: ' + value)
    for value in checks.get('forbidden_text', []):
        require(normalize(value) not in full, 'Forbidden text absent: ' + value)
    for value in checks.get('required_references', []):
        require(any(normalize(value) == x for x in refs), 'Expected reference: ' + value)
    itext = italic_text(data, rt)
    for value in checks.get('required_italic', []):
        require(normalize(value) in itext, 'Verified italic: ' + value)
    for key in checks.get('citation_keys', []):
        require(not re.search(r'(?<![\w@])@' + re.escape(key) + r'(?![\w-])', full), 'No raw citation key: ' + key)
    if before:
        try:
            preservation(before, output, plan)
            passed.append('Source preservation within declared patch scope')
        except (ValueError, KeyError, IndexError) as exc:
            errors.append(str(exc))
    elif plan:
        errors.append('A plan requires --before')
    return {'mechanical_status': 'fail' if errors else 'pass', 'sha256': sha(output),
            'reference_count': len(refs), 'passed': passed, 'errors': errors,
            'not_proven': ['Citation identity and full rule coverage require ledger review',
                           'Visual pagination/fonts require rendered page review']}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inv = sub.add_parser('inventory'); inv.add_argument('docx'); inv.add_argument('--output')
    ap = sub.add_parser('apply'); ap.add_argument('source'); ap.add_argument('plan'); ap.add_argument('output')
    ck = sub.add_parser('check'); ck.add_argument('docx'); ck.add_argument('--checks', required=True)
    ck.add_argument('--before'); ck.add_argument('--plan'); ck.add_argument('--report')
    args = parser.parse_args()
    try:
        if args.command == 'inventory':
            result = inventory(args.docx)
            target = args.output
        elif args.command == 'apply':
            plan = json.loads(Path(args.plan).read_text())
            apply(args.source, plan, args.output)
            result = {'written': args.output, 'sha256': sha(args.output), 'edits': len(plan['edits'])}
            target = None
        else:
            result = check(args.docx, json.loads(Path(args.checks).read_text()), args.before,
                           json.loads(Path(args.plan).read_text()) if args.plan else None)
            target = args.report
        encoded = json.dumps(result, ensure_ascii=False, indent=2)
        if target:
            Path(target).write_text(encoded + '\n', encoding='utf-8')
        print(encoded)
        return 2 if result.get('mechanical_status') == 'fail' else 0
    except Exception as exc:
        print(json.dumps({'mechanical_status': 'fail', 'errors': [str(exc)]}, ensure_ascii=False))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
