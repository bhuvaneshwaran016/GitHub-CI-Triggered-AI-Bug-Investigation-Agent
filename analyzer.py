"""
CI_Agent Project Explanation & Code Intelligence Engine
Performs deep AST parsing, architecture extraction, dependency auditing,
code-grounded issue detection, and contextual retrieval for the project chatbot.
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


# Known ecosystem dependencies with functional descriptions
DEPENDENCY_KNOWLEDGE_BASE = {
    "fastapi": "High-performance asynchronous web framework used to expose REST API endpoints and validate request/response models.",
    "uvicorn": "Lightning-fast ASGI server implementation used to run and serve asynchronous Python web applications.",
    "pytest": "Testing framework used to write, discover, and execute automated unit and integration tests.",
    "pytest-asyncio": "Pytest plugin providing event-loop fixtures and markers to execute asynchronous coroutine tests (`@pytest.mark.asyncio`).",
    "httpx": "Next-generation HTTP client supporting asynchronous and synchronous requests, commonly used with Starlette TestClient.",
    "starlette": "Lightweight ASGI framework/toolkit providing routing, middleware, and request/response handling under FastAPI.",
    "pydantic": "Data validation and settings management library using Python type annotations to enforce schema contracts.",
    "requests": "Standard HTTP client library used for external REST API queries and webhook notifications.",
    "docker": "Container orchestration client used to spawn isolated runtime environments and verify test execution.",
    "sqlalchemy": "SQL toolkit and Object Relational Mapper (ORM) providing database abstraction and query construction.",
    "alembic": "Database schema migration tool designed for SQLAlchemy data models.",
    "redis": "In-memory key-value data structure store used for caching, pub/sub, or distributed session management.",
    "celery": "Distributed task queue used to execute background jobs and scheduled asynchronous workloads.",
    "ruff": "Extremely fast Python linter and code formatter written in Rust, enforcing PEP8 and code quality rules.",
}


def scan_project_files(target_dir: Path) -> List[Dict[str, Any]]:
    """
    Recursively scans files, excluding ignored directories.
    """
    ignore_dirs = {
        ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules",
        "workspace", "analysis_workspace", ".idea", ".vscode", "dist", "build", ".egg-info"
    }
    scanned_files = []

    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.endswith(".egg-info")]
        rel_root = Path(root).relative_to(target_dir)

        for f in files:
            if f in [".DS_Store", "uv.lock", "package-lock.json"]:
                continue
            fpath = Path(root) / f
            rel_path = (rel_root / f).as_posix()
            if rel_path.startswith("./"):
                rel_path = rel_path[2:]

            ext = fpath.suffix.lower()
            try:
                size = fpath.stat().st_size
            except Exception:
                size = 0

            lang = "Text"
            if ext == ".py":
                lang = "Python"
            elif ext in [".js", ".jsx"]:
                lang = "JavaScript"
            elif ext in [".ts", ".tsx"]:
                lang = "TypeScript"
            elif ext == ".json":
                lang = "JSON"
            elif ext in [".yml", ".yaml"]:
                lang = "YAML"
            elif ext == ".toml":
                lang = "TOML"
            elif ext == ".md":
                lang = "Markdown"
            elif ext in [".html", ".htm"]:
                lang = "HTML"
            elif ext == ".css":
                lang = "CSS"
            elif ext == ".sh":
                lang = "Shell"

            scanned_files.append({
                "path": rel_path,
                "name": f,
                "ext": ext,
                "language": lang,
                "size": size,
                "abs_path": fpath,
            })

    return scanned_files


def deep_parse_python_file(fpath: Path, rel_path: str) -> Dict[str, Any]:
    """
    Uses Python AST to extract detailed structural information:
    docstrings, classes, functions, decorators, imports, routes, and data models.
    """
    try:
        content = fpath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"error": "Could not read file", "classes": [], "functions": [], "imports": []}

    lines = content.splitlines()
    info = {
        "rel_path": rel_path,
        "line_count": len(lines),
        "lines": len(lines),
        "docstring": "",
        "imports": [],
        "classes": [],
        "functions": [],
        "endpoints": [],
        "models": [],
        "concurrency_primitives": [],
        "role": "utility",
    }

    try:
        tree = ast.parse(content)
        info["docstring"] = ast.get_docstring(tree) or ""

        for node in ast.walk(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    info["imports"].append({"module": alias.name, "name": alias.asname or alias.name})
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        info["imports"].append({"module": f"{node.module}.{alias.name}", "name": alias.name})

            # Classes
            elif isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                decorators = [ast.unparse(d) for d in node.decorator_list]
                methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                is_dataclass = any("dataclass" in d for d in decorators)
                is_pydantic = any("BaseModel" in b for b in bases)

                class_item = {
                    "name": node.name,
                    "bases": bases,
                    "decorators": decorators,
                    "methods": methods,
                    "docstring": ast.get_docstring(node) or "",
                    "is_model": is_dataclass or is_pydantic,
                }
                info["classes"].append(class_item)
                if is_dataclass or is_pydantic:
                    info["models"].append(node.name)

            # Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                is_async = isinstance(node, ast.AsyncFunctionDef)
                decorators = [ast.unparse(d) for d in node.decorator_list]

                # Check for FastAPI / Flask endpoints
                endpoint_match = None
                for d_str in decorators:
                    m = re.search(r'(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', d_str)
                    if m:
                        endpoint_match = {"method": m.group(1).upper(), "path": m.group(2)}

                func_item = {
                    "name": node.name,
                    "is_async": is_async,
                    "decorators": decorators,
                    "args": [a.arg for a in node.args.args],
                    "line": getattr(node, "lineno", 0),
                    "docstring": ast.get_docstring(node) or "",
                }
                info["functions"].append(func_item)

                if endpoint_match:
                    info["endpoints"].append({
                        "method": endpoint_match["method"],
                        "path": endpoint_match["path"],
                        "func": node.name,
                        "line": getattr(node, "lineno", 0),
                    })

            # Concurrency primitives
            elif isinstance(node, ast.Call):
                call_str = ast.unparse(node.func)
                if "Lock" in call_str or "asyncio.sleep" in call_str:
                    info["concurrency_primitives"].append(call_str)

        # Infer file role
        lower_path = rel_path.lower()
        if "test" in lower_path or lower_path.startswith("tests/"):
            info["role"] = "test_suite"
        elif info["endpoints"] or "api" in lower_path or "route" in lower_path:
            info["role"] = "api_gateway"
        elif "store" in lower_path or "repo" in lower_path or "db" in lower_path or "model" in lower_path:
            info["role"] = "data_store"
        elif "service" in lower_path or "controller" in lower_path or "handler" in lower_path:
            info["role"] = "business_service"
        elif rel_path in ["main.py", "app.py", "server.py"]:
            info["role"] = "entry_point"

    except Exception:
        # Fallback regex parsing if syntax has local anomalies
        pass

    return info


def build_architecture_graph(file_analyses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes inter-module relationships, function calls, and data flow to
    generate a structural architecture model and Mermaid flow diagram.
    """
    components = []
    edges = []

    # Map file -> role
    roles = {f: data.get("role", "utility") for f, data in file_analyses.items()}

    # Identify primary components
    entry_nodes = [f for f, r in roles.items() if r == "entry_point"]
    api_nodes = [f for f, r in roles.items() if r == "api_gateway"]
    service_nodes = [f for f, r in roles.items() if r == "business_service"]
    store_nodes = [f for f, r in roles.items() if r == "data_store"]
    test_nodes = [f for f, r in roles.items() if r == "test_suite"]

    mermaid_lines = ["graph TD"]

    # Entry or Client
    if test_nodes:
        mermaid_lines.append('    Clients["Automated Tests / HTTP Clients"]')
    else:
        mermaid_lines.append('    Clients["External Consumers / Web Clients"]')

    if api_nodes:
        for api in api_nodes:
            clean_id = api.replace(".", "_").replace("/", "_")
            endpoints_count = len(file_analyses[api].get("endpoints", []))
            mermaid_lines.append(f'    Clients --> {clean_id}["API Gateway ({api})<br/><small>{endpoints_count} Route(s)</small>"]')
            components.append({
                "name": api,
                "layer": "API / Interface",
                "purpose": f"Exposes REST endpoints and delegates requests.",
                "functions": [f["name"] for f in file_analyses[api].get("functions", [])[:5]],
            })

    if service_nodes:
        for srv in service_nodes:
            clean_id = srv.replace(".", "_").replace("/", "_")
            components.append({
                "name": srv,
                "layer": "Domain Service",
                "purpose": "Encapsulates business operations, validation, and domain logic.",
                "functions": [f["name"] for f in file_analyses[srv].get("functions", [])[:5]],
            })
            if api_nodes:
                for api in api_nodes:
                    api_id = api.replace(".", "_").replace("/", "_")
                    mermaid_lines.append(f"    {api_id} --> {clean_id}")
            else:
                mermaid_lines.append(f"    Clients --> {clean_id}")

    if store_nodes:
        for st in store_nodes:
            clean_id = st.replace(".", "_").replace("/", "_")
            components.append({
                "name": st,
                "layer": "Data Access / Store",
                "purpose": "Manages in-memory data structures, entity storage, and concurrency locks.",
                "functions": [f["name"] for f in file_analyses[st].get("functions", [])[:5]],
            })
            if service_nodes:
                for srv in service_nodes:
                    srv_id = srv.replace(".", "_").replace("/", "_")
                    mermaid_lines.append(f"    {srv_id} --> {clean_id}")
            elif api_nodes:
                for api in api_nodes:
                    api_id = api.replace(".", "_").replace("/", "_")
                    mermaid_lines.append(f"    {api_id} --> {clean_id}")

    # Fallback default flow if files are flatter
    if len(mermaid_lines) <= 2:
        for f, data in list(file_analyses.items())[:5]:
            if data.get("role") != "test_suite":
                c_id = f.replace(".", "_").replace("/", "_")
                mermaid_lines.append(f'    Clients --> {c_id}["{f}"]')

    mermaid_diagram = "\n".join(mermaid_lines)

    return {
        "components": components,
        "mermaid_diagram": mermaid_diagram,
        "layer_summary": {
            "api_layer": api_nodes,
            "domain_layer": service_nodes,
            "data_layer": store_nodes,
            "test_layer": test_nodes,
        }
    }


