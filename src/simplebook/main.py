

import json
import unicodedata
from pathlib import Path

from ebooklib import epub  # type: ignore[import-untyped]
from bs4 import BeautifulSoup, Comment  # type: ignore[import-untyped]

from .config import (
    MAX_CHUNK_ADDITION_CHARS,
    MAX_CHUNK_CHARS,
    LARGE_PARAGRAPH_CHARS,
    CHAPTER_PATTERNS,
    ROMAN_NUMERALS,
    FRONT_MATTER_KEYWORDS,
    BACK_MATTER_KEYWORDS,
    NON_CHAPTER_KEYWORDS,
    STRIP_ELEMENTS,
)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

DOUBLE_QUOTE_CHARS = {'"', "“", "”", "„"}


def _normalize_quotes(text: str) -> str:
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
    if not text:
        return text
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _normalize_quotes(text)
    text = _to_ascii(text)
    text = " ".join(text.split())
    return text.strip()


def _ordered_items(book: epub.EpubBook):
    item_document = getattr(epub, "ITEM_DOCUMENT", 9)
    items_by_id = {item.get_id(): item for item in book.get_items_of_type(item_document)}
    ordered = []
    for item_id, _linear in book.spine:
        item = items_by_id.get(item_id)
        if item:
            ordered.append(item)
    return ordered


def _classify_label_type(label: str | None) -> str:
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
    texts: list[str] = []
    seen: set[str] = set()

    def _add(text: str) -> None:
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
            classes = " ".join(el.get("class", [])) if hasattr(el, "get") else ""
            epub_type = (attrs.get("epub:type") or "").lower()
            is_heading_p = any(key in epub_type for key in ["title", "subtitle", "heading"])
            is_heading_p = is_heading_p or any(
                key in classes.lower() for key in ["title", "subtitle", "chapter", "heading"]
            )
            if is_heading_p:
                _add(el.get_text(" ", strip=True))
                continue
            break

        classes = " ".join(el.get("class", [])) if hasattr(el, "get") else ""
        is_heading = name in {"h1", "h2", "h3", "h4", "h5", "h6", "subtitle"}
        is_heading = is_heading or (hasattr(el, "get") and el.get("role") == "heading")
        is_heading = is_heading or any(
            key in classes.lower() for key in ["title", "subtitle", "chapter", "heading"]
        )

        if is_heading:
            _add(el.get_text(" ", strip=True))

    return texts


def _extract_heading_label(soup: BeautifulSoup) -> str | None:
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

ALLOWED_TEXT_TAGS = set(ELEMENT_TAG_TYPES.keys()) | HEADING_TAGS | TABLE_CELL_TAGS


def _html_to_soup(html: bytes | str) -> BeautifulSoup:
    if isinstance(html, (bytes, bytearray)):
        html = html.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIP_ELEMENTS):
        tag.decompose()
    return soup


def _assert_supported_text(root: BeautifulSoup) -> None:
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
    rows: list[list[str]] = []
    for tr in tag.find_all("tr"):
        cells = []
        for cell in tr.find_all(list(TABLE_CELL_TAGS)):
            cell_text = _clean_text(cell.get_text("\n"))
            cells.append(cell_text)
        if cells:
            rows.append(cells)
    return rows


def _extract_elements(soup: BeautifulSoup) -> list["Element"]:
    root = soup.body if soup.body is not None else soup
    _assert_supported_text(root)
    elements: list[Element] = []

    def walk(node) -> None:
        for child in node.children:
            if not hasattr(child, "name") or child.name is None:
                continue
            name = child.name.lower()
            if name in STRIP_ELEMENTS:
                continue
            if name in CONTAINER_TAGS:
                walk(child)
                continue
            if name in HEADING_TAGS:
                text = _clean_text(child.get_text("\n"))
                if text:
                    elements.append(Element("heading", text=text))
                continue
            if name == "blockquote":
                text = _blockquote_text(child)
                if text:
                    elements.append(Element("blockquote", text=text))
                for cite in child.find_all("cite"):
                    cite_text = _clean_text(cite.get_text("\n"))
                    if cite_text:
                        elements.append(Element("cite", text=cite_text))
                continue
            if name == "table":
                caption = child.find("caption") or child.find("figcaption")
                if caption is not None:
                    caption_text = _clean_text(caption.get_text("\n"))
                    if caption_text:
                        elements.append(Element("caption", text=caption_text))
                rows = _table_rows(child)
                if rows:
                    elements.append(Element("table", rows=rows))
                continue
            if name in ELEMENT_TAG_TYPES:
                text = _clean_text(child.get_text("\n"))
                if text:
                    elements.append(Element(ELEMENT_TAG_TYPES[name], text=text))
                continue
            walk(child)

    walk(root)
    return elements


def _classify_html_item(html: bytes | str) -> tuple[str | None, str]:
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
        self.title = ""
        self.author = ""
        self.language = ""
        self.isbn = ""
        self.uuid = ""


