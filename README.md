# format-citations-to-word

**根据 PDF 中的引用示例，调整稿件的文内引注和参考文献，生成经过检查的 Word 文档。**

中英文混排的word文档引用一直是个老大难问题，很少有csl文件能够完美支持混排，且不同杂志规范又常常偏离国家标准。Agentic应用提供了一个可以实时生成csl，并进行混排的方案。

这个skill支持：提供一份引用格式示例 PDF，以及 Word、Markdown 或 R Markdown 稿件，交由 AI Agent 提取规则、编写 CSL、处理兼容性问题并输出 `.docx`。已有的 BibTeX、CSL JSON、CSL 样式或 Word 模板也可以一并提供。

处理顺序：**CSL → Python／R 脚本 → 必要时由 Agent 逐条修订 Word → 自动检查与逐页复核**。

## 功能

| 能力 | 处理内容 |
| --- | --- |
| 从示例提取规则 | 文内引注、作者人数、同年后缀、排序、标点、斜体、卷期页码、译编者及网页格式 |
| 按稿件生成 CSL | 根据用户提供的样例确定规则，并在目标引擎中测试 |
| Markdown／Rmd 转 Word | 通过 Pandoc 转换 Markdown，或实际执行 R Markdown knit |
| 编辑现有 Word | 先检查引文字段和文档结构，再选择保留字段或局部修订的路线 |
| 中英文适配 | 根据当前规范处理语言字段、作者连接词、页码范围符号及拼音排序 |
| 逐条修订后备方案 | 为无法可靠规则化的引用建立台账，按证据逐项修改 |
| 自动保真检查 | 核对引用数量、预期文本、斜体和修改范围，拦截计划外的正文变化 |
| 视觉复核 | 渲染 Word，逐页检查中文字体、分页、表格、脚注及参考文献排版 |

格式由本次 PDF 及用户要求决定。示例没有规定的地方会标明推断；缺失的作者、年份、卷期或页码会列为数据缺口。

## 快速开始

### 安装

将完整的 `format-citations-to-word` 文件夹放入 Codex 的技能目录。默认目录结构如下；自定义 `CODEX_HOME` 时使用相应的 `skills` 目录。

```text
~/.codex/skills/
└── format-citations-to-word/
    ├── SKILL.md
    ├── README.md
    ├── agents/
    ├── references/
    └── scripts/
```

保留整个文件夹，确保技能可以访问参考说明和辅助脚本。

### 提供材料

| 材料 | 要求 |
| --- | --- |
| 引用格式 PDF | 必需；可以是投稿规范，也可以是包含引用和参考文献的论文示例页 |
| 稿件 | 必需；支持 `.docx`、`.md`、`.rmd` |
| 文献库 | 有则提供；例如 `.bib`、CSL JSON，可提高格式转换的可靠性 |
| 现有样式或模板 | 有则提供；例如 `.csl`、作为排版依据的 `.docx` |

未提供文献库时，Agent 会先检查稿件中的引文字段和文末条目。只有无法确定引用对应关系或缺少必要材料时，才需要补充信息。

### 调用示例

```text
使用 $format-citations-to-word。

请根据“引用格式示例.pdf”，调整“论文.rmd”中的引用，
文献库是“references.bib”，最终输出 Word 文档。
请保留正文内容，并检查中英文标点、斜体、排序和页码格式。
```

```text
使用 $format-citations-to-word。

请根据这个 PDF 中的引用例子，修改“论文.docx”的文内引注和参考文献。
先检查是否存在 Zotero 或 EndNote 字段，尽量保留活动字段。
无法通过 CSL 或脚本处理的地方，再逐条修订并记录依据。
```

## 工作流程

