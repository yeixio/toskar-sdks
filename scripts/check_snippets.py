"""Checks the code snippets in the SDKs' READMEs, and in other pages given
(such as toskar.ai's developers page), so a snippet that stops working
fails CI.

    python3 scripts/check_snippets.py --core <toskar daemon> \\
        --python python/.venv/bin/python [more pages...]

Every snippet is type-checked against the SDK: mypy for Python, tsc for
TypeScript, the Go compiler for Go, the Swift compiler for Swift, and
Gradle for Kotlin and Java, the .NET SDK for C#, and cargo for Rust. A
fragment may use `toskar` (a client), `c` and `ctx` (Go), and
`ask_the_person` / `askThePerson` / `AskThePerson` without defining
them. `--langs` picks
the languages, for a runner that has only some of the toolchains. Snippets marked to run are also run against a throwaway
Core, which chats with the scripted model (conformance/run.py):

- in Markdown, `<!-- snippet: run -->` on the line before the fence;
- in a .tsx page, `// snippet: run` on the line before a `const NAME = \\`...\\``
  holding the snippet. The name says its language: PY_ for Python, GO_ for
  Go, SWIFT_ for Swift, KT_ for Kotlin, JAVA_ for Java, anything else
  TypeScript; *_INSTALL ones are commands, not checked.

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
READMES = [ROOT / "python" / "README.md", ROOT / "typescript" / "README.md", ROOT / "go" / "README.md", ROOT / "swift" / "README.md",
           ROOT / "kotlin" / "README.md", ROOT / "dotnet" / "README.md", ROOT / "rust" / "README.md"]
LANGS = {"python": "python", "py": "python", "ts": "ts", "typescript": "ts", "js": "ts", "go": "go", "swift": "swift",
         "kotlin": "kotlin", "kt": "kotlin", "java": "java", "csharp": "csharp", "cs": "csharp", "rust": "rust",
         "rs": "rust"}


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
            prefixes = {"PY_": "python", "GO_": "go", "SWIFT_": "swift", "KT_": "kotlin", "JAVA_": "java", "CS_": "csharp",
                        "RS_": "rust"}
            lang = next((v for k, v in prefixes.items() if name.startswith(k)), "ts")
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
    if lang == "swift":
        return re.search(rf"\b(?:let|var|func)\s+{name}\b", code) is not None
    if lang == "kotlin":
        return re.search(rf"\b(?:val|var|fun)\s+{name}\b", code) is not None
    if lang == "java":
        return re.search(rf"\b[\w<>]+\s+{name}\s*[=;(]", code) is not None
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


def swift_program(s: Snippet) -> str:
    """A snippet as a main.swift: its imports first, then toskar and
    askThePerson when it doesn't make its own."""
    imports = re.findall(r"^import .+$", s.code, re.M)
    body = re.sub(r"^import .+\n", "", s.code, flags=re.M)
    lines = ["import Foundation", "import Toskar", *[i for i in imports if i not in ("import Foundation", "import Toskar")]]
    if not defines(s.code, "askThePerson", "swift"):
        lines.append("@Sendable func askThePerson(_ short: String) async -> Bool { true }")
    if not defines(s.code, "toskar", "swift"):
        lines.append("let toskar = try Toskar()")
    return "\n".join(lines) + "\n" + body


SWIFT_PACKAGE = """// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "snippetcheck",
    platforms: [.macOS(.v13)],
    dependencies: [
        .package(name: "toskar-sdks", path: "../.."),
        .package(url: "https://github.com/swift-server/swift-openapi-async-http-client", from: "1.0.0"),
    ],
    targets: [
%s
    ]
)
"""


