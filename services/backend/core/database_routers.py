"""Database routing for isolated storage."""

import logging

logger = logging.getLogger(__name__)


class PaymentDatabaseRouter:
    """Route payment models to the payments database."""

    payment_apps = {'payments'}

    payment_related_models = {
        'orders': ['Order'],  # Orders reference payments
    }

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.payment_apps:
            logger.debug(
                f"Routing read for {model._meta.app_label}.{model._meta.model_name} "
                f"to 'payments' database"
            )
            return 'payments'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.payment_apps:
            logger.debug(
                f"Routing write for {model._meta.app_label}.{model._meta.model_name} "
                f"to 'payments' database"
            )
            return 'payments'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (obj1._meta.app_label in self.payment_apps and
            obj2._meta.app_label in self.payment_apps):
            return True

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

        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.payment_apps:
            return db == 'payments'

        return db != 'payments'


class AIServicesDatabaseRouter:
    """Route AI-related models to the ai_services database."""

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
    """Read/write splitting with optional replicas."""

    def db_for_read(self, model, **hints):
        from django.conf import settings

        if model._meta.app_label == 'payments':
            return None

        if 'replica1' in settings.DATABASES:
            return 'replica1'

        return 'default'

    def db_for_write(self, model, **hints):
        """All writes go to primary database."""
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
