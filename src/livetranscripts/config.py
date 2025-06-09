"""Configuration management for Live Transcripts.

This module provides a centralized configuration system that supports:
- Environment variables
- Configuration files (YAML/JSON)
- Command-line overrides
- Platform-specific defaults
"""

import os
import json
import yaml
import platform
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum


class AudioBackendPreference(Enum):
    """User preference for audio backend selection."""
    AUTO = "auto"  # Automatic selection
    PIPEWIRE = "pipewire"
    PULSEAUDIO = "pulseaudio"
    PYAUDIO = "pyaudio"
    SOUNDDEVICE = "sounddevice"
    WASAPI = "wasapi"
    COREAUDIO = "coreaudio"
    BLACKHOLE = "blackhole"
    JACK = "jack"
    ALSA = "alsa"


@dataclass
class AudioConfig:
    """Audio capture configuration."""
    
    # Backend selection
    backend_preference: AudioBackendPreference = AudioBackendPreference.AUTO
    backend_fallback_enabled: bool = True
    preferred_backends_linux: List[str] = field(default_factory=lambda: ["pipewire", "pulseaudio", "pyaudio"])
    preferred_backends_macos: List[str] = field(default_factory=lambda: ["blackhole", "coreaudio", "sounddevice"])
    preferred_backends_windows: List[str] = field(default_factory=lambda: ["wasapi", "sounddevice", "pyaudio"])
    
    # Audio parameters
    sample_rate: int = 16000
    channels: int = 1
    format: str = "int16"
    chunk_size: int = 1024
    buffer_duration: float = 10.0
    latency_mode: str = "low"  # low, normal, high
    
    # Device selection
    device_name: Optional[str] = None
    device_auto_select: bool = True
    prefer_monitor_devices: bool = True
    
    # Processing
    enable_noise_reduction: bool = False
    enable_auto_gain: bool = False
    silence_threshold: float = 500.0
    
    def __post_init__(self):
        """Validate configuration."""
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.channels not in [1, 2]:
            raise ValueError("channels must be 1 or 2")
        if self.latency_mode not in ["low", "normal", "high"]:
            raise ValueError("latency_mode must be low, normal, or high")


@dataclass
class TranscriptionConfig:
    """Transcription configuration."""
    
    # Model selection
    transcription_model: str = "gpt-4o-transcribe"
    model_fallback: List[str] = field(default_factory=lambda: ["whisper-1"])
    
    # Whisper settings (legacy, kept for backward compatibility)
    whisper_model: str = "whisper-1"
    whisper_language: Optional[str] = None  # Auto-detect if None
    whisper_prompt: Optional[str] = None
    
    # Batching
    min_batch_duration: float = 3.0
    max_batch_duration: float = 30.0
    silence_duration_threshold: float = 0.5
    batch_overlap: float = 0.5
    
    # API settings
    api_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        """Validate configuration."""
        supported_models = ["whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"]
        if self.transcription_model not in supported_models:
            raise ValueError(f"Unsupported transcription model: {self.transcription_model}")
        
        # Validate fallback models
        for model in self.model_fallback:
            if model not in supported_models:
                raise ValueError(f"Unsupported fallback model: {model}")


@dataclass
class AIConfig:
    """AI integration configuration."""
    
    # Gemini settings
    gemini_model: str = "gemini-2.0-flash-lite"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 1024
    
    # Context management
    use_full_context: bool = True
    max_context_tokens: int = 1_000_000
    
    # Features
    enable_insights: bool = True
    insight_interval: float = 60.0
    enable_dynamic_questions: bool = True
    question_update_interval: float = 15.0
    num_dynamic_questions: int = 4
    
    # Session settings
    default_session_focus: Optional[str] = None


@dataclass
class ServerConfig:
    """Server configuration."""
    
    host: str = "localhost"
    port: int = 8765
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:*", "http://127.0.0.1:*"])
    
    # WebSocket settings
    ws_ping_interval: float = 30.0
    ws_ping_timeout: float = 10.0
    ws_max_message_size: int = 10 * 1024 * 1024  # 10MB
    
    # Session management
    max_sessions: int = 10
    session_timeout: float = 3600.0  # 1 hour


