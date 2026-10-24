"""Generates the Python SDK's code from spec/openapi.sdk.json.

- src/toskar/_generated/models.py: a Pydantic model for each schema
  (datamodel-code-generator).
- src/toskar/_generated/operations.py: a method for each operation, on Api
  and AsyncApi, named after its operationId.
- src/toskar/_generated/codes.py: the error codes, and the contract the SDK
  was built for.

    python scripts/generate.py
"""

from __future__ import annotations

import json
import keyword
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPEC = ROOT.parent / "spec" / "openapi.sdk.json"
ERRORS = ROOT.parent / "spec" / "errors.json"
OUT = ROOT / "src" / "toskar" / "_generated"
METHODS = ("get", "post", "put", "patch", "delete")


def models() -> None:
    subprocess.run(
        [
            sys.executable, "-m", "datamodel_code_generator",
            "--input", str(SPEC), "--input-file-type", "openapi",
            "--output", str(OUT / "models.py"),
            "--output-model-type", "pydantic_v2.BaseModel",
            "--target-python-version", "3.10",
            "--formatters", "black", "isort",
            "--use-standard-collections", "--use-union-operator", "--field-constraints",
            "--use-schema-description", "--use-field-description", "--snake-case-field",
            "--allow-population-by-field-name", "--extra-fields", "allow",
            "--disable-timestamp", "--use-annotated",
            # An inline object is named after its parent, such as ModelRatingModel,
            # so it never takes a schema's own name, such as Model.
            "--naming-strategy", "parent-prefixed",
        ],
        check=True,
    )


def snake(name: str) -> str:
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    return f"{name}_" if keyword.iskeyword(name) else name


def ref_name(schema: dict) -> str | None:
    ref = schema.get("$ref", "")
    return ref.rsplit("/", 1)[-1] if ref.startswith("#/components/schemas/") else None


def py_type(schema: dict | None, names: set[str]) -> str:
    """The Python type of a schema: a model where it's named, else a builtin."""
    if not schema:
        return "Any"
    if (name := ref_name(schema)) is not None:
        return f"models.{name}" if name in names else "Any"
    if "oneOf" in schema or "anyOf" in schema:
        options = [py_type(s, names) for s in schema.get("oneOf", schema.get("anyOf", []))]
        return "Any" if "Any" in options else " | ".join(options)
    kind = schema.get("type")
    if kind == "array":
        return f"list[{py_type(schema.get('items'), names)}]"
    if kind == "object":
        extra = schema.get("additionalProperties")
        if isinstance(extra, dict) and not schema.get("properties"):
            return f"dict[str, {py_type(extra, names)}]"
        return "dict[str, Any]"
    return {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}.get(kind, "Any")


def answer(op: dict, names: set[str]) -> tuple[str, str]:
    """What an operation answers: (Python type, how to read it: json, bytes, or none)."""
    for code, response in sorted(op.get("responses", {}).items()):
        if not str(code).startswith("2"):
            continue
        content = response.get("content") or {}
        if "application/json" in content:
            return py_type(content["application/json"].get("schema"), names), "json"
        if content:
            return "bytes", "bytes"
        return "None", "none"
    return "None", "none"


def doc(op: dict, body: dict | None) -> str:
    lines = [s.strip() for s in (op.get("summary"), op.get("description")) if s] or [op["operationId"]]
    if len(lines) == 2:
        lines.insert(1, "")
    if body and not ref_name(body) and body.get("properties"):
        lines.append("")
        lines.append("Body fields:")
        required = set(body.get("required", []))
        for name, prop in body["properties"].items():
            note = (prop.get("description") or "").strip()
            mark = " (required)" if name in required else ""
            lines.append(f"    {name}{mark}: {note}".rstrip(": ").rstrip())
    text = "\n".join(lines).replace('"""', "'''").replace("\\", "\\\\")
    return "\n".join(("        " + line if i and line else line) for i, line in enumerate(text.split("\n")))


