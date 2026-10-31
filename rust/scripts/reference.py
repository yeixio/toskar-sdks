"""Writes reference/rust/ from the Rust SDK's doc comments:

- README.md: every public item of the SDK's own code, in sections, as the
  other SDKs' references are;
- api.md: every route on toskar.api(), from the generated api.rs;
- errors.md: the error codes, Toskar Core's and the SDK's own.

It reads the sources, not rustdoc, so the sync workflow runs it without
Rust: every public item says `pub`, with its `///` comment before it. A
public item with no section stops it, so nothing new ships undocumented.
docs.rs has the same, once the crate is published.

    python3 rust/scripts/reference.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ERRORS = ROOT.parent / "spec" / "errors.json"
OUT = ROOT.parent / "reference" / "rust"

# The files of the SDK's own code, and the module each one's items are in
# (lib.rs re-exports the rest at the crate's root).
FILES = {
    "client.rs": "", "error.rs": "", "api.rs": "", "connect.rs": "", "discover.rs": "",
    "records.rs": "records::", "generated/codes.rs": "",
}

# Each section's items, by path. A type brings its fields, variants, and
# methods along, except those listed in a section of their own.
SECTIONS = [
    ("Connecting", ["Client", "Builder", "ChatEvent", "Api", "DEFAULT_URL"]),
    ("Errors", ["Error", "Result", "error_codes"]),
    ("Pairing and reaching a computer from anywhere", [
        "pair", "Builder::device", "Client::path", "Client::reconnect", "Device", "Route", "ConnectionPath",
        "records", "records::AddressRecord", "records::route_id", "records::pin_of", "records::short_pin",
        "records::open",
    ]),
    ("Finding computers on the network", ["find", "SERVICE_TYPE", "DiscoveredComputer"]),
    ("The contract", ["CONTRACT_VERSION"]),
]

ITEM = re.compile(r"^(?P<indent>\s*)pub\s+(?P<rest>(?:async\s+)?(?:fn|struct|enum|const|type|mod|trait)\b.*)$")
FIELD = re.compile(r"^\s*pub\s+(?:r#)?(?P<name>\w+)\s*:\s*(?P<type>.+?),?$")
VARIANT = re.compile(r"^\s*(?P<name>[A-Z]\w*)\s*(?P<rest>[({].*|,)?$")
IMPL = re.compile(r"^impl(?:<[^>]*>)?\s+(?P<name>\w+)(?:<[^>]*>)?\s*\{")


@dataclass
class Item:
    path: str
    title: str
    signature: str
    doc: str
    kind: str


def strip_code(line: str) -> str:
    """A line without its strings, characters, and // comment, so braces in them don't count."""
    line = re.sub(r'r#*"[^"]*"#*', '""', line)
    line = re.sub(r'"(?:[^"\\]|\\.)*"', '""', line)
    line = re.sub(r"'(?:[^'\\]|\\.)'", "''", line)
    return re.sub(r"//.*", "", line)


def header(lines: list[str], i: int) -> tuple[str, int]:
    """The item starting at lines[i], to where its body starts: rustfmt runs
    long parameter lists over lines. Answers it and the line it ends on."""
    out = []
    depth = 0
    for j in range(i, len(lines)):
        text = strip_code(lines[j]) if j > i else lines[j]
        for k, c in enumerate(text):
            if c in "([<":
                depth += 1
            elif c in ")]>" and not (c == ">" and text[k - 1:k] in "-="):
                depth -= 1
            elif depth == 0 and c in "{;":
                out.append(text[:k])
                return " ".join(" ".join(out).split()), j
        out.append(text)
    return " ".join(" ".join(out).split()), len(lines) - 1


def tidy(sig: str) -> str:
    sig = re.sub(r"\(\s+", "(", sig)
    sig = re.sub(r",?\s*\)", ")", sig)
    sig = re.sub(r"\(&self,\s*\)", "(&self)", sig)
    sig = re.sub(r"\bmut self\b", "self", sig)
    sig = sig.replace("crate::", "toskar::")
    return " ".join(sig.split())


def param_names(sig: str) -> list[str]:
    inner = sig[sig.index("(") + 1:]
    depth, start, params = 0, 0, []
    for k, c in enumerate(inner):
        if c in "(<[":
            depth += 1
        elif c in ")>]" and not (c == ">" and inner[k - 1:k] == "-"):
            if depth == 0:
                params.append(inner[start:k])
                break
            depth -= 1
        elif c == "," and depth == 0:
            params.append(inner[start:k])
            start = k + 1
    names = []
    for p in params:
        p = p.strip()
        if p and "self" not in p.split(":")[0]:
            names.append(p.split(":")[0].strip().removeprefix("mut "))
    return names


def doc_markdown(comment: list[str]) -> str:
    """A /// comment as Markdown: rustdoc's own, without its links' targets or hidden example lines."""
    lines = [re.sub(r"^\s*///\s?", "", line) for line in comment]
    out, in_code = [], False
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
            out.append("```rust" if in_code else "```")
            continue
        if in_code and (line == "#" or line.startswith("# ")):
            continue
        out.append(line)
    md = "\n".join(out).strip()
    # Intra-doc links read the same as code.
    md = re.sub(r"\[(`[^`]+`)\](?:\([^)]*\))?", r"\1", md)
    md = re.sub(r"`(?:crate|toskar)::", "`", md)
    return md


