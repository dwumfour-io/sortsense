# Changelog

All notable changes to SortSense will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

## [1.0.0] - 2026-01-17

### Added
- Initial release of SortSense
- OCR-powered text extraction using Tesseract
- PDF text extraction with pdftotext
- Support for images (PNG, JPG, JPEG, TIFF, BMP)
- Support for Word documents (.docx)
- Support for Excel files (.xlsx)
- Support for text files (.txt, .md)
- 8 default categories: finance, immigration, career, medical, education, dev, housing, vehicles
- Keyword-based categorization with confidence scoring
- Custom configuration file support (sortsense.json)
- Dry run mode for previewing changes
- Execute mode for moving files
- JSON report export
- Recursive folder scanning
- Progress bar with tqdm
- Cross-platform support (macOS, Linux, Windows)
- Transaction logging for undo support
- Python API for programmatic use
- CLI with analyze, organize, categories, and undo commands

### Security
- No external network calls
- All processing done locally

---

## Version History

- **1.0.0** - Initial public release