def operations(spec: dict) -> str:
    names = set(spec["components"]["schemas"])
    sync: list[str] = []
    asyn: list[str] = []
    for path, ops in sorted(spec["paths"].items()):
        for method in METHODS:
            op = ops.get(method)
            if not op or "operationId" not in op:
                continue
            content = op.get("responses", {})
            only_stream = all(
                "text/event-stream" in (r.get("content") or {}) and "application/json" not in (r.get("content") or {})
                for c, r in content.items() if str(c).startswith("2")
            ) and any(str(c).startswith("2") for c in content)
            if only_stream:
                continue  # the events stream is Toskar.events()
            params = op.get("parameters", [])
            path_params = [p for p in params if p.get("in") == "path"]
            # Path parameters in the order the path names them.
            order = re.findall(r"\{([^}]+)\}", path)
            path_params.sort(key=lambda p: order.index(p["name"]) if p["name"] in order else 99)
            query = [p for p in params if p.get("in") == "query"]
            body_schema = (op.get("requestBody") or {}).get("content", {}).get("application/json", {}).get("schema")
            body_required = (op.get("requestBody") or {}).get("required", False)
            result, read = answer(op, names)

            args = ["self"] + [f"{snake(p['name'])}: str" for p in path_params]
            kw = []
            if body_schema is not None:
                body_type = py_type(body_schema, names)
                body_type = f"{body_type} | dict[str, Any]" if body_type.startswith("models.") else body_type
                kw.append(f"body: {body_type}" + ("" if body_required else " | None = None"))
            for q in query:
                kw.append(f"{snake(q['name'])}: {py_type(q.get('schema'), names)} | None = None")
            signature = ", ".join(args + (["*"] + kw if kw else []))
            path_expr = "f" + json.dumps(re.sub(r"\{([^}]+)\}", lambda m: "{" + snake(m.group(1)) + "}", path))
            query_expr = "{" + ", ".join(f"{json.dumps(q['name'])}: {snake(q['name'])}" for q in query) + "}"
            call = (
                f"_request({json.dumps(method.upper())}, {path_expr}, "
                f"query={query_expr}, body={'body' if body_schema is not None else 'None'}, "
                f"answer={result if read == 'json' else 'None'}, read={json.dumps(read)})"
            )
            name = snake(op["operationId"])
            text = doc(op, body_schema)
            sync.append(f'    def {name}({signature}) -> {result}:\n        """{text}"""\n        return self._client.{call}\n')
            asyn.append(f'    async def {name}({signature}) -> {result}:\n        """{text}"""\n        return await self._client.{call}\n')
    head = '''# Generated by scripts/generate.py from spec/openapi.sdk.json. Do not edit.
"""Every operation of Toskar Core's API, as a method named after its operationId."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import models

if TYPE_CHECKING:
    from .._client import AsyncToskar, Toskar


class Api:
    """Every route of the API, typed: toskar.api.list_models() and so on."""

    def __init__(self, client: Toskar) -> None:
        self._client = client

'''
    middle = '''

class AsyncApi:
    """Every route of the API, typed, for asyncio."""

    def __init__(self, client: AsyncToskar) -> None:
        self._client = client

'''
    return head + "\n".join(sync) + middle + "\n".join(asyn)


def codes(spec: dict) -> str:
    catalog = json.loads(ERRORS.read_text())
    lines = []
    for code in sorted(catalog):
        text = re.sub(r"\s+", " ", str(catalog[code])).replace('"""', "'''").replace("\\", "\\\\")
        lines.append(f'    {code} = "{code}"\n    """{text}"""')
    return (
        '# Generated by scripts/generate.py from Toskar Core\'s error catalog. Do not edit.\n'
        '"""Toskar Core\'s stable error codes, and the contract this SDK was built for."""\n\n'
        f'CONTRACT_VERSION = "{spec["info"]["version"]}"\n'
        '"""The client contract this SDK was built for."""\n\n\n'
        "class ErrorCodes:\n"
        '    """The codes Toskar Core answers errors with. A newer Core may answer with one this list doesn\'t have yet."""\n\n'
        + "\n".join(lines) + "\n"
    )


def main() -> None:
    spec = json.loads(SPEC.read_text())
    models()
    (OUT / "operations.py").write_text(operations(spec))
    (OUT / "codes.py").write_text(codes(spec))
    subprocess.run([sys.executable, "-m", "black", "-q", "-l", "120", str(OUT / "operations.py"), str(OUT / "codes.py")], check=True)
    (OUT / "__init__.py").write_text("# Generated by scripts/generate.py. Do not edit.\n")
    print(f"src/toskar/_generated: contract {spec['info']['version']}")


if __name__ == "__main__":
    main()