def swift_package(names: list[str]) -> Path:
    """The snippets' package, which uses the SDK as it is in this checkout,
    with one executable for each of names."""
    base = ROOT / "swift" / ".snippetcheck"
    deps = '[.product(name: "Toskar", package: "toskar-sdks"), .product(name: "OpenAPIAsyncHTTPClient", package: "swift-openapi-async-http-client")]'
    targets = ",\n".join(f'        .executableTarget(name: "{n}", dependencies: {deps})' for n in names)
    (base / "Package.swift").write_text(SWIFT_PACKAGE % targets)
    return base


def check_swift(snippets: list[tuple[int, Snippet]], work: Path) -> dict[int, str]:
    base = ROOT / "swift" / ".snippetcheck"
    shutil.rmtree(base / "Sources", ignore_errors=True)
    files = {}
    for i, s in snippets:
        d = base / "Sources" / f"snippet_{i}"
        d.mkdir(parents=True)
        (d / "main.swift").write_text(swift_program(s))
        files[i] = d / "main.swift"
    if not files:
        return {}
    swift_package([f"snippet_{i}" for i in files])
    r = subprocess.run(["swift", "build", "--package-path", str(base)], capture_output=True, text=True)
    out = "\n".join(line for line in (r.stdout + r.stderr).splitlines() if "error:" in line)
    return errors_by_file(out, files, r.returncode)


JVM_SETTINGS = """rootProject.name = "snippetcheck"
includeBuild("..")
dependencyResolutionManagement { repositories { mavenCentral() } }
"""

JVM_BUILD = """plugins {
    kotlin("jvm") version "%s"
}
kotlin { jvmToolchain(21) }
dependencies { implementation("ai.toskar:toskar") }
tasks.register("classpath") {
    val files = sourceSets["main"].runtimeClasspath
    // Builds what's on it, such as the SDK's jar, before naming it.
    inputs.files(files)
    doLast { file("build/classpath.txt").writeText(files.asPath) }
}
"""


def jvm_program(s: Snippet, name: str) -> tuple[str, str]:
    """A snippet as a file of its own package, name: its imports first, then
    the SDK's, then a main that makes toskar and askThePerson when it
    doesn't. Answers the file's path in the project and its source."""
    imports = re.findall(r"^import .+$", s.code, re.M)
    body = re.sub(r"^import .+\n", "", s.code, flags=re.M)
    if s.lang == "kotlin":
        lines = [f"package {name}", "", *imports, "import ai.toskar.*", "import ai.toskar.api.*", ""]
        if not defines(s.code, "askThePerson", "kotlin"):
            lines.append("fun askThePerson(short: String): Boolean = true")
        lines.append("fun main() {")
        if not defines(s.code, "toskar", "kotlin"):
            lines.append("val toskar = Toskar()")
        return f"src/main/kotlin/{name}/Main.kt", "\n".join(lines) + "\n" + body + "}\n"
    lines = [f"package {name};", "", *imports, "import ai.toskar.*;", "import ai.toskar.api.*;", "",
             "public class Main {", "static boolean askThePerson(String s) { return true; }",
             "public static void main(String[] args) throws Exception {"]
    if not defines(s.code, "toskar", "java"):
        lines.append("Toskar toskar = new Toskar();")
    return f"src/main/java/{name}/Main.java", "\n".join(lines) + "\n" + body + "}\n}\n"


def jvm_project(snippets: list[tuple[str, Snippet]]) -> dict[str, Path]:
    """The snippets' Gradle project, which uses the SDK as it is in this
    checkout. Answers each snippet's file."""
    base = ROOT / "kotlin" / ".snippetcheck"
    shutil.rmtree(base / "src", ignore_errors=True)
    kotlin = re.search(r'kotlin\("jvm"\) version "([^"]+)"', (ROOT / "kotlin" / "build.gradle.kts").read_text())
    base.mkdir(exist_ok=True)
    (base / "settings.gradle.kts").write_text(JVM_SETTINGS)
    (base / "build.gradle.kts").write_text(JVM_BUILD % kotlin.group(1))
    files = {}
    for name, s in snippets:
        path, source = jvm_program(s, name)
        f = base / path
        f.parent.mkdir(parents=True)
        f.write_text(source)
        files[name] = f
    return files


