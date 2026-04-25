# Python Environment

This extension requires **Python 3.12 or later**.

## Auto-Detection

By default, the extension downloads `uv` into VS Code global storage and creates an isolated Python 3.12 environment there. Your system Python is not modified.

If `zoteroMcp.useEmbeddedPython` is disabled, the extension searches for Python in:
1. Your configured `zoteroMcp.pythonPath` setting
2. VS Code Python extension's interpreter
3. System `python3` or `python` command

Package installation still happens inside a writable virtual environment managed by the extension.

## If Python is Not Found

Install Python from [python.org](https://www.python.org/downloads/) or use your system's package manager:

```bash
# Ubuntu/Debian
sudo apt install python3.12

# macOS (Homebrew)
brew install python@3.12

# Windows
winget install Python.Python.3.12
```
