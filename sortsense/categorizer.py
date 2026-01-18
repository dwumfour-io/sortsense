"""
SortSense Categorization Engine

Handles keyword-based categorization of extracted text
with confidence scoring.
"""

import logging
from typing import Any, Dict, List, Tuple

from sortsense.config import Config, DEFAULT_CATEGORIES

logger = logging.getLogger(__name__)


class Categorizer:
    """Categorizes files based on extracted text and filename"""
    
    def __init__(self, config: Config = None, categories: Dict[str, Dict[str, Any]] = None):
        """
        Initialize categorizer with categories.
        
        Args:
            config: Config object containing categories
            categories: Direct dictionary of categories (overrides config)
        """
        if categories:
            self.categories = categories
        elif config:
            self.categories = config.categories
        else:
            self.categories = DEFAULT_CATEGORIES.copy()
        
        self.default_category = "unsorted"
        if config:
            self.default_category = config.settings.default_category
    
    def categorize(self, text: str, filename: str = "") -> Tuple[str, int, List[str]]:
        """
        Categorize content based on keyword matching.
        
        Args:
            text: Extracted text content
            filename: Original filename (for additional context)
        
        Returns:
            Tuple of (category, confidence_score, matched_keywords)
        """
        # Combine text and filename for matching
        combined = f"{text} {filename}".lower()
        
        scores: Dict[str, int] = {}
        matches: Dict[str, List[str]] = {}
        
        for category, config in self.categories.items():
            keywords = config.get('keywords', [])
            matched = []
            
            for keyword in keywords:
                # Check for keyword match (case-insensitive)
                if keyword.lower() in combined:
                    matched.append(keyword)
            
            scores[category] = len(matched)
            matches[category] = matched
        
        # Find highest scoring category
        max_score = max(scores.values()) if scores else 0
        
        if max_score > 0:
            # Return first category with max score
            for category, score in scores.items():
                if score == max_score:
                    return category, score, matches[category]
        
        return self.default_category, 0, []
    
    def get_destination_folder(self, category: str, base_path: str) -> str:
        """
        Get the destination folder path for a category.
        
        Args:
            category: Category name
            base_path: Base destination path
            
        Returns:
            Full path to destination folder
        """
        import os
        
        if category in self.categories:
            folder = self.categories[category].get('folder', category)
        else:
            folder = self.default_category
        
        return os.path.join(base_path, folder)
    
    def get_category_info(self, category: str) -> Dict[str, Any]:
        """
        Get information about a category.
        
        Args:
            category: Category name
            
        Returns:
            Category configuration dictionary
        """
        return self.categories.get(category, {})
    
    def list_categories(self) -> List[str]:
        """Get list of all category names"""
        return list(self.categories.keys())
    
    def add_category(
        self,
        name: str,
        description: str,
        folder: str,
        keywords: List[str]
    ) -> None:
        """
        Add or update a category.
        
        Args:
            name: Category name (identifier)
            description: Human-readable description
            folder: Destination folder name
            keywords: List of keywords for matching
        """
        self.categories[name] = {
            "description": description,
            "folder": folder,
            "keywords": keywords
        }
    
    def remove_category(self, name: str) -> bool:
        """
        Remove a category.
        
        Args:
            name: Category name to remove
            
        Returns:
            True if removed, False if not found
        """
        if name in self.categories:
            del self.categories[name]
            return True
        return False
    
    def add_keywords(self, category: str, keywords: List[str]) -> bool:
        """
        Add keywords to an existing category.
        
        Args:
            category: Category name
            keywords: Keywords to add
            
        Returns:
            True if successful, False if category not found
        """
        if category not in self.categories:
            return False
        
        existing = set(self.categories[category].get('keywords', []))
        existing.update(keywords)
        self.categories[category]['keywords'] = list(existing)
        return True