def gradle(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(ROOT / "kotlin" / "gradlew"), "-q", "-p", str(ROOT / "kotlin" / ".snippetcheck"), *args],
                          capture_output=True, text=True)


def check_jvm(snippets: list[tuple[int, Snippet]], work: Path) -> dict[int, str]:
    if not snippets:
        return {}
    files = jvm_project([(f"snippet_{i}", s) for i, s in snippets])
    r = gradle("classes")
    # kotlinc: e: file:///…/snippet_1/Main.kt:3:5 …; javac: /…/snippet_1/Main.java:3: error: …
    out = "\n".join(line for line in (r.stdout + r.stderr).splitlines() if line.startswith("e: ") or ": error:" in line)
    return errors_by_file(out, {i: files[f"snippet_{i}"] for i, _ in snippets}, r.returncode)


CSHARP_PROJECT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <RollForward>Major</RollForward>
    <OutputType>Exe</OutputType>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <!-- A fragment's variables are often there to show what a call answers. -->
    <NoWarn>CS0168;CS0219;CS8321</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="../src/Toskar/Toskar.csproj" />
  </ItemGroup>
</Project>
"""


def csharp_program(s: Snippet, name: str) -> str:
    """A snippet as a method of its own class, its usings first, with toskar
    and AskThePerson when it doesn't make its own."""
    usings = re.findall(r"^using [\w.]+;$", s.code, re.M)
    body = re.sub(r"^using [\w.]+;\n", "", s.code, flags=re.M)
    lines = [*usings, "using Toskar;", "using Toskar.Models;", "", f"namespace {name};", "",
             "public static class Snippet", "{"]
    if not re.search(r"\bAskThePerson\s*\(string", s.code):
        lines.append("    static bool AskThePerson(string shortPin) => true;")
    lines.append("    public static async System.Threading.Tasks.Task Run()")
    lines.append("    {")
    if not re.search(r"\bvar\s+toskar\b|\bToskarClient\s+toskar\b", s.code):
        lines.append("        using var toskar = new ToskarClient();")
    return "\n".join(lines) + "\n" + body + "\n    }\n}\n"


def csharp_project(snippets: list[tuple[str, Snippet]], main: str | None) -> dict[str, Path]:
    """The snippets' project, which uses the SDK as it is in this checkout.
    main, when given, is the snippet the program runs."""
    base = ROOT / "dotnet" / ".snippetcheck"
    shutil.rmtree(base / "Snippets", ignore_errors=True)
    (base / "Snippets").mkdir(parents=True)
    (base / "Snippets.csproj").write_text(CSHARP_PROJECT)
    run = f"await {main}.Snippet.Run();" if main else "await System.Threading.Tasks.Task.CompletedTask;"
    (base / "Snippets" / "Program.cs").write_text(f"public static class Program\n{{\n    public static async System.Threading.Tasks.Task Main() {{ {run} }}\n}}\n")
    files = {}
    for name, s in snippets:
        f = base / "Snippets" / f"{name}.cs"
        f.write_text(csharp_program(s, name))
        files[name] = f
    return files


def check_csharp(snippets: list[tuple[int, Snippet]], work: Path) -> dict[int, str]:
    if not snippets:
        return {}
    files = csharp_project([(f"snippet_{i}", s) for i, s in snippets], None)
    r = subprocess.run(["dotnet", "build", str(ROOT / "dotnet" / ".snippetcheck"), "-nologo", "-v", "q"],
                       capture_output=True, text=True)
    out = "\n".join(line for line in (r.stdout + r.stderr).splitlines() if ": error " in line)
    return errors_by_file(out, {i: files[f"snippet_{i}"] for i, _ in snippets}, r.returncode)


RUST_MANIFEST = """[package]
name = "snippetcheck"
version = "0.0.0"
edition = "2024"
publish = false

[dependencies]
toskar = { path = ".." }
futures-util = "0.3"
serde_json = "1"
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }

[workspace]
"""


