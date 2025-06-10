"""Test cases for API key management functionality."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.livetranscripts.api_key_manager import (
    APIKeyManager,
    APIKeyValidationError,
    mask_api_key,
    validate_openai_key,
    validate_gemini_key,
)


class TestAPIKeyValidation:
    """Test API key validation functions."""

    def test_validate_openai_key_valid(self):
        """Test validation of valid OpenAI API keys."""
        # Valid formats
        assert validate_openai_key("sk-1234567890abcdefghijklmnopqrstuvwxyz") is True
        assert validate_openai_key("sk-proj-1234567890abcdefghijklmnopqrstuvwxyz") is True
        assert validate_openai_key("sk-" + "a" * 48) is True

    def test_validate_openai_key_invalid(self):
        """Test validation of invalid OpenAI API keys."""
        # Invalid formats
        assert validate_openai_key("") is False
        assert validate_openai_key("invalid-key") is False
        assert validate_openai_key("sk-") is False
        assert validate_openai_key("sk-tooshort") is False
        assert validate_openai_key("not-starting-with-sk") is False
        assert validate_openai_key(None) is False

    def test_validate_gemini_key_valid(self):
        """Test validation of valid Gemini API keys."""
        # Valid format (39 characters, alphanumeric with underscores/hyphens)
        assert validate_gemini_key("AIzaSyD-1234567890abcdefghijklmnopqrstu") is True
        assert validate_gemini_key("AIzaSyC_abcdefghijklmnopqrstuvwxyz12345") is True

    def test_validate_gemini_key_invalid(self):
        """Test validation of invalid Gemini API keys."""
        assert validate_gemini_key("") is False
        assert validate_gemini_key("invalid-key") is False
        assert validate_gemini_key("AIzaSyD-tooshort") is False
        assert validate_gemini_key("not-starting-with-AIza") is False
        assert validate_gemini_key(None) is False

    def test_mask_api_key(self):
        """Test API key masking for display."""
        # OpenAI key
        assert mask_api_key("sk-1234567890abcdefghijklmnopqrstuvwxyz") == "sk-1...vwxyz"
        
        # Gemini key
        assert mask_api_key("AIzaSyD-1234567890abcdefghijklmnopqrstu") == "AIza...qrstu"
        
        # Short key (shouldn't happen but handle gracefully)
        assert mask_api_key("short") == "s...t"
        
        # Empty key
        assert mask_api_key("") == ""
        assert mask_api_key(None) == ""


class TestAPIKeyManager:
    """Test API key manager functionality."""

    @pytest.fixture
    def temp_env_file(self):
        """Create a temporary .env file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("# Test environment file\n")
            f.write("EXISTING_VAR=value\n")
            f.write("OPENAI_API_KEY=sk-existingkey1234567890abcdefghijklmnop\n")
            f.write("ANOTHER_VAR=another_value\n")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

    @pytest.fixture
    def api_key_manager(self, temp_env_file):
        """Create API key manager with temp file."""
        return APIKeyManager(env_file_path=temp_env_file)

    def test_initialization(self, api_key_manager, temp_env_file):
        """Test API key manager initialization."""
        assert api_key_manager.env_file_path == Path(temp_env_file)
        assert api_key_manager.env_file_path.exists()

    def test_initialization_creates_env_file(self):
        """Test that initialization creates .env file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            assert not env_path.exists()
            
            manager = APIKeyManager(env_file_path=str(env_path))
            assert env_path.exists()

    def test_get_api_keys_from_env(self, api_key_manager):
        """Test retrieving API keys from environment."""
        # Set environment variables
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'sk-test1234567890abcdefghijklmnopqrstuvwxyz',
            'GOOGLE_API_KEY': 'AIzaSyD-test1234567890abcdefghijklmnop'
        }):
            keys = api_key_manager.get_api_keys()
            
            assert keys['openai_key'] == 'sk-test1234567890abcdefghijklmnopqrstuvwxyz'
            assert keys['gemini_key'] == 'AIzaSyD-test1234567890abcdefghijklmnop'

    def test_get_api_keys_masked(self, api_key_manager):
        """Test retrieving masked API keys."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'sk-test1234567890abcdefghijklmnopqrstuvwxyz',
            'GOOGLE_API_KEY': 'AIzaSyD-test1234567890abcdefghijklmnop'
        }):
            keys = api_key_manager.get_api_keys(masked=True)
            
            assert keys['openai_key'] == 'sk-t...vwxyz'
            assert keys['gemini_key'] == 'AIza...lmnop'

    def test_get_api_keys_empty(self, api_key_manager):
        """Test retrieving API keys when none are set."""
        with patch.dict(os.environ, {}, clear=True):
            keys = api_key_manager.get_api_keys()
            
            assert keys['openai_key'] == ''
            assert keys['gemini_key'] == ''

    def test_set_openai_key_valid(self, api_key_manager, temp_env_file):
        """Test setting a valid OpenAI API key."""
        new_key = "sk-newkey1234567890abcdefghijklmnopqrstuvwxyz"
        
        api_key_manager.set_openai_key(new_key)
        
        # Verify it was written to file
        with open(temp_env_file, 'r') as f:
            content = f.read()
            assert f"OPENAI_API_KEY={new_key}" in content
            # Ensure other vars are preserved
            assert "EXISTING_VAR=value" in content
            assert "ANOTHER_VAR=another_value" in content

    def test_set_openai_key_invalid(self, api_key_manager):
        """Test setting an invalid OpenAI API key."""
        with pytest.raises(APIKeyValidationError) as exc_info:
            api_key_manager.set_openai_key("invalid-key")
        
        assert "Invalid OpenAI API key format" in str(exc_info.value)

    def test_set_gemini_key_valid(self, api_key_manager, temp_env_file):
        """Test setting a valid Gemini API key."""
        new_key = "AIzaSyD-newkey1234567890abcdefghijklmno"
        
        api_key_manager.set_gemini_key(new_key)
        
        # Verify it was written to file
        with open(temp_env_file, 'r') as f:
            content = f.read()
            assert f"GOOGLE_API_KEY={new_key}" in content

    def test_set_gemini_key_invalid(self, api_key_manager):
        """Test setting an invalid Gemini API key."""
        with pytest.raises(APIKeyValidationError) as exc_info:
            api_key_manager.set_gemini_key("invalid-key")
        
        assert "Invalid Gemini API key format" in str(exc_info.value)

    def test_set_both_keys(self, api_key_manager, temp_env_file):
        """Test setting both API keys."""
        openai_key = "sk-both1234567890abcdefghijklmnopqrstuvwxyz"
        gemini_key = "AIzaSyD-both1234567890abcdefghijklmnopq"
        
        api_key_manager.set_api_keys(
            openai_key=openai_key,
            gemini_key=gemini_key
        )
        
        # Verify both were written
        with open(temp_env_file, 'r') as f:
            content = f.read()
            assert f"OPENAI_API_KEY={openai_key}" in content
            assert f"GOOGLE_API_KEY={gemini_key}" in content

    def test_set_keys_with_empty_values(self, api_key_manager, temp_env_file):
        """Test setting empty values (clearing keys)."""
        # First set some keys
        api_key_manager.set_api_keys(
            openai_key="sk-test1234567890abcdefghijklmnopqrstuvwxyz",
            gemini_key="AIzaSyD-test1234567890abcdefghijklmnopq"
        )
        
        # Then clear them
        api_key_manager.set_api_keys(openai_key="", gemini_key="")
        
        with open(temp_env_file, 'r') as f:
            content = f.read()
            # Keys should be present but empty
            assert "OPENAI_API_KEY=" in content
            assert "GOOGLE_API_KEY=" in content
            # But not with values
            assert "sk-test" not in content
            assert "AIzaSyD-test" not in content

    def test_update_env_file_preserves_comments(self, api_key_manager, temp_env_file):
        """Test that updating .env file preserves comments and structure."""
        # Add a key
        api_key_manager.set_openai_key("sk-preserve1234567890abcdefghijklmnopqrstuvw")
        
        with open(temp_env_file, 'r') as f:
            content = f.read()
            # Comments should be preserved
            assert "# Test environment file" in content

    def test_env_file_creation_on_set(self):
        """Test that setting keys creates .env file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            manager = APIKeyManager(env_file_path=str(env_path))
            
            # Remove the file that was created on init
            os.unlink(env_path)
            assert not env_path.exists()
            
            # Set a key
            manager.set_openai_key("sk-create1234567890abcdefghijklmnopqrstuvwx")
            
            # File should be created
            assert env_path.exists()
            with open(env_path, 'r') as f:
                content = f.read()
                assert "OPENAI_API_KEY=sk-create" in content

    def test_concurrent_updates(self, api_key_manager):
        """Test that concurrent updates don't corrupt the file."""
        # This is a basic test - in production you'd want file locking
        import threading
        
        def update_openai():
            api_key_manager.set_openai_key("sk-thread11234567890abcdefghijklmnopqrstuv")
        
        def update_gemini():
            api_key_manager.set_gemini_key("AIzaSyD-thread21234567890abcdefghijklmn")
        
        t1 = threading.Thread(target=update_openai)
        t2 = threading.Thread(target=update_gemini)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Both keys should be present
        keys = api_key_manager.get_api_keys()
        assert keys['openai_key'].startswith('sk-')
        assert keys['gemini_key'].startswith('AIza')

    @patch.dict(os.environ, {}, clear=True)
    def test_reload_environment(self, api_key_manager):
        """Test reloading environment variables from file."""
        # Write keys directly to file without updating os.environ
        api_key_manager._update_env_file('OPENAI_API_KEY', "sk-reload1234567890abcdefghijklmnopqrstuvw")
        api_key_manager._update_env_file('GOOGLE_API_KEY', "AIzaSyD-reload1234567890abcdefghijklmno")
        
        # Environment shouldn't have them yet
        assert os.environ.get('OPENAI_API_KEY') is None
        assert os.environ.get('GOOGLE_API_KEY') is None
        
        # Reload environment
        api_key_manager.reload_environment()
        
        # Now they should be loaded
        assert os.environ.get('OPENAI_API_KEY') == "sk-reload1234567890abcdefghijklmnopqrstuvw"
        assert os.environ.get('GOOGLE_API_KEY') == "AIzaSyD-reload1234567890abcdefghijklmno"