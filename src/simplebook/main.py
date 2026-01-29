"""Core normalization pipeline and data model for SimpleBook."""

import json
import unicodedata
from pathlib import Path

from ebooklib import epub  # type: ignore[import-untyped]
from bs4 import BeautifulSoup, Comment  # type: ignore[import-untyped]

# Rule parameters (chunking/normalization heuristics)
# Soft-limit constants (deprecated in favor of size class sum).
SOFT_MAX_CHUNK_WORDS = 300
MAX_CHUNK_ADDITION_WORDS = 80
LARGE_PARAGRAPH_WORDS = 120
SOFT_WORD_THRESHOLD = 10
SOFT_WORD_MAX = 500

# Element size breakpoints (word counts)
ELEM_BP_S = 10
ELEM_BP_M = 30
ELEM_BP_L = 100
ELEM_BP_XL = 250

# Chunk size breakpoints (word counts)
CHUNK_BP_S = 50
CHUNK_BP_M = 100
CHUNK_BP_L = 200
CHUNK_BP_XL = 300

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

NON_CHAPTER_KEYWORDS = FRONT_MATTER_KEYWORDS + \
    BACK_MATTER_KEYWORDS + ["toc", "contents"]

# Quote normalization (unused but kept for future normalization passes)
OPENING_QUOTES = ['"', '"', "'", "„"]
CLOSING_QUOTES = ['"', '"', "'", '"']
GUILLEMET_OPEN = "<<"
GUILLEMET_CLOSE = ">>"

# HTML elements to strip during text extraction
STRIP_ELEMENTS = ["script", "style", "nav"]


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

DOUBLE_QUOTE_CHARS = {'"', "“", "”", "„"}


def _normalize_quotes(text: str) -> str:
    """Normalize straight/curly double quotes to << >> pairs."""
    if not text:
        return text
    result: list[str] = []
    open_quote = True
    for ch in text:
        if ch in DOUBLE_QUOTE_CHARS:
            result.append("<<" if open_quote else ">>")
            open_quote = not open_quote
        else:
            result.append(ch)
    return "".join(result)


def _to_ascii(text: str) -> str:
    """Transliterate text to ASCII and normalize dashes."""
    if not text:
        return text
    text = text.replace("—", "--").replace("–", "--")
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _clean_text(raw: str) -> str:
    """Normalize whitespace, quotes, and ASCII in a raw text string."""
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _normalize_quotes(text)
    text = _to_ascii(text)
    text = " ".join(text.split())
    return text.strip()


def _ordered_items(book: epub.EpubBook):
    """Return spine-ordered document items from an EbookLib book."""
    item_document = getattr(epub, "ITEM_DOCUMENT", 9)
    items_by_id = {
        item.get_id(): item for item in book.get_items_of_type(item_document)}
    ordered = []
    for item_id, _linear in book.spine:
        item = items_by_id.get(item_id)
        if item:
            ordered.append(item)
    return ordered


def _classify_label_type(label: str | None) -> str:
    """Classify a label as chapter/front/back/other by heuristics."""
    lowered = (label or "").strip().lower()
    if not lowered:
        return "other"
    if any(key in lowered for key in FRONT_MATTER_KEYWORDS):
        return "front"
    if any(key in lowered for key in BACK_MATTER_KEYWORDS):
        return "back"
    if any(key in lowered for key in ["toc", "contents"]):
        return "front"
    if _heading_matches_chapter(lowered):
        return "chapter"
    return "other"


def _heading_matches_chapter(text: str) -> bool:
    """Return True if heading text looks like a chapter label."""
    lowered = text.strip().lower()
    if not lowered:
        return False
    if any(pat in lowered for pat in CHAPTER_PATTERNS):
        return True
    tokens = lowered.replace(".", " ").replace("-", " ").split()
    if any(tok in ROMAN_NUMERALS for tok in tokens):
        return True
    if any(char.isdigit() for char in lowered):
        return True
    return False


def _extract_heading_texts(soup: BeautifulSoup) -> list[str]:
    """Collect heading-like text nodes used to name a chapter."""
    texts: list[str] = []
    seen: set[str] = set()

    def _add(text: str) -> None:
        """Add a cleaned heading text if it is unique."""
        cleaned = _clean_text(text)
        if cleaned and cleaned not in seen:
            texts.append(cleaned)
            seen.add(cleaned)

    if soup.title is not None:
        _add(soup.title.get_text(" ", strip=True))

    root = soup.body if soup.body is not None else soup
    for el in root.descendants:
        name = getattr(el, "name", None)
        if not name:
            continue

        if name == "p":
            text = _clean_text(el.get_text("\n"))
            if not text:
                continue
            attrs = el.attrs if hasattr(el, "attrs") else {}
            classes = " ".join(el.get("class", [])) if hasattr(
                el, "get") else ""
            epub_type = (attrs.get("epub:type") or "").lower()
            is_heading_p = any(key in epub_type for key in [
                               "title", "subtitle", "heading"])
            is_heading_p = is_heading_p or any(
                key in classes.lower() for key in ["title", "subtitle", "chapter", "heading"]
            )
            if is_heading_p:
                _add(el.get_text(" ", strip=True))
                continue
            break

        classes = " ".join(el.get("class", [])) if hasattr(el, "get") else ""
        is_heading = name in {"h1", "h2", "h3", "h4", "h5", "h6", "subtitle"}
        is_heading = is_heading or (
            hasattr(el, "get") and el.get("role") == "heading")
        is_heading = is_heading or any(
            key in classes.lower() for key in ["title", "subtitle", "chapter", "heading"]
        )

        if is_heading:
            _add(el.get_text(" ", strip=True))

    return texts


