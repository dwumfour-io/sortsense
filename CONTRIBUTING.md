# Contributing to SortSense

First off, thank you for considering contributing to SortSense! 🎉

## Code of Conduct

By participating in this project, you agree to maintain a welcoming and inclusive environment for everyone.

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

When creating a bug report, include:
- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs **actual behavior**
- **Environment details** (OS, Python version, Tesseract version)
- **Sample files** (if possible and not sensitive)
- **Error messages** or logs

### 💡 Suggesting Features

Feature requests are welcome! Please include:
- **Clear description** of the feature
- **Use case** - why would this be useful?
- **Possible implementation** (optional)

### 🔧 Pull Requests

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```
4. **Make your changes** with clear commit messages
5. **Add tests** for new functionality
6. **Run tests** to ensure nothing is broken:
   ```bash
   pytest
   ```
7. **Lint your code**:
   ```bash
   ruff check .
   ruff format .
   ```
8. **Push** to your fork
9. **Open a Pull Request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/sortsense.git
cd sortsense

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode with dev dependencies
pip install -e ".[dev,full]"

# Install pre-commit hooks (optional)
pre-commit install
```

## Project Structure

```
sortsense/
├── sortsense/           # Main package
│   ├── __init__.py      # Package exports
│   ├── __main__.py      # Entry point for `python -m sortsense`
│   ├── cli.py           # Command-line interface
│   ├── config.py        # Configuration management
│   ├── extractor.py     # Text extraction (OCR, PDF, etc.)
│   ├── categorizer.py   # Categorization logic
│   ├── engine.py        # Main SortSense engine
│   └── utils.py         # Utility functions
├── tests/               # Test suite
├── examples/            # Example configs and usage
├── pyproject.toml       # Project configuration
└── README.md            # Documentation
```

## Coding Guidelines

### Style
- Follow PEP 8 (enforced by Ruff)
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Documentation
- Docstrings for all public functions/classes (Google style)
- Update README.md for new features
- Add changelog entry for notable changes

### Testing
- Write tests for new functionality
- Aim for >80% code coverage
- Use pytest fixtures for common setups

### Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Reference issues when applicable ("Fix #123")

## Adding New Categories

To add a new default category:

1. Edit `sortsense/config.py`
2. Add to `DEFAULT_CATEGORIES`:
   ```python
   "category_name": {
       "description": "Human-readable description",
       "folder": "folder_name",
       "keywords": ["keyword1", "keyword2", ...]
   }
   ```
3. Update README.md category table
4. Add tests for the new category

## Adding New File Types

To support a new file type:

1. Add extension to appropriate set in `config.py`
2. Implement extraction method in `extractor.py`
3. Update README.md supported file types table
4. Add tests with sample files

## Questions?

Feel free to open an issue with the "question" label if you need help!

---

Thank you for contributing! 🙌
