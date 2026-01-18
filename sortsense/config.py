"""
SortSense Configuration Management

Handles loading configuration from files and environment,
cross-platform tool detection, and default settings.
"""

import json
import os
import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "documents": {
        "description": "Legal, Financial & Official Papers",
        "folder": "documents",
        "keywords": [
            "invoice", "receipt", "payment", "transaction", "bank", "statement",
            "tax", "w-2", "w2", "1099", "paystub", "pay stub", "cheque", "check",
            "billing", "price", "total", "amount due", "balance", "purchase",
            "credit card", "debit", "venmo", "paypal", "salary", "wage",
            "visa", "passport", "immigration", "uscis", "green card", "citizenship",
            "birth certificate", "social security", "ssn", "drivers license",
            "national id", "contract", "agreement", "lease", "deed", "insurance",
            "mortgage", "utilities", "registration", "dmv", "vin"
        ]
    },
    "work": {
        "description": "Career & Employment",
        "folder": "work",
        "keywords": [
            "resume", "cv", "curriculum vitae", "career summary", "job application",
            "offer letter", "employment", "interview", "position", "cover letter",
            "professional experience", "job description", "work history",
            "references", "recommendation", "linkedin", "portfolio", "promotion",
            "performance review", "salary", "benefits", "onboarding"
        ]
    },
    "school": {
        "description": "Education & Academic",
        "folder": "school",
        "keywords": [
            "transcript", "degree", "diploma", "certificate", "university", "college",
            "course", "student", "academic", "gpa", "enrollment", "graduation",
            "school", "class", "semester", "credits", "scholarship", "syllabus",
            "assignment", "exam", "lecture", "professor", "homework", "thesis"
        ]
    },
    "health": {
        "description": "Medical & Wellness",
        "folder": "health",
        "keywords": [
            "medical", "health", "doctor", "hospital", "prescription", "patient",
            "diagnosis", "vaccination", "vaccine", "clinical", "fitness", "body scan",
            "lab results", "blood test", "pharmacy", "medicine", "therapy",
            "weight", "exercise", "workout", "physical", "dental", "vision",
            "insurance", "copay", "deductible"
        ]
    },
    "photos": {
        "description": "Pictures & Memories",
        "folder": "photos",
        "keywords": [
            "photo", "image", "picture", "dsc", "img_", "jpeg", "screenshot",
            "selfie", "family", "friends", "vacation", "trip", "holiday", "birthday",
            "wedding", "party", "event", "memories", "album", "camera", "portrait"
        ]
    },
    "projects": {
        "description": "Tech, Code & Creative Work",
        "folder": "projects",
        "keywords": [
            "programming", "javascript", "python", "html", "css", "code", "github",
            "software", "developer", "api", "server", "database", "linux", "mysql",
            "docker", "kubernetes", "cloud", "aws", "azure", "git", "npm", "react",
            "nodejs", "typescript", "design", "project", "portfolio", "creative"
        ]
    },
    "misc": {
        "description": "Uncategorized Files",
        "folder": "misc",
        "keywords": []
    }
}


# ═══════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Settings:
    """Runtime settings for SortSense"""
    
    # Text extraction
    ocr_timeout: int = 30
    max_text_length: int = 2000
    
    # Categorization
    default_category: str = "unsorted"
    min_confidence: int = 1
    
    # File handling
    skip_hidden: bool = True
    follow_symlinks: bool = False
    
    # Logging
    transaction_log: str = "sortsense-transactions.json"
    verbose: bool = False


# ═══════════════════════════════════════════════════════════════════════════
# FILE EXTENSIONS
# ═══════════════════════════════════════════════════════════════════════════

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.jfif', '.webp'}
PDF_EXTENSIONS = {'.pdf'}
WORD_EXTENSIONS = {'.docx', '.doc'}
EXCEL_EXTENSIONS = {'.xlsx', '.xls'}
TEXT_EXTENSIONS = {'.txt', '.md', '.rtf', '.json', '.xml', '.csv', '.log'}
SPREADSHEET_EXTENSIONS = {'.xlsx', '.xls', '.numbers', '.csv', '.ods'}


# ═══════════════════════════════════════════════════════════════════════════
# TOOL DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def detect_tesseract() -> Optional[str]:
    """Detect Tesseract OCR installation path"""
    # Check environment variable first
    env_path = os.environ.get("TESSERACT_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    
    # Common installation paths by platform
    system = platform.system()
    
    if system == "Darwin":  # macOS
        paths = [
            "/opt/homebrew/bin/tesseract",  # Apple Silicon
            "/usr/local/bin/tesseract",     # Intel Mac
        ]
    elif system == "Windows":
        paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    else:  # Linux
        paths = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
        ]
    
    # Check known paths
    for path in paths:
        if os.path.isfile(path):
            return path
    
    # Fall back to PATH lookup
    return shutil.which("tesseract")


