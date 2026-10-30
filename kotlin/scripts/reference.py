"""Writes reference/kotlin/ from the Kotlin SDK's KDoc:

- README.md: every public class, function, and property of the SDK's own
  code, in sections, as the other SDKs' references are;
- api.md: every route on toskar.api, from the generated Api.kt;
- errors.md: the error codes, Toskar Core's and the SDK's own.

The SDK builds in explicit API mode, so every public declaration says
`public`: that's what this reads, with the KDoc before it. A public symbol
with no section stops it, so nothing new ships undocumented. Standard
library only, so the sync workflow runs it without a JDK.

    python3 kotlin/scripts/reference.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "main" / "kotlin" / "ai" / "toskar"
ERRORS = ROOT.parent / "spec" / "errors.json"
OUT = ROOT.parent / "reference" / "kotlin"

# Each section's symbols. A class brings its members along, except those
# listed in a section of their own.
SECTIONS = [
    ("Connecting", ["Toskar", "ChatEvent", "EventStream"]),
    ("Errors", ["ToskarException", "ErrorCodes"]),
    ("Pairing and reaching a computer from anywhere", [
        "Toskar.pair(address, code, deviceName, confirm)", "Toskar.constructor(device, retries, timeout)",
        "Toskar.path", "Toskar.reconnect()", "Device", "Route", "ConnectionPath", "ShortPinCheck", "Records",
        "AddressRecord",
    ]),
    ("Finding computers on the network", ["Toskar.find(timeout)", "Toskar.SERVICE_TYPE", "DiscoveredComputer"]),
    ("The contract", ["CONTRACT_VERSION"]),
]

CLASS = re.compile(
    r"^(?P<indent>\s*)(?:@\S+\s+)*(?:(?P<vis>public|internal|private|protected)\s+)?"
    r"(?:(?:data|sealed|enum|abstract|open|inner|value)\s+)*(?P<kind>fun interface|class|object|interface)\s+(?P<name>\w+)")
COMPANION = re.compile(r"^(?P<indent>\s*)(?:(?:public|internal|private)\s+)?companion object\b")
PUBLIC = re.compile(r"^(?P<indent>\s*)(?:@\S+(?:\([^)]*\))?\s+)*public\s+(?P<rest>.*)$")
ENUM_ENTRY = re.compile(r"^(?P<indent>\s+)(?P<name>[A-Z][A-Z0-9_]*)\b")


@dataclass
class Symbol:
    path: str
    title: str
    signature: str
    doc: str
    kind: str
    members: list["Symbol"] = field(default_factory=list)


def signature(lines: list[str], i: int, start: int, commas: bool = True) -> str:
    """The declaration from lines[i][start:], to where its body or default
    value starts, or the end of its parameter or line."""
    out = []
    depth = 0
    for line in lines[i:]:
        text = line[start:] if not out else line
        start = 0
        j = 0
        while j < len(text):
            c = text[j]
            if c in "([":
                depth += 1
            elif c in ")]":
                depth -= 1
                if depth < 0:
                    out.append(text[:j])
                    return " ".join(" ".join(out).split())
            elif depth == 0 and (c == "{" or (c == "," and commas) or (c == "=" and text[j + 1:j + 2] != "=" and text[j - 1:j] not in "!<>=")):
                out.append(text[:j])
                return " ".join(" ".join(out).split())
            j += 1
        out.append(text)
        if depth == 0:
            break
    return " ".join(" ".join(out).split())


def param_list(sig: str) -> str:
    """The text between a signature's first ( and the ) that closes it."""
    start = sig.index("(")
    depth = 0
    for i in range(start, len(sig)):
        depth += {"(": 1, ")": -1}.get(sig[i], 0)
        if depth == 0:
            return sig[start + 1:i]
    return sig[start + 1:]