def rust_project(snippets: list[tuple[str, Snippet]], main: str | None) -> dict[str, Path]:
    """The snippets' crate, which uses the SDK as it is in this checkout: each
    snippet an async fn in a module of its own, with toskar when it doesn't
    make its own. main, when given, is the snippet the program runs."""
    base = ROOT / "rust" / ".snippetcheck"
    shutil.rmtree(base / "src", ignore_errors=True)
    (base / "src").mkdir(parents=True)
    (base / "Cargo.toml").write_text(RUST_MANIFEST)
    files = {}
    mods = []
    for name, s in snippets:
        lines = ["#![allow(unused)]", "use futures_util::StreamExt;", "use toskar::models::*;", "use toskar::*;", "",
                 "fn ask_the_person(short_pin: &str) -> bool { true }", "",
                 "pub async fn run() -> std::result::Result<(), Box<dyn std::error::Error>> {"]
        if not re.search(r"\blet\s+(mut\s+)?toskar\b", s.code):
            lines.append("let toskar = Client::new()?;")
        f = base / "src" / f"{name}.rs"
        f.write_text("\n".join(lines) + "\n" + s.code + "\nOk(())\n}\n")
        files[name] = f
        mods.append(f"mod {name};")
    run = f"{main}::run().await?;" if main else ""
    (base / "src" / "main.rs").write_text(
        "#![allow(unused)]\n" + "\n".join(mods) + "\n\n#[tokio::main]\n"
        "async fn main() -> std::result::Result<(), Box<dyn std::error::Error>> {\n" + run + "\nOk(())\n}\n")
    return files


def check_rust(snippets: list[tuple[int, Snippet]], work: Path) -> dict[int, str]:
    if not snippets:
        return {}
    files = rust_project([(f"snippet_{i}", s) for i, s in snippets], None)
    r = subprocess.run(["cargo", "build", "--quiet", "--manifest-path", str(ROOT / "rust" / ".snippetcheck" / "Cargo.toml")],
                       capture_output=True, text=True)
    # rustc says the error, then where it is on the next line: one line each, where first.
    out, said = [], ""
    for line in r.stderr.splitlines():
        if line.startswith("error"):
            said = line
        elif "-->" in line and said:
            out.append(f"{line.split('-->', 1)[1].strip()}: {said}")
            said = ""
    out = "\n".join(out)
    return errors_by_file(out, {i: files[f"snippet_{i}"] for i, _ in snippets}, r.returncode)


