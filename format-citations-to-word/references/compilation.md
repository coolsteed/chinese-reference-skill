# 编译与兼容性

## 格式与数据分开

CSL 定义排版，Python/R 做可解释的数据解析与兼容性适配。不把当前稿件的人名、期刊或年份固化进通用代码。

- 记录 Zotero/citeproc-js 或 Pandoc/citeproc 的实际版本。`layout locale`、`if locale`、`default-locale-sort` 不能视为普适语法。必要时分开维护 Zotero 和 Pandoc 版本，并说明依赖。
- CSL 可以定义 `page-range-delimiter` 为 `～`。BibTeX 中 `~` 是不换行空格；先检查派生 JSON，再测试范围符号，不把解析失败误诊为 CSL 不支持。必要时仅在派生中文 page 值预排范围符号，英文仍由 CSL 控制。
- 某些 Pandoc 读取器需 `langid` 才传递 CSL language。实际导出 JSON 验证，不只看源 `.bib`。
- 文档 `lang` 可能覆盖 CSL 默认术语环境。逐项测试 and、et al.、译编者、月份、引号内句号和页码符号；不要把所有中文稿都不设 lang 当普遍规则。
- 中文排序需经测试的排序引擎或拼音键；Unicode 顺序不等于拼音。不能重新排列作者本身的顺序。
- literal 姓名不一定是个人，也可能是机构；不可批量按空格拆分。`and others` 不代表已知完整作者名单。已接收/待刊不是年份。

## 可选适配器

```text
Rscript prepare_bibliography.R INPUT.bib OUTPUT.json [--bilingual] [--pandoc=/path/to/pandoc]
```

默认只在临时副本中适配 language/langid 和 pages 里的 `~`，再导出 JSON。两种语言字段共存时保留并发警告，要求检查实际结果。

`--bilingual` 额外：中文 `original-title="zh-CN"`，所有条目 `citation-label` 为作者排序键；冲突即停止。中文页码转 `～`。该模式仅适用于当前规范需要波浪号、当前 CSL 用 `if variable="original-title"` 分流并按 citation-label 排序的情况。两字段是内部约定，不应打印；现有字段被占用时换约定，不能覆盖。

适配器不修改作者、类型、日期事实，也不从 ID 猜测待刊状态。日期解析丢失的文字状态单独提取到 status 并核对原稿。缺语言时中文标题推断会发警告；译著以实际引用版本语言为准。

## Rmd

找到实际 Pandoc executable，必要时只给本进程设置 `RSTUDIO_PANDOC`，不改全局配置。脚本 source 只定义函数；可在稿件副本的隐藏 setup 块按需调用：

```r
source("prepare_bibliography.R", encoding = "UTF-8")
prepare_bibliography("references.bib", "references.generated.json", bilingual = TRUE)
```

YAML 指向派生 bibliography 和当前 CSL；真实执行 `render_word.R` 或等价 `rmarkdown::render()`，保存日志。先检查未知代码块及依赖，格式任务不授权执行正文中任意命令。

## MD

先解析 Cite AST（排除注释、代码块），用其统计覆盖；再运行：

```text
pandoc manuscript.md --citeproc --bibliography references.json --csl target.csl --reference-doc template.docx -o final.docx
```

无模板可省略 reference-doc。输出一般为静态引文。

## Word

inventory 报告各 part 的段落、样式、字段和保护标记，仅作定位而非书目事实解析。对应应用不可用时不要静默 flatten 字段。往返 Pandoc 可能丢评论、修订、公式和控件，须以保真证据决定是否可用。

## 字体与渲染

按可用文档技能使用 `render_docx.py` 和其要求的 bundled LibreOffice。不要失败后静默切换用户桌面应用。

若中文在 PNG 中空白但 XML 尚有汉字，检查嵌入字体、实际字体文件和 fontconfig 搜索目录。可在任务 work/ 建只读系统字体目录的配置，仅给渲染子进程传 `FONTCONFIG_FILE` 和必要的 `SAL_FONTPATH_PRIVATE`；不写系统字体目录或全局环境。字体名应来自实际已安装字体，保留粗体、斜体和正文样式。

表格宽度、重复表头、行不跨页、标题与下段同页属于 Word 排版，不由 CSL 代管；修改后检查受影响及重排的其他页面。