def _extract_heading_label(soup: BeautifulSoup) -> str | None:
    """Combine heading fragments into a single chapter label."""
    texts = _extract_heading_texts(soup)
    if not texts:
        return None
    label = ""
    for text in texts:
        if not label:
            label = text
            continue
        if text.lower() in label.lower():
            continue
        label = f"{label} - {text}"
    return label or None


ELEMENT_TAG_TYPES = {
    "p": "paragraph",
    "blockquote": "blockquote",
    "li": "list_item",
    "dt": "definition_term",
    "dd": "definition_desc",
    "cite": "cite",
    "figcaption": "caption",
    "caption": "caption",
    "table": "table",
}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
TABLE_CELL_TAGS = {"td", "th"}
CONTAINER_TAGS = {
    "div",
    "section",
    "article",
    "header",
    "footer",
    "aside",
    "main",
    "figure",
    "ul",
    "ol",
    "dl",
    "tbody",
    "thead",
    "tfoot",
    "tr",
}

ALLOWED_TEXT_TAGS = set(ELEMENT_TAG_TYPES.keys()
                        ) | HEADING_TAGS | TABLE_CELL_TAGS


def _html_to_soup(html: bytes | str) -> BeautifulSoup:
    """Parse HTML into BeautifulSoup and remove stripped elements."""
    if isinstance(html, (bytes, bytearray)):
        html = html.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIP_ELEMENTS):
        tag.decompose()
    return soup


def _assert_supported_text(root: BeautifulSoup) -> None:
    """Raise if text appears outside the supported tag set."""
    for text in root.find_all(string=True):
        if not text or not text.strip():
            continue
        if isinstance(text, Comment):
            continue
        if text.find_parent(ALLOWED_TEXT_TAGS):
            continue
        parent = text.parent
        parent_name = parent.name if parent else "unknown"
        snippet = " ".join(str(text).split())
        if len(snippet) > 120:
            snippet = f"{snippet[:120]}..."
        raise NotImplementedError(
            f"Unsupported text outside allowed tags (parent <{parent_name}>): {snippet}"
        )


def _blockquote_text(tag) -> str:
    """Extract blockquote text, excluding nested cite content."""
    parts: list[str] = []
    for text in tag.find_all(string=True):
        if not text or not text.strip():
            continue
        if isinstance(text, Comment):
            continue
        if text.find_parent("cite"):
            continue
        parts.append(str(text))
    return _clean_text("\n".join(parts))


def _table_rows(tag) -> list[list[str]]:
    """Extract table rows as a list of cleaned cell strings."""
    rows: list[list[str]] = []
    for tr in tag.find_all("tr"):
        cells = []
        for cell in tr.find_all(list(TABLE_CELL_TAGS)):
            cell_text = _clean_text(cell.get_text("\n"))
            cells.append(cell_text)
        if cells:
            rows.append(cells)
    return rows


def _manual_text_from_html(raw_html: str) -> str:
    """Convert inline emphasis tags to markers and normalize text."""
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup.find_all(["em", "i"]):
        tag.replace_with(f"///{tag.get_text()}///")
    for tag in soup.find_all(["strong", "b"]):
        tag.replace_with(f"**{tag.get_text()}**")
    text = soup.get_text("\n")
    return _clean_text(text)


def _render_markdown(
    element_type: str,
    text: str | None,
    rows: list[list[str]] | None = None,
    heading_level: int | None = None,
) -> str | None:
    """Render a lightweight Markdown representation for an element."""
    if text is None and not rows:
        return None
    base_text = text or ""
    if element_type == "heading":
        level = heading_level or 1
        prefix = "#" * max(level, 1)
        return f"{prefix} {base_text}".strip()
    if element_type == "blockquote":
        if not base_text:
            return ""
        return "\n".join(
            f"> {line}" if line else ">" for line in base_text.splitlines()
        )
    if element_type == "list_item":
        return f"- {base_text}".strip()
    if element_type == "table":
        if not rows:
            return ""
        return "\n".join(" | ".join(row) for row in rows)
    return base_text