def detect_pdftotext() -> Optional[str]:
    """Detect pdftotext installation path"""
    env_path = os.environ.get("PDFTOTEXT_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    
    return shutil.which("pdftotext")


def detect_pdftoppm() -> Optional[str]:
    """Detect pdftoppm installation path"""
    env_path = os.environ.get("PDFTOPPM_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    
    return shutil.which("pdftoppm")


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG CLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    """SortSense configuration container"""
    
    # Tool paths (auto-detected)
    tesseract_path: Optional[str] = field(default_factory=detect_tesseract)
    pdftotext_path: Optional[str] = field(default_factory=detect_pdftotext)
    pdftoppm_path: Optional[str] = field(default_factory=detect_pdftoppm)
    
    # Categories
    categories: Dict[str, Dict[str, Any]] = field(default_factory=lambda: DEFAULT_CATEGORIES.copy())
    
    # Vision categories (for CLIP model)
    vision_categories: Optional[Dict[str, List[str]]] = None
    
    # Settings
    settings: Settings = field(default_factory=Settings)
    
    # File extensions
    image_extensions: set = field(default_factory=lambda: IMAGE_EXTENSIONS.copy())
    pdf_extensions: set = field(default_factory=lambda: PDF_EXTENSIONS.copy())
    word_extensions: set = field(default_factory=lambda: WORD_EXTENSIONS.copy())
    excel_extensions: set = field(default_factory=lambda: EXCEL_EXTENSIONS.copy())
    text_extensions: set = field(default_factory=lambda: TEXT_EXTENSIONS.copy())
    
    def has_ocr(self) -> bool:
        """Check if OCR is available"""
        return self.tesseract_path is not None
    
    def has_pdf_tools(self) -> bool:
        """Check if PDF tools are available"""
        return self.pdftotext_path is not None
    
    def get_tools_status(self) -> Dict[str, str]:
        """Get status of all tools"""
        return {
            "tesseract": self.tesseract_path or "NOT FOUND",
            "pdftotext": self.pdftotext_path or "NOT FOUND",
            "pdftoppm": self.pdftoppm_path or "NOT FOUND",
        }


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG LOADING
# ═══════════════════════════════════════════════════════════════════════════

def get_user_config_dir() -> Path:
    """Get the user config directory (~/.sortsense/)"""
    return Path.home() / ".sortsense"


def get_user_config_path() -> Path:
    """Get the user config file path (~/.sortsense/config.json)"""
    return get_user_config_dir() / "config.json"


def find_config_file(start_path: Optional[str] = None) -> Optional[Path]:
    """
    Find sortsense config file.
    Search order: 
      1. ~/.sortsense/config.json (user config - highest priority)
      2. current dir → parent dirs 
      3. home dir
    """
    config_names = ["sortsense.json", ".sortsenserc", ".sortsense.json"]
    
    # First check user config directory
    user_config = get_user_config_path()
    if user_config.is_file():
        return user_config
    
    # Start from provided path or current directory
    search_dir = Path(start_path) if start_path else Path.cwd()
    
    # Search upward through parent directories
    for _ in range(10):  # Limit depth
        for name in config_names:
            config_path = search_dir / name
            if config_path.is_file():
                return config_path
        
        parent = search_dir.parent
        if parent == search_dir:  # Reached root
            break
        search_dir = parent
    
    # Check home directory
    home = Path.home()
    for name in config_names:
        config_path = home / name
        if config_path.is_file():
            return config_path
    
    return None


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from file or use defaults.
    
    Args:
        config_path: Explicit path to config file, or None to auto-detect
    
    Returns:
        Config object with loaded settings
    """
    config = Config()
    
    # Find config file
    if config_path:
        path = Path(config_path)
        if not path.is_file():
            raise FileNotFoundError(f"Config file not found: {config_path}")
    else:
        path = find_config_file()
    
    if not path:
        return config
    
    # Load JSON config
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file: {e}")
    
    # Apply categories
    if "categories" in data:
        # Check if user wants to replace all categories or just add/override
        if data.get("replace_default_categories", False):
            # Complete replacement - only use user categories
            config.categories = data["categories"]
        else:
            # Merge: user categories override defaults with same name
            for name, cat_config in data["categories"].items():
                config.categories[name] = cat_config
    
    # Apply settings
    if "settings" in data:
        settings_data = data["settings"]
        for key, value in settings_data.items():
            if hasattr(config.settings, key):
                setattr(config.settings, key, value)
    
    # Apply tool paths (if explicitly set)
    if "tools" in data:
        tools = data["tools"]
        if "tesseract" in tools:
            config.tesseract_path = tools["tesseract"]
        if "pdftotext" in tools:
            config.pdftotext_path = tools["pdftotext"]
        if "pdftoppm" in tools:
            config.pdftoppm_path = tools["pdftoppm"]
    
    # Apply vision categories
    if "vision_categories" in data:
        config.vision_categories = data["vision_categories"]
    
    return config


def save_config_template(path: str) -> None:
    """Save a template configuration file"""
    template = {
        "categories": {
            "custom_category": {
                "description": "My Custom Category",
                "folder": "custom",
                "keywords": ["keyword1", "keyword2", "keyword3"]
            }
        },
        "settings": {
            "ocr_timeout": 30,
            "max_text_length": 2000,
            "default_category": "unsorted",
            "min_confidence": 1,
            "verbose": False
        },
        "tools": {
            "tesseract": "/path/to/tesseract",
            "pdftotext": "/path/to/pdftotext",
            "pdftoppm": "/path/to/pdftoppm"
        }
    }
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2)
