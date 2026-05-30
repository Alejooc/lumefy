import json
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
OUTPUT_DIR = ROOT / "docs" / "postman"

sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


SAFE_NO_AUTH_PATHS = {
    "/api/v1/login/access-token",
    "/api/v1/password-recovery/{email}",
    "/api/v1/reset-password",
    "/api/v1/register",
}


def title_case(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def resolve_ref(ref: str, components: dict) -> dict:
    name = ref.split("/")[-1]
    return components.get("schemas", {}).get(name, {})


def example_from_schema(schema: dict, components: dict, seen: set | None = None):
    if seen is None:
        seen = set()
    if not schema:
        return {}
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in seen:
            return {}
        seen.add(ref)
        return example_from_schema(resolve_ref(ref, components), components, seen)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    schema_type = schema.get("type")
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    if schema_type == "object" or "properties" in schema:
        result = {}
        required = set(schema.get("required", []))
        for key, value in schema.get("properties", {}).items():
            sample = example_from_schema(value, components, seen.copy())
            if sample != {} or key in required:
                result[key] = sample
        return result
    if schema_type == "array":
        item_value = example_from_schema(schema.get("items", {}), components, seen.copy())
        return [item_value]
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return True
    if schema_type == "string":
        schema_format = schema.get("format")
        if schema_format == "email":
            return "admin@lumefy.com"
        if schema_format == "date":
            return "2026-05-30"
        if schema_format == "date-time":
            return "2026-05-30T12:00:00Z"
        if schema_format in {"uuid", "guid"}:
            return "11111111-1111-1111-1111-111111111111"
        if schema_format == "binary":
            return "<seleccionar_archivo>"
        return "string"
    for key in ("anyOf", "oneOf", "allOf"):
        if schema.get(key):
            return example_from_schema(schema[key][0], components, seen.copy())
    return {}


def make_path_segments(path: str) -> list[str]:
    segments = [part for part in path.strip("/").split("/") if part]
    return [segment if not segment.startswith("{") else f":{segment[1:-1]}" for segment in segments]


def make_query_params(parameters: list[dict]) -> list[dict]:
    result = []
    for param in parameters:
        if param.get("in") != "query":
            continue
        schema = param.get("schema", {})
        value = example_from_schema(schema, {"schemas": {}})
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        result.append(
            {
                "key": param["name"],
                "value": "" if value in ({}, []) else str(value),
                "description": param.get("description", ""),
                "disabled": not param.get("required", False),
            }
        )
    return result


def make_body(request_body: dict, components: dict):
    if not request_body:
        return None, []
    content = request_body.get("content", {})
    if "application/json" in content:
        schema = content["application/json"].get("schema", {})
        sample = example_from_schema(schema, components)
        return (
            {
                "mode": "raw",
                "raw": json.dumps(sample, ensure_ascii=False, indent=2),
                "options": {"raw": {"language": "json"}},
            },
            [{"key": "Content-Type", "value": "application/json"}],
        )
    if "application/x-www-form-urlencoded" in content:
        schema = content["application/x-www-form-urlencoded"].get("schema", {})
        sample = example_from_schema(schema, components)
        urlencoded = []
        if isinstance(sample, dict):
            for key, value in sample.items():
                urlencoded.append({"key": key, "value": "" if value == {} else str(value), "type": "text"})
        return {"mode": "urlencoded", "urlencoded": urlencoded}, [
            {"key": "Content-Type", "value": "application/x-www-form-urlencoded"}
        ]
    if "multipart/form-data" in content:
        schema = content["multipart/form-data"].get("schema", {})
        resolved = example_from_schema(schema, components)
        formdata = []
        properties = schema.get("properties")
        if "$ref" in schema:
            properties = resolve_ref(schema["$ref"], components).get("properties", {})
        for key, value in (properties or {}).items():
            field_type = "file" if value.get("format") == "binary" else "text"
            formdata.append(
                {
                    "key": key,
                    "type": field_type,
                    "src": [] if field_type == "file" else None,
                    "value": "" if field_type == "file" else str(resolved.get(key, "")),
                }
            )
        return {"mode": "formdata", "formdata": formdata}, []
    return None, []


def make_description(operation: dict, full_path: str) -> str:
    summary = operation.get("summary") or f"{operation.get('operationId', 'request')}"
    lines = [summary, "", f"Endpoint: `{full_path}`"]
    if operation.get("description"):
        lines.extend(["", operation["description"]])
    return "\n".join(lines)


def collection_item(path: str, method: str, operation: dict, components: dict) -> dict:
    parameters = operation.get("parameters", [])
    query = make_query_params(parameters)
    body, headers = make_body(operation.get("requestBody"), components)
    auth_required = bool(operation.get("security")) and path not in SAFE_NO_AUTH_PATHS
    item = {
        "name": operation.get("summary") or f"{method.upper()} {path}",
        "request": {
            "method": method.upper(),
            "header": headers + ([{"key": "Accept", "value": "application/json"}] if True else []),
            "description": make_description(operation, path),
            "url": {
                "raw": "{{baseUrl}}" + path,
                "host": ["{{baseUrl}}"],
                "path": make_path_segments(path),
                "query": query,
            },
        },
        "response": [],
        "event": [
            {
                "listen": "test",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "pm.test('Status code is valid', function () {",
                        "  pm.expect(pm.response.code).to.be.oneOf([200, 201, 204, 400, 401, 403, 404, 422]);",
                        "});",
                    ],
                },
            }
        ],
    }
    if body:
        item["request"]["body"] = body
    if auth_required:
        item["request"]["auth"] = {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}],
        }
    return item


