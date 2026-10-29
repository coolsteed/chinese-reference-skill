# Actual knitr/rmarkdown Word render. Inspect unknown Rmd code before invoking.
# Usage: Rscript render_word.R INPUT.rmd OUTPUT.docx [REFERENCE.docx] [PANDOC]
render_citation_word <- function(input, output, reference = NULL, pandoc = NULL) {
  if (!requireNamespace("rmarkdown", quietly = TRUE) || !requireNamespace("knitr", quietly = TRUE)) {
    stop("R packages rmarkdown and knitr are required")
  }
  input <- normalizePath(input)
  dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
  output <- file.path(normalizePath(dirname(output)), basename(output))
  if (!is.null(reference)) reference <- normalizePath(reference)
  if (!is.null(pandoc)) {
    pandoc <- normalizePath(pandoc)
    Sys.setenv(RSTUDIO_PANDOC = if (dir.exists(pandoc)) pandoc else dirname(pandoc))
  } else if (!rmarkdown::pandoc_available()) {
    for (p in c("/Applications/quarto/bin/tools/aarch64", "/Applications/quarto/bin/tools/x86_64")) {
      if (file.exists(file.path(p, "pandoc"))) { Sys.setenv(RSTUDIO_PANDOC = p); break }
    }
  }
  if (!rmarkdown::pandoc_available()) stop("Pandoc unavailable; pass its path as the fourth argument")
  format <- if (is.null(reference)) rmarkdown::word_document() else rmarkdown::word_document(reference_docx = reference)
  rmarkdown::render(input, output_format = format, output_file = basename(output),
                    output_dir = dirname(output), knit_root_dir = dirname(input), quiet = FALSE)
  if (!file.exists(output)) stop("Render finished without expected Word output")
  invisible(output)
}
if (sys.nframe() == 0L) {
  a <- commandArgs(trailingOnly = TRUE)
  if (length(a) < 2L || length(a) > 4L) stop("Usage: Rscript render_word.R INPUT.rmd OUTPUT.docx [REFERENCE.docx] [PANDOC]")
  render_citation_word(a[1], a[2], if (length(a) >= 3L) a[3] else NULL, if (length(a) >= 4L) a[4] else NULL)
}
