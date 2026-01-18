<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/OCR-Tesseract-orange.svg" alt="Tesseract OCR">
</p>

<h1 align="center">📂 SortSense</h1>

<p align="center">
  <strong>Smart File Categorization & Reorganization System</strong><br>
  Uses OCR and text extraction to analyze file contents and automatically categorize documents.
</p>

---

## ✨ Features

- **🔍 OCR-Powered Analysis** - Extract text from scanned documents and images using Tesseract
- **📄 Multi-Format Support** - PDFs, images, Word docs, Excel, text files, and more
- **🏷️ Smart Categorization** - Keyword-based scoring with confidence levels
- **⚙️ Customizable Categories** - Define your own categories and keywords via config file
- **🔄 Dry Run Mode** - Preview changes before moving any files
- **📊 JSON Reports** - Export detailed analysis for review
- **🖥️ Cross-Platform** - Works on macOS, Linux, and Windows
- **↩️ Undo Support** - Rollback moves with transaction logging

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install sortsense
```

### From Source

```bash
git clone https://github.com/dwumfour-io/sortsense.git
cd sortsense
pip install -e .
```

### Requirements

- **Python 3.8+**
- **Tesseract OCR** (for image/scanned PDF support)

#### Install Tesseract

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install tesseract poppler
```
</details>

<details>
<summary><strong>Ubuntu/Debian</strong></summary>

```bash
sudo apt-get install tesseract-ocr poppler-utils
```
</details>

<details>
<summary><strong>Windows</strong></summary>

1. Download installer from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
2. Add to PATH or set `TESSERACT_PATH` environment variable
</details>

## 🚀 Quick Start

### Analyze a folder

```bash
# See what categories your files belong to
sortsense analyze ~/Downloads

# Analyze recursively with progress
sortsense analyze ~/Documents/unsorted -r --progress
```

### Organize files

```bash
# Preview what would happen (dry run)
sortsense organize ~/Downloads --dry-run

# Actually move files
sortsense organize ~/Downloads --execute

# Move to a specific destination
sortsense organize ~/Downloads --execute -d ~/Documents
```

### View categories

```bash
sortsense categories
```

### Export report

```bash
sortsense analyze ~/Documents -o analysis-report.json
```

## ⚙️ Configuration

Create a `sortsense.json` in your home directory or project folder:

```json
{
  "categories": {
    "finance": {
      "description": "Financial Documents",
      "folder": "finance",
      "keywords": ["invoice", "receipt", "payment", "tax", "bank", "statement"]
    },
    "legal": {
      "description": "Legal Documents", 
      "folder": "legal",
      "keywords": ["contract", "agreement", "attorney", "court", "legal"]
    },
    "work": {
      "description": "Work Documents",
      "folder": "work",
      "keywords": ["meeting", "project", "deadline", "memo", "report"]
    }
  },
  "settings": {
    "ocr_timeout": 30,
    "max_text_length": 2000,
    "default_category": "unsorted"
  }
}
```

### Load custom config

```bash
sortsense analyze ~/Downloads --config ~/my-sortsense.json
```

## 📁 Default Categories

| Category | Description | Example Keywords |
|----------|-------------|------------------|
| `documents` | Legal, Financial & Official Papers | invoice, receipt, tax, passport, contract |
| `work` | Career & Employment | resume, cv, offer letter, interview |
| `school` | Education & Academic | transcript, degree, diploma, course |
| `health` | Medical & Wellness | doctor, hospital, prescription, lab |
| `photos` | Pictures & Memories | photo, image, screenshot, selfie |
| `projects` | Tech, Code & Creative Work | python, javascript, github, api |
| `misc` | Uncategorized Files | (fallback for low-confidence files) |

## 📊 Supported File Types

| Type | Extensions | Extraction Method |
|------|------------|-------------------|
| **Images** | .png, .jpg, .jpeg, .tiff, .bmp | Tesseract OCR |
| **PDFs** | .pdf | pdftotext + OCR fallback |
| **Documents** | .docx, .doc, .rtf, .odt | python-docx / textract |
| **Spreadsheets** | .xlsx, .xls, .csv | openpyxl / pandas |
| **Text** | .txt, .md, .json, .xml | Direct read |

## 🔧 CLI Reference

```
sortsense <command> [options]

Commands:
  analyze     Analyze files and show categorization
  organize    Analyze and move files to categories
  categories  List available categories
  undo        Rollback last organize operation

Options:
  -r, --recursive     Process folders recursively
  -d, --destination   Base destination folder
  -c, --config        Path to config file
  -o, --output        Export JSON report
  --dry-run           Preview without moving
  --execute           Actually move files
  --progress          Show progress bar
  --verbose           Verbose output
  --max N             Limit to N files
```

## 🐍 Python API

```python
from sortsense import SortSense

# Initialize
ss = SortSense(destination="/path/to/organized")

# Analyze a single file
result = ss.analyze_file("/path/to/document.pdf")
print(f"Category: {result.category}")
print(f"Confidence: {result.confidence_score}")
print(f"Keywords: {result.keyword_matches}")

# Analyze a folder
results = ss.analyze_folder("/path/to/folder", recursive=True)

# Print summary
ss.print_summary()

# Execute moves
ss.execute_moves(dry_run=False)
```

## 🧪 Development

```bash
# Clone repo
git clone https://github.com/dwumfour-io/sortsense.git
cd sortsense

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR engine
- [Poppler](https://poppler.freedesktop.org/) - PDF utilities
- [python-docx](https://python-docx.readthedocs.io/) - Word document parsing

---

<p align="center">
  Made with ❤️ for organizing digital chaos
</p>
