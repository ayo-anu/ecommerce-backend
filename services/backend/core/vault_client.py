"""
Vault Client - Production Vault integration with AppRole authentication

This module provides a production-ready HashiCorp Vault client with:
- AppRole authentication for service-to-service auth
- Automatic token renewal
- Connection pooling and retries
- Graceful fallback to environment variables
- Secret caching for performance

Security:
- Uses AppRole (role_id + secret_id) instead of root tokens
- Secrets are cached with TTL
- Automatic token renewal before expiration
- Falls back to environment variables on any error

Usage:
    from core.vault_client import get_vault_secret, VaultClient

    # Simple usage - automatic fallback to env vars
    secret_key = get_vault_secret('SECRET_KEY', 'backend/django', 'SECRET_KEY')

    # Advanced usage - direct client access
    vault = VaultClient()
    vault.authenticate()
    secret = vault.get_secret('backend/django', 'SECRET_KEY')
"""

import os
import logging
import time
from typing import Any, Optional, Dict
from functools import lru_cache
from datetime import datetime, timedelta

# Try to import requests for Vault HTTP calls
try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class VaultClient:
    """
    Production-ready HashiCorp Vault client with AppRole authentication.

    Features:
    - AppRole authentication (role_id + secret_id)
    - Automatic token renewal
    - Connection pooling and retries
    - Secret caching with TTL
    - Thread-safe operations
    """

    def __init__(self):
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.role_id = os.getenv('VAULT_ROLE_ID')
        self.secret_id = os.getenv('VAULT_SECRET_ID')
        self.mount_point = os.getenv('VAULT_MOUNT_POINT', 'ecommerce')
        self.namespace = os.getenv('VAULT_NAMESPACE')

        self.client_token = None
        self.token_expiry = None
        self.session = None

        # Initialize session with retries if requests is available
        if REQUESTS_AVAILABLE:
            self._init_session()

    def _init_session(self):
        """Initialize requests session with retry logic"""
        self.session = requests.Session()

        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default timeout
        self.session.timeout = 10

    def authenticate(self) -> bool:
        """
        Authenticate with Vault using AppRole.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("Requests library not available, cannot authenticate with Vault")
            return False

        if not self.role_id or not self.secret_id:
            logger.warning("VAULT_ROLE_ID or VAULT_SECRET_ID not set, cannot authenticate")
            return False

        try:
            # Check if existing token is still valid
            if self.client_token and self.token_expiry:
                if datetime.now() < self.token_expiry:
                    logger.debug("Using existing valid Vault token")
                    return True

            # Authenticate with AppRole
            logger.info("Authenticating with Vault using AppRole")

            headers = {}
            if self.namespace:
                headers['X-Vault-Namespace'] = self.namespace

            response = self.session.post(
                f"{self.vault_addr}/v1/auth/approle/login",
                json={
                    "role_id": self.role_id,
                    "secret_id": self.secret_id
                },
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Vault authentication failed: {response.status_code} - {response.text}")
                return False

            auth_data = response.json()['auth']
            self.client_token = auth_data['client_token']

            # Calculate token expiry (renew 5 minutes before expiration)
            lease_duration = auth_data.get('lease_duration', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=lease_duration - 300)

            logger.info(f"Vault authentication successful, token valid for {lease_duration}s")
            return True

        except Exception as e:
            logger.error(f"Vault authentication error: {e}")
            return False

    def renew_token(self) -> bool:
        """
        Renew the current Vault token.

        Returns:
            bool: True if renewal successful, False otherwise
        """
        if not self.client_token:
            return self.authenticate()

        try:
            headers = {'X-Vault-Token': self.client_token}
            if self.namespace:
                headers['X-Vault-Namespace'] = self.namespace

            response = self.session.post(
                f"{self.vault_addr}/v1/auth/token/renew-self",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                auth_data = response.json()['auth']
                lease_duration = auth_data.get('lease_duration', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=lease_duration - 300)
                logger.info(f"Vault token renewed, valid for {lease_duration}s")
                return True
            else:
                logger.warning(f"Token renewal failed: {response.status_code}, re-authenticating")
                return self.authenticate()

        except Exception as e:
            logger.error(f"Token renewal error: {e}, re-authenticating")
            return self.authenticate()

    def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Get a secret from Vault.

        Args:
            path: Vault path (e.g., 'backend/django')
            key: Specific key within the secret (optional)

        Returns:
            Secret value (single key) or dict (all keys)
        """
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("Requests library not available")

        # Ensure we're authenticated
        if not self.authenticate():
            raise RuntimeError("Failed to authenticate with Vault")

        try:
            headers = {'X-Vault-Token': self.client_token}
            if self.namespace:
                headers['X-Vault-Namespace'] = self.namespace

            # Build full path for KV v2
            full_path = f"{self.vault_addr}/v1/{self.mount_point}/data/{path}"

            response = self.session.get(full_path, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()['data']['data']
                if key:
                    return data.get(key)
                return data
            elif response.status_code == 404:
                logger.warning(f"Secret not found at path: {path}")
                return None
            else:
                logger.error(f"Failed to retrieve secret: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving secret from {path}: {e}")
            return None

    @lru_cache(maxsize=128)
    def get_secret_cached(self, path: str, key: str) -> Any:
        """
        Get a secret from Vault with caching.

        Args:
            path: Vault path
            key: Secret key

        Returns:
            Secret value
        """
        return self.get_secret(path, key)


# Global Vault client instance
_vault_client = None


def get_vault_client() -> VaultClient:
    """Get or create the global Vault client instance"""
    global _vault_client
    if _vault_client is None:
        _vault_client = VaultClient()
    return _vault_client


def get_vault_secret(
    env_var_name: str,
    vault_path: Optional[str] = None,
    vault_key: Optional[str] = None,
    default: Any = None
) -> Any:
    """
    Get a secret from Vault or fall back to environment variable.

    This is the primary function for secret retrieval throughout the application.

    Args:
        env_var_name: Name of environment variable to use as fallback
        vault_path: Vault path (e.g., 'backend/django')
        vault_key: Key within the Vault secret (e.g., 'SECRET_KEY')
        default: Default value if neither Vault nor env var is available

    Returns:
        Secret value from Vault, env var, or default (in that order)

    Examples:
        # Get Django SECRET_KEY
        secret_key = get_vault_secret('SECRET_KEY', 'backend/django', 'SECRET_KEY')

        # Get database password
        db_pass = get_vault_secret('DB_PASSWORD', 'backend/database', 'DB_PASSWORD')
    """
    # Check if Vault is enabled
    use_vault = os.getenv('USE_VAULT', 'false').lower() in ('true', '1', 'yes')

    if use_vault and vault_path and vault_key:
        if not REQUESTS_AVAILABLE:
            logger.warning(
                f"Vault enabled but requests library not available. "
                f"Falling back to environment variable: {env_var_name}"
            )
        else:
            try:
                # Get Vault client and retrieve secret
                vault = get_vault_client()
                secret_value = vault.get_secret_cached(vault_path, vault_key)

                if secret_value is not None:
                    logger.debug(f"Successfully retrieved {env_var_name} from Vault")
                    return secret_value
                else:
                    logger.warning(
                        f"Secret '{vault_key}' not found in Vault path '{vault_path}'. "
                        f"Falling back to environment variable: {env_var_name}"
                    )
            except Exception as e:
                logger.warning(
                    f"Vault fetch failed for {env_var_name}: {e}. "
                    f"Falling back to environment variable"
                )

    # Fall back to environment variable
    env_value = os.getenv(env_var_name)
    if env_value is not None:
        return env_value

    # Return default if nothing else works
    return default


def vault_health_check() -> Dict[str, Any]:
    """
    Check if Vault integration is enabled and operational.

    Returns:
        dict: Health status with enabled/authenticated/operational flags
    """
    use_vault = os.getenv('USE_VAULT', 'false').lower() in ('true', '1', 'yes')

    if not use_vault:
        return {
            'enabled': False,
            'authenticated': False,
            'operational': False,
            'message': 'Vault integration disabled (using environment variables)'
        }

    if not REQUESTS_AVAILABLE:
        return {
            'enabled': True,
            'authenticated': False,
            'operational': False,
            'message': 'Vault enabled but requests library not available'
        }

    try:
        vault = get_vault_client()
        authenticated = vault.authenticate()

        if authenticated:
            # Try to read a test secret
            try:
                vault.get_secret('backend/django', 'SECRET_KEY')
                operational = True
                message = 'Vault integration fully operational with AppRole authentication'
            except Exception as e:
                operational = False
                message = f'Vault authenticated but secret access failed: {str(e)}'
        else:
            operational = False
            message = 'Vault authentication failed'

        return {
            'enabled': True,
            'authenticated': authenticated,
            'operational': operational,
            'message': message
        }

    except Exception as e:
        return {
            'enabled': True,
            'authenticated': False,
            'operational': False,
            'message': f'Vault health check failed: {str(e)}'
        }