def errors_by_file(output: str, files: dict[int, Path], code: int) -> dict[int, str]:
    """Each snippet's lines of a checker's output. Go's files are all
    main.go, each in a folder of its own. A checker that failed without
    naming a snippet fails them all."""
    def mark(f: Path) -> str:
        # mypy: snippet_1.py:3: …; tsc: snippet_1.ts(3,5): …; go: snippet_1/main.go:3:5: …;
        # swift: snippet_1/main.swift:3:5: …
        # C#: snippet_1.cs(3,5): …; rustc:  --> src/snippet_1.rs:3:5
        if f.suffix in (".py", ".ts", ".cs", ".rs"):
            return f.name + {".py": ":", ".ts": "(", ".cs": "(", ".rs": ":"}[f.suffix]
        return f.parent.name + "/"

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
    elif s.lang == "swift":
        base = ROOT / "swift" / ".snippetcheck"
        shutil.rmtree(base / "Sources", ignore_errors=True)
        d = base / "Sources" / f"run_{i}"
        d.mkdir(parents=True)
        (d / "main.swift").write_text(swift_program(s))
        swift_package([f"run_{i}"])
        r = subprocess.run(["swift", "build", "--package-path", str(base), "--product", f"run_{i}"], capture_output=True, text=True)
        if r.returncode:
            return r.stdout + r.stderr
        bin_dir = subprocess.run(["swift", "build", "--package-path", str(base), "--show-bin-path"], capture_output=True, text=True).stdout.strip()
        cmd = [str(Path(bin_dir) / f"run_{i}")]
    elif s.lang == "csharp":
        csharp_project([(f"run_{i}", s)], f"run_{i}")
        project = ROOT / "dotnet" / ".snippetcheck"
        r = subprocess.run(["dotnet", "build", str(project), "-nologo", "-v", "q", "-o", str(work / "cs")], capture_output=True, text=True)
        if r.returncode:
            return r.stdout + r.stderr
        cmd = ["dotnet", str(work / "cs" / "Snippets.dll")]
    elif s.lang == "rust":
        rust_project([(f"run_{i}", s)], f"run_{i}")
        manifest = ROOT / "rust" / ".snippetcheck" / "Cargo.toml"
        r = subprocess.run(["cargo", "build", "--quiet", "--manifest-path", str(manifest)], capture_output=True, text=True)
        if r.returncode:
            return r.stdout + r.stderr
        cmd = [str(ROOT / "rust" / ".snippetcheck" / "target" / "debug" / "snippetcheck")]
    elif s.lang in ("kotlin", "java"):
        jvm_project([(f"run_{i}", s)])
        r = gradle("classes", "classpath")
        if r.returncode:
            return r.stdout + r.stderr
        classpath = (ROOT / "kotlin" / ".snippetcheck" / "build" / "classpath.txt").read_text()
        java = Path(os.environ["JAVA_HOME"]) / "bin" / "java" if os.environ.get("JAVA_HOME") else "java"
        cmd = [str(java), "-cp", classpath, f"run_{i}.MainKt" if s.lang == "kotlin" else f"run_{i}.Main"]
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
    ap.add_argument("--langs", default="python,ts,go",
                    help="the languages to check, of python, ts, go, swift, kotlin, java, csharp, and rust")
    args = ap.parse_args()
    langs = set(args.langs.split(","))
    python = str(Path(args.python).absolute()) if os.sep in args.python else args.python

    snippets = [s for page in READMES + [p.resolve() for p in args.pages] for s in extract(page) if s.lang in langs]
    numbered = list(enumerate(snippets))
    failed = 0
    with tempfile.TemporaryDirectory(prefix="toskar-snippets-") as tmp_name:
        tmp = Path(tmp_name)
        try:
            problems: dict[int, str] = {}
            for lang, check in (("python", lambda n: check_python(n, python, mk(tmp, "py"))),
                                ("ts", lambda n: check_ts(n, mk(tmp, "ts"))),
                                ("go", lambda n: check_go(n, tmp)),
                                ("swift", lambda n: check_swift(n, tmp)),
                                ("csharp", lambda n: check_csharp(n, tmp)),
                                ("rust", lambda n: check_rust(n, tmp))):
                if lang in langs:
                    problems.update(check([(i, s) for i, s in numbered if s.lang == lang]))
            # Kotlin and Java build together, in one Gradle project.
            problems.update(check_jvm([(i, s) for i, s in numbered if s.lang in ("kotlin", "java")], tmp))
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
            shutil.rmtree(ROOT / "swift" / ".snippetcheck" / "Sources", ignore_errors=True)
            shutil.rmtree(ROOT / "kotlin" / ".snippetcheck" / "src", ignore_errors=True)
            shutil.rmtree(ROOT / "dotnet" / ".snippetcheck" / "Snippets", ignore_errors=True)
            shutil.rmtree(ROOT / "rust" / ".snippetcheck" / "src", ignore_errors=True)
    print(f"{failed} of {len(snippets)} snippets failed" if failed else f"all {len(snippets)} snippets work")
    return 1 if failed else 0


def mk(tmp: Path, name: str) -> Path:
    d = tmp / name
    d.mkdir(exist_ok=True)
    return d


if __name__ == "__main__":
    sys.exit(main())