def _extract_elements(soup: BeautifulSoup) -> list["Element"]:
    """Extract typed Elements from HTML soup in document order."""
    root = soup.body if soup.body is not None else soup
    _assert_supported_text(root)
    elements: list[Element] = []
    saw_title = False

    def tag_path(node) -> str:
        """Return a slash-delimited tag path for a node."""
        parts: list[str] = []
        cur = node
        while cur is not None:
            name = getattr(cur, "name", None)
            if not name:
                break
            parts.append(name.lower())
            cur = cur.parent
            if cur == root:
                root_name = getattr(cur, "name", None)
                if root_name:
                    parts.append(root_name.lower())
                break
        return "/".join(reversed(parts))

    def append_element(
        element_type: str,
        text: str | None = None,
        rows: list[list[str]] | None = None,
        raw_html: str | None = None,
        path: str | None = None,
        role: str | None = None,
        heading_level: int | None = None,
        meta: dict | None = None,
    ) -> None:
        """Construct and append an Element with rendered markdown."""
        markdown = _render_markdown(
            element_type,
            text,
            rows=rows,
            heading_level=heading_level,
        )
        elements.append(
            Element(
                element_type,
                text=text,
                rows=rows,
                raw_html=raw_html,
                markdown=markdown,
                path=path,
                role=role,
                meta=meta,
            )
        )

    def walk(node) -> None:
        """Walk the DOM and emit elements in document order."""
        nonlocal saw_title
        for child in node.children:
            if not hasattr(child, "name") or child.name is None:
                continue
            name = child.name.lower()
            if name in STRIP_ELEMENTS:
                continue
            if name in CONTAINER_TAGS:
                walk(child)
                continue
            raw_html = str(child)
            if name in HEADING_TAGS:
                text = _clean_text(child.get_text("\n"))
                if text:
                    level = int(name[1]) if len(
                        name) > 1 and name[1].isdigit() else None
                    role = "title" if not saw_title else "heading"
                    saw_title = True if role == "title" else saw_title
                    meta = {"level": level} if level is not None else None
                    append_element(
                        "heading",
                        text=text,
                        raw_html=raw_html,
                        path=tag_path(child),
                        role=role,
                        heading_level=level,
                        meta=meta,
                    )
                continue
            if name == "blockquote":
                text = _blockquote_text(child)
                if text:
                    append_element(
                        "blockquote",
                        text=text,
                        raw_html=raw_html,
                        path=tag_path(child),
                        role="body",
                    )
                for cite in child.find_all("cite"):
                    cite_text = _clean_text(cite.get_text("\n"))
                    if cite_text:
                        append_element(
                            "cite",
                            text=cite_text,
                            raw_html=str(cite),
                            path=tag_path(cite),
                            role="comment",
                        )
                continue
            if name == "table":
                caption = child.find("caption") or child.find("figcaption")
                if caption is not None:
                    caption_text = _clean_text(caption.get_text("\n"))
                    if caption_text:
                        append_element(
                            "caption",
                            text=caption_text,
                            raw_html=str(caption),
                            path=tag_path(caption),
                            role="comment",
                        )
                rows = _table_rows(child)
                if rows:
                    append_element(
                        "table",
                        rows=rows,
                        raw_html=raw_html,
                        path=tag_path(child),
                        role="body",
                    )
                continue
            if name in ELEMENT_TAG_TYPES:
                text = _clean_text(child.get_text("\n"))
                if text:
                    element_type = ELEMENT_TAG_TYPES[name]
                    role = "comment" if element_type in {
                        "caption", "cite"} else "body"
                    append_element(
                        element_type,
                        text=text,
                        raw_html=raw_html,
                        path=tag_path(child),
                        role=role,
                    )
                continue
            walk(child)

    walk(root)
    return elements


def _classify_html_item(html: bytes | str) -> tuple[str | None, str]:
    """Classify an HTML spine item as chapter/front/back/other."""
    soup = _html_to_soup(html)

    name = _extract_heading_label(soup)
    label_type = _classify_label_type(name)

    # Fallback: element count threshold.
    elements = _extract_elements(soup)
    element_count = sum(1 for el in elements if el.text_length() > 0)

    if label_type in {"front", "back"}:
        return name, label_type
    if label_type == "chapter":
        return name, "chapter"
    if element_count >= 10:
        return name, "chapter"
    return name, "other"


# ============================================================================
# DATA CLASSES
# ============================================================================

class Metadata:
    """Minimal book metadata."""

    def __init__(self) -> None:
        """Initialize empty metadata fields."""
        self.title = ""
        self.author = ""
        self.language = ""
        self.isbn = ""
        self.uuid = ""


class Node:
    """Prototype node to enforce delegation."""

    def __init__(self) -> None:
        """Initialize an empty child list."""
        self.children = []

    def validate(self) -> None:
        """Validate this node and its children."""
        for child in self.children:
            child.validate()

    def repair(self) -> None:
        """Repair this node and its children."""
        for child in self.children:
            child.repair()

    def serialize(self):
        """Serialize children into a list representation."""
        return [child.serialize() for child in self.children]

    def to_string(self) -> str:
        """Render children as a concatenated string."""
        return "\n".join(child.to_string() for child in self.children)

    def normalize(self) -> None:
        """Normalize this node and its children."""
        for child in self.children:
            child.normalize()