def parse(path: Path, module: str) -> list[Item]:
    """The public items of a file, with their owners' paths."""
    lines = path.read_text().split("\n")
    found: list[Item] = []
    owners: list[tuple[int, str | None, str]] = []  # brace depth of the body, path (None: not public), kind
    pending: tuple[str | None, str] | None = None
    depth = 0
    comment: list[str] = []
    derive = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("///"):
            comment.append(line)
            i += 1
            continue
        if stripped.startswith("#[derive("):
            derive = stripped
            i += 1
            continue
        owner = owners[-1] if owners else None
        hidden = owner is not None and owner[1] is None
        end = i
        if stripped.startswith(("#[", "//")) or not stripped:
            i += 1
            continue
        if (m := IMPL.match(stripped)) is not None and not hidden:
            # A trait's impl, such as Display, says what it is in its type's docs.
            pending = (module + m.group("name"), "impl")
        elif (m := ITEM.match(line)) is not None and not hidden:
            sig, end = header(lines, i)
            sig = tidy(sig)
            rest = m.group("rest")
            kind = re.match(r"(?:async\s+)?(\w+)", rest).group(1)
            name = re.match(r"(?:async\s+)?\w+\s+(\w+)", rest).group(1)
            in_impl = owner is not None and owner[1] is not None and owner[2] in ("impl", "mod")
            p = f"{owner[1]}::{name}" if in_impl else module + name
            title = p
            if kind == "fn":
                title = f"{p}({', '.join(param_names(sig))})"
            elif kind in ("struct", "enum") and derive:
                # What it derives says what it can do, such as Serialize.
                sig = f"{derive}\n{sig}"
            found.append(Item(p, title, sig, doc_markdown(comment), kind))
            if kind in ("struct", "enum", "mod", "trait") and "{" in strip_code(lines[end]):
                pending = (p, kind)
        elif owner is not None and owner[1] is not None and owner[2] == "struct" and (f := FIELD.match(line)):
            p = f"{owner[1]}::{f.group('name')}"
            found.append(Item(p, p, f"pub {f.group('name')}: {f.group('type').rstrip(',')}", doc_markdown(comment), "field"))
        elif owner is not None and owner[1] is not None and owner[2] == "enum" and (v := VARIANT.match(line)):
            p = f"{owner[1]}::{v.group('name')}"
            found.append(Item(p, p, stripped.rstrip(","), doc_markdown(comment), "variant"))
        elif re.match(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:struct|enum|mod|fn|trait|impl)\b", line):
            # Not public, or in something that isn't: nothing in it is.
            pending = (None, "private")
        comment = []
        derive = ""
        for x in lines[i:end + 1]:
            for c in strip_code(x):
                if c == "{":
                    depth += 1
                    owners.append((depth, *(pending or (owner[1] if owner and owner[2] == "impl" else None, "block"))))
                    pending = None
                elif c == "}":
                    if owners and owners[-1][0] == depth:
                        owners.pop()
                    depth -= 1
        i = end + 1
    return found


def anchor(title: str, seen: dict[str, int]) -> str:
    """GitHub's anchor for a heading."""
    slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
    n = seen.get(slug, 0)
    seen[slug] = n + 1
    return slug if n == 0 else f"{slug}-{n}"


def entry(s: Item, level: int) -> list[str]:
    out = [f"{'#' * level} {s.title}", ""]
    if s.doc:
        out += [s.doc, ""]
    out += ["```rust", s.signature, "```", ""]
    return out


