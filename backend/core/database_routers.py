"""
Database Routers for Multi-Database Configuration.

Implements payment data isolation by routing payment-related models
to a separate database for enhanced security and PCI compliance.
"""

import logging

logger = logging.getLogger(__name__)


class PaymentDatabaseRouter:
    """
    Router to isolate payment-related models to a separate database.

    This provides defense-in-depth for PCI DSS compliance by:
    1. Isolating payment data from other application data
    2. Enabling separate backup/retention policies
    3. Restricting access to payment data
    4. Facilitating separate database encryption

    Usage:
        Add to settings.py:
        DATABASE_ROUTERS = ['core.database_routers.PaymentDatabaseRouter']

        Configure separate database:
        DATABASES = {
            'default': {...},
            'payments': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'ecommerce_payments',
                ...
            }
        }
    """

    # Apps that contain payment-related models
    payment_apps = {'payments'}

    # Models that reference payments (allow cross-db relations)
    payment_related_models = {
        'orders': ['Order'],  # Orders reference payments
    }

    def db_for_read(self, model, **hints):
        """
        Direct reads of payment models to the payments database.

        Args:
            model: The model being read
            **hints: Additional routing hints

        Returns:
            str: Database alias ('payments') or None to defer to next router
        """
        if model._meta.app_label in self.payment_apps:
            logger.debug(
                f"Routing read for {model._meta.app_label}.{model._meta.model_name} "
                f"to 'payments' database"
            )
            return 'payments'
        return None

    def db_for_write(self, model, **hints):
        """
        Direct writes of payment models to the payments database.

        Args:
            model: The model being written
            **hints: Additional routing hints

        Returns:
            str: Database alias ('payments') or None to defer to next router
        """
        if model._meta.app_label in self.payment_apps:
            logger.debug(
                f"Routing write for {model._meta.app_label}.{model._meta.model_name} "
                f"to 'payments' database"
            )
            return 'payments'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations between payment models and selected other models.

        This allows Orders to reference Payments while maintaining isolation.

        Args:
            obj1: First model instance
            obj2: Second model instance
            **hints: Additional routing hints

        Returns:
            bool: True if relation is allowed, None to defer
        """
        # Allow relations within payment app
        if (obj1._meta.app_label in self.payment_apps and
            obj2._meta.app_label in self.payment_apps):
            return True

        # Allow relations between payments and orders
        app1 = obj1._meta.app_label
        app2 = obj2._meta.app_label
        model1 = obj1._meta.model_name
        model2 = obj2._meta.model_name

        if (app1 in self.payment_apps and
            app2 in self.payment_related_models and
            model2.capitalize() in self.payment_related_models.get(app2, [])):
            return True

        if (app2 in self.payment_apps and
            app1 in self.payment_related_models and
            model1.capitalize() in self.payment_related_models.get(app1, [])):
            return True

        # Defer to other routers
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure payment app only migrates to the payments database.

        Args:
            db: Database alias
            app_label: App label being migrated
            model_name: Model name being migrated (optional)
            **hints: Additional migration hints

        Returns:
            bool: True if migration is allowed, False if not
        """
        if app_label in self.payment_apps:
            # Payment models only migrate to 'payments' database
            return db == 'payments'

        # Non-payment models should not migrate to payments database
        return db != 'payments'


class AIServicesDatabaseRouter:
    """
    Router to isolate AI-related data to a separate database.

    This keeps AI service data (vectors, embeddings, training data)
    separate from transactional data for:
    1. Performance isolation
    2. Different backup strategies
    3. Separate scaling
    """

    ai_apps = {'recommendations', 'search', 'analytics'}

    def db_for_read(self, model, **hints):
        """Route AI model reads to AI database."""
        if model._meta.app_label in self.ai_apps:
            return 'ai_services'
        return None

    def db_for_write(self, model, **hints):
        """Route AI model writes to AI database."""
        if model._meta.app_label in self.ai_apps:
            return 'ai_services'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations within AI apps."""
        if (obj1._meta.app_label in self.ai_apps and
            obj2._meta.app_label in self.ai_apps):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure AI apps only migrate to AI database."""
        if app_label in self.ai_apps:
            return db == 'ai_services'
        return db != 'ai_services'


class ReadReplicaRouter:
    """
    Router for read/write splitting with read replicas.

    Directs read queries to read replicas and writes to primary database.

    Configuration:
        DATABASES = {
            'default': {...},  # Primary (write)
            'replica1': {...},  # Read replica
        }

        DATABASE_ROUTERS = ['core.database_routers.ReadReplicaRouter']
    """

    def db_for_read(self, model, **hints):
        """
        Direct read queries to read replica.

        In development, falls back to default if replica not configured.
        """
        from django.conf import settings

        # Skip for payment models (handled by PaymentDatabaseRouter)
        if model._meta.app_label == 'payments':
            return None

        # Use replica if configured
        if 'replica1' in settings.DATABASES:
            return 'replica1'

        return 'default'

    def db_for_write(self, model, **hints):
        """All writes go to primary database."""
        # Skip for payment models
        if model._meta.app_label == 'payments':
            return None

        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow all relations (same data, different instances)."""
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Only migrate on primary database."""
        if app_label == 'payments':
            return None  # Defer to PaymentDatabaseRouter

        return db == 'default'
