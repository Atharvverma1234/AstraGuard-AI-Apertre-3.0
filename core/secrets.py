"""
Centralized Secrets Management Module

Provides unified, secure secret access across the application with:
- Environment variable loading
- .env file support
- Startup validation
- Log masking for sensitive values
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# Try to import dotenv for .env file support
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


logger = logging.getLogger(__name__)


class SecretManager:
    """
    Centralized secret management with validation and masking.
    
    Usage:
        from core.secrets import secrets_manager, get_secret, require_secrets
        
        # Validate required secrets at startup
        require_secrets(["API_KEY", "JWT_SECRET"])
        
        # Get a secret
        api_key = get_secret("API_KEY")
    """
    
    _instance: Optional["SecretManager"] = None
    _initialized: bool = False
    
    # Patterns that indicate a secret (for auto-masking in logs)
    SECRET_PATTERNS = [
        r".*password.*",
        r".*secret.*",
        r".*key.*",
        r".*token.*",
        r".*credential.*",
        r".*auth.*",
    ]
    
    def __new__(cls) -> "SecretManager":
        """Singleton pattern to ensure single instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the secret manager."""
        if SecretManager._initialized:
            return
        
        self._secrets_cache: Dict[str, str] = {}
        self._loaded_from_file = False
        self._env_file_path: Optional[Path] = None
        
        # Auto-load .env file if available
        self._load_env_file()
        
        SecretManager._initialized = True
    
    def _load_env_file(self, env_path: Optional[str] = None) -> bool:
        """
        Load secrets from .env file.
        
        Args:
            env_path: Optional path to .env file. If None, searches for:
                      .env.local, .env, in project root
        
        Returns:
            True if .env file was loaded, False otherwise
        """
        if not DOTENV_AVAILABLE:
            logger.debug("python-dotenv not installed, skipping .env file loading")
            return False
        
        # Search paths for .env file
        search_paths = []
        if env_path:
            search_paths.append(Path(env_path))
        else:
            # Look in common locations
            project_root = Path(__file__).parent.parent
            search_paths = [
                project_root / ".env.local",
                project_root / ".env",
            ]
        
        for path in search_paths:
            if path.exists():
                load_dotenv(path, override=False)
                self._loaded_from_file = True
                self._env_file_path = path
                logger.info(f"Loaded secrets from {path}")
                return True
        
        return False
    
    def get(
        self,
        name: str,
        default: Optional[str] = None,
        required: bool = False
    ) -> Optional[str]:
        """
        Get a secret value.
        
        Args:
            name: Name of the secret (environment variable name)
            default: Default value if secret is not set
            required: If True, raises ValueError when secret is missing
        
        Returns:
            The secret value, or default if not found
        
        Raises:
            ValueError: If required=True and secret is not found
        """
        # Check cache first
        if name in self._secrets_cache:
            return self._secrets_cache[name]
        
        # Get from environment
        value = os.environ.get(name)
        
        if value is None:
            if required:
                raise ValueError(
                    f"Required secret '{name}' is not set. "
                    f"Set it via environment variable or .env file."
                )
            return default
        
        # Cache the value
        self._secrets_cache[name] = value
        return value
    
    def require(self, names: List[str]) -> Dict[str, str]:
        """
        Validate that all required secrets exist.
        
        Args:
            names: List of secret names to validate
        
        Returns:
            Dictionary of secret name -> value
        
        Raises:
            ValueError: If any required secret is missing
        """
        missing = []
        secrets = {}
        
        for name in names:
            value = os.environ.get(name)
            if value is None:
                missing.append(name)
            else:
                secrets[name] = value
        
        if missing:
            raise ValueError(
                f"Missing required secrets: {', '.join(missing)}. "
                f"Set them via environment variables or .env file."
            )
        
        return secrets
    
    def is_secret_name(self, name: str) -> bool:
        """
        Check if a name looks like it contains sensitive data.
        
        Args:
            name: The name to check
        
        Returns:
            True if the name matches secret patterns
        """
        name_lower = name.lower()
        for pattern in self.SECRET_PATTERNS:
            if re.match(pattern, name_lower):
                return True
        return False
    
    def mask(self, value: str, visible_chars: int = 4) -> str:
        """
        Mask a secret value for safe logging.
        
        Args:
            value: The secret value to mask
            visible_chars: Number of characters to show at the end
        
        Returns:
            Masked string like "****abcd"
        """
        if not value:
            return ""
        
        if len(value) <= visible_chars:
            return "*" * len(value)
        
        masked_length = len(value) - visible_chars
        return "*" * masked_length + value[-visible_chars:]
    
    def get_masked(self, name: str, default: Optional[str] = None) -> str:
        """
        Get a secret value in masked form (safe for logging).
        
        Args:
            name: Name of the secret
            default: Default value if not found
        
        Returns:
            Masked secret value
        """
        value = self.get(name, default)
        if value is None:
            return "<not set>"
        return self.mask(value)
    
    def clear_cache(self) -> None:
        """Clear the secrets cache (useful for testing or secret rotation)."""
        self._secrets_cache.clear()
    
    def reload(self, env_path: Optional[str] = None) -> bool:
        """
        Reload secrets from .env file (supports secret rotation).
        
        Args:
            env_path: Optional path to .env file
        
        Returns:
            True if reload was successful
        """
        self.clear_cache()
        return self._load_env_file(env_path)


# Global singleton instance
secrets_manager = SecretManager()


# Convenience functions
def get_secret(
    name: str,
    default: Optional[str] = None,
    required: bool = False
) -> Optional[str]:
    """
    Get a secret value from environment.
    
    Args:
        name: Name of the secret (environment variable name)
        default: Default value if secret is not set
        required: If True, raises ValueError when secret is missing
    
    Returns:
        The secret value, or default if not found
    
    Raises:
        ValueError: If required=True and secret is not found
    
    Example:
        api_key = get_secret("API_KEY", required=True)
        optional_key = get_secret("OPTIONAL_KEY", default="fallback")
    """
    return secrets_manager.get(name, default, required)


def require_secrets(names: List[str]) -> Dict[str, str]:
    """
    Validate that all required secrets exist at startup.
    
    Args:
        names: List of secret names to validate
    
    Returns:
        Dictionary of secret name -> value
    
    Raises:
        ValueError: If any required secret is missing
    
    Example:
        # At application startup
        require_secrets(["API_KEY", "JWT_SECRET", "DATABASE_URL"])
    """
    return secrets_manager.require(names)


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Mask a secret value for safe logging.
    
    Args:
        value: The secret value to mask
        visible_chars: Number of characters to show at end (default: 4)
    
    Returns:
        Masked string like "****abcd"
    
    Example:
        logger.info(f"Using API key: {mask_secret(api_key)}")
        # Output: "Using API key: ****xyz1"
    """
    return secrets_manager.mask(value, visible_chars)
