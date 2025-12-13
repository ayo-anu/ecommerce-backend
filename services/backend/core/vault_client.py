"""
Vault Client - Minimal Vault integration for secrets management

This module provides a lightweight helper for optional Vault integration.
It is completely optional and controlled by the USE_VAULT environment variable.

When USE_VAULT=false (default), the application uses environment variables.
When USE_VAULT=true, secrets can be fetched from Vault.

Security:
- No secrets or credentials are hardcoded
- Only activates when USE_VAULT=true
- Falls back to environment variables on any error

Usage:
    from core.vault_client import get_vault_secret

    # Returns from Vault if USE_VAULT=true, else from environment
    secret_key = get_vault_secret('SECRET_KEY', default='fallback-value')
"""

import os
import logging
from typing import Any, Optional

# Try to import requests for Vault HTTP calls
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_vault_secret(
    env_var_name: str,
    vault_path: Optional[str] = None,
    vault_key: Optional[str] = None,
    default: Any = None
) -> Any:
    """
    Get a secret from Vault or fall back to environment variable.

    This is the primary function for secret retrieval throughout the application.
    By default (USE_VAULT=false), this simply returns the environment variable.

    Args:
        env_var_name: Name of environment variable to use as fallback
        vault_path: Vault path (e.g., 'secret/data/django') - currently unused
        vault_key: Key within the Vault secret (e.g., 'SECRET_KEY') - currently unused
        default: Default value if neither Vault nor env var is available

    Returns:
        Secret value from Vault, env var, or default (in that order)

    Note:
        This is a minimal implementation for PR-A. Full Vault integration
        (with actual HTTP calls to Vault) will be added in a future PR.
        For now, this provides the interface and graceful fallback behavior.

    Examples:
        # Get Django SECRET_KEY (currently from env, future: from Vault)
        secret_key = get_vault_secret('SECRET_KEY', 'secret/data/django', 'SECRET_KEY')

        # Get database password
        db_pass = get_vault_secret('DB_PASSWORD', 'secret/data/postgres', 'password')
    """
    # Check if Vault is enabled
    use_vault = os.getenv('USE_VAULT', 'false').lower() in ('true', '1', 'yes')

    if use_vault and vault_path and vault_key:
        # Attempt to fetch from Vault if requests is available
        if not REQUESTS_AVAILABLE:
            logger.warning(
                f"Vault enabled but requests library not available. "
                f"Falling back to environment variable: {env_var_name}"
            )
        else:
            vault_addr = os.getenv('VAULT_ADDR')
            vault_token = os.getenv('VAULT_TOKEN')

            if vault_addr and vault_token:
                try:
                    # Build headers
                    headers = {'X-Vault-Token': vault_token}
                    vault_namespace = os.getenv('VAULT_NAMESPACE')
                    if vault_namespace:
                        headers['X-Vault-Namespace'] = vault_namespace

                    # Perform HTTP GET to Vault
                    response = requests.get(
                        f"{vault_addr}/v1/{vault_path}",
                        headers=headers,
                        timeout=5
                    )

                    # On success, extract and return the secret
                    if response.status_code == 200:
                        data = response.json()
                        secret_value = data['data']['data'].get(vault_key)
                        if secret_value is not None:
                            logger.info(f"Successfully retrieved {env_var_name} from Vault")
                            return secret_value
                        else:
                            logger.warning(
                                f"Key '{vault_key}' not found in Vault path '{vault_path}'. "
                                f"Falling back to environment variable: {env_var_name}"
                            )
                    else:
                        logger.warning(
                            f"Vault returned status {response.status_code} for {env_var_name}. "
                            f"Falling back to environment variable"
                        )
                except Exception as e:
                    logger.warning(f"Vault fetch failed for {env_var_name}: {e}. Falling back to environment variable")
            else:
                logger.warning(
                    f"Vault enabled but VAULT_ADDR or VAULT_TOKEN not set. "
                    f"Falling back to environment variable: {env_var_name}"
                )

    # Fall back to environment variable (current behavior)
    env_value = os.getenv(env_var_name)
    if env_value is not None:
        return env_value

    # Return default if nothing else works
    return default


def vault_health_check() -> dict:
    """
    Check if Vault integration is enabled and operational.

    Returns:
        dict: Health status with enabled/implemented flags

    Note:
        Returns 'implemented': True when USE_VAULT=true and requests library
        is available, indicating full HTTP GET capability is active.
    """
    use_vault = os.getenv('USE_VAULT', 'false').lower() in ('true', '1', 'yes')
    is_implemented = use_vault and REQUESTS_AVAILABLE

    if is_implemented:
        message = 'Vault HTTP GET integration active (read-only)'
    elif use_vault and not REQUESTS_AVAILABLE:
        message = 'Vault enabled but requests library not available'
    else:
        message = 'Vault integration disabled (using environment variables)'

    return {
        'enabled': use_vault,
        'implemented': is_implemented,
        'message': message
    }
