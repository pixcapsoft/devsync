"""
watcher.py - Monitor local files/folders and sync changes to Android.

Uses the 'watchdog' library to detect:
  - File created
  - File modified
  - File deleted
  - File/folder renamed/moved

On each event, the corresponding ADB or HTTP push is triggered.
"""

import os
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirModifiedEvent,
    DirDeletedEvent,
    DirMovedEvent,
)
from utils import log_info, log_success, log_error, log_warn


# Files/patterns to ignore (IDE artifacts, OS files, etc.)
IGNORE_PATTERNS = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
    ".git", "__pycache__", ".idea", ".vscode",
    "node_modules", ".gradle", "build",
}

IGNORE_EXTENSIONS = {
    ".tmp", ".swp", ".swo", "~",  # temp files
    ".class",                      # Java compiled
}


def should_ignore(path: str) -> bool:
    """Return True if this path should not be synced."""
    parts = Path(path).parts
    for part in parts:
        if part in IGNORE_PATTERNS:
            return True
    ext = os.path.splitext(path)[1]
    if ext in IGNORE_EXTENSIONS:
        return True
    # Ignore hidden files (starting with .)
    name = os.path.basename(path)
    if name.startswith(".") and name != ".":
        return True
    return False


class SyncEventHandler(FileSystemEventHandler):
    """Handles filesystem events and triggers sync operations."""

    def __init__(self, local_root: str, remote_root: str, bridge, method: str = "adb"):
        self.local_root = os.path.abspath(local_root)
        self.remote_root = remote_root.rstrip("/")
        self.bridge = bridge
        self.method = method
        self._debounce = {}          # path → last event time
        self._debounce_delay = 0.5   # seconds, avoid duplicate events
        self._lock = threading.Lock()

    def _remote_path(self, local_path: str) -> str:
        """Convert a local absolute path to its Android counterpart."""
        rel = os.path.relpath(local_path, self.local_root)
        # Normalize to forward slashes for Android
        rel = rel.replace(os.sep, "/")
        if rel == ".":
            return self.remote_root
        return f"{self.remote_root}/{rel}"

    def _debounced(self, path: str) -> bool:
        """Return True if this event is too soon after the last one (duplicate)."""
        now = time.time()
        with self._lock:
            last = self._debounce.get(path, 0)
            if now - last < self._debounce_delay:
                return True
            self._debounce[path] = now
        return False

    def _do_push(self, local_path: str):
        """Push a file or folder to Android."""
        if should_ignore(local_path):
            return
        if self._debounced(local_path):
            return

        remote = self._remote_path(local_path)
        rel = os.path.relpath(local_path, self.local_root)

        ok, msg = self.bridge.push(local_path, remote)
        if ok:
            log_success(f"  ↑ PUSH  {rel}  →  {remote}")
        else:
            log_error(f"  ✗ FAIL  {rel}: {msg}")

    def _do_delete(self, local_path: str):
        """Delete the corresponding file on Android."""
        if should_ignore(local_path):
            return
        if self._debounced(f"del:{local_path}"):
            return

        remote = self._remote_path(local_path)
        rel = os.path.relpath(local_path, self.local_root)

        if self.method == "adb":
            ok, msg = self.bridge.delete_remote(remote)
            if ok:
                log_warn(f"  ✗ DEL   {rel}  (also deleted on device)")
            else:
                log_error(f"  ✗ Could not delete remote {remote}: {msg}")
        else:
            log_warn(f"  ✗ DEL   {rel}  (manual delete needed on Android in HTTP mode)")

    def _do_rename(self, old_path: str, new_path: str):
        """Handle rename/move: rename on Android or re-push."""
        if should_ignore(old_path) and should_ignore(new_path):
            return

        old_remote = self._remote_path(old_path)
        new_remote = self._remote_path(new_path)
        old_rel = os.path.relpath(old_path, self.local_root)
        new_rel = os.path.relpath(new_path, self.local_root)

        if self.method == "adb":
            ok, msg = self.bridge.rename_remote(old_remote, new_remote)
            if ok:
                log_info(f"  ↕ MOVE  {old_rel}  →  {new_rel}")
            else:
                # Fallback: push the new path
                log_warn(f"  ↕ MOVE failed, re-pushing as: {new_rel}")
                self._do_push(new_path)
        else:
            # HTTP mode: just push new file
            self._do_push(new_path)

    # ─── Event handlers ────────────────────────────────────────────────────────

    def on_created(self, event):
        if not isinstance(event, (FileCreatedEvent, DirCreatedEvent)):
            return
        path = event.src_path
        if os.path.exists(path):
            self._do_push(path)

    def on_modified(self, event):
        if not isinstance(event, (FileModifiedEvent, DirModifiedEvent)):
            return
        path = event.src_path
        # Only push files, not directory modification events (too noisy)
        if os.path.isfile(path):
            self._do_push(path)

    def on_deleted(self, event):
        self._do_delete(event.src_path)

    def on_moved(self, event):
        self._do_rename(event.src_path, event.dest_path)


class SyncWatcher:
    """Manages multiple watchers for all configured sync pairs."""

    def __init__(self, pairs: list[dict], bridge, method: str = "adb"):
        self.pairs = pairs
        self.bridge = bridge
        self.method = method
        self.observer = Observer()
        self._handlers = []

    def start(self):
        """Start watching all sync pairs."""
        for pair in self.pairs:
            local = pair["local"]
            remote = pair["remote"]

            if not os.path.exists(local):
                log_error(f"Watch path not found, skipping: {local}")
                continue

            handler = SyncEventHandler(
                local_root=local if os.path.isdir(local) else os.path.dirname(local),
                remote_root=remote if os.path.isdir(local) else os.path.dirname(remote),
                bridge=self.bridge,
                method=self.method,
            )
            self._handlers.append(handler)

            watch_path = local if os.path.isdir(local) else os.path.dirname(local)
            self.observer.schedule(handler, watch_path, recursive=True)

        self.observer.start()

        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop all watchers."""
        self.observer.stop()
        self.observer.join()