```text
PDF 示例 + 稿件 + 可选文献库／模板
                 │
                 ▼
       提取规则、证据页与独立预期
                 │
                 ▼
       检查稿件结构和引用对应关系
                 │
                 ▼
       编写／调整 CSL，在目标引擎测试
                 │
                 ▼
       Python／R 适配数据、编译 Word
                 │
          仍有无法处理的条目？
                 │ 是
                 ▼
       Agent 逐条判断，按修订计划写入
                 │
                 ▼
       自动检查 → 修复 → 再检查
                 │
                 ▼
       渲染 Word，逐页视觉复核
                 │
                 ▼
       最终 .docx + 检查结果与未决项
```

### Markdown 和 R Markdown

优先保留引用键和原文献库，通过 CSL 生成引用。Rmd 会实际执行 `rmarkdown::render()`；运行前检查代码块及依赖。稿件副本只增加必要配置与准备步骤，正文内容保持不变。

### 已有 Word

先检查活动引文字段、普通文本引用、脚注、表格、评论和修订。有 Zotero／EndNote 字段时优先使用相应引擎。复杂 Word 的处理路线以保真为前提，保留活动字段的能力取决于当前应用和工具环境。

### Agent 逐条修订

当 CSL 难以表达少量例外、书目无法可靠结构化，或目标引擎确有兼容限制时，建立逐条台账：

- 原始引用及其位置；
- 对应的文献 ID；
- 适用规则和 PDF 证据页；
- 目标文本或带斜体等属性的片段；
- 执行状态与复核结果。

Agent 负责判断，确定性脚本负责受控写入。修改限于明确的引用范围。受保护字段或复杂结构无法安全处理时，会保留该项并说明限制。

## 自动检查与复核

| 检查层 | 主要检查 |
| --- | --- |
| 规则 | PDF 证据、适用范围、独立预期及未明确规定的部分 |
| 引用映射 | 源稿引用键或编号、正文与文末的对应、作者年份和定位页 |
| 编译 | 目标引擎实际运行结果、未解释警告、CSL schema 校验 |
| Word 结构 | ZIP／XML 完整性、内部关系、参考文献条目数及字段保护 |
| 修改范围 | 段落是否只按已声明的计划变化，未触碰的文档部件是否保持一致 |
| 格式 | 预期引用文本、标点、斜体，以及实际出现的特殊文献类型 |
| 视觉 | 中文缺字、悬挂缩进、标题、表格跨页、脚注、长网址和末页 |

逐条修订的项目需要全量复核。脚本只给出机械检查的 `pass`／`fail`；最终状态结合引用台账和视觉检查确定：

| 状态 | 含义 |
| --- | --- |
| `verified` | 机械检查、引用复核和视觉检查均已完成，无待处理引用 |
| `verified_with_data_gaps` | 格式与保真检查通过，但原始书目信息仍有明确缺口 |
| `needs_review` | 存在未处理引用、映射歧义、失败或未完成的检查 |

编译成功和零警告只构成部分验证证据。作者、年份或编号是否仍指向同一来源，需要结合原稿与文献数据核对。

## 辅助脚本

以下命令在技能目录下运行。AI Agent 可根据任务调用，无需使用者手动执行全部命令。

### 文献库适配

```bash
Rscript scripts/prepare_bibliography.R references.bib references.json
```

为配套的双语 CSL 启用中文分流、拼音排序和波浪号页码：

```bash
Rscript scripts/prepare_bibliography.R references.bib references.json --bilingual
```

此模式需要与相应 CSL 配合：在派生 JSON 中用 `original-title` 标记中文，用 `citation-label` 保存排序键。如果字段已被占用，脚本会停止，避免覆盖原数据。启用前应确认当前 PDF 确实要求这些规则。

适配器保留原始 `.bib`，并输出数据适配说明；不会自动猜测个人姓名、文献类型或缺失年份。

### Rmd 编译为 Word

```bash
Rscript scripts/render_word.R manuscript.rmd final.docx
```

可指定 Word 参考模板和 Pandoc 路径：

```bash
Rscript scripts/render_word.R manuscript.rmd final.docx reference.docx /path/to/pandoc
```

Rmd 的 bibliography、CSL 和所需准备步骤应先配置好。脚本执行实际 knit，未知代码块需要先检查。

### Word 清单与受控修订