@dataclass
class LoggingConfig:
    """Logging configuration."""
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = "logs/livetranscripts.log"
    console: bool = True
    rotate_logs: bool = True
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class PathConfig:
    """Path configuration."""
    
    home: str = str(Path.home())
    config_dir: str = ""
    log_dir: str = ""
    cache_dir: str = ""
    system_config: Optional[str] = None
    
    def expand_paths(self) -> None:
        """Expand environment variables and ~ in paths."""
        self.home = os.path.expandvars(os.path.expanduser(self.home))
        self.config_dir = os.path.expandvars(os.path.expanduser(self.config_dir))
        self.log_dir = os.path.expandvars(os.path.expanduser(self.log_dir))
        self.cache_dir = os.path.expandvars(os.path.expanduser(self.cache_dir))
        if self.system_config:
            self.system_config = os.path.expandvars(os.path.expanduser(self.system_config))


@dataclass
class Config:
    """Main configuration container."""
    
    audio: AudioConfig = field(default_factory=AudioConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    
    # Development settings
    debug: bool = False
    profile: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        # Handle nested dataclasses
        if "audio" in data and isinstance(data["audio"], dict):
            # Convert backend_preference string to enum
            if "backend_preference" in data["audio"]:
                data["audio"]["backend_preference"] = AudioBackendPreference(data["audio"]["backend_preference"])
            data["audio"] = AudioConfig(**data["audio"])
        
        if "transcription" in data and isinstance(data["transcription"], dict):
            data["transcription"] = TranscriptionConfig(**data["transcription"])
        
        if "ai" in data and isinstance(data["ai"], dict):
            data["ai"] = AIConfig(**data["ai"])
        
        if "server" in data and isinstance(data["server"], dict):
            data["server"] = ServerConfig(**data["server"])
        
        if "logging" in data and isinstance(data["logging"], dict):
            data["logging"] = LoggingConfig(**data["logging"])
        
        if "paths" in data and isinstance(data["paths"], dict):
            data["paths"] = PathConfig(**data["paths"])
        
        return cls(**data)


class ConfigProfile:
    """Predefined configuration profiles for different platforms and setups."""
    
    # Common settings shared across platforms
    COMMON = {
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "format": "int16",
            "buffer_duration": 10.0,
            "device_auto_select": True,
            "prefer_monitor_devices": True,
            "silence_threshold": 500.0
        },
        "transcription": {
            "transcription_model": "gpt-4o-transcribe",
            "model_fallback": ["whisper-1"],
            "whisper_model": "whisper-1",
            "min_batch_duration": 3.0,
            "max_batch_duration": 30.0,
            "silence_duration_threshold": 0.5,
            "batch_overlap": 0.5,
            "api_timeout": 30.0,
            "max_retries": 3
        },
        "ai": {
            "gemini_model": "gemini-2.0-flash-lite",
            "gemini_temperature": 0.7,
            "enable_insights": True,
            "insight_interval": 60.0,
            "enable_dynamic_questions": True,
            "question_update_interval": 15.0,
            "num_dynamic_questions": 4
        },
        "server": {
            "host": "localhost",
            "port": 8765,
            "enable_cors": True,
            "ws_ping_interval": 30.0,
            "max_sessions": 10
        }
    }
    
    PROFILES = {
        "macos": {
            "audio": {
                "backend_preference": "auto",
                "preferred_backends_macos": ["blackhole", "coreaudio", "sounddevice", "pyaudio"],
                "latency_mode": "low",
                "chunk_size": 1024
            },
            "paths": {
                "home": "/Users",
                "config_dir": "~/Library/Application Support/LiveTranscripts",
                "log_dir": "~/Library/Logs/LiveTranscripts",
                "cache_dir": "~/Library/Caches/LiveTranscripts"
            },
            "logging": {
                "file": "~/Library/Logs/LiveTranscripts/livetranscripts.log"
            }
        },
        "linux": {
            "audio": {
                "backend_preference": "auto",
                "preferred_backends_linux": ["pipewire", "pulseaudio", "sounddevice", "pyaudio", "jack", "alsa"],
                "latency_mode": "low",
                "chunk_size": 512  # Lower chunk size for lower latency on Linux
            },
            "transcription": {
                "min_batch_duration": 2.5  # Slightly lower for better Linux audio handling
            },
            "paths": {
                "home": "/home",
                "config_dir": "~/.config/livetranscripts",
                "log_dir": "~/.local/share/livetranscripts/logs",
                "cache_dir": "~/.cache/livetranscripts",
                "system_config": "/etc/livetranscripts"
            },
            "logging": {
                "file": "~/.local/share/livetranscripts/logs/livetranscripts.log"
            }
        },
        "windows": {
            "audio": {
                "backend_preference": "auto",
                "preferred_backends_windows": ["wasapi", "sounddevice", "pyaudio"],
                "latency_mode": "low",
                "chunk_size": 1024
            },
            "paths": {
                "home": "C:/Users",
                "config_dir": "%APPDATA%/LiveTranscripts",
                "log_dir": "%APPDATA%/LiveTranscripts/Logs",
                "cache_dir": "%LOCALAPPDATA%/LiveTranscripts/Cache"
            },
            "logging": {
                "file": "%APPDATA%/LiveTranscripts/Logs/livetranscripts.log"
            }
        },
        "development": {
            "audio": {
                "backend_preference": "auto",
                "latency_mode": "normal",
                "enable_noise_reduction": True,
                "enable_auto_gain": True
            },
            "ai": {
                "gemini_temperature": 0.9,  # More creative for development
                "enable_insights": True,
                "insight_interval": 30.0  # More frequent insights
            },
            "logging": {
                "level": "DEBUG",
                "console": True
            },
            "debug": True,
            "profile": True
        },
        "production": {
            "audio": {
                "backend_preference": "auto",
                "latency_mode": "normal",
                "backend_fallback_enabled": True
            },
            "ai": {
                "gemini_temperature": 0.7,
                "enable_insights": True,
                "insight_interval": 60.0
            },
            "server": {
                "enable_cors": True,
                "max_sessions": 50
            },
            "logging": {
                "level": "INFO",
                "console": False,
                "rotate_logs": True
            },
            "debug": False
        }
    }
    
    @classmethod
    def get_profile(cls, name: str) -> Dict[str, Any]:
        """Get a configuration profile by name, merged with common settings."""
        profile = cls.PROFILES.get(name, {})
        if not profile:
            return {}
        
        # Deep merge common settings with profile-specific settings
        import copy
        merged = copy.deepcopy(cls.COMMON)
        
        def deep_merge(base: dict, override: dict) -> dict:
            """Recursively merge override into base."""
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        return deep_merge(merged, profile)
    
    @classmethod
    def list_profiles(cls) -> List[str]:
        """List available profile names."""
        return list(cls.PROFILES.keys())
    
    @classmethod
    def get_platform_default_profile(cls) -> str:
        """Get the default profile for the current platform."""
        system = platform.system()
        if system == "Darwin":
            return "macos"
        elif system == "Linux":
            return "linux"
        elif system == "Windows":
            return "windows"
        else:
            return "production"


