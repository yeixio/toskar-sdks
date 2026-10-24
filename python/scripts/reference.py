"""Writes the Python SDK's reference docs, as Markdown, to reference/python:
the hand-written API from its docstrings, every route's method on
toskar.api, and the error codes. CI checks they're current.

    python scripts/reference.py
"""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
from pathlib import Path
from typing import Any

import toskar
from toskar._generated import operations

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "reference" / "python"

# The hand-written API, in the order a reader meets it.
SECTIONS = [
    ("Connecting", ["Toskar", "AsyncToskar"]),
    ("Streamed answers", ["ChatStreamEvent", "Token", "Done"]),
    ("Errors", ["ToskarError", "ErrorCodes"]),
    ("Pairing and reaching a computer from anywhere", [
        "pair", "apair", "Device", "Route", "TOSKAR_RELAY", "NotConfirmed", "PinMismatch", "Unreachable",
        "pin_of", "short_pin", "route_id", "open_record", "Record", "RecordError",
    ]),
    ("Finding computers on the network", ["discover", "Computer"]),
    ("Server-sent events", ["read_events", "aread_events", "ServerSentEvent"]),
    ("The contract", ["CONTRACT_VERSION"]),
]


def doc(obj: Any) -> str:
    """A docstring as Markdown: indented examples become code blocks, and
    reST's ``code`` and trailing :: become Markdown's."""
    # A module's docstring from its source, indented as written: Python 3.13
    # dedents __doc__, which takes its examples' indentation as the whole's.
    if inspect.ismodule(obj):
        raw = (ast.get_docstring(ast.parse(inspect.getsource(obj)), clean=False) or "").strip("\n")
    else:
        raw = inspect.getdoc(obj) or ""
    lines = raw.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("    "):
            j = i
            while j < len(lines) and (lines[j].startswith("    ") or not lines[j].strip()):
                j += 1
            block = [line[4:] for line in lines[i:j]]
            while block and not block[-1].strip():
                block.pop()
            out += ["", "```python", *block, "```", ""]
            i = j
            continue
        out.append(lines[i])
        i += 1
    text = "\n".join(out)
    text = re.sub(r"::\n", ":\n", text)
    text = re.sub(r"(?<!`)``([^`\n]+)``(?!`)", r"`\1`", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def attribute_docs(cls: type) -> dict[str, str]:
    """Docstrings under class attributes, as dataclass fields have."""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(cls)))
    except (OSError, TypeError):
        return {}
    out: dict[str, str] = {}
    body = tree.body[0].body  # type: ignore[attr-defined]
    for a, b in zip(body, body[1:]):
        target = a.targets[0] if isinstance(a, ast.Assign) else getattr(a, "target", None)
        name = getattr(target, "id", None)
        if name and isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
            out[name] = inspect.cleandoc(b.value.value)
    return out


def signature(name: str, fn: Any) -> str:
    try:
        sig = str(inspect.signature(fn))
    except (TypeError, ValueError):
        sig = "(...)"
    sig = re.sub(r"toskar\._[a-z_.]+\.", "", sig.replace("'", ""))
    prefix = "async def " if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn) else "def "
    return f"```python\n{prefix}{name}{sig}\n```"


def anchor(name: str) -> str:
    return name.lower()


def render_class(name: str, cls: type) -> list[str]:
    out = [f"### {name}", ""]
    bases = [b.__name__ for b in cls.__bases__ if b is not object]
    if bases:
        out += [f"*Subclass of {', '.join(bases)}.*", ""]
    if d := doc(cls):
        out += [d, ""]
    fields = attribute_docs(cls)
    if getattr(cls, "__dataclass_fields__", None):
        out += ["| Field | Type | |", "| --- | --- | --- |"]
        for f in cls.__dataclass_fields__.values():  # type: ignore[attr-defined]
            t = str(f.type).replace("|", "\\|")
            about = re.sub(r"(?<!`)``([^`\n]+)``(?!`)", r"`\1`", fields.get(f.name, "")).replace("\n", " ")
            out.append(f"| `{f.name}` | `{t}` | {about} |")
        out.append("")
    elif name == "ErrorCodes":
        out += ["Every code, with what it means: [errors.md](errors.md).", ""]
        return out
    init = cls.__dict__.get("__init__")
    if init and not getattr(cls, "__dataclass_fields__", None) and not issubclass(cls, Exception):
        out += [signature(name, init).replace("(self, ", "(").replace("(self)", "()").replace("def " + name, name), ""]
    for attr, value in cls.__dict__.items():
        if attr.startswith("_") or not callable(value) and not isinstance(value, property):
            continue
        if isinstance(value, property):
            out += [f"#### {name}.{attr}", "", doc(value), ""]
            continue
        fn = value.__func__ if isinstance(value, (classmethod, staticmethod)) else value
        sig = signature(attr, fn).replace("(self, ", "(").replace("(self)", "()").replace("(cls, ", "(")
        out += [f"#### {name}.{attr}", "", sig, ""]
        if d := doc(fn):
            out += [d, ""]
    if name in ("Toskar", "AsyncToskar"):
        out += ["#### " + name + ".api", "",
                "Every route of the API, one method each, such as `toskar.api.list_models()`: [api.md](api.md).", ""]
    return out


