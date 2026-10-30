# AI CI_Agent & Project Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20(qwen2.5:3b)-black?logo=ollama&logoColor=white)](https://ollama.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20(Salted%20PBKDF2)-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-Container%20Verification-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Pytest-12%2F12%20Passing-brightgreen?logo=pytest&logoColor=white)](https://pytest.org/)

An autonomous CI failure diagnosis, repair, and deep codebase understanding platform powered by local LLMs (`qwen2.5:3b`), Python AST code intelligence, containerized verification, and an editorial web interface.

---

## 🎨 Editorial Design System & Theme

* **Muted Sage Grey:** `#A5A79B` — Primary background and foundational surfaces
* **Warm Cream Beige:** `#E8D2B5` — Typography, cards, and light surfaces
* **Deep Burgundy:** `#590907` — Buttons, active states, and important accents
* **Typography:** Editorial typography pairing *Playfair Display* serif headings with *Fira Code* monospace accents
* **Kinetic Animations:** 3D Orbital CI Reactor emblem, interactive particle constellation backdrop, and conic border laser scanner beam

---

## 🌟 Key Capabilities

### 1. Codebase Intelligence & Project Explanation
Submit any GitHub repository URL or choose a local project directory (`webkitdirectory`) to receive a deep, grounded architectural analysis:
* **Overview:** Executive summary, language distribution metrics, and code volume stats.
* **Architecture:** Component boundaries, module responsibilities, and visual **Mermaid diagrams**.
* **File Explorer:** Interactive 2-column code browser with live AST metadata (file role, docstrings, classes, functions with signatures).
* **Execution Flow:** Step-by-step application lifecycle, entry points, and discovered REST API endpoints.
* **Dependencies & Ecosystem:** Manifest libraries cross-referenced against actual import statements across the codebase.
* **Testing & CI/CD:** GitHub Actions workflows and pytest configurations.
* **Issues & Actionable Suggestions:** Prioritized code deficits (concurrency race conditions, unhandled math boundaries, exception swallowing, missing build recipes) with 6 structured fields:
  * *Severity*, *Issue Title*, *Evidence*, *Reason*, *Recommendation*, *Implementation Plan*, and *Validation Command*.
* **Context-Aware AI Chatbot:** Multi-turn AI assistant with inverted keyword code chunk retrieval (`ProjectRetrievalIndex`) and honest handling of non-existent project files.

---

### 2. Autonomous CI Failure Diagnosis & Self-Healing Repair
Autonomous end-to-end self-healing pipeline for broken CI builds:
1. **Workspace Sandbox Isolation:** Clones repository into an isolated sandbox and auto-detects dependencies (`requirements.txt`, `pyproject.toml`, or `uv`).
2. **Baseline Reproduction:** Executes test suite to capture baseline failure exit codes and tracebacks.
3. **AST Fault Localization:** Dissects pytest failure traces and maps them to culprit source modules and failing test functions.
4. **Iterative Repair Loop:** Multi-round prompt engineering with AST syntax verification, test reconciliation, and regression protection.
5. **Docker Verification (Optional):** Runs pytest inside an ephemeral Linux container (`python:3.12-slim`) to eliminate "works on my machine" platform drift before committing.
6. **Publication Approval:** Human-in-the-loop review of unified diff before committing and pushing fixes to remote GitHub branches.

---

### 3. Privacy-First SQLite Authentication
User management backed by local SQLite (`users.db`):
* **Zero Plaintext Storage:** Passwords are cryptographically salted and hashed using **PBKDF2-HMAC-SHA256** with 100,000 rounds.
* **Constant-Time Verification:** Employs `secrets.compare_digest` to prevent timing side-channel attacks.
* **Forgot Password Recovery:** Secure 32-byte URL-safe reset tokens with a 1-hour expiration timestamp.
* **Authenticated Password Change:** Live modal for logged-in users to update their credentials.

---

## 🚀 Quick Start Guide

### Prerequisites
1. **Python 3.12+** and **[uv](https://github.com/astral-sh/uv)** installed.
2. **[Ollama](https://ollama.com/)** running locally:
   ```powershell
   ollama serve
   ollama pull qwen2.5:3b
   ```

---

### Method 1: Launch the Web Platform (Recommended)

1. Start the FastAPI application server:
   ```powershell
   uv run python server.py
   ```
2. Open your web browser at:
   👉 **`http://localhost:8000`**

3. Default seeded test credentials:
   * **Email:** `lead.engineer@taskflow.dev`
   * **Password:** `projectdemo2026`

---

### Method 2: Terminal CLI Autonomous Repair

Run the autonomous repair engine directly from your terminal:
```powershell
# Interactive mode
uv run python main.py

# Direct target repository URL
uv run python main.py https://github.com/bhuvaneshwaran016/Taskflow-Hard-Level-
```

---

### Method 3: Containerized Deployment (Docker)

To run the entire application inside Docker:

```powershell
# Build image
docker build -t ci-agent .

# Run container (connecting to host Ollama instance)
docker run -p 8000:8000 -e OLLAMA_HOST=http://host.docker.internal:11434 ci-agent
```

---

## 🧪 Automated Test Suite

Run the full automated test suite covering SQLite encryption, AST code parsing, contextual retrieval, and honest error handling:

```powershell
uv run pytest test_auth_db.py test_project_explanation.py -v
```

```
test_auth_db.py::test_sqlite_user_creation_and_hashing PASSED            [  8%]
test_auth_db.py::test_password_verification PASSED                       [ 16%]
test_auth_db.py::test_password_change PASSED                             [ 25%]
test_auth_db.py::test_forgot_and_reset_password_flow PASSED              [ 33%]
test_auth_db.py::test_api_auth_endpoints_end_to_end PASSED               [ 41%]
test_project_explanation.py::test_real_ast_parsing_grounded PASSED       [ 50%]
test_project_explanation.py::test_architecture_graph_generation PASSED   [ 58%]
test_project_explanation.py::test_dependency_analysis_with_imports PASSED [ 66%]
test_project_explanation.py::test_actionable_issues_contain_all_six_fields PASSED [ 75%]
test_project_explanation.py::test_contextual_retrieval_index PASSED      [ 83%]
test_project_explanation.py::test_honest_handling_of_nonexistent_files PASSED [ 91%]
test_project_explanation.py::test_multi_turn_history_isolation PASSED    [100%]
============================== 12 passed in 1.24s ==============================
```

---

## 📁 Repository Structure

```
.
├── auth_db.py                 # SQLite database layer, PBKDF2 hashing & reset tokens
├── analyzer.py                # Deep AST parser, Mermaid graph & ProjectRetrievalIndex
├── server.py                  # FastAPI server, REST endpoints & static file mounting
├── main.py                    # Autonomous CI detection, test runner & repair loop
├── Dockerfile                 # Multi-stage production container build recipe
├── .dockerignore              # Excludes virtual environments and ephemeral data
├── .gitignore                 # Excludes caches, SQLite DBs, sandboxes & temp files
├── pyproject.toml             # Project dependencies and tool configurations
├── test_auth_db.py            # Automated tests for SQLite auth & password privacy
├── test_project_explanation.py# Automated tests for AST engine & contextual chatbot
└── static/
    ├── index.html             # Semantic SPA with 7 analysis tabs & repair stepper
    ├── styles.css             # Editorial design system (Sage, Cream, Burgundy)
    └── app.js                 # Routing, kinetic animations, file preview & CI poller
```

---

## 📄 License
MIT License.
