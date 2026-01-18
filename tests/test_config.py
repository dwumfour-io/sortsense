"""
Tests for the Config module
"""

import json
import os
import tempfile
import pytest

from sortsense.config import (
    Config,
    Settings,
    load_config,
    find_config_file,
    save_config_template,
    detect_tesseract,
    DEFAULT_CATEGORIES
)


class TestConfig:
    """Test cases for Config class"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = Config()
        
        assert config.categories == DEFAULT_CATEGORIES
        assert isinstance(config.settings, Settings)
        assert config.settings.ocr_timeout == 30
        assert config.settings.max_text_length == 2000
    
    def test_tool_detection(self):
        """Test tool detection methods"""
        config = Config()
        
        # These return bool regardless of whether tools are installed
        assert isinstance(config.has_ocr(), bool)
        assert isinstance(config.has_pdf_tools(), bool)
    
    def test_get_tools_status(self):
        """Test tools status dictionary"""
        config = Config()
        status = config.get_tools_status()
        
        assert "tesseract" in status
        assert "pdftotext" in status
        assert "pdftoppm" in status
    
    def test_file_extensions(self):
        """Test file extension sets"""
        config = Config()
        
        assert '.pdf' in config.pdf_extensions
        assert '.png' in config.image_extensions
        assert '.jpg' in config.image_extensions
        assert '.docx' in config.word_extensions
        assert '.xlsx' in config.excel_extensions
        assert '.txt' in config.text_extensions


class TestSettings:
    """Test cases for Settings dataclass"""
    
    def test_default_settings(self):
        """Test default settings values"""
        settings = Settings()
        
        assert settings.ocr_timeout == 30
        assert settings.max_text_length == 2000
        assert settings.default_category == "unsorted"
        assert settings.min_confidence == 1
        assert settings.skip_hidden is True
        assert settings.verbose is False
    
    def test_custom_settings(self):
        """Test custom settings values"""
        settings = Settings(
            ocr_timeout=60,
            max_text_length=5000,
            default_category="misc"
        )
        
        assert settings.ocr_timeout == 60
        assert settings.max_text_length == 5000
        assert settings.default_category == "misc"


class TestLoadConfig:
    """Test cases for config loading"""
    
    def test_load_default_config(self):
        """Test loading without config file"""
        config = load_config()
        
        assert isinstance(config, Config)
        assert "finance" in config.categories
    
    def test_load_from_json_file(self):
        """Test loading from JSON config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "categories": {
                    "custom": {
                        "description": "Custom Category",
                        "folder": "custom",
                        "keywords": ["test", "example"]
                    }
                },
                "settings": {
                    "ocr_timeout": 45
                }
            }, f)
            f.flush()
            
            try:
                config = load_config(f.name)
                
                assert "custom" in config.categories
                assert config.settings.ocr_timeout == 45
            finally:
                os.unlink(f.name)
    
    def test_load_invalid_path(self):
        """Test loading from non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.json")
    
    def test_load_invalid_json(self):
        """Test loading from invalid JSON file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("not valid json {{{")
            f.flush()
            
            try:
                with pytest.raises(ValueError):
                    load_config(f.name)
            finally:
                os.unlink(f.name)


class TestSaveConfigTemplate:
    """Test cases for config template generation"""
    
    def test_save_template(self):
        """Test saving config template"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        
        try:
            save_config_template(path)
            
            assert os.path.exists(path)
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            assert "categories" in data
            assert "settings" in data
            assert "tools" in data
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestToolDetection:
    """Test cases for tool detection"""
    
    def test_detect_tesseract_returns_path_or_none(self):
        """Test tesseract detection returns valid result"""
        result = detect_tesseract()
        assert result is None or os.path.exists(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
