"""Writes reference/dotnet/ from the .NET SDK's XML doc comments:

- README.md: every public type and member of the SDK's own code, in
  sections, as the other SDKs' references are;
- api.md: every route on toskar.Api, from the generated ToskarApi.cs;
- errors.md: the error codes, Toskar Core's and the SDK's own.

It reads the sources, not a build, so the sync workflow runs it without the
.NET SDK: every public declaration says `public`, with its `///` comment
before it. A public symbol with no section stops it, so nothing new ships
undocumented.

    python3 dotnet/scripts/reference.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "Toskar"
ERRORS = ROOT.parent / "spec" / "errors.json"
OUT = ROOT.parent / "reference" / "dotnet"

# Each section's symbols, by path; overloads share one. A type brings its
# members along, except those listed in a section of their own.
SECTIONS = [
    ("Connecting", ["ToskarClient", "ToskarOptions", "ChatEvent", "ToskarApi"]),
    ("Errors", ["ToskarException", "ErrorCodes"]),
    ("Pairing and reaching a computer from anywhere", [
        "ToskarClient.PairAsync", "ToskarClient.new(device, options)", "ToskarClient.Path",
        "ToskarClient.ReconnectAsync", "Device", "Route", "ConnectionPath", "Records", "AddressRecord",
    ]),
    ("Finding computers on the network", ["ToskarClient.FindAsync", "ToskarClient.ServiceType", "DiscoveredComputer"]),
    ("The contract", ["Contract"]),
]

TYPE = re.compile(
    r"^\s*(?P<mods>(?:(?:public|internal|private|protected|static|sealed|abstract|partial|readonly)\s+)*)"
    r"(?P<kind>record struct|record|class|struct|interface|enum)\s+(?P<name>\w+)")
MODIFIERS = re.compile(
    r"^(?:(?:public|static|sealed|abstract|virtual|override|readonly|const|async|required|new|partial|extern)\s+)*")


@dataclass
class Symbol:
    path: str
    title: str
    signature: str
    doc: str
    kind: str


def strip_code(line: str) -> str:
    """A line without its strings, characters, and // comment, so braces in them don't count."""
    line = re.sub(r'\$?@?"(?:[^"\\]|\\.)*"', '""', line)
    line = re.sub(r"'(?:[^'\\]|\\.)'", "''", line)
    return re.sub(r"//.*", "", line)


def header(lines: list[str], i: int) -> tuple[str, int]:
    """The declaration starting at lines[i], to where its body starts: its
    parameters may run over lines. Answers it and the line it ends on."""
    out = []
    depth = 0
    for j in range(i, len(lines)):
        text = strip_code(lines[j]) if j > i else lines[j]
        for k, c in enumerate(text):
            if c in "(<[":
                depth += 1
            elif c in ")>]":
                depth -= 1
            elif depth == 0 and (c in "{;" or text[k:k + 2] == "=>" or (c == "=" and text[k + 1:k + 2] != "=")):
                out.append(text[:k])
                return " ".join(" ".join(out).split()), j
        out.append(text)
        if depth <= 0 and j > i and not text.rstrip().endswith((",", "(")):
            break
    return " ".join(" ".join(out).split()), j


def split_params(params: str) -> list[str]:
    """A parameter list's parameters, split at commas outside <> and ()."""
    out, depth, start = [], 0, 0
    for k, c in enumerate(params):
        if c in "<([":
            depth += 1
        elif c in ">)]":
            depth -= 1
        elif c == "," and depth == 0:
            out.append(params[start:k])
            start = k + 1
    if params[start:].strip():
        out.append(params[start:])
    return [p.strip() for p in out]


def tidy(sig: str) -> str:
    """A signature as a reader needs it: no attributes, no public, and no
    constructor chaining."""
    sig = re.sub(r"\[[A-Za-z][^\]]*\]\s*", "", sig)
    sig = re.sub(r"\b(?:public|async|partial)\s+", "", sig)
    sig = re.sub(r"\)\s*:\s*(?:this|base)\s*\(.*$", ")", sig)
    sig = re.sub(r"\(\s+", "(", sig)
    return " ".join(sig.split())


