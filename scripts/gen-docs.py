#!/usr/bin/env python3
"""Generate markdown docs from source and schema."""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
import os
from pathlib import Path
import sys
import textwrap


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DOCS_DIR = PROJECT_ROOT / "docs" / "generated"
SCHEMA_PATH = SRC_DIR / "simplebook" / "output_schema.json"
CLI_HELP_PATH = DOCS_DIR / "cli_help.txt"

sys.path.insert(0, str(SRC_DIR))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _format_doc(obj) -> str:
    doc = inspect.getdoc(obj) or "No docstring."
    return textwrap.indent(doc, "  ")


def _emit_module_from_ast(module_name: str, file_path: Path, error: str | None) -> str:
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines: list[str] = [f"## Module: `{module_name}`", ""]
    if error:
        lines.append(f"_Note: import failed, parsed from source ({error})._")
        lines.append("")

    classes = []
    functions = []
    constants: list[tuple[str, str]] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or "No docstring."
            classes.append((node.name, doc))
        elif isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node) or "No docstring."
            functions.append((node.name, doc))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    try:
                        value = ast.literal_eval(node.value)
                        constants.append((target.id, repr(value)))
                    except Exception:
                        constants.append((target.id, "<expr>"))

    if classes:
        lines.append("### Classes")
        for name, doc in classes:
            lines.append(f"- `{name}`")
            lines.append(textwrap.indent(doc, "  "))
        lines.append("")

    if functions:
        lines.append("### Functions")
        for name, doc in functions:
            lines.append(f"- `{name}`")
            lines.append(textwrap.indent(doc, "  "))
        lines.append("")

    if constants:
        lines.append("### Constants")
        for name, value in constants:
            lines.append(f"- `{name}` = `{value}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _emit_module(module_name: str) -> str:
    lines: list[str] = [f"## Module: `{module_name}`", ""]
    file_path = SRC_DIR / "simplebook"
    if module_name == "simplebook":
        file_path = file_path / "__init__.py"
    else:
        file_path = file_path / f"{module_name.split('.', 1)[1]}.py"

    try:
        module = __import__(module_name, fromlist=["*"])
    except Exception as exc:
        if file_path.exists():
            return _emit_module_from_ast(module_name, file_path, str(exc))
        lines.append(f"_Note: import failed ({exc})._")
        lines.append("")
        return "\n".join(lines)

    classes = [
        member
        for name, member in inspect.getmembers(module, inspect.isclass)
        if member.__module__ == module_name
    ]
    if classes:
        lines.append("### Classes")
        for cls in classes:
            lines.append(f"- `{cls.__name__}`")
            lines.append(_format_doc(cls))
        lines.append("")

    functions = [
        member
        for name, member in inspect.getmembers(module, inspect.isfunction)
        if member.__module__ == module_name
    ]
    if functions:
        lines.append("### Functions")
        for fn in functions:
            lines.append(f"- `{fn.__name__}`")
            lines.append(_format_doc(fn))
        lines.append("")

    constants = [
        (name, value)
        for name, value in inspect.getmembers(module)
        if name.isupper() and module.__dict__.get(name) is value
    ]
    if constants:
        lines.append("### Constants")
        for name, value in constants:
            lines.append(f"- `{name}` = `{value!r}`")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def generate_api_docs() -> None:
    module_names = [
        "simplebook",
        "simplebook.main",
        "simplebook.cli",
        "simplebook.schema_validator",
        "simplebook.config",
    ]
    content = ["# SimpleBook API Reference", ""]
    for name in module_names:
        content.append(_emit_module(name))
    _write(DOCS_DIR / "api.md", "\n".join(content))


def _schema_section(title: str, data: dict) -> list[str]:
    lines = [f"## {title}", ""]
    required = data.get("required", [])
    props = data.get("properties", {})
    if required:
        lines.append("### Required fields")
        lines.extend([f"- `{name}`" for name in required])
        lines.append("")
    if props:
        lines.append("### Properties")
        for name, info in props.items():
            desc = info.get("description", "")
            type_info = info.get("type", "")
            suffix = []
            if type_info:
                suffix.append(f"type: `{type_info}`")
            if desc:
                suffix.append(desc)
            tail = f" ({' | '.join(suffix)})" if suffix else ""
            lines.append(f"- `{name}`{tail}")
        lines.append("")
    return lines


def generate_schema_docs() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    lines = ["# SimpleBook Output Schema", ""]
    lines.extend(_schema_section("Top-level", schema))

    metadata = schema.get("properties", {}).get("metadata", {})
    if metadata:
        lines.extend(_schema_section("Metadata", metadata))

    chapters = schema.get("properties", {}).get("chapters", {})
    if chapters:
        lines.extend(_schema_section("Chapters", chapters))
        items = chapters.get("items", {})
        if items:
            lines.extend(_schema_section("Chapter Item", items))

    _write(DOCS_DIR / "schema.md", "\n".join(lines))


def generate_index() -> None:
    content = """# Generated Docs

- [API Reference](api.md)
- [Output Schema](schema.md)
"""
    _write(DOCS_DIR / "README.md", content)


def generate_cli_help() -> None:
    """Capture CLI help output for documentation."""
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(SRC_DIR)
        result = subprocess.run(
            [sys.executable, "-m", "simplebook", "--help"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Failed to capture CLI help: {exc}") from exc
    CLI_HELP_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLI_HELP_PATH.write_text(result.stdout.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    generate_api_docs()
    generate_schema_docs()
    generate_index()
    generate_cli_help()
    print(f"OK: wrote docs to {DOCS_DIR}")
    docs_root = PROJECT_ROOT / "docs"
    build_dir = docs_root / "_build"
    try:
        subprocess.check_call(
            [
                "sphinx-build",
                "-M",
                "html",
                str(docs_root),
                str(build_dir),
            ]
        )
    except FileNotFoundError:
        print("WARN: sphinx-build not found. Install sphinx to build docs.")
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: sphinx build failed ({exc.returncode}).")
        return exc.returncode
    print(f"OK: built Sphinx docs at {build_dir / 'html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
