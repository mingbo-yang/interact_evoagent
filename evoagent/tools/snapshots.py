"""Workspace file snapshots for undo/rollback (P0.3).

Before a mutating file tool writes, it records the prior state of every path it
will touch as a *snapshot group* (one group per tool call). ``undo_last``
restores the most recent group, reverting that tool call: modified files are
rewritten with their backed-up bytes and newly-created files are removed.

Durability: each group is built in a temporary directory and atomically
``rename``d into place, so a group directory only ever exists once its manifest
and all backups are fully written. On construction the on-disk journal is
rebuilt, so an undo stack survives a crash. Snapshot + write are serialized
through an :class:`asyncio.Lock` since writes in the agent loop are serial.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from evoagent.core.time import utc_now_iso


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class SnapshotEntry:
    """Recorded prior state of one path within a group."""

    path: str  # workspace-relative
    existed: bool
    backup: str | None = None  # backup filename within the group dir, if existed
    post_sha: str | None = None  # sha256 of content written by the tool, if known


@dataclass
class SnapshotGroup:
    seq: int
    label: str
    timestamp: str
    entries: list[SnapshotEntry] = field(default_factory=list)


class WorkspaceSnapshotManager:
    """Manages stacked file snapshots under ``<workspace>/.evoagent/snapshots``."""

    def __init__(self, workspace: str | Path, snapshot_dir: str | Path | None = None,
                 max_groups: int = 50):
        self.workspace = Path(workspace).resolve()
        self.dir = Path(snapshot_dir).resolve() if snapshot_dir \
            else self.workspace / ".evoagent" / "snapshots"
        self.max_groups = max_groups
        self._lock = asyncio.Lock()
        self._groups: list[SnapshotGroup] = []
        self._rebuild()

    # ── persistence ──────────────────────────────────────────────────
    def _rebuild(self) -> None:
        """Reload the journal from disk, ignoring malformed/partial groups."""
        self._groups = []
        if not self.dir.exists():
            return
        for child in self.dir.iterdir():
            if not child.is_dir() or not child.name.isdigit():
                continue
            manifest = child / "manifest.json"
            if not manifest.exists():
                # Incomplete group (crash before atomic rename leftover) — drop it.
                shutil.rmtree(child, ignore_errors=True)
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                entries = [SnapshotEntry(**e) for e in data["entries"]]
                self._groups.append(SnapshotGroup(
                    seq=int(data["seq"]), label=data["label"],
                    timestamp=data["timestamp"], entries=entries))
            except Exception:
                shutil.rmtree(child, ignore_errors=True)
        self._groups.sort(key=lambda g: g.seq)

    def _next_seq(self) -> int:
        return (self._groups[-1].seq + 1) if self._groups else 1

    def _rel(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(self.workspace)).replace(os.sep, "/")

    def _is_internal(self, path: Path) -> bool:
        """True if path lives inside the snapshot dir (never snapshot those)."""
        try:
            Path(path).resolve().relative_to(self.dir)
            return True
        except ValueError:
            return False

    def _prune(self) -> None:
        while len(self._groups) > self.max_groups:
            oldest = self._groups.pop(0)
            shutil.rmtree(self.dir / str(oldest.seq), ignore_errors=True)

    # ── public API ───────────────────────────────────────────────────
    def record(self, paths: list[Path | str], label: str) -> int | None:
        """Snapshot the current state of ``paths`` as one new group.

        Call this immediately before performing the writes. Returns the group
        seq, or None if there was nothing to record.
        """
        resolved: list[Path] = []
        seen: set[str] = set()
        for p in paths:
            rp = Path(p).resolve()
            if self._is_internal(rp):
                continue
            key = str(rp)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(rp)
        if not resolved:
            return None

        seq = self._next_seq()
        tmp = self.dir / f".tmp-{seq}"
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True, exist_ok=True)

        entries: list[SnapshotEntry] = []
        for i, rp in enumerate(resolved):
            rel = self._rel(rp)
            if rp.exists() and rp.is_file():
                backup_name = f"{i}.bak"
                shutil.copyfile(rp, tmp / backup_name)
                entries.append(SnapshotEntry(path=rel, existed=True, backup=backup_name))
            else:
                entries.append(SnapshotEntry(path=rel, existed=False))

        group = SnapshotGroup(seq=seq, label=label, timestamp=utc_now_iso(), entries=entries)
        manifest = {"seq": seq, "label": label, "timestamp": group.timestamp,
                    "entries": [vars(e) for e in entries]}
        (tmp / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        # Atomic publish: the numbered group dir appears only once fully built.
        os.replace(tmp, self.dir / str(seq))
        self._groups.append(group)
        self._prune()
        return seq

    def finalize(self, seq: int, post: dict[str, str]) -> None:
        """Record the sha256 of content the tool wrote, for conflict reporting.

        ``post`` maps workspace-relative path -> written content (str). Files not
        present in ``post`` are left without a post hash.
        """
        group = next((g for g in self._groups if g.seq == seq), None)
        if group is None:
            return
        changed = False
        for e in group.entries:
            if e.path in post:
                e.post_sha = _sha(post[e.path].encode("utf-8"))
                changed = True
        if changed:
            manifest = {"seq": group.seq, "label": group.label,
                        "timestamp": group.timestamp,
                        "entries": [vars(e) for e in group.entries]}
            (self.dir / str(seq) / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8")

    def undo_last(self) -> dict:
        """Revert the most recent snapshot group.

        Returns a summary dict with restored/deleted/conflicted/skipped path lists.
        """
        if not self._groups:
            return {"ok": False, "error": "Nothing to undo.",
                    "restored": [], "deleted": [], "conflicted": [], "skipped": []}
        group = self._groups[-1]
        gdir = self.dir / str(group.seq)
        restored: list[str] = []
        deleted: list[str] = []
        conflicted: list[str] = []
        skipped: list[str] = []

        for e in group.entries:
            target = (self.workspace / e.path).resolve()
            # Note any divergence from what the tool wrote (external edits).
            if e.post_sha is not None and target.exists() and target.is_file():
                try:
                    cur = _sha(target.read_bytes())
                    if cur != e.post_sha:
                        conflicted.append(e.path)
                except Exception:
                    pass
            if e.existed:
                backup = gdir / (e.backup or "")
                if backup.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(backup, target)
                    restored.append(e.path)
                else:
                    skipped.append(e.path)
            else:
                # File was newly created by the tool; remove it (regular files only).
                if target.exists() and target.is_file():
                    target.unlink()
                    deleted.append(e.path)
                elif target.exists():
                    skipped.append(e.path)  # became a dir/something else — leave it

        self._groups.pop()
        shutil.rmtree(gdir, ignore_errors=True)
        return {"ok": True, "label": group.label, "seq": group.seq,
                "restored": restored, "deleted": deleted,
                "conflicted": conflicted, "skipped": skipped}

    def has_undo(self) -> bool:
        return bool(self._groups)

    def relpath(self, path: Path | str) -> str:
        return self._rel(Path(path))

    @property
    def lock(self) -> asyncio.Lock:
        return self._lock


async def apply_writes(snapshots: WorkspaceSnapshotManager | None,
                       writes: dict[Path, str], label: str) -> int | None:
    """Write ``{path: content}`` to disk, snapshotting first when enabled.

    When ``snapshots`` is provided, the snapshot + writes are serialized under
    the manager lock so the recorded pre-state and the writes stay consistent.
    Parent directories are created as needed. Returns the snapshot seq or None.
    """
    if snapshots is None:
        for p, content in writes.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return None
    async with snapshots.lock:
        seq = snapshots.record(list(writes.keys()), label)
        for p, content in writes.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        if seq is not None:
            snapshots.finalize(seq, {snapshots.relpath(p): c for p, c in writes.items()})
        return seq
