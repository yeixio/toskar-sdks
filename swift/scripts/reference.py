"""Writes the Swift SDK's reference docs (reference/swift/) from its doc
comments. Run from the repository root on a Mac:

    python3 swift/scripts/reference.py

README.md comes from the compiler's symbol graph, and a public symbol
with no section here fails, so a new one is placed before it ships.
errors.md comes from the codes' declarations alone, so `--errors` writes
just it, anywhere: the sync workflow does on Linux, where Swift isn't
installed and pairing and discovery, which need Apple's frameworks,
aren't compiled. Standard library only.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reference" / "swift"

# Sections, in order, and the top-level symbols in each. A type's members
# follow it.
SECTIONS = [
    ("Connecting", ["Toskar", "ChatRequest"]),
    ("Errors", ["ToskarError"]),
    ("Pairing and reaching a computer from anywhere", [
        "Toskar.pair(address:code:deviceName:confirm:)", "Toskar.init(device:retries:timeout:)", "Toskar.path",
        "Toskar.reconnect()", "Device", "Route", "ConnectionPath", "Toskar.toskarRelay", "Toskar.pinOf(_:)",
        "Toskar.shortPin(_:)", "Toskar.routeID(_:)", "Toskar.openRecord(_:secret:pin:now:maxAge:)", "AddressRecord",
    ]),
    ("Finding computers on the network", ["Toskar.find(timeout:)", "Toskar.serviceType", "DiscoveredComputer"]),
    ("The contract", ["contractVersion"]),
]

# What Swift makes for every type, which says nothing about this SDK.
SYNTHESIZED = {"!=(_:_:)", "==(_:_:)", "hash(into:)", "hashValue", "init(from:)", "encode(to:)", "init(rawValue:)",
               "rawValue", "localizedDescription", "description", "testDescription"}


def symbols() -> list[dict]:
    # The compiler writes the graph while it builds the Toskar target alone:
    # `swift package dump-symbol-graph` extracts every module, test bundle
    # too, which fails on some Xcodes.
    with tempfile.TemporaryDirectory() as tmp:
        flags = ["-emit-symbol-graph", "-emit-symbol-graph-dir", tmp, "-symbol-graph-minimum-access-level", "public"]
        build = subprocess.run(["swift", "build", "--target", "Toskar", *(a for f in flags for a in ("-Xswiftc", f))],
                               cwd=ROOT, capture_output=True, text=True)
        if build.returncode != 0:
            sys.exit(build.stdout[-4000:] + build.stderr[-4000:] + "\nswift build failed")
        graphs = sorted(Path(tmp).glob("Toskar*.symbols.json"))
        if not graphs:
            sys.exit("no symbol graph for Toskar")
        texts = [g.read_text() for g in graphs]
    out = []
    for t in texts:
        for s in json.loads(t)["symbols"]:
            # Only this SDK's own code: ToskarAPI's is re-exported, and has its own reference.
            # Extension blocks, such as Error's, are where members are, not symbols.
            if "/swift/Sources/Toskar/" in s.get("location", {}).get("uri", "") and s["kind"]["identifier"] != "swift.extension":
                out.append(s)
    return out


def path(s: dict) -> str:
    return ".".join(s["pathComponents"])


def anchor(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum() or c in "-_") or "symbol"


def declaration(s: dict) -> str:
    return "".join(f["spelling"] for f in s.get("declarationFragments", [])).strip()


def doc(s: dict) -> str:
    lines = [line["text"] for line in s.get("docComment", {}).get("lines", [])]
    return "\n".join(lines).strip()


def entry(s: dict, level: int) -> list[str]:
    out = [f"{'#' * level} {path(s)}", ""]
    if text := doc(s):
        out += [text, ""]
    if decl := declaration(s):
        out += ["```swift", decl, "```", ""]
    return out


def write_errors() -> int:
    """errors.md, from the codes' doc comments and values where they're
    declared: Codes.swift, from Core's catalog, and the SDK's own."""
    source = "".join(f.read_text() for f in sorted((ROOT / "swift" / "Sources" / "Toskar").glob("*.swift")))
    found = re.findall(r'((?:[ \t]*///.*\n)+)[ \t]*public static let `?(\w+)`? = Self\("(\w+)"\)', source)
    rows = []
    for comment, name, value in sorted(found, key=lambda f: f[1]):
        text = " ".join(line.strip()[3:].strip() for line in comment.strip().splitlines()).replace("|", "\\|")
        rows.append(f"| `.{name}` | `{value}` | {text} |")
    OUT.mkdir(parents=True, exist_ok=True)
    errors = ["# Swift error codes", "",
              "*Generated from the codes' declarations by `swift/scripts/reference.py`: Toskar Core's error catalog, "
              "by way of `swift/scripts/codes.swift`, and the SDK's own.*", "",
              "The codes Toskar Core and the SDK answer errors with, as `ToskarError.Code`, with each one's English "
              "text. A newer Core may answer with a code this list doesn't have yet.", "",
              "| Code | Value | Text |", "| --- | --- | --- |", *rows]
    (OUT / "errors.md").write_text("\n".join(errors) + "\n")
    return len(rows)


def main() -> int:
    if sys.argv[1:] == ["--errors"]:
        print(f"reference/swift/errors.md: {write_errors()} codes")
        return 0
    all_symbols = symbols()
    by_path: dict[str, dict] = {}
    for s in all_symbols:
        by_path.setdefault(path(s), s)
    codes = sorted((s for s in all_symbols if s["pathComponents"][:2] == ["ToskarError", "Code"]
                    and len(s["pathComponents"]) == 3 and s["kind"]["identifier"] == "swift.type.property"),
                   key=path)
    placed: set[str] = {path(s) for s in codes}
    # A symbol with a section of its own isn't also listed with its type,
    # and an Error's own copy of Error.toskar isn't listed at all.
    placed |= {name for _, names in SECTIONS for name in names}
    placed |= {p for p in by_path if p.endswith(".toskar") and p != "Error.toskar"}

    def members(parent: str) -> list[dict]:
        depth = parent.count(".") + 1
        return sorted((s for p, s in by_path.items()
                       if p.startswith(parent + ".") and p.count(".") == depth
                       and s["pathComponents"][-1] not in SYNTHESIZED and p not in placed),
                      key=lambda s: (s["kind"]["identifier"] != "swift.init", path(s)))

    body: list[str] = []
    contents: list[str] = []
    for title, names in SECTIONS:
        body += [f"## {title}", ""]
        links = []
        for name in names:
            s = by_path.get(name)
            if s is None:
                sys.exit(f"{name} isn't a public symbol any more: update SECTIONS in {Path(__file__).name}")
            body += entry(s, 3)
            links.append(f"[{name.split('(')[0]}](#{anchor(name)})")
            for m in members(name):
                placed.add(path(m))
                body += entry(m, 4)
                for n in members(path(m)):
                    placed.add(path(n))
                    body += entry(n, 5)
        contents.append(f"- **{title}:** " + ", ".join(links))
    # Error.toskar, an extension of Swift's own Error, after ToskarError. A
    # type that is an Error shows it as its own member too, so that copy is
    # left out.
    if (s := by_path.get("Error.toskar")) is not None:
        placed.add("Error.toskar")
        at = body.index("## Pairing and reaching a computer from anywhere")
        body[at:at] = entry(s, 3)
        contents[1] += ", [Error.toskar](#errortoskar)"
    missing = sorted(p for p, s in by_path.items() if p not in placed and s["pathComponents"][-1] not in SYNTHESIZED)
    if missing:
        sys.exit("no section for: " + ", ".join(missing) + f" (add them to SECTIONS in {Path(__file__).name})")

    OUT.mkdir(parents=True, exist_ok=True)
    readme = [
        "# Swift reference", "",
        "*Generated from the SDK's doc comments by `swift/scripts/reference.py`.*", "",
        "The official Swift SDK for Toskar: local AI across your own computers.", "",
        "```swift",
        "let toskar = try Toskar()",
        'for try await event in toskar.chatStream(ChatRequest(message: "Plan a three-day trip to Juneau")) {',
        '    if case .token(let text) = event { print(text, terminator: "") }',
        "}",
        "```", "",
        "`toskar.api` has every route, generated from Toskar Core's API spec. The routes themselves, with every field: "
        "[toskar.ai/developers/api](https://toskar.ai/developers/api).", "",
        "## Contents", "", *contents, "- [Error codes](errors.md)", "", *body,
    ]
    (OUT / "README.md").write_text("\n".join(readme).rstrip() + "\n")
    write_errors()
    print(f"reference/swift: {len(placed) - len(codes)} symbols, {len(codes)} codes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