class Element(Node):
    """Typed content element extracted from HTML."""

    def __init__(
        self,
        element_type: str,
        text: str | None = None,
        rows: list[list[str]] | None = None,
        raw_html: str | None = None,
        markdown: str | None = None,
        path: str | None = None,
        role: str | None = None,
        meta: dict | None = None,
    ) -> None:
        """Create an element with optional text, rows, and metadata."""
        super().__init__()
        self.type = element_type
        self.text = text
        self.rows = rows
        self.raw_html = raw_html
        self.markdown = markdown
        self.path = path or ""
        self.role = role
        self.meta = meta or {}

    def validate(self) -> None:
        """Ensure element fields are typed as strings where expected."""
        if self.text is not None and not isinstance(self.text, str):
            self.text = str(self.text)
        if self.raw_html is not None and not isinstance(self.raw_html, str):
            self.raw_html = str(self.raw_html)
        if self.markdown is not None and not isinstance(self.markdown, str):
            self.markdown = str(self.markdown)
        if self.role is not None and not isinstance(self.role, str):
            self.role = str(self.role)

    def repair(self) -> None:
        """Normalize text, rows, and markdown for this element."""
        if self.text is None:
            self.text = None
        else:
            if self.raw_html:
                self.text = _manual_text_from_html(self.raw_html)
            else:
                self.text = _clean_text(self.text)
        if self.rows:
            self.rows = [[_clean_text(cell) for cell in row]
                         for row in self.rows]
        self.markdown = _render_markdown(
            self.type,
            self.text,
            rows=self.rows,
            heading_level=self._heading_level(),
        )

    def text_length(self) -> int:
        """Return character length across text or table rows."""
        if self.text:
            return len(self.text)
        if self.rows:
            return sum(len(cell) for row in self.rows for cell in row)
        return 0

    def word_count(self) -> int:
        """Return word count of the element's normalized string."""
        text = self.to_string()
        if not text:
            return 0
        return len(text.split())

    def is_small(self) -> bool:
        """True if element is short enough to be merged past soft limits."""
        return self.word_count() <= SOFT_WORD_THRESHOLD

    def is_large_element(self) -> bool:
        """True if element should be isolated as its own chunk."""
        return self.word_count() >= LARGE_PARAGRAPH_WORDS

    def is_small_size(self) -> bool:
        """True if element word count is below the small breakpoint."""
        return self.word_count() < ELEM_BP_S

    def is_medium(self) -> bool:
        """True if element word count is below the medium breakpoint."""
        return self.word_count() < ELEM_BP_M

    def is_large(self) -> bool:
        """True if element word count is at or above the large breakpoint."""
        return self.word_count() >= ELEM_BP_L

    def size_label(self) -> str:
        """Return size label (XS/S/M/L/XL) based on word count."""
        wc = self.word_count()
        if wc < ELEM_BP_S:
            return "XS"
        if wc < ELEM_BP_M:
            return "S"
        if wc < ELEM_BP_L:
            return "M"
        if wc < ELEM_BP_XL:
            return "L"
        return "XL"

    def size_class(self) -> int:
        """Return size class as an integer for threshold math."""
        wc = self.word_count()
        if wc < ELEM_BP_S:
            return 0
        if wc < ELEM_BP_M:
            return 1
        if wc < ELEM_BP_L:
            return 2
        if wc < ELEM_BP_XL:
            return 3
        return 4

    def is_heading(self) -> bool:
        """True if element is a heading."""
        return self.type == "heading"

    def is_blockquote(self) -> bool:
        """True if element is a blockquote."""
        return self.type == "blockquote"

    def is_table(self) -> bool:
        """True if element is a table."""
        return self.type == "table"

    def is_dialogue(self) -> bool:
        """True if element starts with a dialogue marker."""
        text = self.get_normalized()
        return text.startswith("<<") if text else False

    def starts_with_quote(self) -> bool:
        """True if element starts with a quote marker."""
        text = self.get_normalized()
        return text.startswith("<<") if text else False

    def has_quote(self) -> bool:
        """True if element contains a quote marker."""
        text = self.get_normalized()
        return ("<<" in text) if text else False

    def has_exchange_marker(self) -> bool:
        """True if element contains dialogue or italic exchange markers."""
        text = self.exchange_text()
        if not text:
            return False
        return ("<<" in text) or ("///" in text)

    def has_quote_within_words(self, limit: int) -> bool:
        """True if a quote marker appears within the first N words."""
        text = self.get_normalized()
        if not text:
            return False
        words = text.split()
        if not words:
            return False
        limit = max(1, limit)
        return any("<<" in word for word in words[:limit])

    def words_before_first_quote(self) -> int:
        """Count words before the first quote marker."""
        text = self.get_normalized()
        if not text:
            return 0
        words = text.split()
        for idx, word in enumerate(words):
            if "<<" in word or "///" in word:
                return idx
        return len(words)

    def words_after_last_quote(self) -> int:
        """Count words after the last quote marker."""
        text = self.get_normalized()
        if not text:
            return 0
        words = text.split()
        for idx in range(len(words) - 1, -1, -1):
            if ">>" in words[idx] or "<<" in words[idx] or "///" in words[idx]:
                return len(words) - idx - 1
        return len(words)

    def words_before_first_exchange(self) -> int:
        """Count words before the first exchange marker (quote/italic)."""
        text = self.exchange_text()
        if not text:
            return 0
        words = text.split()
        for idx, word in enumerate(words):
            if "<<" in word or "///" in word:
                return idx
        return len(words)

    def words_after_last_exchange(self) -> int:
        """Count words after the last exchange marker (quote/italic)."""
        text = self.exchange_text()
        if not text:
            return 0
        words = text.split()
        for idx in range(len(words) - 1, -1, -1):
            if ">>" in words[idx] or "<<" in words[idx] or "///" in words[idx]:
                return len(words) - idx - 1
        return len(words)

    def exchange_text(self) -> str:
        """Return text normalized with exchange markers preserved."""
        if self.raw_html:
            return _manual_text_from_html(self.raw_html)
        return self.get_normalized()

    def serialize(self, preview: bool = False) -> dict:
        """Serialize element for JSON output."""
        data = {"type": self.type}
        if not preview:
            if self.text is not None:
                data["text"] = self.text
            if self.rows is not None:
                data["rows"] = self.rows
            if self.raw_html is not None:
                data["raw_html"] = self.raw_html
            if self.markdown is not None:
                data["markdown"] = self.markdown
            if self.role is not None:
                data["role"] = self.role
            if self.meta:
                data["meta"] = self.meta
        return data

    def to_string(self) -> str:
        """Render the element to a plain string."""
        if self.text is not None:
            return self.text
        if self.rows:
            return "\n".join(" | ".join(row) for row in self.rows)
        return ""

    def get_raw(self) -> str | None:
        """Return raw HTML for the element if available."""
        return self.raw_html

    def get_markdown(self) -> str | None:
        """Return rendered markdown for the element if available."""
        return self.markdown

    def get_normalized(self) -> str:
        """Return normalized text for the element."""
        return self.to_string()

    def _heading_level(self) -> int | None:
        """Extract heading level from metadata when available."""
        if self.type == "heading" and isinstance(self.meta, dict):
            level = self.meta.get("level")
            if isinstance(level, int):
                return level
            if isinstance(level, str) and level.isdigit():
                return int(level)
        return None

    def normalize(self) -> None:
        """Normalize text, rows, and markdown for this element."""
        if self.text is not None:
            if self.raw_html:
                self.text = _manual_text_from_html(self.raw_html)
            else:
                self.text = _clean_text(self.text)
        if self.rows:
            self.rows = [[_clean_text(cell) for cell in row]
                         for row in self.rows]
        self.markdown = _render_markdown(
            self.type,
            self.text,
            rows=self.rows,
            heading_level=self._heading_level(),
        )


