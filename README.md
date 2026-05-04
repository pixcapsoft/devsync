<div align="center">
  <h1>⚡ DevSync ⚡</h1>
  <p><strong>Automatic PC → Android file sync over WiFi. No USB. No manual steps.</strong></p>
  
  <p>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python version" /></a>
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Supported Platforms" />
    <img src="https://img.shields.io/badge/Status-Beta-brightgreen.svg" alt="Status" />
  </p>
</div>

---

**DevSync** is built for developers who want to push build outputs to their Android device automatically every time they build. With a beautiful GUI, managing your device connections and tracked files has never been easier!

## ✨ Features

| Feature | ADB Mode | HTTP Mode |
|---|:---:|:---:|
| **Push files/folders to Android** | ✅ Auto | ❌ Manual pull |
| **Watch & sync on change** | ✅ | ✅ (serves updated files) |
| **Handle renames** | ✅ | ⚠️ re-push |
| **Handle deletes** | ✅ | ⚠️ manual |
| **No app needed on Android** | ✅ (Dev options) | ✅ (browser) |
| **Works over WiFi** | ✅ | ✅ |

- **Beautiful Desktop GUI:** Modern dark-themed UI built with CustomTkinter.
- **Save Devices:** Quick-connect to your favorite Android devices.
- **Track Pairs:** Automatically push any local directory to a remote Android destination when files change.

---

## 🛠 Prerequisites

**PC side:**
- **Python 3.10+**
- **Android Platform Tools** ([Download here](https://developer.android.com/tools/releases/platform-tools)) (`adb` must be in your PATH)

**Android side (ADB mode):**
- **Developer Options** enabled.
- **Android 11+:** Enable **Wireless Debugging**.
- **Older Androids:** Connect via USB once, run `adb tcpip 5555`, then disconnect USB.

---

## 🚀 Installation & Getting Started

1. **Visit Release and get the latest version(Beta only available on Windows) and run it.**

### Build from source

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the GUI:**
   ```bash
   python gui.py
   ```

### Quick Start (GUI)

1. **Enable Wireless Debugging** on your Android device (Settings > Developer Options > Wireless Debugging) and note the IP Address & Port.
2. Open **DevSync GUI** and navigate to the **Connect** tab.
3. Enter the Android IP Address and Port, then click **Connect**.
4. Go to the **Files** tab and add a local file/folder and its Android destination path (e.g., `/sdcard/Download/app-debug.apk`).
5. Head over to the **Sync** tab and hit **Start Watch**! 🎉

Every time your files change or you run a build, your new files will be pushed to your Android automatically.

---

## 💻 Command Line Interface (CLI)

If you prefer the terminal, DevSync still has full CLI support!

```bash
# Connect to Android over WiFi
python cli/devsync.py connect --ip <IP>

# Add a file/folder to track
python cli/devsync.py add ./my-app/build/outputs /sdcard/DevTest/my-app

# Start watching + auto-sync on changes
python cli/devsync.py watch
```

### All CLI Commands

- `connect --ip <IP>`: Connect to Android over WiFi
- `devices`: List connected devices
- `add <local> <remote>`: Add a file/folder to track
- `remove <local>`: Stop tracking a file/folder
- `list`: Show all tracked sync pairs
- `push`: Manually push all tracked files now
- `watch`: Start watching & auto-syncing on changes
- `serve`: HTTP server mode (Android browser pull)

---

## 💡 Use Cases

- **Game Developer:** Push an APK on every build.
  Every Gradle/Unity build → APK auto-pushed to Android → Ready to install.
- **Web Developer:** Push static dist files to Android for mobile browser testing.
- **No ADB? Use HTTP mode:**
  Run the `serve` command and download files directly from your Android browser.

---

## ⚙️ How It Works

1. The **watchdog** service monitors your local files/folders for changes (creates, modifies, renames, deletes).
2. The corresponding `adb push` command is executed over WiFi.
3. The updated files land seamlessly on your Android device within seconds.

---

## ⚠️ Troubleshooting

- **"adb not found"**  
  Install Android Platform Tools and add `adb` to your system's PATH.
- **"No devices connected"**  
  Ensure you ran the connect command or connected via the GUI, and that the device shows "Connected" in Wireless Debugging.
- **"Connection refused"**  
  Both devices must be on the **same WiFi network**. Check your firewall rules (allow port 5555).
- **Files not syncing**  
  Click **Push Now** in the GUI for a manual sync to ensure ADB is working. Then start the **Watch** again.

---

<div align="center">
  <sub>Built with ❤️ by PixCap Soft.</sub>
</div>
