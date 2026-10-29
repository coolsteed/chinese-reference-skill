# 逐条修订与复核

## 后备路径与台账

触发须具体：无法可靠结构化的书目、少量 CSL 难表达的例外、已确认引擎限制，或活动字段环境不可用且用户已选择静态修订。不要把少量例外升级成全文手改。

台账至少包括 citation_id、part/位置、原始文本、关联书目 ID、规则 ID、证据、目标富文本、执行状态及复核结果。同作者同年、译名、重复引用、编号重排须全局一致。编号变动要覆盖正文、表格、脚注，不能只改文末。歧义条目标未决，不自动合并。

执行技能的 agent 自行逐项判断即可；不要求子 agent。只有另有授权和实际益处时才做独立代理复核。独立复核应只拿规则、原稿和成稿，不先给出预期结论。

## Patch 协议

运行 inventory 获取 part 与 paragraph 索引。索引从 0 开始，按对应 XML part 的全部 w:p 文档序排列（包括表格和脚注）。计划必须带原稿 SHA-256，不能对改过的稿复用索引。

```json
{
  "source_sha256": "实际原稿哈希",
  "edits": [
    {
      "kind": "span", "part": "word/document.xml", "paragraph": 3,
      "start": 12, "end": 21, "old": "实际旧引注", "new": "目标引注",
      "citation_id": "cite-004", "evidence": ["rules:cite-parentheses", "pdf:p2"]
    },
    {
      "kind": "reference", "part": "word/document.xml", "paragraph": 51,
      "old": "完整旧文献段落",
      "segments": [{"text": "Author. 2020. "}, {"text": "Book Title", "italic": true}, {"text": ". Publisher."}],
      "citation_id": "ref-012", "evidence": ["rules:book-title"]
    }
  ]
}
```

这只是结构示例，偏移与文本并不匹配，不能原样执行。span 的 old 必须等于该段纯文本 `[start:end]`；可跨普通 run，不能重叠。reference 必须确认整段就是一条文献，保留 pPr 并按 segments 重建 runs。脚本拒绝复杂段落而非删除保护结构。

```text
python docx_audit.py apply source.docx plan.json candidate.docx
python docx_audit.py check candidate.docx --before source.docx --plan plan.json --checks checks.json --report audit.json
```

## 复核协议

### 独立期望

```json
{
  "bibliography_styles": ["Bibliography"],
  "reference_count": 36,
  "required_text": ["第159～181页", "210–219"],
  "forbidden_text": ["CITATION NOT FOUND"],
  "required_italic": ["A verified journal title"],
  "required_references": ["One independently expected full reference"],
  "citation_keys": ["known_source_key"]
}
```

值按当前规范决定：计数来自源 AST/引用字段清单，不是整个文献库数或输出倒填值。required_text 来自独立解读的样例，required_references 仅查书目样式段落；样式定位失败先修定位。citation_keys 只排查未处理 @key，不代替来源映射。required_italic 查明确应斜体的文本（含样式继承），未能确认不能默认通过。

### 自动检查

- 包/关系目标可解析；引用书目条目数；未解析原始键；代表性完整引用、标点、字体属性。
- 有 Word before + patch plan 时，所有段落输出须等于原段按计划替换后的文本，未触碰 ZIP part 字节相同，保护结构计数不变。无计划且文字变动时自动保真应失败，而非猜测授权范围。
- 其他生成路线需另做 AST/引用键与引擎输出映射、非引用正文内容、表格/脚注等保真审计。通用脚本不能自动证明作者年份仍指向同一文献。
- 原始数据缺失与格式错误分别列明；成功退出、零警告或 schema 通过仅是部分证据。

### 全量与视觉复核

1. 所有台账项有复核结果；agent 修改的例外必须100%核对，不能抽查。
2. 作者、年份、题名/DOI、编号来源和定位页保持身份对应；同源的多次引用不是重复错误。
3. 按实际出现情况回归单页、范围页、联期、文章号、多作者、同年后缀、中英混合簇、译编者、待刊稿。
4. 每页 PNG 检查字体、斜体、悬挂缩进、换行、表格和脚注；最终 Word 改动后重新渲染。
5. 未处理引用、映射歧义、字段无法刷新、视觉未做等不能因无编译警告自动关闭。

脚本仅给机械状态 pass/fail。执行者综合台账与视觉决定：全部完成为 verified；仅书目事实缺口为 verified_with_data_gaps；有失败、未决引用或未完成检查则 needs_review。不宣称脚本已证明“完全符合期刊”。