class Chunk:
    """Logical grouping of elements within a chapter."""

    def __init__(self, elements: list[Element], start_index: int, end_index: int) -> None:
        """Create a chunk spanning a contiguous element range."""
        self.elements = elements
        self.start_index = start_index
        self.end_index = end_index
        self.summary = None

    def length(self) -> int:
        """Return total character length of elements."""
        return sum(element.text_length() for element in self.elements)

    def word_count(self) -> int:
        """Return total word count of elements."""
        text = self.get_text()
        if not text:
            return 0
        return len(text.split())

    def get_text(self) -> str:
        """Concatenate element text into a single string."""
        parts = [element.to_string()
                 for element in self.elements if element.to_string()]
        return " ".join(parts)

    def is_larger_than_max(self) -> bool:
        """True if chunk exceeds soft max word count."""
        return self.word_count() > SOFT_MAX_CHUNK_WORDS

    def is_small(self) -> bool:
        """True if chunk is below the small breakpoint."""
        return self.word_count() < CHUNK_BP_S

    def is_medium(self) -> bool:
        """True if chunk is below the medium breakpoint."""
        return self.word_count() < CHUNK_BP_M

    def is_large(self) -> bool:
        """True if chunk is at or above the large breakpoint."""
        return self.word_count() >= CHUNK_BP_L

    def size_label(self) -> str:
        """Return size label (XS/S/M/L/XL) based on word count."""
        wc = self.word_count()
        if wc < CHUNK_BP_S:
            return "XS"
        if wc < CHUNK_BP_M:
            return "S"
        if wc < CHUNK_BP_L:
            return "M"
        if wc < CHUNK_BP_XL:
            return "L"
        return "XL"

    def size_class(self) -> int:
        """Return size class as an integer for threshold math."""
        wc = self.word_count()
        if wc < CHUNK_BP_S:
            return 0
        if wc < CHUNK_BP_M:
            return 1
        if wc < CHUNK_BP_L:
            return 2
        if wc < CHUNK_BP_XL:
            return 3
        return 4

    def __repr__(self) -> str:
        """Return a compact debug representation."""
        summary_state = "set" if self.summary else "none"
        return (
            f"Chunk(start={self.start_index}, end={self.end_index}, "
            f"length={self.length()}, summary={summary_state})"
        )


