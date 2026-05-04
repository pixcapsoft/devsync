#!/usr/bin/env python3
"""
DevSync GUI — Beautiful desktop interface for DevSync.
Wraps the CLI (in ./cli/) via subprocess.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import signal
import sys
import os
import json
import time
import re
from pathlib import Path

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG         = "#0b0b0b"
SURFACE    = "#111111"
CARD       = "#181818"
CARD2      = "#1e1e1e"
BORDER     = "#282828"
BORDER2    = "#333333"
ACCENT     = "#00c9e0"
ACCENT_DIM = "#006d7a"
SUCCESS    = "#28c76f"
WARNING    = "#ff9f43"
ERROR      = "#ea5455"
TEXT       = "#e8e8e8"
SUBTEXT    = "#6a6a6a"
DIM        = "#333333"
SIDEBAR_W  = 210

CLI_CONFIG_FILE = Path.home() / ".devsync" / "config.json"
GUI_CONFIG_FILE = Path.home() / ".devsync" / "gui_config.json"

FONT_MONO = "Courier New"
FONT_UI   = "Segoe UI" if sys.platform == "win32" else "SF Pro Display" if sys.platform == "darwin" else "Ubuntu"


# ── Config helpers ─────────────────────────────────────────────────────────────

def get_cli_path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    cli_exe = os.path.join(base, "cli", "cli.exe")
    if os.path.isfile(cli_exe):
        return cli_exe
    cli_py = os.path.join(base, "cli", "devsync.py")
    if os.path.isfile(cli_py):
        return cli_py
    raise FileNotFoundError(f"CLI not found. Expected: {cli_exe}")


def load_cli_config() -> dict:
    try:
        if CLI_CONFIG_FILE.exists():
            return json.loads(CLI_CONFIG_FILE.read_text())
    except Exception:
        pass
    return {"device_ip": None, "device_port": "5555", "sync_pairs": []}


def load_gui_config() -> dict:
    try:
        if GUI_CONFIG_FILE.exists():
            return json.loads(GUI_CONFIG_FILE.read_text())
    except Exception:
        pass
    return {"known_devices": []}


def save_gui_config(data: dict):
    GUI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    GUI_CONFIG_FILE.write_text(json.dumps(data, indent=2))


def save_known_device(ip: str, port: str):
    """Add/update a device in the saved devices list."""
    cfg = load_gui_config()
    devices = cfg.get("known_devices", [])
    # Avoid duplicates
    if not any(d["ip"] == ip and d["port"] == port for d in devices):
        devices.insert(0, {"ip": ip, "port": port, "last_used": int(time.time())})
        cfg["known_devices"] = devices[:10]  # keep last 10
        save_gui_config(cfg)


def remove_known_device(ip: str, port: str):
    cfg = load_gui_config()
    cfg["known_devices"] = [d for d in cfg.get("known_devices", [])
                             if not (d["ip"] == ip and d["port"] == port)]
    save_gui_config(cfg)


def kill_proc_tree(proc: subprocess.Popen):
    """Kill a process and all its children (cross-platform)."""
    if proc is None:
        return
    try:
        if sys.platform == "win32":
            subprocess.call(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass


# ── Reusable widgets ───────────────────────────────────────────────────────────

class Label(ctk.CTkLabel):
    def __init__(self, master, text, size=12, weight="normal", color=TEXT, **kw):
        super().__init__(master, text=text,
                         font=ctk.CTkFont(family=FONT_UI, size=size, weight=weight),
                         text_color=color, **kw)

class Heading(Label):
    def __init__(self, master, text, **kw):
        super().__init__(master, text, size=17, weight="bold", **kw)

class SubLabel(Label):
    def __init__(self, master, text, **kw):
        super().__init__(master, text, size=12, color=SUBTEXT, **kw)

class Divider(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=BORDER, height=1, **kw)

class Card(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=CARD, corner_radius=10,
                         border_width=1, border_color=BORDER, **kw)

class PrimaryButton(ctk.CTkButton):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text,
                         fg_color=ACCENT_DIM, hover_color=ACCENT, text_color="#ffffff",
                         font=ctk.CTkFont(family=FONT_UI, size=13, weight="bold"),
                         height=38, corner_radius=8, **kw)

class GhostButton(ctk.CTkButton):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text,
                         fg_color="transparent", hover_color=CARD2,
                         border_width=1, border_color=BORDER2, text_color=TEXT,
                         font=ctk.CTkFont(family=FONT_UI, size=12),
                         height=36, corner_radius=8, **kw)

class DangerButton(ctk.CTkButton):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text,
                         fg_color="transparent", hover_color="#2a0a0a",
                         border_width=1, border_color="#3a1212", text_color=ERROR,
                         font=ctk.CTkFont(family=FONT_UI, size=12),
                         height=36, corner_radius=8, **kw)

class Entry(ctk.CTkEntry):
    def __init__(self, master, **kw):
        super().__init__(master,
                         fg_color=SURFACE, border_color=BORDER2,
                         text_color=TEXT, placeholder_text_color=DIM,
                         font=ctk.CTkFont(family=FONT_MONO, size=12),
                         height=36, corner_radius=8, **kw)

class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text.upper(),
                         font=ctk.CTkFont(family=FONT_UI, size=12, weight="bold"),
                         text_color="#3a3a3a", **kw)


# ── Console ────────────────────────────────────────────────────────────────────

class Console(ctk.CTkTextbox):
    TAGS = {
        "success": SUCCESS, "error": ERROR, "warn": WARNING,
        "info": ACCENT, "dim": "#3a3a3a", "default": "#c0c0c0",
    }

    def __init__(self, master, **kw):
        super().__init__(master,
                         font=ctk.CTkFont(family=FONT_MONO, size=12),
                         text_color="#c0c0c0", fg_color="#080808",
                         border_color=BORDER, border_width=1,
                         corner_radius=8, wrap="word", **kw)
        self.configure(state="disabled")
        self._tw = self._textbox
        for name, color in self.TAGS.items():
            self._tw.tag_config(name, foreground=color)

    def write(self, text: str, tag: str = "default"):
        self.configure(state="normal")
        self._tw.insert("end", text + "\n", tag)
        self._tw.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")

    def smart_write(self, line: str):
        s = line.strip()
        if not s:
            return
        lo = s.lower()
        if any(x in s for x in ("✓", "✔")) or any(x in lo for x in ("pushed", "connected", "success")):
            self.write(s, "success")
        elif any(x in s for x in ("✗", "✘")) or any(x in lo for x in ("error", "fail", "not found")):
            self.write(s, "error")
        elif "warn" in lo or s.startswith("!"):
            self.write(s, "warn")
        elif any(x in lo for x in ("watching", "push", "sync", "start")):
            self.write(s, "info")
        elif s.startswith("--") or s.startswith("=="):
            self.write(s, "dim")
        else:
            self.write(s)


# ── Nav button ─────────────────────────────────────────────────────────────────

class NavButton(ctk.CTkButton):
    def __init__(self, master, icon: str, label: str, **kw):
        super().__init__(master, text=f" {icon}  {label}", anchor="w",
                         fg_color="transparent", hover_color="#1a1a1a",
                         text_color=SUBTEXT, font=ctk.CTkFont(family=FONT_UI, size=13),
                         height=40, corner_radius=6, **kw)

    def set_active(self, active: bool):
        self.configure(fg_color="#1a1a1a" if active else "transparent",
                       text_color=ACCENT if active else SUBTEXT)


# ── Device cards ───────────────────────────────────────────────────────────────

class ActiveDeviceCard(Card):
    """Shows an ADB-connected device."""
    def __init__(self, master, serial: str, **kw):
        super().__init__(master, **kw)
        ctk.CTkLabel(self, text="●", text_color=SUCCESS,
                     font=ctk.CTkFont(size=16)).pack(side="left", padx=(14, 0), pady=14)
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        Label(info, serial, size=13, weight="bold", anchor="w").pack(fill="x")
        SubLabel(info, "Connected via ADB  ·  WiFi", anchor="w").pack(fill="x")
        badge = ctk.CTkFrame(self, fg_color="#001a1f", corner_radius=6, width=44, height=20)
        badge.pack(side="right", padx=14)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="ADB", text_color=ACCENT,
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight="bold")).pack(expand=True)


class SavedDeviceCard(ctk.CTkFrame):
    """Quick-connect card for a saved (previously used) device."""
    def __init__(self, master, ip: str, port: str, on_connect, on_forget, **kw):
        super().__init__(master, fg_color=CARD2, corner_radius=8,
                         border_width=1, border_color=BORDER, **kw)
        self.ip, self.port = ip, port

        ctk.CTkLabel(self, text="📱", font=ctk.CTkFont(size=15)).pack(
            side="left", padx=(12, 0), pady=10)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        Label(info, f"{ip}", size=13, weight="bold", anchor="w").pack(fill="x")
        SubLabel(info, f"Port {port}", anchor="w").pack(fill="x")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)

        ctk.CTkButton(btn_frame, text="Connect", height=28, width=72,
                      fg_color=ACCENT_DIM, hover_color=ACCENT, text_color="#fff",
                      font=ctk.CTkFont(family=FONT_UI, size=11, weight="bold"),
                      corner_radius=6,
                      command=lambda: on_connect(ip, port)).pack(pady=(0, 4))

        ctk.CTkButton(btn_frame, text="Forget", height=22, width=72,
                      fg_color="transparent", hover_color="#2a0a0a",
                      border_width=1, border_color="#3a1212", text_color="#555",
                      font=ctk.CTkFont(family=FONT_UI, size=10),
                      corner_radius=6,
                      command=lambda: on_forget(ip, port)).pack()


# ── Sync pair row ──────────────────────────────────────────────────────────────

class SyncPairRow(Card):
    def __init__(self, master, pair: dict, on_remove, **kw):
        super().__init__(master, **kw)
        is_dir = os.path.isdir(pair["local"])
        ctk.CTkLabel(self, text="▤" if is_dir else "▪",
                     text_color=ACCENT if is_dir else "#888",
                     font=ctk.CTkFont(size=18), width=36).pack(side="left", padx=(12, 4))
        paths = ctk.CTkFrame(self, fg_color="transparent")
        paths.pack(side="left", fill="both", expand=True, pady=10)
        name = os.path.basename(pair["local"].rstrip("/\\")) or pair["local"]
        Label(paths, name, size=13, weight="bold", anchor="w").pack(fill="x")
        row = ctk.CTkFrame(paths, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="->", text_color=DIM,
                     font=ctk.CTkFont(family=FONT_MONO, size=11)).pack(side="left")
        ctk.CTkLabel(row, text="  " + pair["remote"], text_color=SUBTEXT,
                     font=ctk.CTkFont(family=FONT_MONO, size=11), anchor="w").pack(side="left")
        ctk.CTkButton(self, text="x", width=28, height=28,
                      fg_color="transparent", hover_color="#2a0a0a",
                      text_color="#444", font=ctk.CTkFont(size=14, weight="bold"),
                      command=lambda: on_remove(pair)).pack(side="right", padx=10)


# ── Status bar ─────────────────────────────────────────────────────────────────

class StatusBar(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="#080808", height=28, corner_radius=0, **kw)
        self.pack_propagate(False)
        self._dev = ctk.CTkLabel(self, text="No device",
                                  font=ctk.CTkFont(family=FONT_MONO, size=11),
                                  text_color=SUBTEXT)
        self._dev.pack(side="left", padx=14)
        ctk.CTkFrame(self, fg_color=BORDER, width=1, height=14).pack(side="left")
        self._pairs = ctk.CTkLabel(self, text="0 pairs",
                                    font=ctk.CTkFont(family=FONT_MONO, size=11),
                                    text_color=SUBTEXT)
        self._pairs.pack(side="left", padx=12)
        ctk.CTkFrame(self, fg_color=BORDER, width=1, height=14).pack(side="left")
        self._last = ctk.CTkLabel(self, text="",
                                   font=ctk.CTkFont(family=FONT_MONO, size=11),
                                   text_color=SUBTEXT)
        self._last.pack(side="left", padx=12)
        self._watch = ctk.CTkLabel(self, text="",
                                    font=ctk.CTkFont(family=FONT_MONO, size=11),
                                    text_color=SUCCESS)
        self._watch.pack(side="right", padx=14)

    def update(self, cfg: dict, watching: bool, last_sync: str = ""):
        ip, port = cfg.get("device_ip"), cfg.get("device_port", "5555")
        n = len(cfg.get("sync_pairs", []))
        self._dev.configure(text=f"●  {ip}:{port}" if ip else "○  No device",
                             text_color=SUCCESS if ip else SUBTEXT)
        self._pairs.configure(text=f"{n} pair{'s' if n != 1 else ''}")
        self._last.configure(text=f"Last sync: {last_sync}" if last_sync else "")
        self._watch.configure(text="●  Watching" if watching else "")


# ── Sidebar device widget ──────────────────────────────────────────────────────

class SidebarDeviceWidget(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="#0d0d0d", **kw)
        self._dot = ctk.CTkLabel(self, text="●", text_color=SUBTEXT,
                                  font=ctk.CTkFont(size=10))
        self._dot.pack(side="left", padx=(12, 4))
        self._lbl = ctk.CTkLabel(self, text="No device",
                                  font=ctk.CTkFont(family=FONT_MONO, size=10),
                                  text_color=SUBTEXT, anchor="w")
        self._lbl.pack(side="left", fill="x", expand=True)

    def refresh(self, cfg: dict):
        ip = cfg.get("device_ip")
        if ip:
            self._dot.configure(text_color=SUCCESS)
            self._lbl.configure(text=ip, text_color="#ccc")
        else:
            self._dot.configure(text_color=SUBTEXT)
            self._lbl.configure(text="No device", text_color=SUBTEXT)


# ── Main application ───────────────────────────────────────────────────────────

class DevSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DevSync  –  Android file sync over WiFi Build 0.0.3-Beta by PixCap Soft")
        self.geometry("850x750")
        self.minsize(820, 560)
        self.configure(fg_color=BG)

        self._cli         = get_cli_path()
        self._section     = None
        self._watch_proc: subprocess.Popen | None = None
        self._all_procs:  list[subprocess.Popen]  = []   # every spawned proc
        self._last_sync   = ""
        self._push_count  = 0

        self._build_layout()
        self._nav_to("connect")
        self._tick_status()

    # ── Layout ──────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Title bar
        tb = ctk.CTkFrame(self, fg_color="#080808", height=46, corner_radius=0)
        tb.pack(fill="x")
        tb.pack_propagate(False)
        ctk.CTkLabel(tb, text="⚡ DevSync",
                     font=ctk.CTkFont(family=FONT_UI, size=18, weight="bold"),
                     text_color=ACCENT).pack(side="left", padx=18)
        ctk.CTkFrame(tb, fg_color=BORDER, width=1, height=20).pack(side="left")
        ctk.CTkLabel(tb, text="  PC → Android  ·  WiFi",
                     font=ctk.CTkFont(family=FONT_UI, size=13),
                     text_color=SUBTEXT).pack(side="left")

        # Status bar
        self._statusbar = StatusBar(self)
        self._statusbar.pack(fill="x", side="bottom")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # Sidebar
        self._sidebar = ctk.CTkFrame(body, fg_color="#0d0d0d", width=SIDEBAR_W, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        ctk.CTkFrame(body, fg_color=BORDER, width=1).pack(side="left", fill="y")

        self._main = ctk.CTkFrame(body, fg_color=SURFACE, corner_radius=0)
        self._main.pack(side="left", fill="both", expand=True)

        self._frames = {
            "connect": self._make_connect(self._main),
            "files":   self._make_files(self._main),
            "sync":    self._make_sync(self._main),
        }

    def _build_sidebar(self):
        sb = self._sidebar

        # App label
        ctk.CTkLabel(sb, text="DEVSYNC",
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight="bold"),
                     text_color="#252525").pack(anchor="w", padx=14, pady=(18, 8))

        # Nav buttons
        self._nav_btns: dict[str, NavButton] = {}
        for key, icon, label in [
            ("connect", "📡", "Connect"),
            ("files",   "📁", "Files"),
            ("sync",    "⚡", "Sync"),
        ]:
            btn = NavButton(sb, icon, label, command=lambda k=key: self._nav_to(k))
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_btns[key] = btn

        Divider(sb).pack(fill="x", padx=14, pady=(16, 10))

        # Quick actions
        ctk.CTkLabel(sb, text="QUICK ACTIONS",
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight="bold"),
                     text_color="#252525").pack(anchor="w", padx=14, pady=(0, 6))

        ctk.CTkButton(sb, text=" ▲  Push Now", anchor="w",
                      fg_color="transparent", hover_color="#1a1a1a",
                      text_color=SUBTEXT, font=ctk.CTkFont(family=FONT_UI, size=13),
                      height=38, corner_radius=6,
                      command=self._do_push).pack(fill="x", padx=8, pady=2)

        ctk.CTkButton(sb, text=" ⟳  Refresh Scan", anchor="w",
                      fg_color="transparent", hover_color="#1a1a1a",
                      text_color=SUBTEXT, font=ctk.CTkFont(family=FONT_UI, size=13),
                      height=38, corner_radius=6,
                      command=self._do_scan).pack(fill="x", padx=8, pady=2)

        Divider(sb).pack(fill="x", padx=14, pady=(16, 10))

        # Device status section
        ctk.CTkLabel(sb, text="DEVICE",
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight="bold"),
                     text_color="#252525").pack(anchor="w", padx=14, pady=(0, 4))

        self._sb_device = SidebarDeviceWidget(sb)
        self._sb_device.pack(fill="x", padx=6, pady=(0, 8))

        # Pairs count
        ctk.CTkLabel(sb, text="TRACKED PAIRS",
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight="bold"),
                     text_color="#252525").pack(anchor="w", padx=14, pady=(0, 4))

        self._sb_pairs_lbl = ctk.CTkLabel(
            sb, text="0 pairs",
            font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=SUBTEXT, anchor="w")
        self._sb_pairs_lbl.pack(anchor="w", padx=14, pady=(0, 8))

        # Push count
        ctk.CTkLabel(sb, text="SESSION PUSHES",
                     font=ctk.CTkFont(family=FONT_UI, size=9, weight="bold"),
                     text_color="#252525").pack(anchor="w", padx=14, pady=(0, 4))

        self._sb_push_lbl = ctk.CTkLabel(
            sb, text="0",
            font=ctk.CTkFont(family=FONT_MONO, size=11), text_color=SUBTEXT, anchor="w")
        self._sb_push_lbl.pack(anchor="w", padx=14)

        # Bottom
        ctk.CTkFrame(sb, fg_color="transparent").pack(fill="y", expand=True)
        Divider(sb).pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(sb, text="v0.0.3-Beta  ·  pixcapsoft",
                     font=ctk.CTkFont(family=FONT_UI, size=10),
                     text_color="#252525").pack(padx=14, pady=(0, 14))

    # ── Section: Connect ──────────────────────────────────────────────────────

    def _make_connect(self, parent) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        self._section_header(f, "📡  Connect Device", "Join your Android over WiFi — no USB, no cables")

        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent", scrollbar_button_color=BORDER)
        scroll.pack(fill="both", expand=True, padx=24, pady=(16, 16))

        # Saved devices section
        SectionTitle(scroll, "Saved Devices").pack(anchor="w", pady=(0, 6))
        self._saved_devices_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self._saved_devices_frame.pack(fill="x", pady=(0, 20))
        self._refresh_saved_devices()

        # Manual connect
        SectionTitle(scroll, "Manual Connection").pack(anchor="w", pady=(0, 6))
        card = Card(scroll)
        card.pack(fill="x", pady=(0, 20))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=16)
        inner.grid_columnconfigure(0, weight=1)

        Label(inner, "Android IP address", size=13, color=SUBTEXT, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        Label(inner, "Port", size=13, color=SUBTEXT, anchor="w").grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 4))

        self._ip_entry = Entry(inner, placeholder_text="192.168.1.xx")
        self._ip_entry.grid(row=1, column=0, sticky="ew")
        self._port_entry = Entry(inner, placeholder_text="5555", width=80)
        self._port_entry.grid(row=1, column=1, padx=(8, 0))
        self._connect_btn = PrimaryButton(inner, "Connect  ->", command=self._do_connect)
        self._connect_btn.grid(row=1, column=2, padx=(8, 0))

        hint = ctk.CTkFrame(card, fg_color="#0d1a1a", corner_radius=6)
        hint.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(hint,
                     text="  Android 11+   ->  Settings > Developer Options > Wireless Debugging\n"
                          "  Older Android  ->  Connect USB once, run: adb tcpip 5555, unplug",
                     font=ctk.CTkFont(family=FONT_MONO, size=11),
                     text_color="#456", justify="left", anchor="w").pack(padx=12, pady=10)

        # Active devices
        SectionTitle(scroll, "Active ADB Devices").pack(anchor="w", pady=(0, 6))
        card2 = Card(scroll)
        card2.pack(fill="x")

        toolbar = ctk.CTkFrame(card2, fg_color="transparent")
        toolbar.pack(fill="x", padx=14, pady=12)
        GhostButton(toolbar, "Refresh", width=90, command=self._do_scan).pack(side="left")
        DangerButton(toolbar, "Disconnect All", width=130, command=self._do_disconnect).pack(
            side="left", padx=8)

        Divider(card2).pack(fill="x", padx=14)
        self._devices_area = ctk.CTkFrame(card2, fg_color="transparent")
        self._devices_area.pack(fill="x", padx=14, pady=12)
        SubLabel(self._devices_area,
                  "No devices found. Click Refresh or connect above.").pack(pady=16)

        return f

    def _refresh_saved_devices(self):
        for w in self._saved_devices_frame.winfo_children():
            w.destroy()
        devices = load_gui_config().get("known_devices", [])
        if not devices:
            SubLabel(self._saved_devices_frame,
                      "No saved devices yet. Connect a device and it will appear here.").pack(
                anchor="w", pady=(0, 4))
        else:
            for d in devices:
                SavedDeviceCard(self._saved_devices_frame,
                                ip=d["ip"], port=d["port"],
                                on_connect=self._quick_connect,
                                on_forget=self._forget_device).pack(fill="x", pady=(0, 6))

    def _quick_connect(self, ip: str, port: str):
        self._ip_entry.delete(0, "end")
        self._ip_entry.insert(0, ip)
        self._port_entry.delete(0, "end")
        self._port_entry.insert(0, port)
        self._do_connect()

    def _forget_device(self, ip: str, port: str):
        remove_known_device(ip, port)
        self._refresh_saved_devices()

    # ── Section: Files ────────────────────────────────────────────────────────

    def _make_files(self, parent) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        self._section_header(f, "📁  Sync Files",
                              "Manage which files and folders are tracked and where they land")

        SectionTitle(f, "Add Sync Pair").pack(anchor="w", padx=24, pady=(16, 6))
        add_card = Card(f)
        add_card.pack(fill="x", padx=24)

        form = ctk.CTkFrame(add_card, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=(14, 0))
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)

        Label(form, "Local path", size=13, color=SUBTEXT, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        Label(form, "Android destination", size=13, color=SUBTEXT, anchor="w").grid(
            row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 4))

        lw = ctk.CTkFrame(form, fg_color="transparent")
        lw.grid(row=1, column=0, sticky="ew")
        lw.grid_columnconfigure(0, weight=1)
        self._local_entry = Entry(lw, placeholder_text="/path/to/file-or-folder")
        self._local_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(lw, text="F", width=34, height=36,
                      fg_color=CARD2, hover_color=BORDER2, border_width=1, border_color=BORDER,
                      text_color=TEXT, corner_radius=8, command=self._browse_file).grid(row=0, column=1, padx=(0, 3))
        ctk.CTkButton(lw, text="D", width=34, height=36,
                      fg_color=CARD2, hover_color=BORDER2, border_width=1, border_color=BORDER,
                      text_color=TEXT, corner_radius=8, command=self._browse_folder).grid(row=0, column=2)

        self._remote_entry = Entry(form, placeholder_text="/sdcard/DevTest/")
        self._remote_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0))
        PrimaryButton(add_card, "+  Add Pair", command=self._do_add_pair).pack(
            anchor="w", padx=16, pady=14)

        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(16, 6))
        SectionTitle(bar, "Tracked Pairs").pack(side="left")
        self._pairs_count_lbl = SubLabel(bar, "")
        self._pairs_count_lbl.pack(side="right")

        self._pairs_scroll = ctk.CTkScrollableFrame(
            f, fg_color="transparent", scrollbar_button_color=BORDER)
        self._pairs_scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        self._refresh_pairs()
        return f

    # ── Section: Sync ─────────────────────────────────────────────────────────

    def _make_sync(self, parent) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, fg_color="transparent")
        self._section_header(f, "⚡  Sync", "One-shot push or continuous watch — your call")

        toolbar = ctk.CTkFrame(f, fg_color=CARD, height=62, corner_radius=0,
                                border_width=1, border_color=BORDER)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(side="left", padx=16, pady=12)

        self._push_btn = PrimaryButton(inner, "Push Now", width=130, command=self._do_push)
        self._push_btn.pack(side="left")
        ctk.CTkFrame(inner, fg_color=BORDER, width=1, height=36).pack(side="left", padx=14)
        self._watch_btn = GhostButton(inner, "Start Watch", width=140, command=self._toggle_watch)
        self._watch_btn.pack(side="left")
        self._watch_indicator = ctk.CTkLabel(inner, text="", text_color=SUCCESS,
                                              font=ctk.CTkFont(family=FONT_MONO, size=11))
        self._watch_indicator.pack(side="left", padx=14)

        GhostButton(toolbar, "Clear", width=70, command=self._clear_console).pack(
            side="right", padx=16, pady=12)

        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(12, 6))
        SectionTitle(bar, "Console Output").pack(side="left")

        self._console = Console(f)
        self._console.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        self._console.write("-- DevSync ready ------------------------------------------", "dim")

        return f

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _section_header(self, parent, title: str, subtitle: str):
        h = ctk.CTkFrame(parent, fg_color="#0d0d0d", corner_radius=0, height=60)
        h.pack(fill="x")
        h.pack_propagate(False)
        Heading(h, title).pack(anchor="w", padx=22, pady=(13, 0))
        SubLabel(h, subtitle).pack(anchor="w", padx=22)

    def _nav_to(self, key: str):
        if self._section == key:
            return
        self._section = key
        for k, btn in self._nav_btns.items():
            btn.set_active(k == key)
        for k, frame in self._frames.items():
            if k == key:
                frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            else:
                frame.place_forget()
        if key == "files":
            self._refresh_pairs()
        elif key == "connect":
            self._refresh_saved_devices()

    def _make_proc_flags(self) -> dict:
        """Subprocess flags to suppress console window on Windows."""
        flags = {}
        if sys.platform == "win32":
            flags["creationflags"] = subprocess.CREATE_NO_WINDOW
        return flags

    def _run_cli(self, *args, stream=False, on_done=None):
        """Spawn a CLI command in a daemon thread; stream output to console if requested."""
        def _worker():
            proc = subprocess.Popen(
                [self._cli] + list(args),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
                **self._make_proc_flags(),
            )
            self._all_procs.append(proc)
            lines = []
            for raw in proc.stdout:
                line = raw.rstrip()
                lines.append(line)
                if stream:
                    self.after(0, self._console.smart_write, line)
            proc.wait()
            if proc in self._all_procs:
                self._all_procs.remove(proc)
            if on_done:
                self.after(0, on_done, proc.returncode, lines)

        threading.Thread(target=_worker, daemon=True).start()

    def _tick_status(self):
        cfg = load_cli_config()
        watching = bool(self._watch_proc and self._watch_proc.poll() is None)
        self._statusbar.update(cfg, watching, self._last_sync)
        self._sb_device.refresh(cfg)
        n = len(cfg.get("sync_pairs", []))
        self._sb_pairs_lbl.configure(text=f"{n} pair{'s' if n != 1 else ''}" if n else "0 pairs")
        self._sb_push_lbl.configure(text=str(self._push_count))
        self.after(1500, self._tick_status)

    # ── Connect actions ────────────────────────────────────────────────────────

    def _do_connect(self):
        ip   = self._ip_entry.get().strip()
        port = self._port_entry.get().strip() or "5555"
        if not ip:
            messagebox.showwarning("Missing IP", "Enter the Android device IP address.")
            return

        self._connect_btn.configure(text="Connecting...", state="disabled")
        self._nav_to("sync")
        self._console.write(f"\n-- Connecting to {ip}:{port} --", "dim")

        def done(code, lines):
            self._connect_btn.configure(text="Connect  ->", state="normal")
            if code == 0:
                self._console.write(f"Connected to {ip}:{port}", "success")
                save_known_device(ip, port)          # ← save for quick-connect
                self._refresh_saved_devices()
                self.after(300, self._do_scan)
            else:
                self._console.write("Connection failed. Check IP and Wireless Debugging.", "error")

        self._run_cli("connect", "--ip", ip, "--port", port, stream=True, on_done=done)

    def _do_scan(self):
        for w in self._devices_area.winfo_children():
            w.destroy()
        SubLabel(self._devices_area, "Scanning...").pack(pady=12)

        def done(code, lines):
            for w in self._devices_area.winfo_children():
                w.destroy()

            # Parse device serials: lines from `adb devices` look like "192.x.x.x:5555   device"
            # or from our CLI "devices" output which prints them with leading spaces/symbols.
            # We match anything that looks like IP:PORT or "emulator-XXXX".
            ip_port_re = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})\b")
            emulator_re = re.compile(r"\b(emulator-\d+)\b")
            devices = []
            for line in lines:
                m = ip_port_re.search(line) or emulator_re.search(line)
                if m:
                    serial = m.group(1)
                    if serial not in devices:
                        devices.append(serial)

            if devices:
                for d in devices:
                    ActiveDeviceCard(self._devices_area, d).pack(fill="x", pady=(0, 6))
            else:
                SubLabel(self._devices_area, "No active devices. Try connecting manually.").pack(pady=16)

        self._run_cli("devices", on_done=done)

    def _do_disconnect(self):
        if messagebox.askyesno("Disconnect", "Disconnect all ADB devices?"):
            self._run_cli("devices", on_done=lambda *_: self.after(500, self._do_scan))

    # ── Files actions ──────────────────────────────────────────────────────────

    def _browse_file(self):
        p = filedialog.askopenfilename(title="Select file to sync")
        if p:
            self._local_entry.delete(0, "end")
            self._local_entry.insert(0, p)

    def _browse_folder(self):
        p = filedialog.askdirectory(title="Select folder to sync")
        if p:
            self._local_entry.delete(0, "end")
            self._local_entry.insert(0, p)

    def _do_add_pair(self):
        local  = self._local_entry.get().strip()
        remote = self._remote_entry.get().strip()
        if not local:
            messagebox.showwarning("Missing path", "Select a local file or folder.")
            return
        if not remote:
            messagebox.showwarning("Missing path", "Enter the Android destination path.")
            return
        if not os.path.exists(local):
            messagebox.showerror("Not found", f"Local path does not exist:\n{local}")
            return

        def done(code, lines):
            if code == 0:
                self._local_entry.delete(0, "end")
                self._remote_entry.delete(0, "end")
                self._refresh_pairs()
            else:
                messagebox.showerror("Error", "\n".join(lines[-5:]))

        self._run_cli("add", local, remote, on_done=done)

    def _do_remove_pair(self, pair: dict):
        name = os.path.basename(pair["local"].rstrip("/\\")) or pair["local"]
        if messagebox.askyesno("Remove pair", f"Stop tracking:\n{name}?"):
            self._run_cli("remove", pair["local"], on_done=lambda *_: self._refresh_pairs())

    def _refresh_pairs(self):
        for w in self._pairs_scroll.winfo_children():
            w.destroy()
        cfg = load_cli_config()
        pairs = cfg.get("sync_pairs", [])
        if not pairs:
            SubLabel(self._pairs_scroll,
                      "No sync pairs yet. Add a file or folder above.").pack(pady=32)
        else:
            for pair in pairs:
                SyncPairRow(self._pairs_scroll, pair, on_remove=self._do_remove_pair).pack(
                    fill="x", pady=(0, 8))
        n = len(pairs)
        self._pairs_count_lbl.configure(text=f"{n} pair{'s' if n != 1 else ''}" if n else "")

    # ── Sync actions ───────────────────────────────────────────────────────────

    def _do_push(self):
        self._nav_to("sync")
        self._console.write("\n-- Push ------------------------------------------------", "dim")
        self._push_btn.configure(state="disabled", text="Pushing...")

        def done(code, _):
            self._push_btn.configure(state="normal", text="Push Now")
            if code == 0:
                self._push_count += 1
                self._last_sync = time.strftime("%H:%M:%S")
            tag = "dim" if code == 0 else "error"
            self._console.write(
                "-- Done ------------------------------------------------" if code == 0
                else "-- Push failed -----------------------------------------", tag)

        self._run_cli("push", stream=True, on_done=done)

    def _toggle_watch(self):
        if self._watch_proc and self._watch_proc.poll() is None:
            self._stop_watch()
        else:
            self._start_watch()

    def _start_watch(self):
        self._console.write("\n-- Watch started ---------------------------------------", "dim")

        flags = self._make_proc_flags()
        # On Unix, start new process group so we can kill the whole tree
        if sys.platform != "win32":
            flags["start_new_session"] = True

        self._watch_proc = subprocess.Popen(
            [self._cli, "watch"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, encoding="utf-8", errors="replace",
            **flags,
        )
        self._all_procs.append(self._watch_proc)

        self._watch_btn.configure(
            text="Stop Watch", fg_color="#1a0a0a",
            hover_color="#2a0a0a", border_color="#3a1212", text_color=ERROR)
        self._watch_indicator.configure(text="● LIVE", text_color=SUCCESS)

        def stream():
            for raw in self._watch_proc.stdout:
                self.after(0, self._console.smart_write, raw.rstrip())
            self.after(0, self._on_watch_ended)

        threading.Thread(target=stream, daemon=True).start()

    def _stop_watch(self):
        if self._watch_proc:
            kill_proc_tree(self._watch_proc)
            if self._watch_proc in self._all_procs:
                self._all_procs.remove(self._watch_proc)
            self._watch_proc = None
        self._on_watch_ended()

    def _on_watch_ended(self):
        self._watch_btn.configure(
            text="Start Watch", fg_color="transparent",
            hover_color=CARD2, border_color=BORDER2, text_color=TEXT)
        self._watch_indicator.configure(text="")
        self._console.write("-- Watch stopped ---------------------------------------", "dim")

    def _clear_console(self):
        self._console.clear()
        self._console.write("-- Console cleared -------------------------------------", "dim")

    def on_close(self):
        """Kill every spawned subprocess before exiting — nothing survives the GUI."""
        # Stop watcher first
        if self._watch_proc and self._watch_proc.poll() is None:
            kill_proc_tree(self._watch_proc)

        # Kill any other lingering CLI processes (push, connect, scan, etc.)
        for proc in list(self._all_procs):
            if proc.poll() is None:
                kill_proc_tree(proc)

        self._all_procs.clear()
        self.destroy()


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    app = DevSyncApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
