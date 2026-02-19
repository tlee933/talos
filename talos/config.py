from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    hivemind_url: str = "http://localhost:8090"
    obsidian_vault: str = ""
    confirm_commands: str = "always"  # always | smart | never
    context_injection: bool = True
    enabled_tools: list[str] = field(
        default_factory=lambda: ["shell", "notify", "clipboard", "files", "obsidian"]
    )

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or Path.home() / ".config" / "talos" / "config.yaml"
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