class Chapter(Node):
    """Chapter container with elements and chunk boundaries."""

    def __init__(self) -> None:
        """Initialize an empty chapter."""
        super().__init__()
        self.elements: list[Element] = []
        self.chunk_starts: list[int] = []
        self.chunks: list[Chunk] = []
        self.label: str | None = None

    def validate(self) -> None:
        """Validate chapter elements."""
        self.children = list(self.elements)
        super().validate()

    def repair(self) -> None:
        """Repair chapter elements."""
        self.children = list(self.elements)
        super().repair()

    def serialize(self, preview: bool = False) -> dict:
        """Serialize chapter into JSON-compatible dict."""
        name = self.label if self.label else None
        return {
            "name": name,
            "elements": [el.serialize(preview=preview) for el in self.elements],
            "chunks": list(self.chunk_starts),
        }

    def load_html(self, html: str) -> None:
        """Load chapter HTML and delegate to child objects."""
        soup = _html_to_soup(html)

        if self.label is None:
            self.label = _extract_heading_label(soup)

        self.elements = _extract_elements(soup)
        self.build_chunks(self.elements)

    def build_chunks(self, elements: list[Element]) -> None:
        """Compute chunk start indexes for element list."""
        chunk_starts, _reasons, _continues = self._compute_chunk_plan(elements)
        self.chunk_starts = chunk_starts
        self.chunks = []
        for idx, start in enumerate(chunk_starts):
            end = chunk_starts[idx + 1] - 1 if idx + \
                1 < len(chunk_starts) else len(elements) - 1
            chunk_elements = elements[start: end + 1]
            self.chunks.append(Chunk(chunk_elements, start, end))

    def to_string(self) -> str:
        """Render chapter as a concatenated string."""
        self.children = list(self.elements)
        return super().to_string()

    def normalize(self) -> None:
        """Normalize chapter elements."""
        self.children = list(self.elements)
        super().normalize()

    def _compute_chunk_plan(
        self, elements: list[Element]
    ) -> tuple[list[int], dict[int, str], dict[int, str]]:
        """Compute chunk starts and optional reasons for each boundary."""
        if not elements:
            return [], {}, {}

        hard_break_types = {"blockquote", "table"}
        soft_break_types = {"heading"}
        chunk_starts: list[int] = [0]
        reasons: dict[int, str] = {}
        continues: dict[int, str] = {}
        current_len = 0
        current_words = 0

        RULE_NEXT = 0
        RULE_CHUNK_BEFORE = 1
        RULE_CHUNK_AFTER = 2
        RULE_CHUNK_CONTINUE = 3

        def add_split(idx: int, reason: str | None) -> None:
            """Record a chunk start index and optional reason."""
            if idx <= 0:
                return
            if idx not in chunk_starts:
                chunk_starts.append(idx)
            if reason:
                reasons[idx] = reason

        def apply_decision(idx: int, decision: int | None, reason: str | None) -> bool:
            """Apply a rule decision and update chunk counters."""
            nonlocal current_len, current_words
            if decision is None or decision == RULE_NEXT:
                return False
            if decision in {RULE_CHUNK_BEFORE, RULE_CHUNK_AFTER}:
                add_split(idx, reason)
            if decision in {RULE_CHUNK_BEFORE, RULE_CHUNK_AFTER}:
                current_len = 0
                current_words = 0
            if decision == RULE_CHUNK_CONTINUE:
                if reason:
                    continues[idx] = reason
                return True
            return True

        def rule_hard_break(element: Element) -> tuple[int, str] | None:
            """Always split before blockquotes/tables to keep them isolated."""
            if element.is_blockquote() or element.is_table():
                return (RULE_CHUNK_BEFORE, "hard_break")
            return None

        def rule_heading(element: Element) -> tuple[int, str] | None:
            """Split at headings to start a new topical section."""
            if element.is_heading():
                return (RULE_CHUNK_BEFORE, "heading")
            return None

        def rule_heading_end(prev: Element | None) -> tuple[int, str] | None:
            """Always split after headings to keep them isolated."""
            if prev is None:
                return None
            if prev.is_heading():
                return (RULE_CHUNK_BEFORE, "heading_end")
            return None

        def rule_dialogue_start(element: Element, prev: Element | None) -> tuple[int, str] | None:
            """Split before a new dialogue line that follows narration."""
            if prev is None:
                return None
            if element.starts_with_quote() and not prev.starts_with_quote():
                if current_words >= CHUNK_BP_M:
                    return (RULE_CHUNK_BEFORE, "dialogue_start")
            return None

        def rule_dialogue_continue(element: Element, prev: Element | None) -> tuple[int, str] | None:
            """Keep adjacent dialogue together unless both sides are large or the quote gap is large."""
            if prev is None:
                return None
            if not (element.starts_with_quote() and prev.has_quote()):
                return None
            gap_words, _tail_words, _lead_words = exchange_gap_words(current_chunk_elements, element)
            if gap_words > 10:
                return None
            if element.is_large_element() and prev.is_large_element():
                return None
            return (RULE_CHUNK_CONTINUE, "dialogue_continue")

        def exchange_gap_words(
            chunk_elements: list[Element],
            next_element: Element,
        ) -> tuple[int, int, int]:
            """Return total gap words between exchange markers in chunk + next element."""
            tail_words = 0
            for prior in reversed(chunk_elements):
                if prior.has_exchange_marker():
                    tail_words = prior.words_after_last_exchange()
                    break
                tail_words += prior.word_count()
            lead_words = next_element.words_before_first_exchange()
            return tail_words + lead_words, tail_words, lead_words

        def rule_quote_gap(
            element: Element,
            prev: Element | None,
            current_chunk_elements: list[Element],
        ) -> tuple[int, str] | None:
            """Split if a quoted paragraph isn't followed by a prompt response."""
            if prev is None:
                return None
            if not prev.has_exchange_marker():
                return None
            if current_words < CHUNK_BP_M:
                return None
            gap_words, tail_words, lead_words = exchange_gap_words(current_chunk_elements, element)
            if gap_words <= 10:
                return None
            return (RULE_CHUNK_BEFORE, f"quote_gap_{gap_words} (tail={tail_words} lead={lead_words})")

        def rule_question_response(element: Element, prev: Element | None) -> tuple[int, str] | None:
            """Keep question+response together when the response is quoted dialogue."""
            if prev is None:
                return None
            if "?" in prev.get_normalized() and element.starts_with_quote():
                return (RULE_CHUNK_CONTINUE, "question_response")
            return None

        def rule_large_chunk_large_element(element: Element, elem_words: int) -> tuple[int, str] | None:
            """Prevent continuing when the chunk is already large and the element is medium+."""
            nonlocal current_words
            if current_words < CHUNK_BP_L:
                return None
            if elem_words < ELEM_BP_M:
                return None
            return (
                RULE_CHUNK_BEFORE,
                f"large_chunk_medium_element (chunk_wc={current_words}, elem_wc={elem_words})",
            )

        def rule_size_class_sum(element: Element) -> tuple[int, str] | None:
            """Split when chunk+element size classes are too large combined."""
            if current_words < CHUNK_BP_S:
                chunk_class_value = 0
            elif current_words < CHUNK_BP_M:
                chunk_class_value = 1
            elif current_words < CHUNK_BP_L:
                chunk_class_value = 2
            elif current_words < CHUNK_BP_XL:
                chunk_class_value = 3
            else:
                chunk_class_value = 4
            elem_class_value = element.size_class()
            if chunk_class_value + elem_class_value >= 5:
                return (
                    RULE_CHUNK_BEFORE,
                    f"size_class_sum {chunk_class_value}+{elem_class_value}",
                )
            return None

        current_chunk_elements: list[Element] = []
        for idx, element in enumerate(elements):
            elem_len = element.text_length()
            elem_words = element.word_count()
            prev = elements[idx - 1] if idx > 0 else None

            rule_list = [
                ("decision", lambda: rule_heading_end(prev)),
                ("decision", lambda: rule_size_class_sum(element)),
                ("decision", lambda: rule_large_chunk_large_element(element, elem_words)),
                ("decision", lambda: rule_dialogue_continue(element, prev)),
                ("decision", lambda: rule_hard_break(element)),
                ("decision", lambda: rule_heading(element)),
                ("decision", lambda: rule_quote_gap(element, prev, current_chunk_elements)),
                ("decision", lambda: rule_question_response(element, prev)),
                ("decision", lambda: rule_dialogue_start(element, prev)),
            ]

            for kind, rule in rule_list:
                result = rule()
                if not result:
                    continue
                if kind == "before":
                    add_split(idx, result)
                    break
                decision, reason = result
                if apply_decision(idx, decision, reason):
                    if decision in {RULE_CHUNK_BEFORE, RULE_CHUNK_AFTER}:
                        current_chunk_elements = []
                    break

            current_len += elem_len
            current_words += elem_words
            current_chunk_elements.append(element)

        chunk_starts.sort()
        return chunk_starts, reasons, continues


