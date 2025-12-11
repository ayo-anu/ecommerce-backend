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
        # Future: Implement actual Vault HTTP GET here
        # For PR-A, we only prepare the interface
        logger.info(
            f"Vault integration enabled but not yet implemented. "
            f"Falling back to environment variable: {env_var_name}"
        )
        # In future PR: Add minimal HTTP GET to Vault
        # try:
        #     vault_addr = os.getenv('VAULT_ADDR')
        #     vault_token = os.getenv('VAULT_TOKEN')
        #     if vault_addr and vault_token:
        #         import requests
        #         response = requests.get(
        #             f"{vault_addr}/v1/{vault_path}",
        #             headers={'X-Vault-Token': vault_token},
        #             timeout=5
        #         )
        #         if response.ok:
        #             data = response.json()
        #             return data['data']['data'].get(vault_key)
        # except Exception as e:
        #     logger.warning(f"Vault fetch failed for {env_var_name}: {e}")

    # Fall back to environment variable (current behavior)
    env_value = os.getenv(env_var_name)
    if env_value is not None:
        return env_value

    # Return default if nothing else works
    return default


def vault_health_check() -> dict:
    """
    Check if Vault integration is enabled.

    Returns:
        dict: Basic health status

    Note:
        This is a placeholder for PR-A. Full health checks will be added
        when actual Vault HTTP integration is implemented.
    """
    use_vault = os.getenv('USE_VAULT', 'false').lower() in ('true', '1', 'yes')

    return {
        'enabled': use_vault,
        'implemented': False,  # Will be True when HTTP integration added
        'message': 'Vault interface prepared, full integration pending'
    }
