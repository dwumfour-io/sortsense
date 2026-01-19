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
class FolderAnalysis:
    """Result of analyzing an entire folder as a cohesive unit"""
    
    folder_path: str
    folder_name: str
    file_count: int
    dominant_category: str
    confidence_score: float
    is_cohesive: bool  # True if all files belong together
    recommended_destination: str = ""
    analysis_type: str = ""  # 'app_bundle', 'cohesive_folder', 'mixed'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class FileAnalysis:
    """Result of analyzing a single file"""
    
    filepath: str
    filename: str
    extension: str
    file_size: int
    extraction_method: str  # 'ocr', 'text', 'pdf', 'docx', 'xlsx', 'filename', 'skip', 'error', 'vision'
    extracted_text: str
    category: str
    confidence_score: int
    keyword_matches: List[str] = field(default_factory=list)
    recommended_destination: str = ""
    error_message: str = ""
    vision_label: str = ""  # Raw vision detection (e.g., 'wedding', 'car') for interactive folder creation
    detected_subfolder: str = ""  # Detected subfolder name (e.g., 'chase', 'gtfs') from content or parent folder
    skip_individual: bool = False  # True if this file is part of a cohesive folder/app bundle
    
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
        
        # Folder path cache (discovered from destination)
        self._folder_path_cache: Dict[str, str] = {}
        
        # Progress callback
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        
        # Cohesive folder results (folders to move as units)
        self.folder_results: List[FolderAnalysis] = []
    
    def discover_existing_folders(self, max_depth: int = 3) -> Dict[str, str]:
        """
        Scan destination folder recursively to find existing category folders.
        
        This allows SortSense to find folders like:
          ~/Documents/personal/housing  → housing
          ~/Documents/personal/vehicles → vehicles
          
        Args:
            max_depth: Maximum folder depth to search
            
        Returns:
            Dict mapping folder names to their full paths
        """
        discovered = {}
        base = Path(self.destination)
        
        if not base.exists():
            return discovered
        
        # Get all category folder names from config
        category_folders = set()
        for cat_name, cat_config in self.config.categories.items():
            folder_name = cat_config.get("folder", cat_name)
            # Handle nested paths like "personal/housing" - extract the leaf name
            leaf_name = Path(folder_name).name
            category_folders.add(leaf_name.lower())
        
        # Walk the destination folder tree
        def walk_folders(path: Path, depth: int = 0):
            if depth > max_depth:
                return
            
            try:
                for item in path.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        folder_name_lower = item.name.lower()
                        
                        # Check if this folder matches any category
                        if folder_name_lower in category_folders:
                            # Store relative path from destination
                            rel_path = item.relative_to(base)
                            
                            # Prefer shallower paths (don't overwrite if already found)
                            if folder_name_lower not in discovered:
                                discovered[folder_name_lower] = str(rel_path)
                                logger.debug(f"Discovered folder: {item.name} at {rel_path}")
                        
                        # Continue searching subdirectories
                        walk_folders(item, depth + 1)
            except PermissionError:
                pass
        
        walk_folders(base)
        self._folder_path_cache = discovered
        
        if discovered:
            logger.info(f"Discovered {len(discovered)} existing category folders")
        
        return discovered
    
    def get_folder_path(self, category: str) -> str:
        """
        Get the folder path for a category, using discovered paths if available.
        
        Args:
            category: Category name
            
        Returns:
            Folder path (relative to destination)
        """
        cat_config = self.config.categories.get(category, {})
        folder_name = cat_config.get("folder", category)
        
        # Check if we discovered this folder in a nested location
        leaf_name = Path(folder_name).name.lower()
        if leaf_name in self._folder_path_cache:
            return self._folder_path_cache[leaf_name]
        
        return folder_name
    
    def detect_subfolder(self, filepath: str, text: str, category: str) -> str:
        """
        Detect a subfolder name from file content or parent folder.
        
        Strategy:
        1. Use parent folder name if it's not a common folder (Downloads, Desktop, etc.)
        2. For financial docs, try to detect bank/institution name
        3. For dev files, use project folder name
        
        Args:
            filepath: Path to the file
            text: Extracted text from the file
            category: The detected category
            
        Returns:
            Subfolder name or empty string if none detected
        """
        # Get parent folder name
        parent_folder = os.path.basename(os.path.dirname(filepath))
        
        # Common folders to ignore
        ignore_folders = {'downloads', 'desktop', 'documents', 'pictures', 'videos', 
                          'music', 'home', 'users', 'tmp', 'temp', '~'}
        
        # If parent folder is meaningful (not a common system folder), use it
        if parent_folder.lower() not in ignore_folders and not parent_folder.startswith('.'):
            # Clean up the folder name (lowercase, replace spaces with dashes)
            subfolder = parent_folder.lower().replace(' ', '-')
            return subfolder
        
        # For financial category, try to detect institution from content
        if category in ('sikasem', 'finance', 'financial'):
            text_lower = text.lower() if text else ''
            # Common financial institutions
            institutions = {
                'chase': ['chase bank', 'jpmorgan chase', 'chase.com'],
                'bank-of-america': ['bank of america', 'bofa', 'bankofamerica'],
                'wells-fargo': ['wells fargo', 'wellsfargo'],
                'capital-one': ['capital one', 'capitalone'],
                'navy-federal': ['navy federal', 'navyfcu'],
                'usaa': ['usaa'],
                'penfed': ['pentagon federal', 'penfed'],
                'discover': ['discover card', 'discover.com'],
                'amex': ['american express', 'amex'],
                'citi': ['citibank', 'citi.com'],
                'langley': ['langley federal', 'langleyfcu'],
                'digital-fcu': ['digital federal', 'dcu'],
            }
            for subfolder, patterns in institutions.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        return subfolder
        
        return ""
    
    def is_app_bundle(self, path: str) -> bool:
        """
        Check if a path is a macOS .app bundle.
        
        Args:
            path: Path to check
            
        Returns:
            True if it's an app bundle
        """
        return os.path.isdir(path) and path.endswith('.app')
    
    def analyze_folder_cohesion(self, folder_path: str) -> Optional[FolderAnalysis]:
        """
        Analyze if a folder's contents are cohesive (should move as a unit).
        
        A folder is cohesive if:
        - All files share the same primary category
        - OR it matches known cohesive folder patterns (GTFS, project folders, etc.)
        
        Args:
            folder_path: Path to the folder to analyze
            
        Returns:
            FolderAnalysis if folder is cohesive, None otherwise
        """
        folder_name = os.path.basename(folder_path)
        folder_name_lower = folder_name.lower()
        
        # Known cohesive folder patterns
        cohesive_patterns = {
            'gtfs': 'dev',
            'node_modules': None,  # Skip entirely
            '__pycache__': None,   # Skip entirely
            '.git': None,          # Skip entirely
            'venv': None,          # Skip entirely
            'env': None,           # Skip entirely
        }
        
        # Check known patterns first
        if folder_name_lower in cohesive_patterns:
            target_cat = cohesive_patterns[folder_name_lower]
            if target_cat is None:
                return None  # Skip this folder
            
            folder_path_obj = Path(folder_path)
            file_count = sum(1 for _ in folder_path_obj.rglob('*') if _.is_file())
            dest_folder = os.path.join(self.destination, self.get_folder_path(target_cat), folder_name_lower)
            
            return FolderAnalysis(
                folder_path=folder_path,
                folder_name=folder_name,
                file_count=file_count,
                dominant_category=target_cat,
                confidence_score=1.0,
                is_cohesive=True,
                recommended_destination=dest_folder,
                analysis_type='cohesive_folder'
            )
        
        # Sample a few files to determine cohesion
        sample_files = []
        try:
            for entry in os.scandir(folder_path):
                if entry.is_file() and not entry.name.startswith('.'):
                    sample_files.append(entry.path)
                    if len(sample_files) >= 5:  # Sample up to 5 files
                        break
        except PermissionError:
            return None
        
        if not sample_files:
            return None
        
        # Analyze sample files
        categories = {}
        for filepath in sample_files:
            result = self.analyze_file(filepath)
            cat = result.category
            categories[cat] = categories.get(cat, 0) + 1
        
        # Check if all files share the same category
        if len(categories) == 1:
            dominant_cat = list(categories.keys())[0]
            if dominant_cat not in ('uncategorized', 'unsorted'):
                folder_path_obj = Path(folder_path)
                file_count = sum(1 for _ in folder_path_obj.rglob('*') if _.is_file())
                dest_folder = os.path.join(
                    self.destination, 
                    self.get_folder_path(dominant_cat), 
                    folder_name_lower.replace(' ', '-')
                )
                
                return FolderAnalysis(
                    folder_path=folder_path,
                    folder_name=folder_name,
                    file_count=file_count,
                    dominant_category=dominant_cat,
                    confidence_score=1.0,
                    is_cohesive=True,
                    recommended_destination=dest_folder,
                    analysis_type='cohesive_folder'
                )
        
        # Check if majority (80%+) share same category
        total_sampled = sum(categories.values())
        for cat, count in categories.items():
            if cat not in ('uncategorized', 'unsorted') and count / total_sampled >= 0.8:
                folder_path_obj = Path(folder_path)
                file_count = sum(1 for _ in folder_path_obj.rglob('*') if _.is_file())
                dest_folder = os.path.join(
                    self.destination, 
                    self.get_folder_path(cat), 
                    folder_name_lower.replace(' ', '-')
                )
                
                return FolderAnalysis(
                    folder_path=folder_path,
                    folder_name=folder_name,
                    file_count=file_count,
                    dominant_category=cat,
                    confidence_score=count / total_sampled,
                    is_cohesive=True,
                    recommended_destination=dest_folder,
                    analysis_type='cohesive_folder'
                )
        
        return None  # Not cohesive, process files individually
    
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
        vision_label = ""  # Raw detection label (e.g., 'wedding photo' -> 'wedding')
        
        if self.use_vision and category in ('uncategorized', 'unsorted'):
            # Check if it's an image file
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic'}
            if ext.lower() in image_extensions:
                try:
                    vision_category, vision_score, vision_matches = self.extractor.extract_with_vision(filepath)
                    if vision_category and vision_score > 0.3:  # Confidence threshold
                        # Extract raw label from matches (e.g., 'a wedding photo' -> 'wedding')
                        if vision_matches:
                            raw_match = vision_matches[0].split('(')[0].strip()
                            # Clean up the label: remove 'a ', 'photo', etc.
                            for prefix in ['a ', 'an ']:
                                if raw_match.lower().startswith(prefix):
                                    raw_match = raw_match[len(prefix):]
                            for suffix in [' photo', ' photograph', ' picture', ' image']:
                                if raw_match.lower().endswith(suffix):
                                    raw_match = raw_match[:-len(suffix)]
                            vision_label = raw_match.strip().lower()
                        
                        category = vision_category
                        score = vision_score
                        matches = vision_matches
                        method = 'vision'
                except Exception as e:
                    error_msg = f"Vision analysis failed: {str(e)}"
        
        # Build result
        # Use discovered folder path if available
        folder_path = self.get_folder_path(category)
        dest_folder = os.path.join(self.destination, folder_path)
        
        # Detect subfolder from content or parent folder
        detected_subfolder = self.detect_subfolder(filepath, text, category)
        
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
            recommended_destination=dest_folder,
            error_message=error_msg,
            vision_label=vision_label,
            detected_subfolder=detected_subfolder
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
        
        Smart behaviors:
        - .app bundles are detected and moved as units to downloaded-apps/
        - Cohesive folders (like GTFS) are moved as units
        - Statement files are analyzed individually for proper categorization
        
        Args:
            folder_path: Path to folder to analyze
            recursive: Whether to analyze recursively
            max_files: Maximum number of files to analyze
            show_progress: Whether to show progress bar (requires tqdm)
            
        Returns:
            List of FileAnalysis results
        """
        self.results = []
        self.folder_results = []
        files_to_process = []
        skip_paths = set()  # Paths to skip (inside app bundles or cohesive folders)
        
        # First pass: detect app bundles and cohesive folders
        try:
            for entry in os.scandir(folder_path):
                # Check for .app bundles
                if entry.is_dir() and entry.name.endswith('.app'):
                    app_name = entry.name
                    file_count = sum(1 for _ in Path(entry.path).rglob('*') if _.is_file())
                    dest_folder = os.path.join(self.destination, 'downloaded-apps')
                    
                    folder_analysis = FolderAnalysis(
                        folder_path=entry.path,
                        folder_name=app_name,
                        file_count=file_count,
                        dominant_category='downloaded-apps',
                        confidence_score=1.0,
                        is_cohesive=True,
                        recommended_destination=dest_folder,
                        analysis_type='app_bundle'
                    )
                    self.folder_results.append(folder_analysis)
                    skip_paths.add(entry.path)
                    logger.info(f"Detected app bundle: {app_name}")
                
                # Check for cohesive folders (but not statements - those need individual analysis)
                elif entry.is_dir() and not entry.name.startswith('.'):
                    folder_name_lower = entry.name.lower()
                    
                    # Folders that should be analyzed individually (financial/statements)
                    individual_analysis_folders = {'statements', 'bank', 'bills', 'invoices', 'receipts'}
                    
                    if folder_name_lower not in individual_analysis_folders:
                        cohesion = self.analyze_folder_cohesion(entry.path)
                        if cohesion and cohesion.is_cohesive:
                            self.folder_results.append(cohesion)
                            skip_paths.add(entry.path)
                            logger.info(f"Detected cohesive folder: {entry.name} -> {cohesion.dominant_category}")
        except PermissionError:
            pass
        
        # Collect files (excluding those in app bundles and cohesive folders)
        if recursive:
            for root, dirs, files in os.walk(folder_path):
                # Skip paths we've marked as cohesive
                if any(root.startswith(skip_path) for skip_path in skip_paths):
                    continue
                
                # Skip hidden directories
                if self.config.settings.skip_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # Skip app bundles and cohesive folders when walking
                dirs[:] = [d for d in dirs if os.path.join(root, d) not in skip_paths]
                
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
        
        Handles:
        - App bundles (.app) → downloaded-apps/
        - Cohesive folders (GTFS, etc.) → moved as units
        - Individual files → organized by category
        
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
        folders_moved = 0
        
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
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: Move cohesive folders and app bundles
        # ═══════════════════════════════════════════════════════════════════
        
        for folder_result in self.folder_results:
            dest_folder = folder_result.recommended_destination
            dest_path = os.path.join(dest_folder, folder_result.folder_name)
            category = folder_result.dominant_category
            
            # Interactive mode: prompt for new folders
            folder_name = os.path.basename(dest_folder).lower()
            if interactive and not dry_run and folder_name not in existing_folders:
                if folder_name not in folder_decisions:
                    analysis_type = folder_result.analysis_type
                    emoji = "📦" if analysis_type == 'app_bundle' else "📁"
                    print(f"\n  {emoji} {folder_result.folder_name}")
                    print(f"     Type: {analysis_type.replace('_', ' ').title()}")
                    print(f"     Files: {folder_result.file_count}")
                    print(f"     Destination: {dest_folder}")
                    response = input(f"     Create '{folder_name}/' and move? [y/N]: ").strip().lower()
                    folder_decisions[folder_name] = response in ('y', 'yes')
                    
                    if folder_decisions[folder_name]:
                        existing_folders.add(folder_name)
                
                if not folder_decisions.get(folder_name, False):
                    skipped += 1
                    continue
            
            if category not in move_counts:
                move_counts[category] = 0
            
            if dry_run:
                emoji = "📦" if folder_result.analysis_type == 'app_bundle' else "📁"
                print(f"  [DRY RUN] {emoji} {folder_result.folder_name}/ ({folder_result.file_count} files)")
                print(f"            → {dest_folder}/")
                move_counts[category] += 1
                folders_moved += 1
            else:
                try:
                    # Create destination folder
                    os.makedirs(dest_folder, exist_ok=True)
                    
                    # Handle existing destination
                    if os.path.exists(dest_path):
                        counter = 1
                        base_name = folder_result.folder_name
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(dest_folder, f"{base_name}_{counter}")
                            counter += 1
                    
                    # Move entire folder
                    shutil.move(folder_result.folder_path, dest_path)
                    
                    # Log transaction
                    self.transaction_log.log_move(
                        source=folder_result.folder_path,
                        destination=dest_path,
                        category=category,
                        session_id=self.session_id
                    )
                    
                    emoji = "📦" if folder_result.analysis_type == 'app_bundle' else "📁"
                    print(f"  ✓ {emoji} {folder_result.folder_name}/ → {category}/")
                    move_counts[category] += 1
                    folders_moved += 1
                    
                except Exception as e:
                    print(f"  ✗ Error moving folder {folder_result.folder_name}: {e}")
                    logger.error(f"Folder move error: {folder_result.folder_path} -> {dest_path}: {e}")
                    errors += 1
        
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2: Move individual files
        # ═══════════════════════════════════════════════════════════════════

        
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
            
            # Track subfolder for display and creation
            parent_category_folder = dest_folder
            is_subfolder = False
            prompt_folder = None
            
            # Check if we detected a subfolder (e.g., 'gtfs', 'new-folder-with-items')
            if result.detected_subfolder:
                subfolder_path = os.path.join(dest_folder, result.detected_subfolder)
                subfolder_exists = os.path.exists(subfolder_path)
                
                if subfolder_exists:
                    # Subfolder exists, use it
                    dest_folder = subfolder_path
                else:
                    # Subfolder doesn't exist - will prompt in interactive mode
                    is_subfolder = True
                    prompt_folder = result.detected_subfolder
                    # For dry run, show the target subfolder
                    if dry_run:
                        dest_folder = subfolder_path
            
            # Interactive mode: prompt for new folders
            if interactive and not dry_run:
                # Also check if vision detected a specific type (and no subfolder detected)
                if not prompt_folder and result.vision_label and result.vision_label != folder_name:
                    # Check if vision label folder exists
                    vision_folder_exists = result.vision_label in existing_folders or result.vision_label in self._folder_path_cache
                    if not vision_folder_exists:
                        prompt_folder = result.vision_label
                        dest_folder = os.path.join(self.destination, 'personal', result.vision_label)
                elif not prompt_folder and not folder_exists:
                    prompt_folder = folder_name
                
                if prompt_folder and prompt_folder not in folder_decisions:
                    # Ask user
                    if is_subfolder:
                        print(f"\\n  📁 Subfolder '{prompt_folder}/' doesn't exist in {os.path.basename(parent_category_folder)}/")
                    else:
                        print(f"\\n  📁 Folder '{prompt_folder}/' doesn't exist.")
                    print(f"     File: {result.filename}")
                    if result.detected_subfolder:
                        print(f"     Detected from: parent folder")
                    elif result.vision_label:
                        print(f"     Detected: {result.vision_label}")
                    print(f"     Confidence: {confidence_normalized*100:.1f}%")
                    response = input(f"     Create '{prompt_folder}/'? [y/N]: ").strip().lower()
                    folder_decisions[prompt_folder] = response in ('y', 'yes')
                    
                    if folder_decisions[prompt_folder]:
                        existing_folders.add(prompt_folder)  # Add to existing set
                        # Update destination
                        if is_subfolder:
                            dest_folder = os.path.join(parent_category_folder, result.detected_subfolder)
                        elif result.vision_label and prompt_folder == result.vision_label:
                            dest_folder = os.path.join(self.destination, 'personal', result.vision_label)
                
                if prompt_folder and not folder_decisions.get(prompt_folder, False):
                    # User said NO - move to category-misc subfolder
                    category_name = os.path.basename(parent_category_folder if is_subfolder else dest_folder)
                    misc_subfolder = os.path.join(parent_category_folder if is_subfolder else dest_folder, f"{category_name}-misc")
                    category = f'{category_name}-misc'
                    dest_folder = misc_subfolder
            
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
            folder_msg = f" ({folders_moved} folders)" if folders_moved else ""
            print(f"\n  Would move {total_moved} items{folder_msg}, skip {skipped}")
        else:
            folder_msg = f" ({folders_moved} folders)" if folders_moved else ""
            print(f"\n  ✅ Moved {total_moved} items{folder_msg}, skipped {skipped}, errors {errors}")
        
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
