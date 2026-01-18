"""
SortSense Main Engine

The core SortSense class that orchestrates file analysis,
categorization, and organization.
"""

import json
import logging
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sortsense.categorizer import Categorizer
from sortsense.config import Config, load_config
from sortsense.extractor import TextExtractor
from sortsense.utils import TransactionLog, generate_session_id

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FileAnalysis:
    """Result of analyzing a single file"""
    
    filepath: str
    filename: str
    extension: str
    file_size: int
    extraction_method: str  # 'ocr', 'text', 'pdf', 'docx', 'xlsx', 'filename', 'skip', 'error'
    extracted_text: str
    category: str
    confidence_score: int
    keyword_matches: List[str] = field(default_factory=list)
    recommended_destination: str = ""
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def __str__(self) -> str:
        return f"{self.filename} → {self.category} (confidence: {self.confidence_score})"


@dataclass
class AnalysisReport:
    """Complete analysis report for a folder"""
    
    timestamp: str
    source_folder: str
    destination_base: str
    total_files: int
    files_by_category: Dict[str, List[str]]
    summary: Dict[str, int]
    analysis_results: List[FileAnalysis] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON export"""
        return {
            "timestamp": self.timestamp,
            "source_folder": self.source_folder,
            "destination_base": self.destination_base,
            "total_files": self.total_files,
            "files_by_category": self.files_by_category,
            "summary": self.summary,
            "results": [r.to_dict() for r in self.analysis_results]
        }
    
    def save(self, filepath: str) -> None:
        """Save report to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════