def render(name: str) -> list[str]:
    obj = getattr(toskar, name)
    if inspect.isclass(obj):
        return render_class(name, obj)
    if callable(obj):
        out = [f"### {name}", "", signature(name, obj), ""]
        return out + ([doc(obj), ""] if doc(obj) else [])
    source_docs = attribute_docs_module(name)
    return [f"### {name}", "", f"```python\n{name} = {obj!r}\n```", "", source_docs, ""]


def attribute_docs_module(name: str) -> str:
    for mod in (toskar._connect, toskar._generated.codes):  # type: ignore[attr-defined]
        tree = ast.parse(inspect.getsource(mod))
        for a, b in zip(tree.body, tree.body[1:]):
            if isinstance(a, (ast.Assign, ast.AnnAssign)):
                target = a.targets[0] if isinstance(a, ast.Assign) else a.target
                if getattr(target, "id", None) == name and isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant):
                    return inspect.cleandoc(str(b.value.value))
            if isinstance(a, ast.Assign) and getattr(a.targets[0], "id", None) == name:
                comment = inspect.getsource(mod).splitlines()[a.lineno - 2].strip()
                if comment.startswith("#"):
                    return comment.lstrip("# ")
    return ""


def readme() -> str:
    out = ["# Python reference", "", "*Generated from the SDK's docstrings by `python/scripts/reference.py`.*", ""]
    out += [doc(toskar), ""]
    out += ["The routes themselves, with every field: [toskar.ai/developers/api](https://toskar.ai/developers/api).", ""]
    out += ["## Contents", ""]
    for title, names in SECTIONS:
        out.append(f"- **{title}:** " + ", ".join(f"[{n}](#{anchor(n)})" for n in names))
    out += ["- [Every route on `toskar.api`](api.md)", "- [Error codes](errors.md)", ""]
    for title, names in SECTIONS:
        out += [f"## {title}", ""]
        for n in names:
            out += render(n)
    return "\n".join(out).rstrip() + "\n"


def api() -> str:
    out = ["# Every route on toskar.api", "",
           "*Generated by `python/scripts/reference.py`.*", "",
           "One method per route, named after its operation in Core's API spec. `AsyncToskar`'s `api` has the same "
           "methods, awaited. Methods with a body take it as `body=`, a dict; answers are the `toskar.models` types.",
           "", "| Method | Route | |", "| --- | --- | --- |"]
    for name, fn in operations.Api.__dict__.items():
        if name.startswith("_"):
            continue
        src = inspect.getsource(fn)
        m = re.search(r'"(GET|POST|PUT|PATCH|DELETE)", f?"([^"]+)"', src)
        route = f"`{m.group(1)} {m.group(2)}`" if m else ""
        sig = signature(name, fn).splitlines()[1].removeprefix("def ").replace("(self, ", "(").replace("(self)", "()")
        sig = re.sub(r"\) -> .*$", ")", sig)
        summary = (inspect.getdoc(fn) or "").splitlines()[0] if inspect.getdoc(fn) else ""
        out.append(f"| `{sig.replace('|', chr(92) + '|')}` | {route} | {summary.replace('|', '/')} |")
    return "\n".join(out) + "\n"


def errors() -> str:
    out = ["# Error codes", "", "*Generated by `python/scripts/reference.py` from Core's error catalog.*", "",
           doc(toskar.ErrorCodes), "",
           "```python", "except ToskarError as err:", "    if err.code == ErrorCodes.NO_MODEL_INSTALLED:", "        ...", "```", "",
           "| Code | What it means |", "| --- | --- |"]
    for code, meaning in attribute_docs(toskar.ErrorCodes).items():
        meaning = "" if meaning.strip() == "{{detail}}" else meaning.replace("|", "/").replace("\n", " ")
        out.append(f"| `{code}` | {meaning} |")
    return "\n".join(out) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "README.md").write_text(readme())
    (OUT / "api.md").write_text(api())
    (OUT / "errors.md").write_text(errors())


if __name__ == "__main__":
    main()
