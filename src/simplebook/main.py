

import json
from pathlib import Path

from ebooklib import epub  # type: ignore[import-untyped]
from bs4 import BeautifulSoup  # type: ignore[import-untyped]

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

def _clean_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    cleaned: list[str] = []
    blank_run = 0
    for line in lines:
        if not line:
            blank_run += 1
            if blank_run <= 1:
                cleaned.append("")
        else:
            blank_run = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


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


def _classify_html_item(html: bytes | str) -> tuple[str | None, str]:
    if isinstance(html, (bytes, bytearray)):
        html = html.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(STRIP_ELEMENTS):
        tag.decompose()

    name = _extract_heading_label(soup)
    label_type = _classify_label_type(name)

    # Fallback: paragraph count threshold.
    paragraphs = [
        _clean_text(p.get_text("\n"))
        for p in soup.find_all("p")
        if _clean_text(p.get_text("\n"))
    ]
    para_count = len(paragraphs)

    if label_type in {"front", "back"}:
        return name, label_type
    if label_type == "chapter":
        return name, "chapter"
    if para_count >= 10:
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


class Chunk(Node):
    """Optional grouping of one or more paragraphs."""

    def __init__(self) -> None:
        super().__init__()
        self.paragraphs: list["Paragraph"] = []
        self.ordinal = 0

    def append_para(self, paragraph: "Paragraph") -> None:
        if paragraph.text.strip():
            self.paragraphs.append(paragraph)

    def validate(self) -> None:
        self.children = list(self.paragraphs)
        super().validate()

    def serialize(self) -> dict:
        text = "\n\n".join(para.text for para in self.paragraphs if para.text.strip()).strip()
        return {"text": text, "ordinal": self.ordinal}

    def build_from_paragraphs(self, paragraphs: list["Paragraph"]) -> None:
        """Populate this chunk from paragraph objects."""
        self.paragraphs = paragraphs

    def normalize(self) -> None:
        self.children = list(self.paragraphs)
        super().normalize()

class Paragraph(Node):
    """A single paragraph taken from the HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.text = ""

    def validate(self) -> None:
        if not isinstance(self.text, str):
            self.text = str(self.text)

    def repair(self) -> None:
        if self.text is None:
            self.text = ""
        else:
            self.text = _clean_text(self.text)

    def serialize(self) -> str:
        return self.text

    def load_html(self, html: str) -> None:
        """Load paragraph text from HTML (stub)."""
        if isinstance(html, (bytes, bytearray)):
            html = html.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        self.text = _clean_text(soup.get_text("\n"))

    def to_string(self) -> str:
        return self.text

    def normalize(self) -> None:
        """Remove special chars and collapse whitespace (stub)."""
        self.text = _clean_text(self.text)


class Chapter(Node):
    def __init__(self) -> None:
        super().__init__()
        self.paragraphs = []
        self.chunks = []
        self.label: str | None = None

    def validate(self) -> None:
        self.children = [*self.paragraphs, *self.chunks]
        super().validate()

    def repair(self) -> None:
        self.children = [*self.paragraphs, *self.chunks]
        super().repair()

    def serialize(self, preview: bool = False) -> dict:
        name = self.label if self.label else None
        kept_paragraphs = [para for para in self.paragraphs if para.text.strip()]
        paragraph_texts = [para.text for para in kept_paragraphs]
        index_by_para = {para: idx for idx, para in enumerate(kept_paragraphs)}
        chunk_starts: list[int] = []
        for chunk in self.chunks:
            if not chunk.paragraphs:
                continue
            first_para = chunk.paragraphs[0]
            if first_para in index_by_para:
                chunk_starts.append(index_by_para[first_para])

        if preview:
            return {
                "name": name,
                "pp": [],
                "chunks": chunk_starts,
            }

        if not paragraph_texts:
            return {
                "name": name,
                "pp": [],
                "chunks": chunk_starts,
            }

        return {
            "name": name,
            "pp": paragraph_texts,
            "chunks": chunk_starts,
        }

    def load_html(self, html: str) -> None:
        """Load chapter HTML and delegate to child objects."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(STRIP_ELEMENTS):
            tag.decompose()

        if self.label is None:
            self.label = _extract_heading_label(soup)

        paragraphs = soup.find_all("p")
        if paragraphs:
            for p in paragraphs:
                para_text = _clean_text(p.get_text("\n"))
                if not para_text:
                    continue
                para = Paragraph()
                para.text = para_text
                self.paragraphs.append(para)
        else:
            raw_text = _clean_text(soup.get_text("\n"))
            for block in raw_text.split("\n\n"):
                block = block.strip()
                if not block:
                    continue
                para = Paragraph()
                para.text = block
                self.paragraphs.append(para)

        self.build_chunks(self.paragraphs)

    def build_chunks(self, paragraphs: list["Paragraph"]) -> None:
        """Group paragraphs into chunks (stub)."""
        if not paragraphs:
            return

        chunks: list[Chunk] = []
        current: list[Paragraph] = []
        current_len = 0

        for para in paragraphs:
            text = para.text.strip()
            if not text:
                if current:
                    chunk = Chunk()
                    chunk.build_from_paragraphs(current)
                    chunks.append(chunk)
                    current = []
                    current_len = 0
                continue

            is_break = text in {"***", "* * *", "---"}
            para_len = len(text)

            if current and (
                is_break
                or para_len >= LARGE_PARAGRAPH_CHARS
                or current_len + para_len > MAX_CHUNK_CHARS
                or (para_len > MAX_CHUNK_ADDITION_CHARS and current_len > 0)
            ):
                chunk = Chunk()
                chunk.build_from_paragraphs(current)
                chunks.append(chunk)
                current = []
                current_len = 0

            if is_break:
                continue

            current.append(para)
            current_len += para_len

        if current:
            chunk = Chunk()
            chunk.build_from_paragraphs(current)
            chunks.append(chunk)

        for idx, chunk in enumerate(chunks, start=1):
            chunk.ordinal = idx

        self.chunks = chunks

    def to_string(self) -> str:
        self.children = [*self.paragraphs, *self.chunks]
        return super().to_string()

    def normalize(self) -> None:
        self.children = [*self.paragraphs, *self.chunks]
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
            if not chapter.paragraphs:
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

    
