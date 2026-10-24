"""Checks the code snippets in the SDKs' READMEs, and in other pages given
(such as toskar.ai's developers page), so a snippet that stops working
fails CI.

    python3 scripts/check_snippets.py --core <toskar daemon> \\
        --python python/.venv/bin/python [more pages...]

Every snippet is type-checked against the SDK: mypy for Python, tsc for
TypeScript, the Go compiler for Go. A fragment may use `toskar` (a
client), `c` and `ctx` (Go), and `ask_the_person` / `askThePerson` without
defining them. Snippets marked to run are also run against a throwaway
Core, which chats with the scripted model (conformance/run.py):

- in Markdown, `<!-- snippet: run -->` on the line before the fence;
- in a .tsx page, `// snippet: run` on the line before a `const NAME = \\`...\\``
  holding the snippet. The name says its language: PY_ for Python, GO_ for
  Go, anything else TypeScript; *_INSTALL ones are commands, not checked.

TypeScript needs typescript/ built (npm run build). Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READMES = [ROOT / "python" / "README.md", ROOT / "typescript" / "README.md", ROOT / "go" / "README.md"]
LANGS = {"python": "python", "py": "python", "ts": "ts", "typescript": "ts", "js": "ts", "go": "go"}


@dataclass
class Snippet:
    where: str
    lang: str
    code: str
    run: bool


def extract(path: Path) -> list[Snippet]:
    text = path.read_text()
    out: list[Snippet] = []
    if path.suffix == ".md":
        for m in re.finditer(r"(?:<!-- snippet: (\w+) -->\n)?```(\w+)\n(.*?)```", text, re.S):
            lang = LANGS.get(m.group(2))
            if lang and m.group(1) != "skip":
                line = text[: m.start(2)].count("\n") + 1
                out.append(Snippet(f"{label(path)}:{line}", lang, m.group(3), m.group(1) == "run"))
    elif path.suffix in (".tsx", ".ts"):
        for m in re.finditer(r"(?:// snippet: (\w+)\n)?const ([A-Z_]+) = `(.*?)`;", text, re.S):
            name = m.group(2)
            if name.endswith("INSTALL") or m.group(1) == "skip":
                continue
            lang = "python" if name.startswith("PY_") else "go" if name.startswith("GO_") else "ts"
            code = m.group(3).replace("\\`", "`").replace("\\${", "${")
            out.append(Snippet(f"{label(path)}:{name}", lang, code + "\n", m.group(1) == "run"))
    return out


def label(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return f"{path.parent.name}/{path.name}"


def defines(code: str, name: str, lang: str) -> bool:
    if lang == "python":
        return re.search(rf"^\s*(?:{name}\s*=|(?:async\s+)?def {name}\b|.*\bas {name}\b)", code, re.M) is not None
    if lang == "ts":
        return re.search(rf"\b(?:const|let|var|function)\s+{name}\b", code) is not None
    return re.search(rf"\b{name}(?:\s*,\s*\w+)*\s*:=|\bvar {name}\b", code) is not None


# Type checks.

def check_python(snippets: list[tuple[int, Snippet]], python: str, work: Path) -> dict[int, str]:
    files = {}
    for i, s in snippets:
        prelude = ["from typing import Callable as _Callable", "from toskar import Toskar as _Toskar"]
        if not defines(s.code, "toskar", "python"):
            prelude.append("toskar: _Toskar")
        if not defines(s.code, "ask_the_person", "python"):
            prelude.append("ask_the_person: _Callable[[str], bool]")
        # Imports first, as the snippet's own may be anywhere.
        f = work / f"snippet_{i}.py"
        f.write_text("\n".join(prelude) + "\n\n" + s.code)
        files[i] = f
    r = subprocess.run([python, "-m", "mypy", "--no-error-summary", "--ignore-missing-imports", *map(str, files.values())],
                       capture_output=True, text=True)
    return errors_by_file(r.stdout + r.stderr, files, r.returncode)


def check_ts(snippets: list[tuple[int, Snippet]], work: Path) -> dict[int, str]:
    sdk = ROOT / "typescript"
    files = {}
    for i, s in snippets:
        prelude = ["export {}"]
        if not defines(s.code, "toskar", "ts"):
            prelude.append("declare const toskar: import('toskar').Toskar")
        if not defines(s.code, "askThePerson", "ts"):
            prelude.append("declare function askThePerson(short: string): boolean | Promise<boolean>")
        f = work / f"snippet_{i}.ts"
        f.write_text("\n".join(prelude) + "\n" + s.code)
        files[i] = f
    (work / "tsconfig.json").write_text(
        '{"extends": "' + str(sdk / "tsconfig.json") + '", "compilerOptions": {"noEmit": true, "rootDir": "/", '
        '"paths": {"toskar": ["' + str(sdk / "src" / "index.ts") + '"], "toskar/node": ["' + str(sdk / "src" / "node.ts") + '"]}, '
        '"typeRoots": ["' + str(sdk / "node_modules" / "@types") + '"]}, "include": ["*.ts"]}'
    )
    shutil.copy(sdk / "package.json", work / "package.json")  # ESM, for top-level await
    r = subprocess.run([str(sdk / "node_modules" / ".bin" / "tsc"), "-p", str(work)], capture_output=True, text=True)
    return errors_by_file(r.stdout + r.stderr, files, r.returncode)


GO_IMPORTS = {
    "context": "context", "errors": "errors", "fmt": "fmt", "os": "os", "time": "time",
    "toskar": 'toskar "github.com/yeixio/toskar-sdks/go"', "api": '"github.com/yeixio/toskar-sdks/go/api"',
}


def go_program(s: Snippet, runnable: bool) -> str:
    if s.code.lstrip().startswith("package "):
        return s.code
    imports = re.findall(r"^import (.+)$", s.code, re.M)
    body = re.sub(r"^import .+\n", "", s.code, flags=re.M)
    # A fragment's variables are often there to show what a call answers;
    # Go builds nothing with one unused.
    declared = {n.strip() for m in re.finditer(r"^(\w+(?:\s*,\s*\w+)*)\s*:=", body, re.M) for n in m.group(1).split(",")}
    body += "".join(f"\t_ = {n}\n" for n in sorted(declared - {"_"}))
    lines = ["package main", "", "import ("]
    lines += [f"\t{v}" if v.startswith(("toskar", '"')) else f'\t"{v}"' for v in GO_IMPORTS.values()]
    lines += [f"\t{i}" for i in imports if i not in GO_IMPORTS.values()]
    lines += [")", "",
              "var _ = errors.As", "var _ = fmt.Sprint", "var _ = os.Exit", "var _ = time.Second", "var _ api.Model",
              "var askThePerson = func(string) bool { return true }", "",
              "func snippet() error {", "\tctx := context.Background()", "\tvar c *toskar.Client", "\t_, _ = ctx, c",
              "\t{", body, "\t}", "\treturn nil", "}", "",
              "func main() {",
              "\tif err := snippet(); err != nil {" if runnable else "\t_ = snippet",
              ]
    if runnable:
        lines += ["\t\tfmt.Fprintln(os.Stderr, err)", "\t\tos.Exit(1)", "\t}"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def check_go(snippets: list[tuple[int, Snippet]], work: Path) -> dict[int, str]:
    # Inside the module, so the SDK's packages resolve as they are here.
    base = ROOT / "go" / "snippetcheck"
    shutil.rmtree(base, ignore_errors=True)
    files = {}
    for i, s in snippets:
        d = base / f"snippet_{i}"
        d.mkdir(parents=True)
        (d / "main.go").write_text(go_program(s, s.run))
        files[i] = d / "main.go"
    r = subprocess.run(["go", "build", "-gcflags=-e", "./snippetcheck/..."], cwd=ROOT / "go",
                       capture_output=True, text=True)
    # A fragment's variables may be there to show what a call answers.
    # Go also says what it downloads, on a runner without the modules yet.
    out = "\n".join(line for line in (r.stdout + r.stderr).splitlines()
                    if "declared and not used" not in line and not line.startswith(("# ", "go: downloading ")))
    return errors_by_file(out, files, r.returncode if out.strip() else 0)


def errors_by_file(output: str, files: dict[int, Path], code: int) -> dict[int, str]:
    """Each snippet's lines of a checker's output. Go's files are all
    main.go, each in a folder of its own. A checker that failed without
    naming a snippet fails them all."""
    def mark(f: Path) -> str:
        # mypy: snippet_1.py:3: …; tsc: snippet_1.ts(3,5): …; go: snippet_1/main.go:3:5: …
        return {".py": f.name + ":", ".ts": f.name + "(", ".go": f.parent.name + "/"}[f.suffix]

    found: dict[int, str] = {}
    if code and not any(mark(f) in output for f in files.values()):
        return {i: output.strip()[-1500:] or f"the checker exited {code}" for i in files}
    for i, f in files.items():
        lines = [line for line in output.splitlines() if mark(f) in line]
        if lines:
            found[i] = "\n".join(lines[:8])
    return found


# Runs.

def run_snippet(s: Snippet, i: int, python: str, env: dict[str, str], work: Path) -> str | None:
    if s.lang == "python":
        f = work / f"run_{i}.py"
        f.write_text(s.code)
        cmd = [python, str(f)]
    elif s.lang == "ts":
        d = work / "run-ts"
        if not d.exists():
            (d / "node_modules").mkdir(parents=True)
            (d / "node_modules" / "toskar").symlink_to(ROOT / "typescript", target_is_directory=True)
            (d / "package.json").write_text('{"type": "module"}')
        f = d / f"run_{i}.ts"
        f.write_text(s.code)
        cmd = ["node", "--experimental-strip-types", "--no-warnings", str(f)]
    else:
        d = ROOT / "go" / "snippetcheck" / f"run_{i}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "main.go").write_text(go_program(s, True))
        b = work / f"run_{i}"
        r = subprocess.run(["go", "build", "-o", str(b), f"./snippetcheck/run_{i}"], cwd=ROOT / "go", capture_output=True, text=True)
        if r.returncode:
            return r.stdout + r.stderr
        cmd = [str(b)]
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60, cwd=work)
    except subprocess.TimeoutExpired:
        return "didn't finish in 60s"
    out = r.stdout + r.stderr
    if r.returncode:
        return f"exited {r.returncode}:\n{out[-1500:]}"
    if re.search(r"chat_?[sS]tream|ChatStream", s.code) and "You said: " not in out:
        return f"the streamed answer didn't print:\n{out[-1500:]}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="*", type=Path, help="more pages with snippets, such as toskar.ai's app/developers/page.tsx")
    ap.add_argument("--core", required=True, help="the Toskar Core daemon to run snippets against")
    ap.add_argument("--python", default=sys.executable, help="a Python with the toskar package and mypy installed")
    args = ap.parse_args()
    python = str(Path(args.python).absolute()) if os.sep in args.python else args.python

    snippets = [s for page in READMES + [p.resolve() for p in args.pages] for s in extract(page)]
    numbered = list(enumerate(snippets))
    failed = 0
    with tempfile.TemporaryDirectory(prefix="toskar-snippets-") as tmp_name:
        tmp = Path(tmp_name)
        try:
            problems: dict[int, str] = {}
            for lang, check in (("python", lambda n: check_python(n, python, mk(tmp, "py"))),
                                ("ts", lambda n: check_ts(n, mk(tmp, "ts"))),
                                ("go", lambda n: check_go(n, tmp))):
                problems.update(check([(i, s) for i, s in numbered if s.lang == lang]))
            runs = [(i, s) for i, s in numbered if s.run and i not in problems]
            if runs:
                sys.path.insert(0, str(ROOT / "conformance"))
                import run as conformance

                model = ThreadingHTTPServer(("127.0.0.1", 0), conformance.ScriptedModel)
                threading.Thread(target=model.serve_forever, daemon=True).start()
                core = conformance.Core(args.core, tmp)
                try:
                    core.api("PUT", "/api/v1/external-server", {"base_url": f"http://127.0.0.1:{model.server_address[1]}/v1"})
                    # The default profile answers with the scripted model, as with a model installed.
                    profile = core.api("GET", "/api/v1/profiles/general-assistant")
                    for role in profile["roles"]:
                        role["model_id"] = "ext:echo"
                    core.api("PATCH", "/api/v1/profiles/general-assistant", profile)
                    env = {k: v for k, v in os.environ.items() if not k.startswith("TOSKAR_")}
                    env["TOSKAR_URL"] = core.url
                    for i, s in runs:
                        if (problem := run_snippet(s, i, python, env, tmp)) is not None:
                            problems[i] = problem
                finally:
                    core.stop()
                    model.shutdown()
            for i, s in numbered:
                kind = "ran" if s.run else "checked"
                if i in problems:
                    failed += 1
                    print(f"FAIL {s.where:28} {s.lang:6}\n{problems[i]}\n")
                else:
                    print(f"ok   {s.where:28} {s.lang:6} {kind}")
        finally:
            shutil.rmtree(ROOT / "go" / "snippetcheck", ignore_errors=True)
    print(f"{failed} of {len(snippets)} snippets failed" if failed else f"all {len(snippets)} snippets work")
    return 1 if failed else 0


def mk(tmp: Path, name: str) -> Path:
    d = tmp / name
    d.mkdir(exist_ok=True)
    return d


if __name__ == "__main__":
    sys.exit(main())