def param_names(sig: str) -> list[str]:
    inner = sig[sig.index("(") + 1:sig.rindex(")")]
    names = []
    for p in split_params(inner):
        p = re.sub(r"^(?:\[[A-Za-z][^\]]*\]\s*)+", "", p).split("=")[0].strip()
        names.append(re.findall(r"@?\w+", p)[-1].lstrip("@"))
    return names


def doc_markdown(comment: list[str]) -> str:
    """A /// comment as Markdown: its summary and remarks, then its parameters as a list."""
    # A blank /// line is a paragraph break.
    xml = "\n".join(re.sub(r"^\s*///\s?", "", line) for line in comment)

    def inline(text: str) -> str:
        text = re.sub(r'<see cref="(?:\w:)?([^"]+)"\s*/>', lambda m: f"`{m.group(1).split('(')[0]}`", text)
        text = re.sub(r'<(?:paramref|typeparamref) name="([^"]+)"\s*/>', r"`\1`", text)
        text = re.sub(r"<c>(.*?)</c>", r"`\1`", text)
        text = re.sub(r"<see href=\"([^\"]+)\">(.*?)</see>", r"[\2](\1)", text)
        text = re.sub(r"</?para>", "\n\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        paragraphs = re.split(r"\n\s*\n", text)
        return html.unescape("\n\n".join(" ".join(p.split()) for p in paragraphs if p.strip()))

    parts = []
    for tag in ("summary", "remarks", "returns"):
        if (m := re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.S)) is not None:
            text = inline(m.group(1))
            parts.append(f"Returns {text[0].lower()}{text[1:]}" if tag == "returns" and text else text)
    md = "\n\n".join(p for p in parts if p)
    params = re.findall(r'<param name="([^"]+)">(.*?)</param>', xml, re.S)
    if params:
        md += "\n\nParameters:\n\n" + "\n".join(f"- `{n}`: {inline(d)}" for n, d in params)
    return md.strip()


