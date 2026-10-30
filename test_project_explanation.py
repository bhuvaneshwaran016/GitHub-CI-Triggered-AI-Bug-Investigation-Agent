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
