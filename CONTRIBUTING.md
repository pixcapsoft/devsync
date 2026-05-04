# Contributing to DevSync

First of all, thank you for considering contributing to DevSync! It's people like you that make it such a great tool for developers. We welcome all contributions, from bug reports and feature requests to code contributions and documentation improvements.

## How to Contribute

### 1. Reporting Bugs
- Ensure you have the latest version of DevSync installed.
- Check the [Issue Tracker](https://github.com/pixcapsoft/devsync/issues) to see if your bug has already been reported.
- Create a new issue describing the bug. Provide as much detail as possible, including:
  - Your operating system and Android version.
  - The mode you were using (ADB Mode or HTTP Mode).
  - Steps to reproduce the bug.
  - Expected behavior vs actual behavior.

### 2. Suggesting Features
- Check the [Issue Tracker](https://github.com/pixcapsoft/devsync/issues) for existing feature requests.
- Open a new issue with the `enhancement` label.
- Clearly describe your use case and why the feature would be beneficial for DevSync users.

### 3. Submitting Pull Requests
We gladly accept your pull requests. Please adhere to the following workflow:

1. **Fork the repository** to your own GitHub account.
2. **Clone the project** to your local machine.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```
5. Make your changes and ensure the CLI and GUI are both working:
   - To test the GUI, run `python gui.py`.
   - To test the CLI, run `python cli/devsync.py`.
6. **Commit your changes**. Write clear, concise commit messages.
7. **Push to your branch**.
8. Submit a **Pull Request** to the `main` branch of the official DevSync repository.
9. Wait for code review and approval. 

## Development Setup

To work on DevSync's source code, you'll need **Python 3.10+**.

Dependencies include `customtkinter`, `watchdog`, and `pyinstaller`. You can install them by running:
```bash
pip install -r requirements.txt
```

### Building the Project
DevSync is packaged using PyInstaller via a batch script.

To build the executable (for GUI and CLI):
```bash
.\build.bat
```
This will output the final nested `\dist` directory which serves as the portable app format. Note that the GUI requires `dist\cli\cli.exe` nested beside it, so ensure they are built and placed correctly if you make changes to internal paths.

## Code of Conduct
Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms. Always be respectful to other contributors.