```bash
python scripts/docx_audit.py inventory manuscript.docx --output inventory.json
python scripts/docx_audit.py apply manuscript.docx plan.json candidate.docx
```

修订计划需要匹配原稿 SHA-256、段落位置和旧文本，并附引用 ID 与规则证据。脚本支持跨普通 run 的文本修改及整条普通参考文献的富文本重建；超链接、字段、书签、评论锚点、修订和控件等复杂段落会被拒绝。

### 输出检查

```bash
python scripts/docx_audit.py check candidate.docx \
  --before manuscript.docx \
  --plan plan.json \
  --checks checks.json \
  --report audit.json
```

由 Markdown／Rmd 直接生成 Word 时，可省略 `--before` 和 `--plan`，同时另做源稿 AST 与输出引用的对应检查。

计划和检查配置的结构见 [逐条修订与复核](references/fallback-and-review.md)。

## 依赖

| 组件 | 使用场景 |
| --- | --- |
| 能读取技能和操作本地文件的 AI Agent | 理解 PDF 规则、选择路线、编写 CSL 和复核 |
| Python 3 与 `lxml` | Word 清单、受控修订和自动检查 |
| Pandoc | Markdown 转 Word，以及 BibTeX／CSL 引用处理 |
| R、`rmarkdown`、`knitr` | R Markdown knit |
| R 包 `jsonlite` | 文献库适配 |
| R 包 `stringi` | 可选的中文检测及拼音排序 |
| PDF 渲染／提取工具 | 读取格式示例，检查扫描页 |
| Word 渲染工具与所需字体 | 逐页排版检查；在 Codex 中遵循可用文档技能的运行时要求 |
| CSL schema 校验工具 | 校验目标样式；不可用时将该检查列为未完成 |

按所选路线准备依赖。在提供 bundled runtime 的环境中，优先使用该运行时；RStudio 或 Quarto 可提供 Pandoc。

## 文件结构

```text
format-citations-to-word/
├── README.md
├── SKILL.md                         # Agent 执行入口
├── agents/
│   └── openai.yaml                  # 技能展示信息
├── references/
│   ├── compilation.md               # 引擎兼容、编译及字体处理
│   └── fallback-and-review.md       # 修订计划与复核协议
└── scripts/
    ├── prepare_bibliography.R       # 生成派生文献数据
    ├── render_word.R                # 实际执行 Rmd → Word
    └── docx_audit.py                # 清单、受控修订与机械检查
```

每次任务所需的 CSL 根据 PDF 示例生成或修改。

## 常见问题

### CSL 可以输出 `～` 页码吗？

可以。需要区分 CSL 的页码分隔符与 BibTeX 的语法：BibTeX 中的 `~` 表示不换行空格。流程会先检查读取后的数据，再按当前规范和目标引擎选择转换方式。

### Zotero 可用的 CSL 能直接用于 Pandoc 吗？

需要实测。部分多语言扩展在两个引擎中的支持不同，可能需要单布局样式和派生元数据配合。配套依赖会在交付说明中列明。

### 没有 `.bib` 文件能处理吗？

可以先从 Word 引文字段或普通参考文献条目中读取信息。若无法确定正文引用与文末条目的关系，会列出具体需要补充的材料。

### 输出仍能用 Zotero／EndNote 刷新吗？

取决于输入字段和处理路线。经 Pandoc 生成的引用通常是静态文本。已有活动字段优先保留，任何刷新限制或静态化选择都应明确说明。

### 能否顺便补齐缺失书目信息？

可单独核实并记录修正依据。格式转换本身不会推测缺失页码、年份或作者。

## 验证情况

已用包含 95 条文献、正文引用其中 36 条的实际稿件测试文献适配和 Rmd → Word 编译，并测试跨 run 修订、斜体条目重建、正文误改检测、过期哈希拒绝、活动字段保护和元数据冲突拦截。

这些测试覆盖已验证的路线。新刊物规则、复杂 Word 结构和其他软件环境仍需按本技能重新检查。
