# Python Environment

This extension requires **Python 3.11 or later**.

## Auto-Detection

The extension automatically searches for Python in:
1. Your configured `zoteroMcp.pythonPath` setting
2. VS Code Python extension's interpreter
3. System `python3` or `python` command

## If Python is Not Found

Install Python from [python.org](https://www.python.org/downloads/) or use your system's package manager:

```bash
# Ubuntu/Debian
sudo apt install python3.11

# macOS (Homebrew)
brew install python@3.11

# Windows
winget install Python.Python.3.11
```
