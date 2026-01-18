"""
SortSense Vision Module

Uses computer vision (CLIP model) to analyze image content
and categorize based on what's actually in the image.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Vision categories with descriptions for CLIP
VISION_CATEGORIES = {
    "photos": [
        "a photo of a person",
        "a selfie",
        "a family photo",
        "a group photo of people",
        "a portrait photograph",
        "people at a party or celebration",
        "friends hanging out",
        "a wedding photo",
        "vacation photos with people"
    ],
    "documents": [
        "a receipt",
        "an invoice document",
        "a bank statement",
        "financial document",
        "a bill or statement",
        "a passport",
        "an ID card or identification",
        "a visa document",
        "government document",
        "a contract or agreement",
        "legal paperwork"
    ],
    "health": [
        "medical document or prescription",
        "health records",
        "x-ray or medical scan",
        "medicine or pills",
        "hospital or clinic",
        "fitness or workout"
    ],
    "school": [
        "a diploma or certificate",
        "academic transcript",
        "school or university",
        "textbook or study materials",
        "classroom or lecture"
    ],
    "projects": [
        "code or programming",
        "computer screen with text",
        "software interface",
        "technical diagram",
        "server or hardware",
        "design mockup"
    ],
    "work": [
        "resume or CV document",
        "office or workplace",
        "business meeting",
        "professional headshot"
    ]
}


class VisionAnalyzer:
    """
    Analyzes images using computer vision (CLIP model).
    Falls back gracefully if dependencies not installed.
    """
    
    def __init__(self, categories: Dict[str, List[str]] = None):
        self.categories = categories or VISION_CATEGORIES
        self.model = None
        self.processor = None
        self.available = False
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the CLIP model for image classification"""
        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel
            
            logger.info("Loading CLIP model for vision analysis...")
            
            # Use smaller CLIP model for faster processing
            model_name = "openai/clip-vit-base-patch32"
            
            self.processor = CLIPProcessor.from_pretrained(model_name)
            self.model = CLIPModel.from_pretrained(model_name)
            self.available = True
            
            logger.info("CLIP model loaded successfully")
            
        except ImportError as e:
            logger.warning(f"Vision dependencies not installed: {e}")
            logger.info("Install with: pip install torch transformers pillow")
            self.available = False
        except Exception as e:
            logger.error(f"Error loading vision model: {e}")
            self.available = False
    
    def analyze_image(self, image_path: str) -> Tuple[str, float, List[str]]:
        """
        Analyze an image and return the best matching category.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (category, confidence, matched_descriptions)
        """
        if not self.available:
            return "unsorted", 0.0, []
        
        try:
            from PIL import Image
            import torch
            
            # Load image
            image = Image.open(image_path).convert("RGB")
            
            # Prepare all category descriptions
            all_descriptions = []
            category_map = {}  # Map description index to category
            
            for category, descriptions in self.categories.items():
                for desc in descriptions:
                    category_map[len(all_descriptions)] = category
                    all_descriptions.append(desc)
            
            # Process with CLIP
            inputs = self.processor(
                text=all_descriptions,
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Get top predictions
            top_probs, top_indices = probs[0].topk(5)
            
            # Aggregate scores by category
            category_scores: Dict[str, float] = {}
            category_matches: Dict[str, List[str]] = {}
            
            for prob, idx in zip(top_probs, top_indices):
                idx = idx.item()
                cat = category_map[idx]
                desc = all_descriptions[idx]
                score = prob.item()
                
                if cat not in category_scores:
                    category_scores[cat] = 0.0
                    category_matches[cat] = []
                
                category_scores[cat] += score
                if score > 0.1:  # Only include significant matches
                    category_matches[cat].append(f"{desc} ({score:.1%})")
            
            # Find best category
            best_category = max(category_scores, key=category_scores.get)
            best_score = category_scores[best_category]
            matches = category_matches.get(best_category, [])
            
            return best_category, best_score, matches
            
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            return "unsorted", 0.0, []
    
    def is_available(self) -> bool:
        """Check if vision analysis is available"""
        return self.available


def check_vision_dependencies() -> Dict[str, bool]:
    """Check which vision dependencies are installed"""
    deps = {}
    
    try:
        import torch
        deps["torch"] = True
    except ImportError:
        deps["torch"] = False
    
    try:
        from transformers import CLIPModel
        deps["transformers"] = True
    except ImportError:
        deps["transformers"] = False
    
    try:
        from PIL import Image
        deps["pillow"] = True
    except ImportError:
        deps["pillow"] = False
    
    return deps


def install_vision_command() -> str:
    """Return the command to install vision dependencies"""
    return "pip install torch transformers pillow"