class EbookContent(epub.EpubBook):
    """EpubBook extension with spine classification helpers."""

    def __init__(self, path: str) -> None:
        """Initialize from an EPUB path."""
        super().__init__()
        self.path = path
        self.items = []
        self._chapter_items = []
        self._item_names: dict[str, str | None] = {}

    def load(self) -> None:
        """Load EPUB into this instance."""
        loaded = epub.read_epub(self.path)
        self.__dict__.update(loaded.__dict__)
        self.items = _ordered_items(self)

    def classify_spine_items(self) -> None:
        """Classify spine items as real chapters vs non-chapters (stub heuristics)."""
        chapter_items = []
        for item in self.items:
            key = self._item_key(item)
            try:
                name, item_type = _classify_html_item(item.get_content())
            except NotImplementedError:
                raise
            except Exception:
                name = None
                item_type = "other"
            self._item_names[key] = name
            if item_type == "chapter":
                chapter_items.append(item)
        self._chapter_items = chapter_items

    def chapter_items(self):
        """Return items classified as chapters."""
        return self._chapter_items or []

    def _item_key(self, item) -> str:
        """Return a stable-ish key for an EbookLib item."""
        return getattr(item, "get_id", lambda: None)() or getattr(item, "get_name", lambda: None)() or str(id(item))

    def item_name(self, item) -> str | None:
        """Return the cached label for a spine item."""
        return self._item_names.get(self._item_key(item))