def parse(path: Path) -> list[Symbol]:
    """The public declarations of a file, with their owners' paths."""
    lines = path.read_text().split("\n")
    found: list[Symbol] = []
    owners: list[tuple[int, str | None, str]] = []  # brace depth of the body, path (None: not public), kind
    pending: tuple[str | None, str] | None = None
    depth = 0
    comment: list[str] = []
    inherit: dict[int, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("///"):
            comment.append(line)
            i += 1
            continue
        code = strip_code(line)
        owner = owners[-1] if owners else None
        prefix = owner[1] + "." if owner and owner[1] else ""
        end = i
        if stripped.startswith("[") or not stripped or stripped.startswith(("#", "using ", "namespace ", "//")):
            pass
        elif (m := TYPE.match(line)) is not None:
            public = "public" in m.group("mods").split() and (owner is None or owner[1] is not None)
            p = prefix + m.group("name")
            sig, end = header(lines, i)
            if public:
                found.append(Symbol(p, p, tidy(sig), doc_markdown(comment), m.group("kind")))
            # A body opens at the next {; a positional record may have none.
            body = "".join(strip_code(x) for x in lines[i:end + 1])
            pending = (p if public else None, m.group("kind")) if "{" in body or ";" not in body else None
        elif owner and owner[2] == "enum" and owner[1] and (e := re.match(r"(\w+)\s*(=\s*[^,]+)?,?$", stripped)):
            p = prefix + e.group(1)
            found.append(Symbol(p, p, e.group(1), doc_markdown(comment), "entry"))
        elif stripped.startswith("public ") and owner and owner[1] is not None:
            sig, end = header(lines, i)
            sig = tidy(sig)
            rest = MODIFIERS.sub("", sig)
            simple = owner[1].split(".")[-1]
            if re.match(rf"{simple}\s*\(", rest):
                names = param_names(rest)
                p = f"{owner[1]}.new({', '.join(names)})"
                title = f"new {simple}({', '.join(names)})"
                sig = rest
            elif (f := re.match(r"(?:[\w.<>\[\]?,() ]+?)\s+(\w+)\s*(?:<[^>]*>)?\s*\(", rest)) is not None and not re.search(r"\{\s*get", lines[i]):
                names = param_names(rest)
                p = prefix + f.group(1)
                title = f"{p}({', '.join(names)})"
            else:
                name = re.findall(r"\w+", rest)[-1]
                p = prefix + name
                title = p
                # A property says how it's set.
                if (acc := re.search(r"\{\s*((?:get|init|set)[^}]*)\}", code)) is not None:
                    sig += " { " + " ".join(acc.group(1).split()) + " }"
                elif "=>" in code and "(" not in rest:
                    sig += " { get; }"
                elif re.match(r"(?:static\s+)?const\s", sig) and (v := re.search(r"=\s*(.+?);\s*$", line)) is not None:
                    sig += f" = {v.group(1)}"
            if (inh := re.search(r'<inheritdoc cref="(\w+)', " ".join(comment))) is not None:
                inherit[len(found)] = prefix + inh.group(1)
            found.append(Symbol(p, title, sig, doc_markdown(comment), "member"))
        comment = []
        # Braces, over the declaration's lines.
        for x in lines[i:end + 1] if end > i else [line]:
            for c in strip_code(x):
                if c == "{":
                    depth += 1
                    if pending is not None:
                        owners.append((depth, pending[0], pending[1]))
                        pending = None
                elif c == "}":
                    if owners and owners[-1][0] == depth:
                        owners.pop()
                    depth -= 1
        i = end + 1
    # <inheritdoc cref="X"/>: the doc of the first X with one of its own.
    for k, target in inherit.items():
        source = next((s for s in found if s.path == target and s.doc), None)
        if source is not None:
            found[k].doc = source.doc
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
    out += ["```csharp", s.signature, "```", ""]
    return out


def readme(symbols: list[Symbol]) -> tuple[str, int]:
    paths = {s.path for s in symbols}
    placed = {name for _, names in SECTIONS for name in names}
    # ErrorCodes' constants are the error codes page; the routes are api.md.
    hidden = {p for p in paths if p.startswith("ErrorCodes.")}

    def parent(p: str) -> str:
        return p.rsplit(".", 1)[0] if "." in p.split("(")[0] else ""

    def members(owner: str) -> list[Symbol]:
        return [s for s in symbols if parent(s.path) == owner and s.path not in placed and s.path not in hidden]

    body, contents, seen, done = [], [], {}, set()
    for title, names in SECTIONS:
        body += [f"## {title}", ""]
        links = []
        for name in names:
            group = [s for s in symbols if s.path == name]
            if not group:
                sys.exit(f"{name} isn't a public symbol any more: update SECTIONS in {Path(__file__).name}")
            for k, s in enumerate(group):
                a = anchor(s.title, seen)
                if k == 0:
                    links.append(f"[{s.title.split('(')[0]}](#{a})")
                body += entry(s, 3)
            done.add(name)
            if name == "ErrorCodes":
                body += ["Every code, with its text: [the error codes](errors.md).", ""]
            if name == "ToskarApi":
                body += ["Its methods: [every route on `toskar.Api`](api.md).", ""]
                continue
            for m in members(name):
                done.add(m.path)
                anchor(m.title, seen)
                body += entry(m, 4)
                for n in members(m.path):
                    done.add(n.path)
                    anchor(n.title, seen)
                    body += entry(n, 5)
        contents.append(f"- **{title}:** " + ", ".join(links))
    missing = sorted(p for p in paths if p not in done and p not in hidden and parent(p) != "ToskarApi")
    if missing:
        sys.exit("no section for: " + ", ".join(missing) + f" (add them to SECTIONS in {Path(__file__).name})")
    text = [
        "# .NET reference", "",
        "*Generated from the SDK's XML doc comments by `dotnet/scripts/reference.py`.*", "",
        "The official .NET SDK for Toskar: local AI across your own computers. It's in the `Toskar` namespace.", "",
        "```csharp",
        "using var toskar = new ToskarClient();",
        'await foreach (var e in toskar.ChatStreamAsync(new ChatRequest { Message = "Plan a three-day trip to Juneau" }))',
        "{",
        "    if (e is ChatEvent.Token token) Console.Write(token.Text);",
        "}",
        "```", "",
        "`toskar.Api` has [every route](api.md), generated from Toskar Core's API spec, and its models are in "
        "`Toskar.Models`. The routes themselves, with every field: "
        "[toskar.ai/developers/api](https://toskar.ai/developers/api).", "",
        "## Contents", "", *contents, "- [Every route on `toskar.Api`](api.md)", "- [Error codes](errors.md)", "",
        *body,
    ]
    return "\n".join(text).rstrip() + "\n", len(done)


def api(symbols: list[Symbol]) -> tuple[str, int]:
    routes = [s for s in symbols if s.path.startswith("ToskarApi.")]
    out = [
        "# Every route on `toskar.Api`", "",
        "*Generated from `Generated/ToskarApi.cs`, which `dotnet/scripts/generate.py` writes from Toskar Core's API "
        "spec.*", "",
        "One async method for each operation, named after its operationId, and each takes a `CancellationToken`. An "
        "error answer throws a `ToskarException`. The models are in `Toskar.Models` (`M.` below), and every field is "
        "described at [toskar.ai/developers/api](https://toskar.ai/developers/api).", "",
    ]
    for s in sorted(routes, key=lambda s: s.title.lower()):
        title = s.title.removeprefix("ToskarApi.").replace(", cancellationToken)", ")").replace("(cancellationToken)", "()")
        doc = s.doc.split("\n\n", 1)
        out += [f"### {title}", "", doc[0], ""]
        rest = doc[1] if len(doc) > 1 else ""
        # Every method's last parameter is the same, so it's said once above.
        rest = re.sub(r"\n?- `cancellationToken`: Cancels the request\.", "", rest)
        rest = re.sub(r"Parameters:\s*$", "", rest).strip()
        if rest:
            out += [rest, ""]
        sig = s.signature.replace("System.Threading.Tasks.", "")
        out += ["```csharp", sig, "```", ""]
    return "\n".join(out).rstrip() + "\n", len(routes)


def errors(sources: list[Path]) -> tuple[str, int]:
    catalog = json.loads(ERRORS.read_text())
    rows = [(f"`ErrorCodes.{code}`", re.sub(r"\s+", " ", str(text))) for code, text in sorted(catalog.items())]
    # Each code's message, the one it's thrown with most.
    said: dict[str, dict[str, int]] = {}
    for path in sources:
        text = path.read_text()
        for m in re.finditer(r'(?:ToskarException|new)\(\s*\w+,\s*"([A-Z][A-Z_]*)",\s*\n?\s*\$?"((?:[^"\\]|\\.)*)"', text):
            message = re.sub(r"\{[^}]*\}", "…", m.group(2))
            counts = said.setdefault(m.group(1), {})
            counts[message] = counts.get(message, 0) + 1
    own = {code: max(counts, key=lambda k: (counts[k], k)) for code, counts in said.items()}
    own["HTTP_<status>"] = "Toskar answered <status> with a body that isn't Toskar's"
    for code in sorted(own):
        if code not in catalog:
            rows.append((f"`{code}` (the SDK's own)", own[code]))
    lines = [
        "# .NET error codes", "",
        "*Generated by `dotnet/scripts/reference.py` from Toskar Core's error catalog and the SDK's own codes.*", "",
        "The codes Toskar Core and the SDK answer errors with, as `ToskarException.Code`, with each one's English "
        "text. Core's are constants on `ErrorCodes`; the SDK's own are for what goes wrong before Core answers. A "
        "newer Core may answer with a code this list doesn't have yet.", "",
        "| Code | Text |", "| --- | --- |",
        *[f"| {c} | {t.replace('|', chr(92) + '|')} |" for c, t in rows],
    ]
    return "\n".join(lines) + "\n", len(rows)


def main() -> int:
    own = sorted(SRC.glob("*.cs"))
    symbols = [s for p in [*own, SRC / "Generated" / "Codes.cs"] for s in parse(p)]
    generated = parse(SRC / "Generated" / "ToskarApi.cs")
    # A partial class's doc can be in either half.
    for s in symbols:
        if not s.doc:
            s.doc = next((g.doc for g in generated if g.path == s.path), "")
    OUT.mkdir(parents=True, exist_ok=True)
    text, n = readme(symbols)
    (OUT / "README.md").write_text(text)
    text, routes = api(generated)
    (OUT / "api.md").write_text(text)
    text, codes = errors(own)
    (OUT / "errors.md").write_text(text)
    print(f"reference/dotnet: {n} symbols, {routes} routes, {codes} codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
