"""Configuration constants for the SimpleBook normalizer."""

# Chunking parameters
MAX_CHUNK_CHARS = 1200
MAX_CHUNK_ADDITION_CHARS = 300
MIN_PARAGRAPH_CHARS = 80
LARGE_PARAGRAPH_CHARS = 400

# Chapter detection patterns
CHAPTER_PATTERNS = ["chapter", "ch.", "book", "part"]

ROMAN_NUMERALS = [
  "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
  "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
  "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi", "xxvii", "xxviii", "xxix", "xxx",
  "xxxi", "xxxii", "xxxiii", "xxxiv", "xxxv", "xxxvi", "xxxvii", "xxxviii", "xxxix", "xl",
  "xli", "xlii", "xliii", "xliv", "xlv", "xlvi", "xlvii", "xlviii", "xlix", "l",
]

FRONT_MATTER_KEYWORDS = [
  "titlepage", "cover", "copyright", "imprint", "dedication",
  "preface", "foreword", "introduction", "prologue",
  "illustration", "illustrations",
]

BACK_MATTER_KEYWORDS = [
  "acknowledgments", "acknowledgements", "notes", "endnotes",
  "epilogue", "afterword", "colophon", "about the author", "about",
]

NON_CHAPTER_KEYWORDS = FRONT_MATTER_KEYWORDS + BACK_MATTER_KEYWORDS + ["toc", "contents"]

# Quote normalization (unused but kept for future normalization passes)
OPENING_QUOTES = ['"', '"', "'", "„"]
CLOSING_QUOTES = ['"', '"', "'", '"']
GUILLEMET_OPEN = "<<"
GUILLEMET_CLOSE = ">>"

# HTML elements to strip during text extraction
STRIP_ELEMENTS = ["script", "style", "nav"]

# Asset media types (unused for now)
IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/svg+xml"]
STYLESHEET_TYPES = ["text/css"]
FONT_TYPES = [
  "font/ttf", "font/otf", "font/woff", "font/woff2",
  "application/font-woff", "application/font-woff2",
  "application/vnd.ms-opentype", "application/x-font-ttf",
  "application/x-font-otf",
]