def tidy(sig: str) -> str:
    """A signature as a reader needs it: no comments or annotations, no
    constructor they can't call, and no constructor delegation."""
    sig = re.sub(r"/\*.*?\*/", "", sig)
    sig = re.sub(r"@[\w.]+(\([^)]*\))?\s*", "", sig)
    sig = re.sub(r"\bpublic\s+", "", sig)
    if (m := re.search(r"\s*\b(?:internal|private|protected)\s+constructor\s*\(", sig)) is not None:
        inner = param_list(sig[m.start():])
        end = sig.index(inner, m.start()) + len(inner) + 1
        sig = sig[:m.start()] + sig[end:]
    if sig.startswith("constructor"):
        inner = param_list(sig)
        sig = f"constructor({inner})"
    sig = re.sub(r"\s+get\(\)$", "", sig)
    sig = re.sub(r"\(\s+", "(", sig)
    sig = re.sub(r",?\s*\)", ")", sig)
    return " ".join(sig.split())


def kdoc(comment: list[str]) -> str:
    """A KDoc comment as Markdown: its text, then its parameters as a list."""
    text = []
    for line in comment:
        line = line.strip()
        line = re.sub(r"^/\*\*\s?|\s?\*/$", "", line)
        line = re.sub(r"^\*\s?", "", line)
        text.append(line)
    body, params = [], []
    for line in text:
        m = re.match(r"@param (\w+) (.*)", line)
        if m:
            params.append([m.group(1), m.group(2)])
        elif params and line and not line.startswith("@"):
            params[-1][1] += " " + line.strip()
        else:
            body.append(line)
    md = "\n".join(body).strip()
    md = code_links(md)
    if params:
        md += "\n\nParameters:\n\n" + "\n".join(f"- `{p}`: {code_links(d)}" for p, d in params)
    return md


def code_links(text: str) -> str:
    """[Name] links to the reference's own names; as code, they read the same."""
    return re.sub(r"\[([\w.]+)\](?!\()", r"`\1`", text)


def parse(path: Path) -> list[Symbol]:
    """The public declarations of a file, with their owners' paths."""
    lines = path.read_text().split("\n")
    found: list[Symbol] = []
    owners: list[tuple[int, str | None, str]] = []  # indent, path (None: not public), kind
    comment: list[str] = []
    in_comment = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_comment:
            comment.append(line)
            in_comment = "*/" not in line
            continue
        if stripped.startswith("/**"):
            comment = [line]
            in_comment = "*/" not in stripped[3:]
            continue
        # The end of a multi-line header or body isn't a declaration, and
        # leaves its owner as it is.
        if (not stripped or stripped.startswith(("//", ")", "}"))
                or stripped.startswith("@") and not PUBLIC.match(line)):
            continue
        indent = len(line) - len(line.lstrip())
        while owners and owners[-1][0] >= indent:
            owners.pop()
        owner = owners[-1] if owners else None
        if owner is not None and owner[1] is None:
            # Inside a type that isn't public: nothing here is.
            if CLASS.match(line) or COMPANION.match(line):
                owners.append((indent, None, ""))
            comment = []
            continue
        prefix = owner[1] + "." if owner else ""
        if COMPANION.match(line):
            owners.append((indent, owner[1] if owner else "", "companion"))
            comment = []
            continue
        if owner and owner[2] == "enum class" and (m := ENUM_ENTRY.match(line)) and not PUBLIC.match(line):
            name = m.group("name")
            found.append(Symbol(prefix + name, prefix + name, stripped.rstrip(",;"), kdoc(comment), "entry"))
            comment = []
            continue
        if (m := CLASS.match(line)) is not None:
            public = m.group("vis") == "public"
            kind = "enum class" if re.search(r"\benum\s+class\b", line) else m.group("kind")
            p = prefix + m.group("name")
            owners.append((indent, p if public else None, kind))
            if public:
                rest = PUBLIC.match(line).group("rest")
                # A class's supertypes are a list: its header ends at its body.
                sig = tidy(signature(lines, i, len(line) - len(rest), commas=False))
                found.append(Symbol(p, p, re.sub(r"\s+constructor\s*\(", "(", sig), kdoc(comment), kind))
            comment = []
            continue
        if (m := PUBLIC.match(line)) is not None:
            rest = m.group("rest")
            sig = signature(lines, i, len(line) - len(rest))
            if (c := re.match(r"(?:@\S+\s+)*constructor\s*\(", rest)) is not None:
                params = re.findall(r"(?:^|,)\s*(?:va[lr]\s+)?(\w+)\s*:", tidy(param_list(sig)))
                name = f"constructor({', '.join(params)})"
            elif (f := re.match(r"(?:(?:override|inline|operator|suspend)\s+)*fun\s+(?:<[^>]*>\s*)?(\w+)\s*\(", rest)) is not None:
                params = re.findall(r"(?:^|,)\s*(\w+)\s*:", re.sub(r"<[^>]*>", "", param_list(sig)))
                name = f"{f.group(1)}({', '.join(params)})"
            elif (v := re.match(r"(?:(?:override|const|lateinit)\s+)*(?:val|var)\s+`?(\w+)`?", rest)) is not None:
                name = v.group(1)
            else:
                comment = []
                continue
            found.append(Symbol(prefix + name, prefix + name, tidy(sig), kdoc(comment), "member"))
        comment = []
    return found