class SimpleBook(Node):
    """Top-level model containing metadata and chapters."""

    def __init__(self) -> None:
        """Initialize an empty book."""
        super().__init__()
        self.metadata = Metadata()
        self.chapters = []

    def add_chapter(self, chapter: "Chapter") -> None:
        """Append a chapter to the book."""
        self.chapters.append(chapter)

    def load_epub(self, path: str) -> None:
        """Loads EPUB and populates chapters."""
        source = EbookContent(path)
        source.load()
        self.populate(source)

    def populate(self, source: EbookContent) -> None:
        """Populate metadata and chapters from EbookContent."""
        if not source.items:
            return

        meta_title = (source.get_metadata("DC", "title") or [[None]])[0][0]
        meta_author = (source.get_metadata("DC", "creator") or [[None]])[0][0]
        meta_language = (source.get_metadata(
            "DC", "language") or [[None]])[0][0]
        meta_identifiers = [val for val,
                            _attrs in source.get_metadata("DC", "identifier")]

        self.metadata.title = meta_title or ""
        self.metadata.author = meta_author or ""
        self.metadata.language = meta_language or ""
        isbn = ""
        uuid = ""
        for ident in meta_identifiers:
            if not ident:
                continue
            lowered = ident.lower()
            if "isbn" in lowered and not isbn:
                isbn = ident.split(":")[-1]
            if "uuid" in lowered and not uuid:
                uuid = ident
        if not uuid and meta_identifiers:
            uuid = meta_identifiers[0]
        self.metadata.isbn = isbn
        self.metadata.uuid = uuid

        source.classify_spine_items()
        for item in source.chapter_items():
            chapter = Chapter()
            chapter.label = source.item_name(item)
            chapter.load_html(item.get_content())
            if not chapter.label:
                continue
            if not chapter.elements:
                continue
            self.chapters.append(chapter)

    def validate(self) -> None:
        """Validate all chapters."""
        self.children = list(self.chapters)
        super().validate()

    def repair(self) -> None:
        """Repair all chapters."""
        self.children = list(self.chapters)
        super().repair()

    def normalize(self) -> None:
        """Normalize all chapters."""
        self.children = list(self.chapters)
        super().normalize()

    def serialize(self, preview: bool = False) -> dict:
        """Serialize the entire book into one JSON-like dict."""
        return {
            "metadata": {
                "title": self.metadata.title,
                "author": self.metadata.author,
                "language": self.metadata.language,
                "isbn": self.metadata.isbn,
                "uuid": self.metadata.uuid,
            },
            "chapters": [chapter.serialize(preview=preview) for chapter in self.chapters],
        }

    def export_chunk_form(self, path: str) -> None:
        """
        Write a simple chunking form:
        [path] :: content
        Blank lines indicate chunk boundaries.
        """
        lines: list[str] = []
        for chapter in self.chapters:
            chapter_name = chapter.label or "Untitled"
            lines.append(f"# Chapter: {chapter_name}")
            _, chunk_reasons, continue_reasons = chapter._compute_chunk_plan(chapter.elements)
            chunk_index = 0
            chunk_starts = chapter.chunk_starts
            chunk_start = chunk_starts[0] if chunk_starts else 0
            chunk_end = (chunk_starts[1] - 1) if len(chunk_starts) > 1 else len(chapter.elements) - 1
            chunk = Chunk(chapter.elements[chunk_start : chunk_end + 1], chunk_start, chunk_end)
            lines.append(
                "%% Total Chunk "
                f"[wc:{chunk.word_count()} "
                f"ec:{len(chunk.elements)}] "
                f"({chunk.size_label()})"
            )
            current_wc = 0
            current_ec = 0
            for idx, element in enumerate(chapter.elements):
                if idx in chunk_starts and idx != chunk_starts[0]:
                    reason = chunk_reasons.get(idx, "manual")
                    lines.append(f"---- {reason}")
                    chunk_index += 1
                    chunk_start = chunk_starts[chunk_index]
                    chunk_end = (
                        chunk_starts[chunk_index + 1] - 1
                        if chunk_index + 1 < len(chunk_starts)
                        else len(chapter.elements) - 1
                    )
                    chunk = Chunk(
                        chapter.elements[chunk_start : chunk_end + 1],
                        chunk_start,
                        chunk_end,
                    )
                    lines.append(
                        "%% Total Chunk "
                        f"[wc:{chunk.word_count()} "
                        f"ec:{len(chunk.elements)}] "
                        f"({chunk.size_label()})"
                    )
                    current_wc = 0
                    current_ec = 0
                def _chunk_label(word_count: int) -> str:
                    """Map word count to a short chunk size label."""
                    if word_count >= CHUNK_BP_L:
                        return "L"
                    if word_count >= CHUNK_BP_M:
                        return "M"
                    if word_count >= CHUNK_BP_S:
                        return "S"
                    return "T"
                if idx in continue_reasons:
                    lines.append(f"... continue ({continue_reasons[idx]})")
                lines.append(
                    "%% current "
                    f"C[wc:{current_wc} "
                    f"ec:{current_ec}]({_chunk_label(current_wc)}) "
                    f"E[wc:{element.word_count()}]({element.size_label()})"
                )
                current_wc += element.word_count()
                current_ec += 1
                if element.type == "heading":
                    lines.append("")
                content = element.get_normalized()
                if element.raw_html:
                    manual_text = _manual_text_from_html(element.raw_html)
                    if manual_text:
                        content = manual_text
                if not content:
                    continue
                path_text = element.path or element.type
                if element.type == "heading":
                    content = f"## {content}"
                lines.append(f"{path_text} :: {content}")
            lines.append("")
        Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    def import_chunk_form(self, path: str) -> None:
        """
        Read the chunking form and rebuild chunk_starts based on blank lines.
        """
        text = Path(path).read_text(encoding="utf-8")
        blocks: list[list[str]] = []
        current: list[str] = []
        for line in text.splitlines():
            if line.strip() == "":
                if current:
                    blocks.append(current)
                    current = []
                continue
            if line.strip().startswith("#"):
                continue
            current.append(line)
        if current:
            blocks.append(current)

        chapter_idx = 0
        line_idx = 0
        for chapter in self.chapters:
            element_count = len(chapter.elements)
            if element_count == 0:
                chapter.chunk_starts = []
                chapter.chunks = []
                continue
            starts = [0]
            seen = 0
            while line_idx < len(blocks):
                block = blocks[line_idx]
                block_len = len(block)
                if seen + block_len >= element_count:
                    break
                seen += block_len
                starts.append(seen)
                line_idx += 1
            chapter.chunk_starts = starts
            chapter.build_chunks(chapter.elements)
            chapter_idx += 1


class EbookNormalizer:
    """Manages conversion of an ebook into a SimpleBook."""

    def __init__(self) -> None:
        """Initialize the normalizer with empty state."""
        self.simple_book = SimpleBook()
        self.source_ebook = EbookContent("")

    def load(self, path: str) -> None:
        """Loads the EbookContent."""
        self.source_ebook.path = path
        self.source_ebook.load()

    def populate(self) -> None:
        """Generates the SimpleBook from loaded content."""
        self.simple_book.populate(self.source_ebook)

    def validate(self) -> list[str]:
        """Return a list of issues to fix."""
        self.simple_book.validate()
        return []

    def report_validations(self) -> None:
        """Print a text report while doing validations."""
        issues = self.validate()
        if not issues:
            print("OK: no validation issues found.")
            return
        print("WARN: validation issues:")
        for issue in issues:
            print(f" - {issue}")

    def repair(self) -> None:
        """Run repair methods for any items with issues."""
        self.simple_book.repair()

    def normalize(self) -> None:
        """Normalize text across the tree."""
        self.simple_book.normalize()

    def serialize(self, preview: bool = False) -> dict:
        """Output format: the entire thing is just one big json file."""
        return self.simple_book.serialize(preview=preview)

    def run_all(self, path: str, preview: bool = False) -> dict:
        """One-shot runner: load → populate → normalize → validate/repair → serialize."""
        self.load(path)
        self.populate()
        self.normalize()
        self.validate()
        self.repair()
        return self.serialize(preview=preview)

    def to_json(self, path: str) -> None:
        """Write the serialized output to disk."""
        data = self.serialize()
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
