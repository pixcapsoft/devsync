"""
adb_bridge.py - Communicate with Android via ADB over WiFi.

ADB (Android Debug Bridge) is the most reliable method for developers.
No app needed on Android — works with standard developer options.

Setup (one-time):
  Option A: Enable "Wireless Debugging" in Android Developer Options (Android 11+)
  Option B: Connect USB once, run: adb tcpip 5555, then disconnect USB
"""

import subprocess
import os
import shutil
import socket
from utils import log_info, log_error, log_warn


class ADBBridge:
    def __init__(self, serial: str = None):
        self._check_adb()
        self._serial = serial  # e.g. "192.168.1.42:5555" — targets this device specifically

    def _check_adb(self):
        """Verify adb is installed and accessible."""
        if not shutil.which("adb"):
            log_error("'adb' not found in PATH.")
            log_warn("Install Android Platform Tools:")
            log_warn("  Windows: https://developer.android.com/tools/releases/platform-tools")
            log_warn("  macOS:   brew install android-platform-tools")
            log_warn("  Linux:   sudo apt install adb")
            raise EnvironmentError("ADB not installed")

    def _run(self, cmd: list, timeout: int = 30, no_target: bool = False) -> tuple[bool, str]:
        """
        Run an adb command and return (success, output).
        Automatically injects -s <serial> when a target device is set,
        preventing the 'more than one device' error.
        """
        base = ["adb"]
        # Inject -s <serial> for all commands except ones that don't target a device
        if self._serial and not no_target:
            base += ["-s", self._serial]
        try:
            result = subprocess.run(
                base + cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = (result.stdout + result.stderr).strip()
            success = result.returncode == 0 and "error" not in out.lower()[:50]
            return success, out
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def connect(self, ip: str, port: int = 5555) -> tuple[bool, str]:
        """Connect to Android device via TCP/IP and lock onto it as the target."""
        serial = f"{ip}:{port}"
        # connect doesn't use -s (it's establishing the connection)
        ok, out = self._run(["connect", serial], timeout=10, no_target=True)
        if "connected" in out.lower() or "already connected" in out.lower():
            self._serial = serial   # ← lock onto this device for all future commands
            return True, f"Connected to {serial}"
        return False, out

    def set_serial(self, serial: str):
        """Manually set the target device serial (e.g. loaded from config)."""
        self._serial = serial

    def disconnect(self, ip: str = None) -> tuple[bool, str]:
        """Disconnect from device."""
        cmd = ["disconnect"]
        if ip:
            cmd.append(ip)
        return self._run(cmd, no_target=True)

    def list_devices(self) -> list[str]:
        """Return list of connected device identifiers."""
        ok, out = self._run(["devices"], no_target=True)
        devices = []
        for line in out.splitlines()[1:]:  # skip header
            line = line.strip()
            if line and not line.startswith("*") and "\t" in line:
                serial, state = line.split("\t", 1)
                if state.strip() == "device":
                    devices.append(serial.strip())
        return devices

    def _resolve_serial(self) -> tuple[bool, str]:
        """
        Make sure we have a valid serial to target.
        If multiple devices exist and no serial is set, returns an error with guidance.
        """
        if self._serial:
            return True, self._serial

        devices = self.list_devices()
        if not devices:
            return False, "No Android device connected. Run: devsync connect --ip <ip>"
        if len(devices) == 1:
            self._serial = devices[0]
            return True, self._serial
        # Multiple devices, no serial configured
        device_list = "\n".join(f"    {d}" for d in devices)
        return False, (
            f"Multiple ADB devices found — don't know which to use:\n{device_list}\n"
            f"  Fix: run 'devsync connect --ip <ip>' to pick your WiFi device."
        )

    def push(self, local_path: str, remote_path: str) -> tuple[bool, str]:
        """
        Push a local file or folder to Android.
        Handles both files and directories.
        """
        if not os.path.exists(local_path):
            return False, f"Local path not found: {local_path}"

        ok, msg = self._resolve_serial()
        if not ok:
            return False, msg

        # Ensure remote directory exists
        if os.path.isfile(local_path):
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self._run(["shell", "mkdir", "-p", remote_dir])
        else:
            self._run(["shell", "mkdir", "-p", remote_path])

        ok, out = self._run(["push", local_path, remote_path], timeout=120)

        if ok or "pushed" in out.lower():
            lines = [l for l in out.splitlines() if "pushed" in l.lower()]
            summary = lines[-1] if lines else "Pushed successfully"
            return True, summary
        return False, out

    def push_file(self, local_file: str, remote_dir: str) -> tuple[bool, str]:
        """Push a single file into a remote directory."""
        filename = os.path.basename(local_file)
        remote_path = remote_dir.rstrip("/") + "/" + filename
        return self.push(local_file, remote_path)

    def delete_remote(self, remote_path: str) -> tuple[bool, str]:
        """Delete a file or folder on the Android device."""
        ok, msg = self._resolve_serial()
        if not ok:
            return False, msg
        return self._run(["shell", "rm", "-rf", remote_path])

    def rename_remote(self, old_path: str, new_path: str) -> tuple[bool, str]:
        """Rename/move a file on the Android device."""
        ok, msg = self._resolve_serial()
        if not ok:
            return False, msg
        return self._run(["shell", "mv", old_path, new_path])

    def list_remote(self, remote_path: str) -> list[str]:
        """List files at a remote Android path."""
        ok, out = self._run(["shell", "ls", "-la", remote_path])
        if ok:
            return [l.strip() for l in out.splitlines() if l.strip()]
        return []

    def device_info(self) -> dict:
        """Get basic info about the connected device."""
        _, model = self._run(["shell", "getprop", "ro.product.model"])
        _, android_ver = self._run(["shell", "getprop", "ro.build.version.release"])
        return {
            "model": model.strip(),
            "android": android_ver.strip(),
        }


def get_local_ip() -> str:
    """Get this machine's local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