def anchor(title: str, seen: dict[str, int]) -> str:
    """GitHub's anchor for a heading."""
    slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
    n = seen.get(slug, 0)
    seen[slug] = n + 1
    return slug if n == 0 else f"{slug}-{n}"


def entry(s: Symbol, level: int) -> list[str]:
    out = [f"{'#' * level} {s.title}", ""]
    if s.doc:
        out += [s.doc, ""]
    out += ["```kotlin", s.signature, "```", ""]
    return out


def readme(symbols: list[Symbol]) -> tuple[str, int]:
    by_path = {}
    for s in symbols:
        # Overloads share a path; the first keeps it, the rest are numbered.
        p = s.path
        n = 1
        while p in by_path:
            n += 1
            p = f"{s.path}#{n}"
        s.path = p
        by_path[p] = s
    placed = {name for _, names in SECTIONS for name in names}
    # ErrorCodes' constants are the error codes page.
    placed |= {p for p in by_path if p.startswith("ErrorCodes.")}

    def members(parent: str) -> list[Symbol]:
        depth = parent.count(".") + 1
        return [s for p, s in by_path.items() if p.startswith(parent + ".") and p.count(".") == depth and p not in placed]

    body, contents, seen, done = [], [], {}, set()
    for title, names in SECTIONS:
        body += [f"## {title}", ""]
        links = []
        for name in names:
            s = by_path.get(name)
            if s is None:
                sys.exit(f"{name} isn't a public symbol any more: update SECTIONS in {Path(__file__).name}")
            body += entry(s, 3)
            done.add(name)
            links.append(f"[{name.split('(')[0]}](#{anchor(s.title, seen)})")
            if name == "ErrorCodes":
                body += ["Every code, with its text: [the error codes](errors.md).", ""]
            for m in members(name):
                done.add(m.path)
                anchor(m.title, seen)
                body += entry(m, 4)
                for n in members(m.path):
                    done.add(n.path)
                    anchor(n.title, seen)
                    body += entry(n, 5)
        contents.append(f"- **{title}:** " + ", ".join(links))
    missing = sorted(p for p in by_path if p not in done and p not in placed)
    if missing:
        sys.exit("no section for: " + ", ".join(missing) + f" (add them to SECTIONS in {Path(__file__).name})")
    text = [
        "# Kotlin and Java reference", "",
        "*Generated from the SDK's KDoc by `kotlin/scripts/reference.py`.*", "",
        "The official Kotlin and Java SDK for Toskar: local AI across your own computers.", "",
        "```kotlin",
        "val toskar = Toskar()",
        'toskar.chatStream(ChatRequest(message = "Plan a three-day trip to Juneau")).use { events ->',
        "    for (event in events) if (event is ChatEvent.Token) print(event.text)",
        "}",
        "```", "",
        "`toskar.api` has [every route](api.md), generated from Toskar Core's API spec, and its models are in "
        "`ai.toskar.api`. The routes themselves, with every field: "
        "[toskar.ai/developers/api](https://toskar.ai/developers/api).", "",
        "## Contents", "", *contents, "- [Every route on `toskar.api`](api.md)", "- [Error codes](errors.md)", "",
        *body,
    ]
    return "\n".join(text).rstrip() + "\n", len(done)


