"""
SortSense Utility Functions

Common utilities for file handling, logging, and display.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════

def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    verbose: bool = False
) -> None:
    """
    Configure logging for SortSense.
    
    Args:
        level: Logging level
        log_file: Optional file to write logs to
        verbose: If True, use DEBUG level
    """
    if verbose:
        level = logging.DEBUG
    
    handlers: List[logging.Handler] = [
        logging.StreamHandler()
    ]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


# ═══════════════════════════════════════════════════════════════════════════
# TRANSACTION LOGGING (for undo support)
# ═══════════════════════════════════════════════════════════════════════════

class TransactionLog:
    """Logs file moves for potential undo operations"""
    
    def __init__(self, log_path: str = "sortsense-transactions.json"):
        self.log_path = log_path
        self.transactions: List[Dict[str, Any]] = []
        self._load()
    
    def _load(self) -> None:
        """Load existing transaction log"""
        if os.path.exists(self.log_path):
            try:
                with open(self.log_path, 'r') as f:
                    data = json.load(f)
                    self.transactions = data.get('transactions', [])
            except (json.JSONDecodeError, IOError):
                self.transactions = []
    
    def _save(self) -> None:
        """Save transaction log to file"""
        try:
            with open(self.log_path, 'w') as f:
                json.dump({
                    'last_updated': datetime.now().isoformat(),
                    'transactions': self.transactions
                }, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save transaction log: {e}")
    
    def log_move(
        self,
        source: str,
        destination: str,
        category: str,
        session_id: str
    ) -> None:
        """
        Log a file move operation.
        
        Args:
            source: Original file path
            destination: New file path
            category: Category the file was moved to
            session_id: Unique session identifier
        """
        self.transactions.append({
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'source': source,
            'destination': destination,
            'category': category,
            'undone': False
        })
        self._save()
    
    def get_session_moves(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all moves from a specific session"""
        return [t for t in self.transactions 
                if t.get('session_id') == session_id and not t.get('undone')]
    
    def get_last_session(self) -> Optional[str]:
        """Get the most recent session ID"""
        for t in reversed(self.transactions):
            if not t.get('undone'):
                return t.get('session_id')
        return None
    
    def mark_undone(self, session_id: str) -> int:
        """
        Mark all moves in a session as undone.
        
        Returns:
            Number of moves marked
        """
        count = 0
        for t in self.transactions:
            if t.get('session_id') == session_id and not t.get('undone'):
                t['undone'] = True
                count += 1
        self._save()
        return count
    
    def clear_old(self, days: int = 30) -> int:
        """
        Remove transactions older than specified days.
        
        Returns:
            Number of transactions removed
        """
        cutoff = datetime.now().timestamp() - (days * 86400)
        original_count = len(self.transactions)
        
        self.transactions = [
            t for t in self.transactions
            if datetime.fromisoformat(t['timestamp']).timestamp() > cutoff
        ]
        
        removed = original_count - len(self.transactions)
        if removed:
            self._save()
        
        return removed


# ═══════════════════════════════════════════════════════════════════════════
# FILE UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def get_file_size_human(size_bytes: int) -> str:
    """Convert bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def count_files(folder: str, recursive: bool = True) -> int:
    """Count files in a folder"""
    if recursive:
        return sum(1 for _ in Path(folder).rglob('*') if _.is_file())
    return sum(1 for _ in Path(folder).iterdir() if _.is_file())


def is_hidden(path: str) -> bool:
    """Check if a file or folder is hidden"""
    name = os.path.basename(path)
    return name.startswith('.')


def generate_session_id() -> str:
    """Generate a unique session ID"""
    import uuid
    return f"ss-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


# ═══════════════════════════════════════════════════════════════════════════
# DISPLAY UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def print_banner() -> None:
    """Print SortSense banner"""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                              SORTSENSE v1.0                               ║
║              Smart File Categorization & Reorganization                   ║
╚═══════════════════════════════════════════════════════════════════════════╝
""")


def print_tools_status(tools: Dict[str, str]) -> None:
    """Print status of detected tools"""
    print("\n🔧 Tool Detection:")
    for tool, path in tools.items():
        status = "✓" if path != "NOT FOUND" else "✗"
        display = path if path != "NOT FOUND" else "Not found"
        print(f"   {status} {tool}: {display}")


def format_category_table(categories: Dict[str, Any]) -> str:
    """Format categories as a display table"""
    lines = []
    lines.append("\n📚 CATEGORIES")
    lines.append("=" * 60)
    
    for name, config in categories.items():
        desc = config.get('description', name)
        folder = config.get('folder', name)
        keywords = config.get('keywords', [])
        
        lines.append(f"\n{name.upper()}")
        lines.append(f"  Description: {desc}")
        lines.append(f"  Folder: {folder}")
        lines.append(f"  Keywords: {', '.join(keywords[:5])}...")
    
    return '\n'.join(lines)
