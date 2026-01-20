

import os

import logging

import time

from typing import Any, Optional, Dict

from functools import lru_cache

from datetime import datetime, timedelta


try:

    import requests

    from requests.adapters import HTTPAdapter

    from requests.packages.urllib3.util.retry import Retry

    REQUESTS_AVAILABLE = True

except ImportError:

    REQUESTS_AVAILABLE = False


logger = logging.getLogger(__name__)



class VaultClient:


    def __init__(self):

        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')

        self.role_id = os.getenv('VAULT_ROLE_ID')

        self.secret_id = os.getenv('VAULT_SECRET_ID')

        self.mount_point = os.getenv('VAULT_MOUNT_POINT', 'ecommerce')

        self.namespace = os.getenv('VAULT_NAMESPACE')


        self.client_token = None

        self.token_expiry = None

        self.session = None


        if REQUESTS_AVAILABLE:

            self._init_session()


    def _init_session(self):

        self.session = requests.Session()


        retry_strategy = Retry(

            total=3,

            backoff_factor=1,

            status_forcelist=[429, 500, 502, 503, 504],

            allowed_methods=["GET", "POST"]

        )


        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)

        self.session.mount("http://", adapter)

        self.session.mount("https://", adapter)


        self.session.timeout = 10


    def authenticate(self) -> bool:

        if not REQUESTS_AVAILABLE:

            logger.warning("Requests library not available, cannot authenticate with Vault")

            return False


        if not self.role_id or not self.secret_id:

            logger.warning("VAULT_ROLE_ID or VAULT_SECRET_ID not set, cannot authenticate")

            return False


        try:

            if self.client_token and self.token_expiry:

                if datetime.now() < self.token_expiry:

                    logger.debug("Using existing valid Vault token")

                    return True


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


            lease_duration = auth_data.get('lease_duration', 3600)

            self.token_expiry = datetime.now() + timedelta(seconds=lease_duration - 300)


            logger.info(f"Vault authentication successful, token valid for {lease_duration}s")

            return True


        except Exception as e:

            logger.error(f"Vault authentication error: {e}")

            return False


    def renew_token(self) -> bool:

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

        if not REQUESTS_AVAILABLE:

            raise RuntimeError("Requests library not available")


        if not self.authenticate():

            raise RuntimeError("Failed to authenticate with Vault")


        try:

            headers = {'X-Vault-Token': self.client_token}

            if self.namespace:

                headers['X-Vault-Namespace'] = self.namespace


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

        return self.get_secret(path, key)



_vault_client = None



def get_vault_client() -> VaultClient:

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

    use_vault = os.getenv('USE_VAULT', 'false').lower() in ('true', '1', 'yes')


    if use_vault and vault_path and vault_key:

        if not REQUESTS_AVAILABLE:

            logger.warning(

                f"Vault enabled but requests library not available. "

                f"Falling back to environment variable: {env_var_name}"

            )

        else:

            try:

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


    env_value = os.getenv(env_var_name)

    if env_value is not None:

        return env_value


    return default



def vault_health_check() -> Dict[str, Any]:

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