def folder_name_from_path(path: str) -> str:
    parts = [segment for segment in path.strip("/").split("/") if segment]
    if len(parts) < 3:
        return "General"
    if parts[0] == "api" and parts[1] == "v1":
        if parts[2] == "admin" and len(parts) > 3:
            return title_case("/".join(parts[2:4]))
        return title_case(parts[2])
    return title_case(parts[0])


def endpoint_line(method: str, path: str, operation: dict) -> str:
    summary = operation.get("summary") or operation.get("operationId", "")
    auth = "Si" if operation.get("security") and path not in SAFE_NO_AUTH_PATHS else "No"
    return f"| `{method.upper()}` | `{path}` | {summary} | {auth} |"


def build_assets():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    spec = app.openapi()
    components = spec.get("components", {})
    folders = defaultdict(list)
    endpoint_tables = defaultdict(list)

    for path in sorted(spec.get("paths", {})):
        operations = spec["paths"][path]
        for method in ("get", "post", "put", "delete", "patch"):
            operation = operations.get(method)
            if not operation:
                continue
            folder = folder_name_from_path(path)
            folders[folder].append(collection_item(path, method, operation, components))
            endpoint_tables[folder].append(endpoint_line(method, path, operation))

    collection = {
        "info": {
            "name": "Lumefy API",
            "_postman_id": "lumefy-api-generated",
            "description": "Coleccion generada desde el OpenAPI real del backend Lumefy.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "auth": {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}],
        },
        "event": [
            {
                "listen": "prerequest",
                "script": {
                    "type": "text/javascript",
                    "exec": [
                        "// Define {{baseUrl}} and {{access_token}} in the environment before running protected endpoints."
                    ],
                },
            }
        ],
        "variable": [
            {"key": "baseUrl", "value": "http://localhost:8000"},
            {"key": "access_token", "value": ""},
        ],
        "item": [{"name": folder, "item": items} for folder, items in sorted(folders.items())],
    }

    environment = {
        "name": "Lumefy Local",
        "values": [
            {"key": "baseUrl", "value": "http://localhost:8000", "enabled": True},
            {"key": "access_token", "value": "", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_at": "2026-05-30T00:00:00Z",
        "_postman_exported_using": "Codex",
    }

    md_lines = [
        "# Endpoints API Lumefy",
        "",
        "Base URL sugerida: `http://localhost:8000`",
        "",
        "Prefijo API: `/api/v1`",
        "",
        "Autenticacion:",
        "- Primero consume `POST /api/v1/login/access-token`.",
        "- Copia el `access_token` en la variable `access_token` de Postman.",
        "",
        f"Total de paths detectados: `{len(spec.get('paths', {}))}`",
        "",
    ]

    for folder in sorted(endpoint_tables):
        md_lines.extend(
            [
                f"## {folder}",
                "",
                "| Metodo | Endpoint | Descripcion | Requiere token |",
                "|---|---|---|---|",
            ]
        )
        md_lines.extend(endpoint_tables[folder])
        md_lines.append("")

    guide_lines = [
        "# Guia rapida para la evidencia",
        "",
        "## Archivos generados",
        "- `Lumefy.postman_collection.json`: coleccion lista para importar en Postman.",
        "- `Lumefy.local.postman_environment.json`: ambiente local con `baseUrl` y `access_token`.",
        "- `ENDPOINTS_Lumefy.md`: inventario de endpoints.",
        "- `REPOSITORIO.txt`: enlace del repositorio.",
        "",
        "## Instalacion de Postman",
        "1. Descarga Postman desde `https://www.postman.com/downloads/`.",
        "2. Instala la aplicacion.",
        "3. Importa la coleccion y el environment generados en `docs/postman/`.",
        "",
        "## Flujo de prueba recomendado",
        "1. Levanta el backend en `http://localhost:8000`.",
        "2. Ejecuta `POST /api/v1/login/access-token` con el usuario admin.",
        "3. Guarda el token en `access_token`.",
        "4. Prueba endpoints `GET` primero.",
        "5. Luego prueba `POST`, `PUT` y `DELETE` con datos controlados.",
        "",
        "## Sugerencia para video y pantallazos",
        "- Muestra el login exitoso.",
        "- Muestra minimo un `GET`, un `POST`, un `PUT` y un `DELETE`.",
        "- Muestra el codigo de respuesta y el body.",
        "- Toma pantallazos de cada prueba relevante y pegalos en tu documento.",
        "",
        "## Nombre de carpeta sugerido",
        "- `NOMBRE_APELLIDO_AA5_EV04`",
        "",
        "## Credenciales iniciales segun README",
        "- Email: `admin@lumefy.com`",
        "- Password: `admin123`",
    ]

    repo_text = "Repositorio: https://github.com/Alejooc/lumefy.git\n"

    (OUTPUT_DIR / "Lumefy.postman_collection.json").write_text(
        json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "Lumefy.local.postman_environment.json").write_text(
        json.dumps(environment, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "ENDPOINTS_Lumefy.md").write_text("\n".join(md_lines), encoding="utf-8")
    (OUTPUT_DIR / "GUIA_EVIDENCIA_POSTMAN.md").write_text("\n".join(guide_lines), encoding="utf-8")
    (OUTPUT_DIR / "REPOSITORIO.txt").write_text(repo_text, encoding="utf-8")


if __name__ == "__main__":
    build_assets()
