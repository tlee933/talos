"""Tests for interaction building and rating enrichment (learning pipeline)."""

from talos.tui import build_interaction, build_reasoning_interaction


def test_build_interaction_with_commands():
    """Interaction dict has correct shape when commands were executed."""
    commands = [
        {"command": "ls -la", "success": True, "exit_code": 0},
        {"command": "cat README.md", "success": True, "exit_code": 0},
    ]
    result = build_interaction("show me the readme", commands, "Here are the files...")
    assert result is not None
    assert result["user_query"] == "show me the readme"
    assert len(result["commands"]) == 2
    assert result["success"] is True
    assert result["response_summary"] == "Here are the files..."


def test_build_interaction_empty_commands_returns_none():
    """No interaction logged when no commands were executed."""
    result = build_interaction("what is python?", [], "Python is a language.")
    assert result is None


def test_build_interaction_partial_failure():
    """success is False when any command failed."""
    commands = [
        {"command": "ls /tmp", "success": True, "exit_code": 0},
        {"command": "cat /nonexistent", "success": False, "exit_code": 1},
    ]
    result = build_interaction("check files", commands)
    assert result is not None
    assert result["success"] is False


def test_build_interaction_truncates_summary():
    """Response summary is truncated to 500 chars."""
    long_summary = "x" * 1000
    result = build_interaction("test", [{"command": "echo hi", "success": True}], long_summary)
    assert len(result["response_summary"]) == 500


def test_rating_enrichment():
    """Rating field can be added to an existing interaction dict."""
    commands = [{"command": "ls", "success": True, "exit_code": 0}]
    interaction = build_interaction("list files", commands)
    assert "rating" not in interaction

    interaction["rating"] = "positive"
    assert interaction["rating"] == "positive"

    interaction["rating"] = "negative"
    assert interaction["rating"] == "negative"


# --- Model metadata tests ---

def test_build_interaction_with_model_metadata():
    """Model routing metadata is included when provided."""
    commands = [{"command": "ls", "success": True, "exit_code": 0}]
    result = build_interaction(
        "list files", commands, "output",
        model_used="HiveCoder-7B", model_id="hivecoder-7b",
        routing_reason="code_signals(3>=0)",
    )
    assert result["model_used"] == "HiveCoder-7B"
    assert result["model_id"] == "hivecoder-7b"
    assert result["routing_reason"] == "code_signals(3>=0)"
    assert "model_source" not in result


def test_build_interaction_r1_auto_tags_source():
    """R1 model responses are tagged with model_source='r1-distill'."""
    commands = [{"command": "tool:web_search", "success": True, "exit_code": 0}]
    result = build_interaction(
        "compare btrfs vs ext4", commands, "btrfs offers...",
        model_used="R1-Distill-14B", model_id="r1-distill-14b",
        routing_reason="reasoning_signals(4>1)",
    )
    assert result["model_source"] == "r1-distill"


def test_build_interaction_backward_compat_no_model():
    """Existing callers without model params still work."""
    commands = [{"command": "ls", "success": True, "exit_code": 0}]
    result = build_interaction("test", commands)
    assert "model_used" not in result
    assert "model_source" not in result


# --- Reasoning interaction tests ---

def test_build_reasoning_interaction_basic():
    """Reasoning interaction captures R1 answers for distillation."""
    result = build_reasoning_interaction(
        "explain why btrfs is better",
        "btrfs offers copy-on-write, snapshots, and checksumming...",
        model_used="R1-Distill-14B", model_id="r1-distill-14b",
        routing_reason="reasoning_signals(3>0)",
    )
    assert result is not None
    assert result["type"] == "reasoning"
    assert result["user_query"] == "explain why btrfs is better"
    assert result["model_source"] == "r1-distill"
    assert result["success"] is True


def test_build_reasoning_interaction_too_short_returns_none():
    """Reasoning interaction returns None for very short responses."""
    result = build_reasoning_interaction("test", "short")
    assert result is None


def test_build_reasoning_interaction_truncates():
    """Response summary is truncated to 2000 chars."""
    long_text = "x" * 5000
    result = build_reasoning_interaction("test", long_text, model_id="r1-distill-14b")
    assert len(result["response_summary"]) == 2000


def test_build_reasoning_interaction_no_model():
    """Reasoning interaction without model metadata still works."""
    result = build_reasoning_interaction("test", "a" * 100)
    assert result is not None
    assert "model_source" not in result