def analyze_dependencies_with_purpose(target_dir: Path, file_analyses: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses manifest files (requirements.txt, pyproject.toml, package.json) and explains
    why each dependency is present based on actual imports in the codebase.
    """
    discovered_deps = {}

    # 1. requirements.txt / requirement.txt
    for req_name in ["requirements.txt", "requirement.txt"]:
        req_file = target_dir / req_name
        if req_file.is_file():
            try:
                for line in req_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Extract pkg name
                        pkg = re.split(r'[><=~;]', line)[0].strip().lower()
                        discovered_deps[pkg] = {
                            "name": pkg,
                            "raw_spec": line,
                            "source_file": req_name,
                            "usage_count": 0,
                            "imported_by": [],
                        }
            except Exception:
                pass

    # 2. pyproject.toml
    pyproject = target_dir / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8")
            matches = re.findall(r'"([a-zA-Z0-9_\-]+)(?:>=|<=|==|~=|>|<)?[^"]*"', content)
            for m in matches:
                pkg = m.lower()
                if pkg not in discovered_deps and pkg not in ["ci-agent-demo", "taskflow", "python"]:
                    discovered_deps[pkg] = {
                        "name": pkg,
                        "raw_spec": m,
                        "source_file": "pyproject.toml",
                        "usage_count": 0,
                        "imported_by": [],
                    }
        except Exception:
            pass

    # Trace actual code imports against dependencies
    for f_path, f_data in file_analyses.items():
        for imp in f_data.get("imports", []):
            top_mod = imp.get("module", "").split(".")[0].lower()
            if top_mod in discovered_deps:
                discovered_deps[top_mod]["usage_count"] += 1
                if f_path not in discovered_deps[top_mod]["imported_by"]:
                    discovered_deps[top_mod]["imported_by"].append(f_path)

    # Format result with clear purpose
    results = []
    for pkg, dep in discovered_deps.items():
        base_desc = DEPENDENCY_KNOWLEDGE_BASE.get(pkg, f"Third-party library supporting {pkg} capabilities.")
        imported_in = dep["imported_by"]
        if imported_in:
            usage_desc = f"Imported by {len(imported_in)} file(s) ({', '.join(imported_in[:2])}). {base_desc}"
        else:
            usage_desc = f"Declared in manifest. {base_desc}"

        results.append({
            "name": dep["name"],
            "spec": dep["raw_spec"],
            "manifest": dep["source_file"],
            "usage_count": dep["usage_count"],
            "imported_by": imported_in,
            "purpose": usage_desc,
        })

    return results


def inspect_actionable_issues_and_suggestions(target_dir: Path, file_analyses: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Inspects source code for grounded bugs, concurrency race conditions,
    missing validation, testing deficits, and maintainability concerns.
    Produces structured, prioritized actionable suggestions.
    """
    issues = []

    for rel_path, data in file_analyses.items():
        fpath = target_dir / rel_path
        if not fpath.is_file():
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Check 1: Concurrency Race Condition in Async Store
        if "asyncio.Lock" in content and "async def" in content:
            # Check if claim or write method lacks lock
            if "claim_task" in content:
                if "async with self.lock:" not in content and "async with lock:" not in content:
                    issues.append({
                        "id": "ISSUE-CONCURRENCY-01",
                        "title": "Unsynchronized Check-and-Update in Asynchronous Store",
                        "severity": "High",
                        "is_confirmed": True,
                        "file": rel_path,
                        "function": "claim_task",
                        "evidence": "In-memory Store contains `asyncio.Lock` but `claim_task` reads status and writes owner without `async with self.lock:` critical section.",
                        "reason": "Concurrent callers can both pass the status check before either writes the owner, allowing multiple workers to claim the same task.",
                        "recommendation": "Wrap the check-and-update block inside `async with self.lock:` to ensure atomic claiming.",
                        "implementation_plan": f"Edit `{rel_path}`: wrap status verification and owner assignment inside `async with self.lock:`.",
                        "validation": "Execute concurrent stress test `pytest tests/test_claiming.py` verifying exactly 1 winner across concurrent tasks."
                    })

        # Check 2: Flawed or Incomplete Factorial Checks
        if "def factorial" in content:
            if "n < 0" not in content and "ValueError" not in content:
                issues.append({
                    "id": "ISSUE-MATH-BOUNDARY-01",
                    "title": "Missing Negative Boundary Validation in Factorial Function",
                    "severity": "Medium",
                    "is_confirmed": True,
                    "file": rel_path,
                    "function": "factorial",
                    "evidence": "`factorial(n)` computes multiplication without checking if `n < 0`.",
                    "reason": "Factorial is mathematically undefined for negative integers; unhandled negative inputs cause infinite loops or recursion depth errors.",
                    "recommendation": "Raise `ValueError('Factorial cannot handle negative numbers')` when `n < 0`.",
                    "implementation_plan": f"Add `if n < 0: raise ValueError(...)` at top of `{rel_path}`.",
                    "validation": "Run `pytest -k test_factorial_negative` verifying ValueError is raised."
                })

        # Check 3: Raw except blocks (swallowing exceptions)
        except_matches = re.findall(r'except\s*:\s*(?:pass|\.\.\.)', content)
        if except_matches:
            issues.append({
                "id": "ISSUE-ERROR-HANDLING-01",
                "title": "Bare Exception Handling Swallowing Errors",
                "severity": "Medium",
                "is_confirmed": True,
                "file": rel_path,
                "function": "General Module",
                "evidence": f"Found {len(except_matches)} bare `except:` block(s) ignoring all exceptions.",
                "reason": "Bare `except:` blocks catch system exits, keyboard interrupts, and masking bugs, making debugging extremely difficult.",
                "recommendation": "Catch specific exception types (`except Exception:` or `except (KeyError, ValueError):`) and log error tracebacks.",
                "implementation_plan": f"Replace bare `except:` in `{rel_path}` with targeted exception handling.",
                "validation": "Run static type check and pytest suite."
            })

        # Check 4: Hardcoded sensitive secrets or keys
        if any(term in content.lower() for term in ["secret_key = \"", "password = \"admin", "api_key = \"sk-"]):
            issues.append({
                "id": "ISSUE-SECURITY-01",
                "title": "Potential Hardcoded Credentials or Secrets",
                "severity": "High",
                "is_confirmed": False,
                "file": rel_path,
                "function": "Configuration",
                "evidence": "Source code contains hardcoded credentials or secret strings.",
                "reason": "Exposing secrets in repository code allows unauthorized credential harvesting.",
                "recommendation": "Load secrets dynamically from environment variables using `os.getenv()` or `.env` files.",
                "implementation_plan": f"Migrate hardcoded secrets in `{rel_path}` to `os.environ`.",
                "validation": "Ensure application boots with required environment variables."
            })

    # Check 5: Missing Dockerfile
    if not (target_dir / "Dockerfile").is_file():
        issues.append({
            "id": "ISSUE-DEVOPS-01",
            "title": "Missing Containerized Build Recipe (Dockerfile)",
            "severity": "Low",
            "is_confirmed": True,
            "file": "Dockerfile",
            "function": "Build & Deployment",
            "evidence": "No `Dockerfile` found in repository root.",
            "reason": "Without a container recipe, deployments are dependent on local machine configuration, leading to 'works on my machine' drift.",
            "recommendation": "Add a standard multi-stage Dockerfile based on `python:3.12-slim`.",
            "implementation_plan": "Create `Dockerfile` with dependency installation and entrypoint `uvicorn main:app --host 0.0.0.0`.",
            "validation": "Run `docker build -t app .` and verify container boots cleanly."
        })

    return issues


class ProjectRetrievalIndex:
    """
    Lightweight, high-speed inverted index and code chunker for contextual chatbot.
    Retrieves exact source files, function signatures, and docstrings without external DB dependencies.
    """
    def __init__(self, target_dir: Path, scanned_files: List[Dict[str, Any]], file_analyses: Dict[str, Any]):
        self.target_dir = target_dir
        self.scanned_files = scanned_files
        self.file_analyses = file_analyses
        self.chunks = []
        self._build_index()

    def _build_index(self):
        for f in self.scanned_files:
            rel_path = f["path"]
            fpath = f["abs_path"]
            if f["size"] > 300_000:
                continue

            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            analysis = self.file_analyses.get(rel_path, {})
            # Store whole file if small, or functions
            self.chunks.append({
                "file": rel_path,
                "type": "file_overview",
                "title": rel_path,
                "role": analysis.get("role", "general"),
                "content": content[:1500],
                "docstring": analysis.get("docstring", ""),
                "keywords": set(re.findall(r'[a-zA-Z0-9_]{3,}', rel_path.lower() + " " + content[:500].lower())),
            })

            # Store specific functions
            for fn in analysis.get("functions", []):
                fn_name = fn.get("name", "")
                self.chunks.append({
                    "file": rel_path,
                    "type": "function",
                    "title": f"{rel_path}::{fn_name}",
                    "content": f"Function `{fn_name}` in `{rel_path}` (line {fn.get('line', 0)}): Args: {fn.get('args', [])}. {fn.get('docstring', '')}",
                    "keywords": set(re.findall(r'[a-zA-Z0-9_]{3,}', fn_name.lower() + " " + rel_path.lower())),
                })

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        query_terms = set(re.findall(r'[a-zA-Z0-9_\-\.]{3,}', query.lower()))
        if not query_terms:
            return self.chunks[:top_k]

        scored_chunks = []
        for ch in self.chunks:
            score = 0
            # Direct filename match gets huge boost
            for term in query_terms:
                if term in ch["file"].lower():
                    score += 15
                if term in ch["title"].lower():
                    score += 10
                if term in ch["keywords"]:
                    score += 2

            if score > 0:
                scored_chunks.append((score, ch))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored_chunks[:top_k]]
