"""
SortSense Command-Line Interface

Provides the `sortsense` command with subcommands for
analyzing, organizing, and managing file categorization.
"""

import argparse
import logging
import os
import sys
from typing import Optional

from sortsense import __version__
from sortsense.config import Config, load_config, save_config_template
from sortsense.engine import SortSense
from sortsense.utils import format_category_table, print_banner, print_tools_status, setup_logging

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser"""
    parser = argparse.ArgumentParser(
        prog="sortsense",
        description="SortSense - Smart File Categorization & Reorganization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a folder
  sortsense analyze ~/Documents/unsorted
  
  # Analyze recursively with progress bar
  sortsense analyze ~/Documents -r --progress
  
  # Preview what would be organized (dry run)
  sortsense organize ~/Downloads --dry-run
  
  # Actually organize files
  sortsense organize ~/Downloads --execute -d ~/Documents
  
  # Export analysis report
  sortsense analyze ~/Downloads -o report.json
  
  # Undo last organization
  sortsense undo
  
  # Show available categories
  sortsense categories
  
  # Generate config template
  sortsense init
        """
    )
    
    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'SortSense {__version__}'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # ═══════════════════════════════════════════════════════════════════════
    # ANALYZE command
    # ═══════════════════════════════════════════════════════════════════════
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze files and show categorization without moving'
    )
    analyze_parser.add_argument(
        'folder',
        help='Folder to analyze'
    )
    analyze_parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Analyze folders recursively'
    )
    analyze_parser.add_argument(
        '--max',
        type=int,
        metavar='N',
        help='Maximum number of files to analyze'
    )
    analyze_parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Export JSON report to file'
    )
    analyze_parser.add_argument(
        '-d', '--destination',
        metavar='PATH',
        help='Base destination folder (for recommendations)',
        default=os.getcwd()
    )
    analyze_parser.add_argument(
        '-c', '--config',
        metavar='FILE',
        help='Path to config file'
    )
    analyze_parser.add_argument(
        '--progress',
        action='store_true',
        help='Show progress bar'
    )
    analyze_parser.add_argument(
        '--vision',
        action='store_true',
        help='Use computer vision (CLIP) to analyze image content'
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # ORGANIZE command
    # ═══════════════════════════════════════════════════════════════════════
    organize_parser = subparsers.add_parser(
        'organize',
        help='Analyze and move files to categories'
    )
    organize_parser.add_argument(
        'folder',
        help='Folder to organize'
    )
    organize_parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Organize folders recursively'
    )
    organize_parser.add_argument(
        '--max',
        type=int,
        metavar='N',
        help='Maximum number of files to process'
    )
    organize_parser.add_argument(
        '-d', '--destination',
        metavar='PATH',
        help='Base destination folder',
        default=os.getcwd()
    )
    organize_parser.add_argument(
        '-c', '--config',
        metavar='FILE',
        help='Path to config file'
    )
    organize_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would happen without moving files'
    )
    organize_parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually move files'
    )
    organize_parser.add_argument(
        '--min-confidence',
        type=int,
        default=1,
        metavar='N',
        help='Minimum confidence score to move (default: 1)'
    )
    organize_parser.add_argument(
        '--progress',
        action='store_true',
        help='Show progress bar'
    )
    organize_parser.add_argument(
        '--vision',
        action='store_true',
        help='Use computer vision (CLIP) to analyze image content'
    )
    organize_parser.add_argument(
        '--misc-threshold',
        type=float,
        default=0.0,
        metavar='PCT',
        help='Move files below this confidence (0.0-1.0) to misc/ folder (e.g., 0.35 for 35%%)'
    )
    organize_parser.add_argument(
        '--existing-only',
        action='store_true',
        help='Only use folders that already exist in destination (don\'t create new category folders)'
    )
    organize_parser.add_argument(
        '--discover-folders',
        action='store_true',
        help='Scan destination recursively to find existing category folders (e.g., personal/vehicles)'
    )
    organize_parser.add_argument(
        '--interactive',
        '-i',
        action='store_true',
        help='Interactive mode: prompt before creating new folders (NO = move to personal/misc/)'
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # CATEGORIES command
    # ═══════════════════════════════════════════════════════════════════════
    cats_parser = subparsers.add_parser(
        'categories',
        help='List available categories'
    )
    cats_parser.add_argument(
        '-c', '--config',
        metavar='FILE',
        help='Path to config file'
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # UNDO command
    # ═══════════════════════════════════════════════════════════════════════
    undo_parser = subparsers.add_parser(
        'undo',
        help='Undo the last organize operation'
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # INIT command
    # ═══════════════════════════════════════════════════════════════════════
    init_parser = subparsers.add_parser(
        'init',
        help='Generate a config file template'
    )
    init_parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        default='sortsense.json',
        help='Output file (default: sortsense.json)'
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STATUS command
    # ═══════════════════════════════════════════════════════════════════════
    status_parser = subparsers.add_parser(
        'status',
        help='Show tool detection status'
    )
    
    return parser


def cmd_analyze(args: argparse.Namespace) -> int:
    """Handle analyze command"""
    # Validate folder
    if not os.path.isdir(args.folder):
        print(f"Error: Not a directory: {args.folder}")
        return 1
    
    folder = os.path.abspath(args.folder)
    
    # Load config
    config = load_config(getattr(args, 'config', None))
    
    # Check for vision mode
    use_vision = getattr(args, 'vision', False)
    if use_vision:
        print("🔮 Vision mode enabled - loading CLIP model...")
    
    # Initialize engine
    ss = SortSense(
        destination=args.destination,
        config=config,
        use_vision=use_vision
    )
    
    print(f"\n📂 Analyzing: {folder}")
    print(f"📍 Destination: {args.destination}")
    
    # Run analysis
    results = ss.analyze_folder(
        folder,
        recursive=args.recursive,
        max_files=getattr(args, 'max', None),
        show_progress=args.progress
    )
    
    # Print summary
    ss.print_summary()
    
    # Export report if requested
    if args.output:
        report = ss.generate_report(folder)
        report.save(args.output)
        print(f"📄 Report saved to: {args.output}")
    
    return 0


def cmd_organize(args: argparse.Namespace) -> int:
    """Handle organize command"""
    # Validate folder
    if not os.path.isdir(args.folder):
        print(f"Error: Not a directory: {args.folder}")
        return 1
    
    folder = os.path.abspath(args.folder)
    
    # Check for --dry-run or --execute
    if not args.dry_run and not args.execute:
        print("Error: Please specify --dry-run or --execute")
        print("  Use --dry-run to preview changes")
        print("  Use --execute to actually move files")
        return 1
    
    # Load config
    config = load_config(getattr(args, 'config', None))
    
    # Check for vision mode
    use_vision = getattr(args, 'vision', False)
    if use_vision:
        print("🔮 Vision mode enabled - loading CLIP model...")
    
    # Initialize engine
    ss = SortSense(
        destination=args.destination,
        config=config,
        use_vision=use_vision
    )
    
    # Discover existing folders if requested
    discover_folders = getattr(args, 'discover_folders', False)
    if discover_folders:
        print("🔍 Scanning destination for existing folders...")
        discovered = ss.discover_existing_folders()
        if discovered:
            print(f"   Found {len(discovered)} category folders:")
            for name, path in discovered.items():
                print(f"   • {name} → {path}")
    
    print(f"\n📂 Organizing: {folder}")
    print(f"📍 Destination: {args.destination}")
    
    # Run analysis
    results = ss.analyze_folder(
        folder,
        recursive=args.recursive,
        max_files=getattr(args, 'max', None),
        show_progress=args.progress
    )
    
    # Print summary
    ss.print_summary()
    
    # Execute moves
    misc_threshold = getattr(args, 'misc_threshold', 0.0)
    existing_only = getattr(args, 'existing_only', False)
    interactive = getattr(args, 'interactive', False)
    
    if interactive:
        print(f"👉 Interactive mode: will prompt before creating new folders")
    elif existing_only:
        print(f"📁 Using existing folders only")
    if misc_threshold > 0:
        print(f"📦 Files below {misc_threshold*100:.0f}% confidence → misc/")
    
    if args.execute:
        print("\n🚀 EXECUTING FILE MOVES...")
        ss.execute_moves(
            dry_run=False, 
            min_confidence=args.min_confidence,
            misc_threshold=misc_threshold,
            existing_only=existing_only,
            interactive=interactive
        )
    else:
        print("\n🔍 DRY RUN - No files will be moved:")
        ss.execute_moves(
            dry_run=True, 
            min_confidence=args.min_confidence,
            misc_threshold=misc_threshold,
            existing_only=existing_only,
            interactive=interactive
        )
    
    return 0


def cmd_categories(args: argparse.Namespace) -> int:
    """Handle categories command"""
    config = load_config(getattr(args, 'config', None))
    print(format_category_table(config.categories))
    return 0


def cmd_undo(args: argparse.Namespace) -> int:
    """Handle undo command"""
    ss = SortSense()
    print("\n↩ UNDO LAST SESSION")
    print("-" * 40)
    restored = ss.undo_last_session()
    return 0 if restored > 0 else 1


def cmd_init(args: argparse.Namespace) -> int:
    """Handle init command"""
    output = args.output
    
    if os.path.exists(output):
        response = input(f"{output} already exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return 1
    
    save_config_template(output)
    print(f"✓ Config template saved to: {output}")
    print("  Edit this file to customize categories and settings.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Handle status command"""
    config = Config()
    print_tools_status(config.get_tools_status())
    
    if not config.has_ocr():
        print("\n⚠️  Tesseract not found. Image OCR will be disabled.")
        print("   Install: brew install tesseract (macOS)")
        print("            apt install tesseract-ocr (Ubuntu)")
    
    if not config.has_pdf_tools():
        print("\n⚠️  pdftotext not found. PDF text extraction will be limited.")
        print("   Install: brew install poppler (macOS)")
        print("            apt install poppler-utils (Ubuntu)")
    
    return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Print banner (unless just showing help)
    if args.command and args.command not in ('categories', 'status'):
        print_banner()
    
    # Route to command handler
    if args.command == 'analyze':
        return cmd_analyze(args)
    elif args.command == 'organize':
        return cmd_organize(args)
    elif args.command == 'categories':
        return cmd_categories(args)
    elif args.command == 'undo':
        return cmd_undo(args)
    elif args.command == 'init':
        return cmd_init(args)
    elif args.command == 'status':
        return cmd_status(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