def readme(items: list[Item], module_docs: dict[str, str]) -> tuple[str, int]:
    paths = {s.path for s in items}
    placed = {name for _, names in SECTIONS for name in names}
    # The error codes are their own page.
    hidden = {p for p in paths if p.startswith("error_codes::")}

    def parent(p: str) -> str:
        return p.rsplit("::", 1)[0] if "::" in p else ""

    def members(owner: str) -> list[Item]:
        return [s for s in items if parent(s.path) == owner and s.path not in placed and s.path not in hidden]

    body, contents, seen, done = [], [], {}, set()
    for title, names in SECTIONS:
        body += [f"## {title}", ""]
        links = []
        for name in names:
            if name in module_docs:
                group = [Item(name, name, f"pub mod {name}", module_docs[name], "mod")]
            else:
                group = [s for s in items if s.path == name]
            if not group:
                sys.exit(f"{name} isn't a public item any more: update SECTIONS in {Path(__file__).name}")
            for s in group:
                links.append(f"[{s.title.split('(')[0]}](#{anchor(s.title, seen)})")
                body += entry(s, 3)
            done.add(name)
            if name == "error_codes":
                body += ["Every code, with its text: [the error codes](errors.md).", ""]
            if name == "Api":
                body += ["Its methods: [every route on `toskar.api()`](api.md).", ""]
                continue
            for m in members(name):
                done.add(m.path)
                anchor(m.title, seen)
                body += entry(m, 4)
        contents.append(f"- **{title}:** " + ", ".join(links))
    missing = sorted(p for p in paths if p not in done and p not in hidden and parent(p) != "Api")
    if missing:
        sys.exit("no section for: " + ", ".join(missing) + f" (add them to SECTIONS in {Path(__file__).name})")
    text = [
        "# Rust reference", "",
        "*Generated from the crate's doc comments by `rust/scripts/reference.py`.*", "",
        "The official Rust SDK for Toskar: local AI across your own computers. Every item is at the crate's root, "
        "but for `records` and `models`.", "",
        "```rust",
        "let toskar = toskar::Client::new()?;",
        'let request = ChatRequest { message: "Plan a three-day trip to Juneau".into(), ..Default::default() };',
        "let mut events = toskar.chat_stream(&request).await?;",
        "while let Some(event) = events.next().await {",
        "    if let ChatEvent::Token(text) = event? {",
        '        print!("{text}");',
        "    }",
        "}",
        "```", "",
        "`toskar.api()` has [every route](api.md), generated from Toskar Core's API spec, and its models are in "
        "`toskar::models`. The routes themselves, with every field: "
        "[toskar.ai/developers/api](https://toskar.ai/developers/api).", "",
        "## Contents", "", *contents, "- [Every route on `toskar.api()`](api.md)", "- [Error codes](errors.md)", "",
        *body,
    ]
    return "\n".join(text).rstrip() + "\n", len(done)


def api(items: list[Item]) -> tuple[str, int]:
    routes = [s for s in items if s.path.startswith("Api::")]
    out = [
        "# Every route on `toskar.api()`", "",
        "*Generated from `src/generated/api.rs`, which `rust/scripts/generate.py` writes from Toskar Core's API "
        "spec.*", "",
        "One async method for each operation, named after its operationId in snake case. An error answer is a "
        "`toskar::Error`. The models are in `toskar::models`, and every field is described at "
        "[toskar.ai/developers/api](https://toskar.ai/developers/api).", "",
    ]
    for s in sorted(routes, key=lambda s: s.title):
        doc = s.doc.split("\n\n", 1)
        out += [f"### {s.title.removeprefix('Api::')}", "", doc[0], ""]
        if len(doc) > 1:
            out += [doc[1], ""]
        out += ["```rust", s.signature, "```", ""]
    return "\n".join(out).rstrip() + "\n", len(routes)


def errors(sources: list[Path]) -> tuple[str, int]:
    catalog = json.loads(ERRORS.read_text())
    rows = [(f"`error_codes::{code}`", re.sub(r"\s+", " ", str(text))) for code, text in sorted(catalog.items())]
    # Each code's message, the one it's made with most.
    said: dict[str, dict[str, int]] = {}
    for path in sources:
        text = path.read_text()
        for m in re.finditer(
                r'Error::new\(\s*\w+,\s*"([A-Z][A-Z_]*)",\s*(?:format!\(\s*)?"((?:[^"\\]|\\.)*)"', text):
            message = re.sub(r"\{[^}]*\}", "…", m.group(2))
            counts = said.setdefault(m.group(1), {})
            counts[message] = counts.get(message, 0) + 1
    own = {code: max(counts, key=lambda k: (counts[k], k)) for code, counts in said.items()}
    own["HTTP_<status>"] = "Toskar answered <status> with a body that isn't Toskar's"
    # Made in one place for every request, with format!, so it's counted once.
    own["CONNECTION_FAILED"] = "Couldn't reach Toskar at …: …"
    for code in sorted(own):
        if code not in catalog:
            rows.append((f"`{code}` (the SDK's own)", own[code]))
    lines = [
        "# Rust error codes", "",
        "*Generated by `rust/scripts/reference.py` from Toskar Core's error catalog and the SDK's own codes.*", "",
        "The codes Toskar Core and the SDK answer errors with, as `Error::code`, with each one's English text. "
        "Core's are constants in `error_codes`; the SDK's own are for what goes wrong before Core answers. A newer "
        "Core may answer with a code this list doesn't have yet.", "",
        "| Code | Text |", "| --- | --- |",
        *[f"| {c} | {t.replace('|', chr(92) + '|')} |" for c, t in rows],
    ]
    return "\n".join(lines) + "\n", len(rows)


def module_doc(path: Path) -> str:
    """A file's //! comment, as its module's doc."""
    return doc_markdown([l.replace("//!", "///", 1) for l in path.read_text().split("\n") if l.startswith("//!")])


def main() -> int:
    items = [s for name, module in FILES.items() for s in parse(SRC / name, module)]
    OUT.mkdir(parents=True, exist_ok=True)
    text, n = readme(items, {"records": module_doc(SRC / "records.rs")})
    (OUT / "README.md").write_text(text)
    text, routes = api(parse(SRC / "generated" / "api.rs", ""))
    (OUT / "api.md").write_text(text)
    text, codes = errors([SRC / name for name in FILES if not name.startswith("generated")])
    (OUT / "errors.md").write_text(text)
    print(f"reference/rust: {n} items, {routes} routes, {codes} codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
