# BibTeX adaptation for a deliberately paired CSL. Never modifies INPUT.bib.
find_citation_pandoc <- function(pandoc = NULL) {
  candidates <- c(pandoc, file.path(Sys.getenv("RSTUDIO_PANDOC"), "pandoc"),
                  unname(Sys.which("pandoc")),
                  "/Applications/quarto/bin/tools/aarch64/pandoc",
                  "/Applications/quarto/bin/tools/x86_64/pandoc")
  if (requireNamespace("rmarkdown", quietly = TRUE)) {
    found <- rmarkdown::find_pandoc()
    if (!is.null(found$dir)) candidates <- c(candidates, file.path(found$dir, "pandoc"))
  }
  for (p in candidates) if (!is.na(p) && nzchar(p) && file.exists(p) && !dir.exists(p)) return(normalizePath(p))
  stop("Pandoc executable not found; pass --pandoc=/absolute/path/to/pandoc")
}

prepare_bibliography <- function(input, output, bilingual = FALSE, pandoc = NULL) {
  if (!requireNamespace("jsonlite", quietly = TRUE)) stop("R package jsonlite is required")
  if (bilingual && !requireNamespace("stringi", quietly = TRUE)) stop("R package stringi is required for bilingual sorting")
  if (normalizePath(input) == normalizePath(output, mustWork = FALSE)) stop("Output must not overwrite the input")
  raw <- paste(readLines(input, encoding = "UTF-8", warn = FALSE), collapse = "\n")
  lines <- strsplit(raw, "\n", fixed = TRUE)[[1]]
  begins <- which(grepl("^\\s*@[A-Za-z]+\\s*[{(]", lines))
  boundaries <- c(begins, length(lines) + 1L)
  notes <- character()
  if (length(begins)) for (i in seq_along(begins)) {
    idx <- seq.int(boundaries[i], boundaries[i + 1L] - 1L)
    block <- paste(lines[idx], collapse = "\n")
    has_language <- grepl("(?i)\\blanguage\\s*=", block, perl = TRUE)
    has_langid <- grepl("(?i)\\blangid\\s*=", block, perl = TRUE)
    if (has_language && has_langid) {
      notes <- c(notes, paste("Both language and langid in entry beginning on line", begins[i], "(langid retained; inspect result)"))
    } else if (has_language) {
      # Same line count; preserves every original field apart from this key.
      lines[idx] <- gsub("(?i)\\blanguage(\\s*=)", "langid\\1", lines[idx], perl = TRUE)
    }
  }
  normalized <- paste(lines, collapse = "\n")
  pages <- gregexpr("(?is)\\bpages\\s*=\\s*\\{[^}]*\\}", normalized, perl = TRUE)
  matches <- regmatches(normalized, pages)
  regmatches(normalized, pages) <- lapply(matches, function(v) gsub("[~～]", "--", v))
  tmpbib <- tempfile(fileext = ".bib"); tmpjson <- tempfile(fileext = ".json")
  on.exit(unlink(c(tmpbib, tmpjson)), add = TRUE)
  writeLines(normalized, tmpbib, useBytes = TRUE)
  executable <- find_citation_pandoc(pandoc)
  status <- system2(executable, c(shQuote(tmpbib), "--from=biblatex", "--to=csljson", "--output", shQuote(tmpjson)))
  if (!identical(status, 0L)) stop("Pandoc bibliography parsing failed")
  refs <- jsonlite::fromJSON(tmpjson, simplifyVector = FALSE)
  for (i in seq_along(refs)) {
    ref <- refs[[i]]
    if (bilingual) {
      if (!is.null(ref[["original-title"]]) || !is.null(ref[["citation-label"]])) {
        stop("Reserved field collision in ", ref$id, "; choose another explicit metadata convention")
      }
      lang <- if (is.null(ref$language)) "" else tolower(ref$language)
      chinese <- startsWith(lang, "zh")
      if (!nzchar(lang)) {
        title <- if (is.null(ref$title)) "" else ref$title
        chinese <- isTRUE(stringi::stri_detect_regex(title, "\\p{Han}"))
        notes <- c(notes, paste(ref$id, "has no language; title-script inference used"))
      }
      if (chinese) {
        ref[["original-title"]] <- "zh-CN"
        if (!is.null(ref$page)) ref$page <- gsub("[-–—~～]+", "～", ref$page)
      }
      if (length(ref$author)) {
        key <- vapply(ref$author, function(a) {
          value <- if (!is.null(a$literal)) a$literal else paste(a$family, a$given)
          if (chinese) value <- stringi::stri_trans_general(value, "Han-Latin; Latin-ASCII")
          tolower(value)
        }, character(1))
        ref[["citation-label"]] <- paste(key, collapse = " | ")
      } else ref[["citation-label"]] <- tolower(if (is.null(ref$title)) ref$id else ref$title)
    }
    # Date and author anomalies are evidence gaps; never guess replacements.
    if (is.null(ref$issued[["date-parts"]]) || !length(ref$issued[["date-parts"]])) {
      notes <- c(notes, paste(ref$id, "has no parsed numeric date; inspect original date/status"))
    }
    if (any(vapply(ref$author, function(a) identical(a$literal, "others"), logical(1)))) {
      notes <- c(notes, paste(ref$id, "has a truncated author list containing others"))
    }
    refs[[i]] <- ref
  }
  dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
  jsonlite::write_json(refs, output, auto_unbox = TRUE, pretty = TRUE, null = "null")
  report <- list(entries = length(refs), bilingual = bilingual, notes = unique(notes),
                 source_modified = FALSE, reserved_fields = if (bilingual) c("original-title", "citation-label") else character())
  jsonlite::write_json(report, paste0(output, ".adaptation.json"), auto_unbox = TRUE, pretty = TRUE)
  if (length(notes)) message(paste(unique(notes), collapse = "\n"))
  invisible(refs)
}

if (sys.nframe() == 0L) {
  args <- commandArgs(trailingOnly = TRUE)
  if (length(args) < 2L) stop("Usage: Rscript prepare_bibliography.R INPUT.bib OUTPUT.json [--bilingual] [--pandoc=/path]")
  opts <- args[-c(1, 2)]
  if (any(!grepl("^(--bilingual|--pandoc=.+)$", opts))) stop("Unknown option")
  pandoc_arg <- sub("^--pandoc=", "", opts[startsWith(opts, "--pandoc=")])
  prepare_bibliography(args[1], args[2], "--bilingual" %in% opts,
                       if (length(pandoc_arg)) pandoc_arg[1] else NULL)
}