class ConfigManager:
    """Manages configuration loading and merging from multiple sources."""
    
    def __init__(self):
        self.config = Config()
        self._config_paths = self._get_config_paths()
        self._profile_name: Optional[str] = None
    
    def _get_config_paths(self) -> List[Path]:
        """Get list of configuration file paths to check."""
        paths = []
        
        # User config directory
        if platform.system() == "Windows":
            config_dir = Path(os.environ.get("APPDATA", "")) / "LiveTranscripts"
        else:
            config_dir = Path.home() / ".config" / "livetranscripts"
        
        # Possible config locations in order of priority
        paths.extend([
            Path("config.yaml"),  # Current directory
            Path("config.json"),
            config_dir / "config.yaml",  # User config
            config_dir / "config.json",
            Path("/etc/livetranscripts/config.yaml"),  # System config (Linux)
            Path("/etc/livetranscripts/config.json"),
        ])
        
        return paths
    
    def load_from_file(self, path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        if not path.exists():
            return {}
        
        with open(path, 'r') as f:
            if path.suffix == '.yaml' or path.suffix == '.yml':
                return yaml.safe_load(f) or {}
            elif path.suffix == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")
    
    def load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}
        
        # Check for profile selection
        profile_env = os.environ.get("LT_PROFILE")
        if profile_env:
            self._profile_name = profile_env
        
        # Map environment variables to config paths
        env_map = {
            # Audio settings
            "LT_AUDIO_BACKEND": ("audio", "backend_preference"),
            "LT_AUDIO_SAMPLE_RATE": ("audio", "sample_rate"),
            "LT_AUDIO_DEVICE": ("audio", "device_name"),
            "LT_AUDIO_LATENCY": ("audio", "latency_mode"),
            
            # Transcription settings
            "LT_WHISPER_MODEL": ("transcription", "whisper_model"),
            "LT_WHISPER_LANGUAGE": ("transcription", "whisper_language"),
            "LT_MIN_BATCH_DURATION": ("transcription", "min_batch_duration"),
            "LT_MAX_BATCH_DURATION": ("transcription", "max_batch_duration"),
            
            # AI settings
            "LT_GEMINI_MODEL": ("ai", "gemini_model"),
            "LT_INSIGHT_INTERVAL": ("ai", "insight_interval"),
            "LT_QUESTION_INTERVAL": ("ai", "question_update_interval"),
            
            # Server settings
            "LT_SERVER_HOST": ("server", "host"),
            "LT_SERVER_PORT": ("server", "port"),
            
            # Logging
            "LT_LOG_LEVEL": ("logging", "level"),
            "LT_LOG_FILE": ("logging", "file"),
            
            # Debug
            "LT_DEBUG": ("debug",),
        }
        
        for env_var, config_path in env_map.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert value to appropriate type
                if env_var in ["LT_AUDIO_SAMPLE_RATE", "LT_SERVER_PORT"]:
                    value = int(value)
                elif env_var in ["LT_MIN_BATCH_DURATION", "LT_MAX_BATCH_DURATION", 
                               "LT_INSIGHT_INTERVAL", "LT_QUESTION_INTERVAL"]:
                    value = float(value)
                elif env_var in ["LT_DEBUG"]:
                    value = value.lower() in ["true", "1", "yes"]
                elif env_var == "LT_AUDIO_BACKEND":
                    value = value.lower()
                
                # Set nested config value
                current = config
                for key in config_path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                current[config_path[-1]] = value
        
        return config
    
    def merge_configs(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries."""
        result = {}
        
        for config in configs:
            for key, value in config.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursively merge dictionaries
                    result[key] = self.merge_configs(result[key], value)
                else:
                    # Override value
                    result[key] = value
        
        return result
    
    def load(self, profile: Optional[str] = None) -> Config:
        """Load configuration from all sources.
        
        Args:
            profile: Configuration profile to use. If None, will use:
                    1. LT_PROFILE environment variable
                    2. 'profile' key in config file
                    3. Platform default profile
        """
        configs = []
        
        # Determine profile to use
        if profile:
            self._profile_name = profile
        elif not self._profile_name:  # Not set by env var
            # Check config files for profile setting
            for path in self._config_paths:
                if path.exists():
                    file_config = self.load_from_file(path)
                    if "profile" in file_config:
                        self._profile_name = file_config["profile"]
                        break
            
            # Use platform default if no profile specified
            if not self._profile_name:
                self._profile_name = ConfigProfile.get_platform_default_profile()
        
        # Load profile configuration first (lowest priority)
        if self._profile_name:
            profile_config = ConfigProfile.get_profile(self._profile_name)
            if profile_config:
                configs.append(profile_config)
            else:
                print(f"Warning: Unknown profile '{self._profile_name}'")
        
        # Load from files (increasing priority)
        for path in reversed(self._config_paths):
            if path.exists():
                configs.append(self.load_from_file(path))
        
        # Load from environment (highest priority)
        configs.append(self.load_from_env())
        
        # Merge all configs
        merged = self.merge_configs(*configs)
        
        # Create Config object
        if merged:
            self.config = Config.from_dict(merged)
            # Expand paths after loading
            self.config.paths.expand_paths()
        
        return self.config
    
    def get_profile_name(self) -> Optional[str]:
        """Get the currently loaded profile name."""
        return self._profile_name
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save current configuration to file."""
        if path is None:
            # Default to user config directory
            if platform.system() == "Windows":
                config_dir = Path(os.environ.get("APPDATA", "")) / "LiveTranscripts"
            else:
                config_dir = Path.home() / ".config" / "livetranscripts"
            
            config_dir.mkdir(parents=True, exist_ok=True)
            path = config_dir / "config.yaml"
        
        # Convert enums to strings for serialization
        config_dict = self.config.to_dict()
        if "backend_preference" in config_dict.get("audio", {}):
            config_dict["audio"]["backend_preference"] = config_dict["audio"]["backend_preference"].value
        
        with open(path, 'w') as f:
            if path.suffix in ['.yaml', '.yml']:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_dict, f, indent=2)


# Global config instance
_config_manager = ConfigManager()


def load_config(profile: Optional[str] = None) -> Config:
    """Load configuration from all sources.
    
    Args:
        profile: Configuration profile to use (e.g., 'macos-blackhole', 'linux-pipewire')
    """
    return _config_manager.load(profile)


def get_config() -> Config:
    """Get current configuration."""
    return _config_manager.config


def save_config(path: Optional[Path] = None) -> None:
    """Save current configuration."""
    _config_manager.save(path)


def get_profile_name() -> Optional[str]:
    """Get the currently loaded profile name."""
    return _config_manager.get_profile_name()


def list_profiles() -> List[str]:
    """List available configuration profiles."""
    return ConfigProfile.list_profiles()