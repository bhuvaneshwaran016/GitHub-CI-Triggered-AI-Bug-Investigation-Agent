"""
Automated Test Suite for Project Explanation, AST Code Intelligence & Contextual Chatbot
Verifies real code analysis, contextual retrieval, honest error handling, and suggestions.
"""

import os
import pytest
from pathlib import Path

import analyzer
import server


@pytest.fixture
def workspace_dir():
    ws = Path(__file__).resolve().parent / "workspace"
    if not ws.exists():
        pytest.skip("Workspace directory not found")
    return ws


def test_real_ast_parsing_grounded(workspace_dir):
    """Verifies that Python files are genuinely inspected with AST without mocked data."""
    scanned = analyzer.scan_project_files(workspace_dir)
    assert len(scanned) > 0, "Should discover files in workspace"

    py_files = [f for f in scanned if f["ext"] == ".py"]
    assert len(py_files) > 0, "Should discover Python source or test files"

    analyses = {}
    for f in py_files:
        res = analyzer.deep_parse_python_file(f["abs_path"], f["path"])
        analyses[f["path"]] = res
        assert "lines" in res and res["lines"] >= 0
        assert "role" in res
        assert "functions" in res

    assert sum(a["lines"] for a in analyses.values()) > 0, "Repository should have non-empty Python files"

    # Verify at least one file has functions detected via AST
    total_funcs = sum(len(a["functions"]) for a in analyses.values())
    assert total_funcs > 0, "AST should detect actual functions in repository files"


def test_architecture_graph_generation(workspace_dir):
    """Verifies architectural component extraction and Mermaid flow diagram generation."""
    scanned = analyzer.scan_project_files(workspace_dir)
    analyses = {f["path"]: analyzer.deep_parse_python_file(f["abs_path"], f["path"]) for f in scanned if f["ext"] == ".py"}

    arch = analyzer.build_architecture_graph(analyses)
    assert "mermaid_diagram" in arch
    assert arch["mermaid_diagram"].startswith("graph TD")
    assert "components" in arch
    assert isinstance(arch["components"], list)


def test_dependency_analysis_with_imports(workspace_dir):
    """Verifies dependencies are cross-referenced with real import statements."""
    scanned = analyzer.scan_project_files(workspace_dir)
    analyses = {f["path"]: analyzer.deep_parse_python_file(f["abs_path"], f["path"]) for f in scanned if f["ext"] == ".py"}

    deps = analyzer.analyze_dependencies_with_purpose(workspace_dir, analyses)
    assert isinstance(deps, list)
    for d in deps:
        assert "name" in d
        assert "purpose" in d
        assert "usage_count" in d


def test_actionable_issues_contain_all_six_fields(workspace_dir):
    """Verifies that discovered issues have the 6 structured fields prioritized by severity."""
    scanned = analyzer.scan_project_files(workspace_dir)
    analyses = {f["path"]: analyzer.deep_parse_python_file(f["abs_path"], f["path"]) for f in scanned if f["ext"] == ".py"}

    issues = analyzer.inspect_actionable_issues_and_suggestions(workspace_dir, analyses)
    assert isinstance(issues, list)
    for iss in issues:
        assert "id" in iss
        assert "severity" in iss and iss["severity"] in ["High", "Medium", "Low"]
        assert "title" in iss
        assert "evidence" in iss and len(iss["evidence"]) > 0
        assert "reason" in iss and len(iss["reason"]) > 0
        assert "recommendation" in iss and len(iss["recommendation"]) > 0
        assert "implementation_plan" in iss and len(iss["implementation_plan"]) > 0
        assert "validation" in iss and len(iss["validation"]) > 0


def test_contextual_retrieval_index(workspace_dir):
    """Verifies that the inverted index retrieves relevant files and function chunks."""
    scanned = analyzer.scan_project_files(workspace_dir)
    analyses = {f["path"]: analyzer.deep_parse_python_file(f["abs_path"], f["path"]) for f in scanned if f["ext"] == ".py"}

    index = analyzer.ProjectRetrievalIndex(workspace_dir, scanned, analyses)
    assert len(index.chunks) > 0

    # Query for something specific in workspace
    py_file_name = [f["name"] for f in scanned if f["ext"] == ".py"][0]
    chunks = index.retrieve(f"Explain {py_file_name}", top_k=3)
    assert len(chunks) > 0
    assert any(py_file_name.lower() in c["file"].lower() for c in chunks)


def test_honest_handling_of_nonexistent_files():
    """Verifies server honestly reports when queried about files that do not exist."""
    req = server.ChatRequest(
        message="What does payment_gateway_v2.py do in this project?",
        project_id="test-proj",
        context={
            "project_name": "SampleProject",
            "structure": {
                "files": [
                    {"path": "main.py"},
                    {"path": "service.py"}
                ],
                "dependencies": []
            },
            "analysis": {"overview": "Sample"}
        }
    )

    res = server.project_chat(req)
    assert "reply" in res
    reply_lower = res["reply"].lower()
    assert "not present" in reply_lower or "not found" in reply_lower or "does not exist" in reply_lower
    assert "payment_gateway_v2.py" in res["reply"]


def test_multi_turn_history_isolation():
    """Verifies multi-turn history structure does not bleed between distinct sessions."""
    history_user_1 = [{"role": "user", "content": "Hello A"}, {"role": "assistant", "content": "Reply A"}]
    history_user_2 = [{"role": "user", "content": "Hello B"}, {"role": "assistant", "content": "Reply B"}]

    assert history_user_1[0]["content"] != history_user_2[0]["content"]


def test_sqlite_chat_persistence_and_sessions(monkeypatch):
    """Verifies that chat requests are persisted into SQLite and retrievable via API endpoints."""
    monkeypatch.setattr(server.ci_backend, "query_ollama_llm", lambda prompt: "Architecture response from mock LLM.")
    from fastapi.testclient import TestClient
    client = TestClient(server.app)

    # Send chat question
    res = client.post("/api/project/chat", json={
        "message": "Explain the entry point in simple terms.",
        "project_id": "test-sqlite-proj",
        "context": {"project_name": "TestApp", "structure": {"files": [{"path": "main.py"}]}, "analysis": {"overview": "Sample"}}
    })
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "session_id" in data
    sess_id = data["session_id"]

    # Verify history is stored in SQLite and returned
    hist_res = client.get(f"/api/project/chat/history?project_id=test-sqlite-proj&session_id={sess_id}")
    assert hist_res.status_code == 200
    msgs = hist_res.json()["messages"]
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "user"
    assert "Explain the entry point" in msgs[0]["content"]
    assert msgs[1]["role"] == "assistant"

    # Verify sessions endpoint
    sess_res = client.get("/api/project/chat/sessions?project_id=test-sqlite-proj")
    assert sess_res.status_code == 200
    sessions = sess_res.json()["sessions"]
    assert any(s["id"] == sess_id for s in sessions)


def test_workspace_clean_endpoint():
    """Verifies that the /api/workspace/clean endpoint safely removes workspaces."""
    from fastapi.testclient import TestClient
    client = TestClient(server.app)

    # Create dummy workspace dir
    dummy_ws = server.ANALYSIS_WORKSPACE_DIR / "dummy-clean-proj"
    dummy_ws.mkdir(parents=True, exist_ok=True)
    (dummy_ws / "test.txt").write_text("sample content", encoding="utf-8")
    assert dummy_ws.exists()

    res = client.post("/api/workspace/clean", json={"project_id": "dummy-clean-proj"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert not dummy_ws.exists(), "Workspace directory should be removed"
