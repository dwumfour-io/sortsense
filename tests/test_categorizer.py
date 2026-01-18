"""
Tests for the Categorizer module
"""

import pytest
from sortsense.categorizer import Categorizer
from sortsense.config import Config


class TestCategorizer:
    """Test cases for the Categorizer class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.categorizer = Categorizer()
    
    def test_categorize_finance_invoice(self):
        """Test categorization of finance-related text"""
        text = "Invoice #12345 for payment of $500.00"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "finance"
        assert score > 0
        assert "invoice" in matches or "payment" in matches
    
    def test_categorize_immigration_visa(self):
        """Test categorization of immigration documents"""
        text = "H1B Visa petition approved by USCIS"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "immigration"
        assert score >= 2
        assert "h1b" in matches or "visa" in matches or "uscis" in matches
    
    def test_categorize_medical_prescription(self):
        """Test categorization of medical documents"""
        text = "Patient: John Doe. Prescription for medication."
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "medical"
        assert "prescription" in matches or "patient" in matches
    
    def test_categorize_career_resume(self):
        """Test categorization of career documents"""
        text = "Resume - Professional Experience and Skills"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "career"
        assert "resume" in matches or "professional experience" in matches
    
    def test_categorize_dev_programming(self):
        """Test categorization of development files"""
        text = "Python programming tutorial with GitHub examples"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "dev"
        assert "python" in matches or "programming" in matches or "github" in matches
    
    def test_categorize_education_transcript(self):
        """Test categorization of education documents"""
        text = "Official University Transcript - GPA 3.5"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "education"
        assert "university" in matches or "transcript" in matches or "gpa" in matches
    
    def test_categorize_housing_lease(self):
        """Test categorization of housing documents"""
        text = "Apartment Lease Agreement between landlord and tenant"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "housing"
        assert "lease" in matches or "apartment" in matches or "landlord" in matches
    
    def test_categorize_vehicles_registration(self):
        """Test categorization of vehicle documents"""
        text = "Vehicle Registration - VIN number, license plate"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "vehicles"
        assert "vehicle" in matches or "registration" in matches or "vin" in matches
    
    def test_categorize_empty_text(self):
        """Test categorization with empty text"""
        category, score, matches = self.categorizer.categorize("")
        
        assert category == "unsorted"
        assert score == 0
        assert matches == []
    
    def test_categorize_unknown_text(self):
        """Test categorization with unrelated text"""
        text = "Random gibberish that matches nothing specific"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "unsorted"
        assert score == 0
    
    def test_categorize_filename_fallback(self):
        """Test that filename is used for categorization"""
        text = ""
        filename = "my_resume_2024.pdf"
        category, score, matches = self.categorizer.categorize(text, filename)
        
        assert category == "career"
        assert "resume" in matches
    
    def test_categorize_case_insensitive(self):
        """Test that categorization is case-insensitive"""
        text = "INVOICE for PAYMENT from BANK"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "finance"
        assert score >= 2
    
    def test_add_custom_category(self):
        """Test adding a custom category"""
        self.categorizer.add_category(
            name="photography",
            description="Photography files",
            folder="photos",
            keywords=["camera", "photo", "lens", "aperture"]
        )
        
        text = "Camera settings with aperture f/2.8"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "photography"
        assert "camera" in matches or "aperture" in matches
    
    def test_remove_category(self):
        """Test removing a category"""
        assert "finance" in self.categorizer.list_categories()
        
        result = self.categorizer.remove_category("finance")
        assert result is True
        assert "finance" not in self.categorizer.list_categories()
    
    def test_add_keywords(self):
        """Test adding keywords to existing category"""
        result = self.categorizer.add_keywords("finance", ["crypto", "bitcoin"])
        assert result is True
        
        text = "Bitcoin crypto trading"
        category, score, matches = self.categorizer.categorize(text)
        
        assert category == "finance"
        assert "bitcoin" in matches or "crypto" in matches
    
    def test_get_destination_folder(self):
        """Test destination folder generation"""
        dest = self.categorizer.get_destination_folder("finance", "/base/path")
        assert dest == "/base/path/finance"
        
        dest = self.categorizer.get_destination_folder("unknown", "/base/path")
        assert dest == "/base/path/unsorted"
    
    def test_list_categories(self):
        """Test listing all categories"""
        categories = self.categorizer.list_categories()
        
        assert isinstance(categories, list)
        assert "finance" in categories
        assert "immigration" in categories
        assert "career" in categories


class TestCategorizerWithConfig:
    """Test Categorizer with custom Config"""
    
    def test_custom_config_categories(self):
        """Test using custom categories from config"""
        config = Config()
        config.categories = {
            "personal": {
                "description": "Personal files",
                "folder": "personal",
                "keywords": ["diary", "journal", "personal"]
            }
        }
        
        categorizer = Categorizer(config)
        
        text = "My personal diary entry"
        category, score, matches = categorizer.categorize(text)
        
        assert category == "personal"
    
    def test_config_default_category(self):
        """Test custom default category"""
        config = Config()
        config.settings.default_category = "misc"
        
        categorizer = Categorizer(config)
        
        text = "Completely unrelated text"
        category, score, matches = categorizer.categorize(text)
        
        assert category == "misc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