class SortSense:
    """
    Main SortSense engine for file analysis and organization.
    
    Example usage:
        ss = SortSense(destination="/path/to/organized")
        results = ss.analyze_folder("/path/to/messy/folder")
        ss.print_summary()
        ss.execute_moves(dry_run=False)
    """
    
    def __init__(
        self,
        destination: Optional[str] = None,
        config: Optional[Config] = None,
        config_path: Optional[str] = None,
        use_vision: bool = False
    ):
        """
        Initialize SortSense.
        
        Args:
            destination: Base destination folder for organized files
            config: Pre-loaded Config object
            config_path: Path to config file to load
            use_vision: Whether to use computer vision for image analysis
        """
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = load_config(config_path)
        
        # Set destination
        self.destination = destination or os.getcwd()
        
        # Vision mode
        self.use_vision = use_vision
        
        # Initialize components
        self.extractor = TextExtractor(self.config, use_vision=use_vision)
        self.categorizer = Categorizer(self.config)
        self.transaction_log = TransactionLog()
        
        # Session tracking
        self.session_id = generate_session_id()
        self.results: List[FileAnalysis] = []
        
        # Progress callback
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """
        Set a callback for progress updates.
        
        Args:
            callback: Function(current, total, filename) called on each file
        """
        self._progress_callback = callback
    
    def analyze_file(self, filepath: str) -> FileAnalysis:
        """
        Analyze a single file and return categorization result.
        
        Args:
            filepath: Path to the file to analyze
            
        Returns:
            FileAnalysis object with categorization results
        """
        filename = os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()
        
        # Get file size
        try:
            file_size = os.path.getsize(filepath)
        except OSError:
            file_size = 0
        
        # Extract text
        method, text = self.extractor.extract(filepath)
        
        # Handle extraction errors
        error_msg = ""
        if method == 'error':
            error_msg = text
            text = ""
        
        # Categorize based on text/keywords
        category, score, matches = self.categorizer.categorize(text, filename)
        
        # If no category found and vision is enabled, try computer vision
        vision_category = ""
        vision_score = 0.0
        vision_matches = []
        
        if self.use_vision and category in ('uncategorized', 'unsorted'):
            # Check if it's an image file
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
            if ext.lower() in image_extensions:
                try:
                    vision_category, vision_score, vision_matches = self.extractor.extract_with_vision(filepath)
                    if vision_category and vision_score > 0.3:  # Confidence threshold
                        category = vision_category
                        score = vision_score
                        matches = vision_matches
                        method = 'vision'
                except Exception as e:
                    error_msg = f"Vision analysis failed: {str(e)}"
        
        # Build result
        result = FileAnalysis(
            filepath=filepath,
            filename=filename,
            extension=ext,
            file_size=file_size,
            extraction_method=method,
            extracted_text=text[:500] if text else '',
            category=category,
            confidence_score=score,
            keyword_matches=matches,
            recommended_destination=self.categorizer.get_destination_folder(
                category, self.destination
            ),
            error_message=error_msg
        )
        
        return result
    
    def analyze_folder(
        self,
        folder_path: str,
        recursive: bool = False,
        max_files: Optional[int] = None,
        show_progress: bool = False
    ) -> List[FileAnalysis]:
        """
        Analyze all files in a folder.
        
        Args:
            folder_path: Path to folder to analyze
            recursive: Whether to analyze recursively
            max_files: Maximum number of files to analyze
            show_progress: Whether to show progress bar (requires tqdm)
            
        Returns:
            List of FileAnalysis results
        """
        self.results = []
        files_to_process = []
        
        # Collect files
        if recursive:
            for root, dirs, files in os.walk(folder_path):
                # Skip hidden directories
                if self.config.settings.skip_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in files:
                    if self.config.settings.skip_hidden and filename.startswith('.'):
                        continue
                    files_to_process.append(os.path.join(root, filename))
        else:
            for entry in os.scandir(folder_path):
                if entry.is_file():
                    if self.config.settings.skip_hidden and entry.name.startswith('.'):
                        continue
                    files_to_process.append(entry.path)
        
        # Apply max limit
        if max_files:
            files_to_process = files_to_process[:max_files]
        
        total = len(files_to_process)
        
        # Process with progress bar if requested
        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(files_to_process, desc="Analyzing", unit="file")
            except ImportError:
                logger.warning("tqdm not installed, progress bar disabled")
                iterator = files_to_process
        else:
            iterator = files_to_process
        
        # Analyze each file
        for i, filepath in enumerate(iterator):
            result = self.analyze_file(filepath)
            self.results.append(result)
            
            # Call progress callback if set
            if self._progress_callback:
                self._progress_callback(i + 1, total, result.filename)
        
        return self.results
    
    def generate_report(self, source_folder: str) -> AnalysisReport:
        """
        Generate a comprehensive report from analysis results.
        
        Args:
            source_folder: The folder that was analyzed
            
        Returns:
            AnalysisReport object
        """
        files_by_category: Dict[str, List[str]] = {}
        summary: Dict[str, int] = {}
        
        for result in self.results:
            cat = result.category
            
            if cat not in files_by_category:
                files_by_category[cat] = []
                summary[cat] = 0
            
            files_by_category[cat].append(result.filename)
            summary[cat] += 1
        
        return AnalysisReport(
            timestamp=datetime.now().isoformat(),
            source_folder=source_folder,
            destination_base=self.destination,
            total_files=len(self.results),
            files_by_category=files_by_category,
            summary=summary,
            analysis_results=self.results
        )
    
    def execute_moves(
        self,
        dry_run: bool = True,
        min_confidence: int = 0,
        misc_threshold: float = 0.0,
        existing_only: bool = False,
        interactive: bool = False
    ) -> Dict[str, int]:
        """
        Execute file moves based on analysis results.
        
        Args:
            dry_run: If True, only show what would happen
            min_confidence: Minimum confidence score to move file
            misc_threshold: Move files below this confidence to misc/ (0.0-1.0)
            existing_only: Only use folders that already exist in destination
            interactive: Prompt user before creating new folders
            
        Returns:
            Dictionary of category -> count of files moved
        """
        move_counts: Dict[str, int] = {}
        skipped = 0
        errors = 0
        
        default_cat = self.config.settings.default_category
        
        # Get existing folders
        existing_folders = set()
        for entry in os.scandir(self.destination):
            if entry.is_dir() and not entry.name.startswith('.'):
                existing_folders.add(entry.name.lower())
        
        # Track user's folder decisions in interactive mode
        folder_decisions: Dict[str, bool] = {}  # folder_name -> True/False
        
        # Default misc folder location
        misc_folder = os.path.join(self.destination, 'personal', 'misc')
        
        for result in self.results:
            category = result.category
            confidence = result.confidence_score
            
            # Normalize confidence to 0-1 range if it's an integer
            if isinstance(confidence, int) and confidence > 1:
                confidence_normalized = confidence / 5.0  # Scale 0-5 to 0-1
            else:
                confidence_normalized = float(confidence)
            
            # Handle low confidence files - move to misc if threshold set
            if misc_threshold > 0 and confidence_normalized < misc_threshold:
                if category != default_cat:  # Only if it had some match
                    category = 'misc'
                    dest_folder = misc_folder
                else:
                    # No match at all, move to misc
                    category = 'misc'
                    dest_folder = misc_folder
            elif category == default_cat:
                # Skip files in default category (no good match) if no misc threshold
                skipped += 1
                continue
            else:
                dest_folder = result.recommended_destination
            
            folder_name = os.path.basename(dest_folder).lower()
            
            # Check if folder exists
            folder_exists = folder_name in existing_folders
            
            # Interactive mode: prompt for new folders
            if interactive and not folder_exists and not dry_run:
                if folder_name not in folder_decisions:
                    # Ask user
                    print(f"\n  📁 Folder '{folder_name}/' doesn't exist.")
                    print(f"     File: {result.filename}")
                    print(f"     Confidence: {confidence_normalized*100:.1f}%")
                    response = input(f"     Create '{folder_name}/'? [y/N]: ").strip().lower()
                    folder_decisions[folder_name] = response in ('y', 'yes')
                    
                    if folder_decisions[folder_name]:
                        existing_folders.add(folder_name)  # Add to existing set
                
                if not folder_decisions.get(folder_name, False):
                    # User said NO - move to personal/misc
                    category = 'misc'
                    dest_folder = misc_folder
            
            # Check existing_only mode (non-interactive)
            elif existing_only and not folder_exists:
                skipped += 1
                continue
            
            dest_path = os.path.join(dest_folder, result.filename)
            
            if category not in move_counts:
                move_counts[category] = 0
            
            if dry_run:
                print(f"  [DRY RUN] {result.filename}")
                print(f"            → {dest_folder}")
                move_counts[category] += 1
            else:
                try:
                    # Create destination folder (unless existing_only mode)
                    if not existing_only:
                        os.makedirs(dest_folder, exist_ok=True)
                    
                    # Handle existing files
                    if os.path.exists(dest_path):
                        base, ext = os.path.splitext(result.filename)
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
                            counter += 1
                    
                    # Move file
                    shutil.move(result.filepath, dest_path)
                    
                    # Log transaction
                    self.transaction_log.log_move(
                        source=result.filepath,
                        destination=dest_path,
                        category=category,
                        session_id=self.session_id
                    )
                    
                    print(f"  ✓ {result.filename} → {category}/")
                    move_counts[category] += 1
                    
                except Exception as e:
                    print(f"  ✗ Error moving {result.filename}: {e}")
                    logger.error(f"Move error: {result.filepath} -> {dest_path}: {e}")
                    errors += 1
        
        # Print summary
        total_moved = sum(move_counts.values())
        if dry_run:
            print(f"\n  Would move {total_moved} files, skip {skipped}")
        else:
            print(f"\n  ✅ Moved {total_moved} files, skipped {skipped}, errors {errors}")
        
        return move_counts
    
    def undo_last_session(self) -> int:
        """
        Undo the last organize session.
        
        Returns:
            Number of files restored
        """
        last_session = self.transaction_log.get_last_session()
        if not last_session:
            print("No sessions to undo")
            return 0
        
        moves = self.transaction_log.get_session_moves(last_session)
        restored = 0
        
        for move in moves:
            source = move['source']
            dest = move['destination']
            
            if os.path.exists(dest):
                try:
                    # Recreate source directory if needed
                    os.makedirs(os.path.dirname(source), exist_ok=True)
                    shutil.move(dest, source)
                    print(f"  ↩ Restored: {os.path.basename(source)}")
                    restored += 1
                except Exception as e:
                    print(f"  ✗ Error restoring {os.path.basename(dest)}: {e}")
            else:
                print(f"  ⚠ Not found: {os.path.basename(dest)}")
        
        # Mark session as undone
        self.transaction_log.mark_undone(last_session)
        
        print(f"\n  ↩ Restored {restored} files from session {last_session}")
        return restored
    
    def print_summary(self) -> None:
        """Print a formatted summary of analysis results"""
        print("\n" + "=" * 70)
        print("                    SORTSENSE ANALYSIS SUMMARY")
        print("=" * 70)
        
        # Group by category
        by_category: Dict[str, List[FileAnalysis]] = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)
        
        # Sort categories by count
        sorted_categories = sorted(
            by_category.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        # Print each category
        for category, files in sorted_categories:
            cat_info = self.categorizer.get_category_info(category)
            desc = cat_info.get('description', category.title())
            
            print(f"\n📁 {category.upper()} ({desc}): {len(files)} files")
            print("-" * 50)
            
            for f in files[:10]:  # Show first 10
                # Handle both int and float confidence scores
                score_int = int(f.confidence_score) if isinstance(f.confidence_score, float) else f.confidence_score
                if isinstance(f.confidence_score, float) and f.confidence_score <= 1.0:
                    score_int = int(f.confidence_score * 5)  # Scale 0-1 to 0-5
                score_bar = "●" * min(score_int, 5) + "○" * (5 - min(score_int, 5))
                print(f"  [{score_bar}] {f.filename[:45]}")
                if f.keyword_matches:
                    print(f"           Matched: {', '.join(f.keyword_matches[:3])}")
            
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more")
        
        print("\n" + "=" * 70)
        print(f"  Total files analyzed: {len(self.results)}")
        print(f"  Categories found: {len(by_category)}")
        print("=" * 70 + "\n")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        by_category = {}
        by_method = {}
        total_size = 0
        
        for r in self.results:
            # By category
            by_category[r.category] = by_category.get(r.category, 0) + 1
            
            # By extraction method
            by_method[r.extraction_method] = by_method.get(r.extraction_method, 0) + 1
            
            # Total size
            total_size += r.file_size
        
        return {
            "total_files": len(self.results),
            "total_size_bytes": total_size,
            "by_category": by_category,
            "by_extraction_method": by_method,
            "session_id": self.session_id
        }
