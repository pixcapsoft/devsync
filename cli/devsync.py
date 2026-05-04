#!/usr/bin/env python3
"""
DevSync - Automatic file synchronization between PC and Android over WiFi/Bluetooth.
No USB needed. Watches for changes and pushes automatically.
"""

import argparse
import sys
import os

from config import ConfigManager
from watcher import SyncWatcher
from adb_bridge import ADBBridge
from http_bridge import HTTPBridge
from utils import print_banner, log_info, log_success, log_error, log_warn


def cmd_connect(args, config):
    """Connect to Android device via ADB over WiFi."""
    bridge = ADBBridge()

    if args.ip:
        log_info(f"Connecting to Android at {args.ip}:{args.port}...")
        success, msg = bridge.connect(args.ip, args.port)
        if success:
            log_success(msg)
            config.set("device_ip", args.ip)
            config.set("device_port", str(args.port))
            config.save()
        else:
            log_error(msg)
            log_warn("Make sure your Android device has:")
            log_warn("  1. WiFi Debugging enabled (Settings > Developer Options > Wireless debugging)")
            log_warn("  OR run once with USB: adb tcpip 5555")
            sys.exit(1)
    else:
        # Auto-discover
        log_info("Scanning for Android devices on local network...")
        devices = bridge.list_devices()
        if devices:
            for d in devices:
                log_success(f"Found: {d}")
        else:
            log_error("No ADB devices found.")
            log_warn("Connect via USB first and run: adb tcpip 5555")
            log_warn("Then use: devsync connect --ip <device-ip>")


def cmd_devices(args, config):
    """List connected devices."""
    bridge = ADBBridge()
    devices = bridge.list_devices()
    if devices:
        log_info(f"Connected devices ({len(devices)}):")
        for d in devices:
            print(f"  → {d}")
    else:
        log_warn("No devices connected. Use 'devsync connect --ip <ip>' first.")


def cmd_add(args, config):
    """Add a sync pair (local path → Android path)."""
    local = os.path.abspath(args.local)
    remote = args.remote

    if not os.path.exists(local):
        log_error(f"Local path does not exist: {local}")
        sys.exit(1)

    pairs = config.get("sync_pairs", [])
    for pair in pairs:
        if pair["local"] == local:
            log_warn(f"Already tracking: {local}")
            log_warn(f"  → {pair['remote']}")
            return

    pairs.append({"local": local, "remote": remote})
    config.set("sync_pairs", pairs)
    config.save()
    log_success(f"Added sync pair:")
    log_success(f"  Local:  {local}")
    log_success(f"  Remote: {remote}")


def cmd_remove(args, config):
    """Remove a sync pair."""
    local = os.path.abspath(args.local)
    pairs = config.get("sync_pairs", [])
    new_pairs = [p for p in pairs if p["local"] != local]

    if len(new_pairs) == len(pairs):
        log_error(f"No sync pair found for: {local}")
    else:
        config.set("sync_pairs", new_pairs)
        config.save()
        log_success(f"Removed sync pair for: {local}")


def cmd_list(args, config):
    """List all tracked sync pairs."""
    pairs = config.get("sync_pairs", [])
    if not pairs:
        log_warn("No sync pairs configured. Use 'devsync add <local> <remote>' to add one.")
        return

    log_info(f"Tracked sync pairs ({len(pairs)}):")
    for i, pair in enumerate(pairs, 1):
        kind = "DIR" if os.path.isdir(pair["local"]) else "FILE"
        print(f"  [{i}] [{kind}] {pair['local']}")
        print(f"       → {pair['remote']}")


def cmd_push(args, config):
    """Manually push all tracked files/folders to Android."""
    pairs = config.get("sync_pairs", [])
    if not pairs:
        log_error("No sync pairs configured.")
        sys.exit(1)

    device_ip = config.get("device_ip")
    if not device_ip:
        log_error("No device connected. Run 'devsync connect --ip <ip>' first.")
        sys.exit(1)

    serial = f"{device_ip}:{config.get('device_port', '5555')}"
    bridge = ADBBridge(serial=serial)
    success_count = 0
    fail_count = 0

    for pair in pairs:
        log_info(f"Pushing: {pair['local']} → {pair['remote']}")
        ok, msg = bridge.push(pair["local"], pair["remote"])
        if ok:
            log_success(f"  ✓ {msg}")
            success_count += 1
        else:
            log_error(f"  ✗ {msg}")
            fail_count += 1

    print()
    log_info(f"Done. {success_count} succeeded, {fail_count} failed.")