def api(symbols: list[Symbol]) -> tuple[str, int]:
    routes = [s for s in symbols if s.path.startswith("Api.")]
    out = [
        "# Every route on `toskar.api`", "",
        "*Generated from `api/Api.kt`, which `kotlin/scripts/generate.py` writes from Toskar Core's API spec.*", "",
        "One method for each operation, named after its operationId. Each waits for its answer, so call it off the "
        "main thread; an error answer throws a `ToskarException`. The models are in `ai.toskar.api`, and every field "
        "is described at [toskar.ai/developers/api](https://toskar.ai/developers/api).", "",
    ]
    for s in sorted(routes, key=lambda s: s.title.lower()):
        title = s.title.removeprefix("Api.")
        doc = s.doc.split("\n\n", 1)
        out += [f"### {title}", "", doc[0], ""]
        if len(doc) > 1:
            out += [doc[1], ""]
        out += ["```kotlin", s.signature, "```", ""]
    return "\n".join(out).rstrip() + "\n", len(routes)


def errors(sources: list[Path]) -> tuple[str, int]:
    catalog = json.loads(ERRORS.read_text())
    rows = [(f"`ErrorCodes.{code}`", re.sub(r"\s+", " ", str(text))) for code, text in sorted(catalog.items())]
    # Each code's message, the one it's thrown with most.
    said: dict[str, dict[str, int]] = {}
    for path in sources:
        text = path.read_text()
        for m in re.finditer(r'ToskarException\(\s*\w+,\s*"([A-Z][A-Z_]*)",\s*\n?\s*"((?:[^"\\]|\\.)*)"', text):
            message = re.sub(r"\$\{[^}]*\}|\$\w+", "…", m.group(2))
            counts = said.setdefault(m.group(1), {})
            counts[message] = counts.get(message, 0) + 1
    own = {code: max(counts, key=lambda k: (counts[k], k)) for code, counts in said.items()}
    own["HTTP_<status>"] = "Toskar answered <status> with a body that isn't Toskar's"
    for code in sorted(own):
        if code not in catalog:
            rows.append((f"`{code}` (the SDK's own)", own[code]))
    lines = [
        "# Kotlin and Java error codes", "",
        "*Generated by `kotlin/scripts/reference.py` from Toskar Core's error catalog and the SDK's own codes.*", "",
        "The codes Toskar Core and the SDK answer errors with, as `ToskarException.code`, with each one's English "
        "text. Core's are constants on `ErrorCodes`; the SDK's own are for what goes wrong before Core answers. A "
        "newer Core may answer with a code this list doesn't have yet.", "",
        "| Code | Text |", "| --- | --- |",
        *[f"| {c} | {t.replace('|', chr(92) + '|')} |" for c, t in rows],
    ]
    return "\n".join(lines) + "\n", len(rows)


def main() -> int:
    own = sorted(p for p in SRC.glob("*.kt"))
    symbols = [s for p in own for s in parse(p)]
    OUT.mkdir(parents=True, exist_ok=True)
    text, n = readme(symbols)
    (OUT / "README.md").write_text(text)
    text, routes = api(parse(SRC / "api" / "Api.kt"))
    (OUT / "api.md").write_text(text)
    text, codes = errors(own)
    (OUT / "errors.md").write_text(text)
    print(f"reference/kotlin: {n} symbols, {routes} routes, {codes} codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
