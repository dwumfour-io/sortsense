"""
SortSense - Smart File Categorization & Reorganization System

Uses OCR and text extraction to analyze file contents and automatically
categorize documents into organized folder structures.
"""

__version__ = "1.0.0"
__author__ = "SortSense Contributors"

from sortsense.engine import SortSense
from sortsense.categorizer import Categorizer
from sortsense.extractor import TextExtractor
from sortsense.config import Config, load_config

__all__ = [
    "SortSense",
    "Categorizer", 
    "TextExtractor",
    "Config",
    "load_config",
    "__version__",
]