class Node:
    """Prototype node to enforce delegation."""

    def __init__(self) -> None:
        self.children = []

    def validate(self) -> None:
        for child in self.children:
            child.validate()

    def repair(self) -> None:
        for child in self.children:
            child.repair()

    def serialize(self):
        return [child.serialize() for child in self.children]

    def to_string(self) -> str:
        return "\n".join(child.to_string() for child in self.children)

    def normalize(self) -> None:
        for child in self.children:
            child.normalize()


class Element(Node):
    """Typed content element extracted from HTML."""

    def __init__(
        self,
        element_type: str,
        text: str | None = None,
        rows: list[list[str]] | None = None,
        meta: dict | None = None,
    ) -> None:
        super().__init__()
        self.type = element_type
        self.text = text
        self.rows = rows
        self.meta = meta or {}

    def validate(self) -> None:
        if self.text is not None and not isinstance(self.text, str):
            self.text = str(self.text)

    def repair(self) -> None:
        if self.text is None:
            self.text = None
        else:
            self.text = _clean_text(self.text)
        if self.rows:
            self.rows = [[_clean_text(cell) for cell in row] for row in self.rows]

    def text_length(self) -> int:
        if self.text:
            return len(self.text)
        if self.rows:
            return sum(len(cell) for row in self.rows for cell in row)
        return 0

    def serialize(self, preview: bool = False) -> dict:
        data = {"type": self.type}
        if not preview:
            if self.text is not None:
                data["text"] = self.text
            if self.rows is not None:
                data["rows"] = self.rows
            if self.meta:
                data["meta"] = self.meta
        return data

    def to_string(self) -> str:
        if self.text is not None:
            return self.text
        if self.rows:
            return "\n".join(" | ".join(row) for row in self.rows)
        return ""

    def normalize(self) -> None:
        if self.text is not None:
            self.text = _clean_text(self.text)
        if self.rows:
            self.rows = [[_clean_text(cell) for cell in row] for row in self.rows]


class Chapter(Node):
    def __init__(self) -> None:
        super().__init__()
        self.elements: list[Element] = []
        self.chunk_starts: list[int] = []
        self.label: str | None = None

    def validate(self) -> None:
        self.children = list(self.elements)
        super().validate()

    def repair(self) -> None:
        self.children = list(self.elements)
        super().repair()

    def serialize(self, preview: bool = False) -> dict:
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
        if not elements:
            self.chunk_starts = []
            return

        hard_break_types = {"blockquote", "table"}
        soft_break_types = {"heading"}
        chunk_starts: list[int] = []
        current_len = 0

        for idx, element in enumerate(elements):
            elem_len = element.text_length()
            is_hard_break = element.type in hard_break_types
            is_soft_break = element.type in soft_break_types

            if is_hard_break:
                chunk_starts.append(idx)
                current_len = 0
                continue

            if is_soft_break:
                chunk_starts.append(idx)
                current_len = elem_len
                continue

            if not chunk_starts:
                chunk_starts.append(idx)
                current_len = 0

            if current_len and (
                elem_len >= LARGE_PARAGRAPH_CHARS
                or current_len + elem_len > MAX_CHUNK_CHARS
                or (elem_len > MAX_CHUNK_ADDITION_CHARS)
            ):
                chunk_starts.append(idx)
                current_len = 0

            current_len += elem_len

        self.chunk_starts = chunk_starts

    def to_string(self) -> str:
        self.children = list(self.elements)
        return super().to_string()

    def normalize(self) -> None:
        self.children = list(self.elements)
        super().normalize()


class EbookContent(epub.EpubBook):
    """EpubBook extension with spine classification helpers."""
    def __init__(self, path: str) -> None:
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
        return getattr(item, "get_id", lambda: None)() or getattr(item, "get_name", lambda: None)() or str(id(item))

    def item_name(self, item) -> str | None:
        return self._item_names.get(self._item_key(item))

class SimpleBook(Node):
    def __init__(self) -> None:
        super().__init__()
        self.metadata = Metadata()
        self.chapters = []

    def add_chapter(self, chapter: "Chapter") -> None:
        self.chapters.append(chapter)

    def load_epub(self, path: str) -> None:
        """Loads EPUB and populates chapters."""
        source = EbookContent(path)
        source.load()
        self.populate(source)

    def populate(self, source: EbookContent) -> None:
        if not source.items:
            return

        meta_title = (source.get_metadata("DC", "title") or [[None]])[0][0]
        meta_author = (source.get_metadata("DC", "creator") or [[None]])[0][0]
        meta_language = (source.get_metadata("DC", "language") or [[None]])[0][0]
        meta_identifiers = [val for val, _attrs in source.get_metadata("DC", "identifier")]

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
        self.children = list(self.chapters)
        super().validate()

    def repair(self) -> None:
        self.children = list(self.chapters)
        super().repair()

    def normalize(self) -> None:
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


class EbookNormalizer:
    """Manages conversion of an ebook into a SimpleBook."""
    def __init__(self) -> None:
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

    
