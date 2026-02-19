"""Tests for talos.config.Config."""

import tempfile
from pathlib import Path

from talos.config import Config


def test_defaults():
    """Default config values when no file exists."""
    cfg = Config.load(Path("/nonexistent/path/config.yaml"))
    assert cfg.hivemind_url == "http://localhost:8090"
    assert cfg.obsidian_vault == ""
    assert cfg.confirm_commands == "always"
    assert "shell" in cfg.enabled_tools


def test_load_from_yaml():
    """Load config from a YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("hivemind_url: http://localhost:9999\n")
        f.write("confirm_commands: never\n")
        f.write("obsidian_vault: /home/user/vault\n")
        f.flush()
        cfg = Config.load(Path(f.name))

    assert cfg.hivemind_url == "http://localhost:9999"
    assert cfg.confirm_commands == "never"
    assert cfg.obsidian_vault == "/home/user/vault"


def test_partial_yaml():
    """Partial YAML — only override specified fields, rest stay default."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("confirm_commands: smart\n")
        f.flush()
        cfg = Config.load(Path(f.name))

    assert cfg.confirm_commands == "smart"
    assert cfg.hivemind_url == "http://localhost:8090"  # default


def test_empty_yaml():
    """Empty YAML file should produce default config."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        f.flush()
        cfg = Config.load(Path(f.name))

    assert cfg.hivemind_url == "http://localhost:8090"


def test_unknown_keys_ignored():
    """Unknown keys in YAML should be silently ignored."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("hivemind_url: http://localhost:8090\n")
        f.write("unknown_key: true\n")
        f.write("another_fake: 42\n")
        f.flush()
        cfg = Config.load(Path(f.name))

    assert cfg.hivemind_url == "http://localhost:8090"


def test_context_injection_default():
    """context_injection should default to True."""
    cfg = Config.load(Path("/nonexistent/path/config.yaml"))
    assert cfg.context_injection is True


def test_context_injection_override():
    """context_injection can be set via YAML."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("context_injection: false\n")
        f.flush()
        cfg = Config.load(Path(f.name))

    assert cfg.context_injection is False
