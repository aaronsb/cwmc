"""API key management for OpenAI and Gemini services."""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Union
from dotenv import load_dotenv, set_key, find_dotenv


class APIKeyValidationError(Exception):
    """Raised when an API key fails validation."""
    pass


def validate_openai_key(key: Optional[str]) -> bool:
    """Validate OpenAI API key format.
    
    OpenAI keys typically start with 'sk-' and are 40+ characters.
    Some keys may have 'sk-proj-' prefix.
    """
    if not key or not isinstance(key, str):
        return False
    
    # Check format: sk- or sk-proj- followed by alphanumeric characters
    pattern = r'^sk-(?:proj-)?[a-zA-Z0-9]{32,}$'
    return bool(re.match(pattern, key))


def validate_gemini_key(key: Optional[str]) -> bool:
    """Validate Gemini/Google API key format.
    
    Google API keys typically start with 'AIza' and are 39 characters.
    """
    if not key or not isinstance(key, str):
        return False
    
    # Check format: AIza followed by any characters totaling 39 chars
    # Google API keys can have various characters including hyphens after the prefix
    if len(key) != 39 or not key.startswith('AIza'):
        return False
    
    # Check that remaining characters are alphanumeric, dash, or underscore
    # Note: We already checked length and prefix, so just verify allowed chars
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
    remaining = key[4:]  # Skip 'AIza'
    return all(c in allowed_chars for c in remaining)


def mask_api_key(key: Optional[str]) -> str:
    """Mask API key for display, showing only first few and last few characters."""
    if not key:
        return ""
    
    if len(key) <= 10:
        # Very short key, just show first and last character
        if len(key) <= 2:
            return key
        return f"{key[0]}...{key[-1]}"
    
    # Show first 4 and last 5 characters
    return f"{key[:4]}...{key[-5:]}"


class APIKeyManager:
    """Manages API keys for the application."""
    
    def __init__(self, env_file_path: Optional[str] = None):
        """Initialize API key manager.
        
        Args:
            env_file_path: Path to .env file. If None, uses default .env in project root.
        """
        if env_file_path:
            self.env_file_path = Path(env_file_path)
        else:
            # Try to find existing .env file
            found_env = find_dotenv()
            if found_env:
                self.env_file_path = Path(found_env)
            else:
                # Default to .env in current directory
                self.env_file_path = Path.cwd() / ".env"
        
        # Create .env file if it doesn't exist
        if not self.env_file_path.exists():
            self.env_file_path.touch()
            self.env_file_path.write_text("# API Keys\n")
        
        # Load environment variables
        load_dotenv(self.env_file_path)
    
    def get_api_keys(self, masked: bool = False) -> Dict[str, str]:
        """Get current API keys from environment.
        
        Args:
            masked: If True, returns masked versions of keys for display
            
        Returns:
            Dict with 'openai_key' and 'gemini_key'
        """
        openai_key = os.environ.get('OPENAI_API_KEY', '')
        gemini_key = os.environ.get('GOOGLE_API_KEY', '')
        
        if masked:
            return {
                'openai_key': mask_api_key(openai_key) if openai_key else '',
                'gemini_key': mask_api_key(gemini_key) if gemini_key else ''
            }
        
        return {
            'openai_key': openai_key,
            'gemini_key': gemini_key
        }
    
    def set_openai_key(self, key: str) -> None:
        """Set OpenAI API key.
        
        Args:
            key: OpenAI API key (can be empty to clear)
            
        Raises:
            APIKeyValidationError: If key format is invalid
        """
        if key and not validate_openai_key(key):
            raise APIKeyValidationError("Invalid OpenAI API key format. Key should start with 'sk-' and be at least 40 characters.")
        
        self._update_env_file('OPENAI_API_KEY', key)
        # Update os.environ immediately
        if key:
            os.environ['OPENAI_API_KEY'] = key
        elif 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
    
    def set_gemini_key(self, key: str) -> None:
        """Set Gemini/Google API key.
        
        Args:
            key: Gemini API key (can be empty to clear)
            
        Raises:
            APIKeyValidationError: If key format is invalid
        """
        if key and not validate_gemini_key(key):
            raise APIKeyValidationError("Invalid Gemini API key format. Key should start with 'AIza' and be 39 characters.")
        
        self._update_env_file('GOOGLE_API_KEY', key)
        # Update os.environ immediately
        if key:
            os.environ['GOOGLE_API_KEY'] = key
        elif 'GOOGLE_API_KEY' in os.environ:
            del os.environ['GOOGLE_API_KEY']
    
    def set_api_keys(self, openai_key: str = "", gemini_key: str = "") -> None:
        """Set both API keys at once.
        
        Args:
            openai_key: OpenAI API key (can be empty)
            gemini_key: Gemini API key (can be empty)
            
        Raises:
            APIKeyValidationError: If any key format is invalid
        """
        # Validate both keys first
        if openai_key and not validate_openai_key(openai_key):
            raise APIKeyValidationError("Invalid OpenAI API key format")
        
        if gemini_key and not validate_gemini_key(gemini_key):
            raise APIKeyValidationError("Invalid Gemini API key format")
        
        # Update both keys
        self._update_env_file('OPENAI_API_KEY', openai_key)
        self._update_env_file('GOOGLE_API_KEY', gemini_key)
        
        # Update os.environ immediately
        if openai_key:
            os.environ['OPENAI_API_KEY'] = openai_key
        elif 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        
        if gemini_key:
            os.environ['GOOGLE_API_KEY'] = gemini_key
        elif 'GOOGLE_API_KEY' in os.environ:
            del os.environ['GOOGLE_API_KEY']
    
    def _update_env_file(self, key: str, value: str) -> None:
        """Update a key in the .env file.
        
        Args:
            key: Environment variable name
            value: Value to set (can be empty)
        """
        # Ensure file exists
        if not self.env_file_path.exists():
            self.env_file_path.touch()
            self.env_file_path.write_text("# API Keys\n")
        
        # Read current content
        content = self.env_file_path.read_text()
        lines = content.splitlines()
        
        # Check if key exists
        key_found = False
        new_lines = []
        
        for line in lines:
            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('#'):
                new_lines.append(line)
                continue
            
            # Check if this line contains our key
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                key_found = True
            else:
                new_lines.append(line)
        
        # If key wasn't found, append it
        if not key_found:
            new_lines.append(f"{key}={value}")
        
        # Write back to file
        new_content = '\n'.join(new_lines)
        if not new_content.endswith('\n'):
            new_content += '\n'
        
        self.env_file_path.write_text(new_content)
    
    def reload_environment(self) -> None:
        """Reload environment variables from .env file.
        
        This updates os.environ with the latest values from the file.
        """
        load_dotenv(self.env_file_path, override=True)