def cmd_watch(args, config):
    """Start watching and auto-syncing all tracked pairs."""
    pairs = config.get("sync_pairs", [])
    if not pairs:
        log_error("No sync pairs configured. Use 'devsync add' first.")
        sys.exit(1)

    method = args.method or config.get("method", "adb")

    if method == "adb":
        device_ip = config.get("device_ip")
        if not device_ip:
            log_error("No device connected. Run 'devsync connect --ip <ip>' first.")
            sys.exit(1)
        serial = f"{device_ip}:{config.get('device_port', '5555')}"
        bridge = ADBBridge(serial=serial)
    elif method == "http":
        port = int(args.http_port or config.get("http_port", "8765"))
        bridge = HTTPBridge(port=port)
        log_info(f"HTTP server mode - open http://<your-pc-ip>:{port} on Android")

    watcher = SyncWatcher(pairs, bridge, method=method)

    log_info("Starting DevSync watcher...")
    log_info(f"Method: {method.upper()}")
    log_info("Syncing pairs:")
    for pair in pairs:
        print(f"  {pair['local']} → {pair['remote']}")
    print()

    # Do an initial push
    if args.initial_push:
        log_info("Performing initial sync...")
        for pair in pairs:
            ok, msg = bridge.push(pair["local"], pair["remote"])
            if ok:
                log_success(f"  ✓ {os.path.basename(pair['local'])}")
            else:
                log_error(f"  ✗ {msg}")
        print()

    log_success("Watching for changes... (Ctrl+C to stop)")
    try:
        watcher.start()
    except KeyboardInterrupt:
        watcher.stop()
        log_info("DevSync stopped.")


def cmd_serve(args, config):
    """Start HTTP file server for manual Android download (no ADB needed)."""
    pairs = config.get("sync_pairs", [])
    port = int(args.port or config.get("http_port", "8765"))
    bridge = HTTPBridge(port=port, pairs=pairs)

    log_info(f"Starting HTTP server on port {port}...")
    log_info("On your Android device, open a browser or file manager and go to:")
    bridge.print_access_urls()
    print()
    log_warn("This mode lets Android pull files. For auto-push, use 'watch' with ADB.")

    try:
        bridge.serve_forever()
    except KeyboardInterrupt:
        log_info("Server stopped.")


def main():
    print_banner()

    config = ConfigManager()

    parser = argparse.ArgumentParser(
        prog="devsync",
        description="Sync files to Android over WiFi — automatically, no USB needed.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # connect
    p_connect = sub.add_parser("connect", help="Connect to Android device via ADB WiFi")
    p_connect.add_argument("--ip", help="Android device IP address")
    p_connect.add_argument("--port", type=int, default=5555, help="ADB port (default: 5555)")

    # devices
    sub.add_parser("devices", help="List connected devices")

    # add
    p_add = sub.add_parser("add", help="Add a file/folder to track")
    p_add.add_argument("local", help="Local file or folder path")
    p_add.add_argument("remote", help="Android destination path (e.g. /sdcard/DevTest/)")

    # remove
    p_remove = sub.add_parser("remove", help="Stop tracking a file/folder")
    p_remove.add_argument("local", help="Local file or folder path to remove")

    # list
    sub.add_parser("list", help="Show all tracked sync pairs")

    # push
    sub.add_parser("push", help="Manually push all tracked files to Android now")

    # watch
    p_watch = sub.add_parser("watch", help="Watch and auto-sync on every file change")
    p_watch.add_argument("--method", choices=["adb", "http"], help="Transfer method")
    p_watch.add_argument("--http-port", help="HTTP server port (for --method http)")
    p_watch.add_argument("--no-initial-push", dest="initial_push",
                         action="store_false", default=True,
                         help="Skip initial sync on start")

    # serve
    p_serve = sub.add_parser("serve", help="Start HTTP server so Android can pull files")
    p_serve.add_argument("--port", help="HTTP server port (default: 8765)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "connect": cmd_connect,
        "devices": cmd_devices,
        "add": cmd_add,
        "remove": cmd_remove,
        "list": cmd_list,
        "push": cmd_push,
        "watch": cmd_watch,
        "serve": cmd_serve,
    }

    dispatch[args.command](args, config)


if __name__ == "__main__":
    main()
