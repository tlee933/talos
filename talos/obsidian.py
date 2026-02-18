"""Obsidian vault access — search, read, create notes.

Obsidian stores everything as plain markdown files in a vault directory.
No API needed, just filesystem operations + the obsidian:// URI for opening.
"""

import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Iterator


class Vault:
    def __init__(self, path: str | Path):
        self.root = Path(path).expanduser().resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"vault not found: {self.root}")

    def _notes(self) -> Iterator[Path]:
        """Yield all .md files, skipping .obsidian/ and .trash/."""
        for f in self.root.rglob("*.md"):
            rel = f.relative_to(self.root)
            if rel.parts[0].startswith("."):
                continue
            yield f

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across vault notes using ripgrep if available, else fallback."""
        results = []
        try:
            proc = subprocess.run(
                ["rg", "--files-with-matches", "--ignore-case", "--glob", "*.md",
                 "--glob", "!.obsidian/**", "--glob", "!.trash/**", query, str(self.root)],
                capture_output=True, text=True, timeout=10,
            )
            for line in proc.stdout.strip().splitlines()[:limit]:
                p = Path(line)
                results.append({
                    "path": str(p),
                    "name": p.stem,
                    "relative": str(p.relative_to(self.root)),
                })
        except FileNotFoundError:
            # ripgrep not installed, fallback to brute force
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            for note in self._notes():
                if len(results) >= limit:
                    break
                try:
                    if pattern.search(note.read_text(errors="replace")):
                        results.append({
                            "path": str(note),
                            "name": note.stem,
                            "relative": str(note.relative_to(self.root)),
                        })
                except OSError:
                    continue
        return results

    def read(self, name_or_path: str) -> str | None:
        """Read a note by name (without .md) or relative path."""
        # Try as relative path first
        candidate = self.root / name_or_path
        if candidate.is_file():
            return candidate.read_text(errors="replace")

        # Try with .md extension
        candidate = self.root / (name_or_path + ".md")
        if candidate.is_file():
            return candidate.read_text(errors="replace")

        # Search by stem
        for note in self._notes():
            if note.stem.lower() == name_or_path.lower():
                return note.read_text(errors="replace")

        return None

    def daily(self, folder: str = "Daily") -> Path:
        """Get or create today's daily note."""
        today = date.today().isoformat()
        daily_dir = self.root / folder
        daily_dir.mkdir(exist_ok=True)
        path = daily_dir / f"{today}.md"
        if not path.exists():
            path.write_text(f"# {today}\n\n")
        return path

    def append(self, name_or_path: str, content: str):
        """Append content to an existing note."""
        text = self.read(name_or_path)
        if text is None:
            raise FileNotFoundError(f"note not found: {name_or_path}")

        # Re-resolve the path
        for note in self._notes():
            if note.stem.lower() == name_or_path.lower() or str(
                note.relative_to(self.root)
            ) == name_or_path:
                with open(note, "a") as f:
                    f.write(content)
                return
        raise FileNotFoundError(f"note not found: {name_or_path}")

    def create(self, name: str, content: str, folder: str = "") -> Path:
        """Create a new note. Returns the path."""
        target_dir = self.root / folder if folder else self.root
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{name}.md"
        if path.exists():
            raise FileExistsError(f"note already exists: {path.relative_to(self.root)}")
        path.write_text(content)
        return path

    def open_in_obsidian(self, name_or_path: str):
        """Open a note in the Obsidian app via URI scheme."""
        vault_name = self.root.name
        # obsidian://open?vault=VaultName&file=path/to/note
        uri = f"obsidian://open?vault={vault_name}&file={name_or_path}"
        subprocess.Popen(
            ["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def list_recent(self, limit: int = 10) -> list[dict]:
        """List recently modified notes."""
        notes = []
        for note in self._notes():
            try:
                notes.append((note, note.stat().st_mtime))
            except OSError:
                continue
        notes.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "path": str(n.relative_to(self.root)),
                "name": n.stem,
                "modified": n.stat().st_mtime,
            }
            for n, _ in notes[:limit]
        ]

    def tags(self) -> dict[str, int]:
        """Count all #tags across the vault."""
        tag_counts: dict[str, int] = {}
        tag_re = re.compile(r"(?:^|\s)#([a-zA-Z][\w/-]*)", re.MULTILINE)
        for note in self._notes():
            try:
                text = note.read_text(errors="replace")
            except OSError:
                continue
            for match in tag_re.finditer(text):
                tag = match.group(1).lower()
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return dict(sorted(tag_counts.items(), key=lambda x: -x[1]))
