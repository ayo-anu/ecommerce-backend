

import logging


logger = logging.getLogger(__name__)



class PaymentDatabaseRouter:


    payment_apps = {'payments'}


    payment_related_models = {

        'orders': ['Order'],

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


    ai_apps = {'recommendations', 'search', 'analytics'}


    def db_for_read(self, model, **hints):

        if model._meta.app_label in self.ai_apps:

            return 'ai_services'

        return None


    def db_for_write(self, model, **hints):

        if model._meta.app_label in self.ai_apps:

            return 'ai_services'

        return None


    def allow_relation(self, obj1, obj2, **hints):

        if (obj1._meta.app_label in self.ai_apps and

            obj2._meta.app_label in self.ai_apps):

            return True

        return None


    def allow_migrate(self, db, app_label, model_name=None, **hints):

        if app_label in self.ai_apps:

            return db == 'ai_services'

        return db != 'ai_services'



class ReadReplicaRouter:


    def db_for_read(self, model, **hints):

        from django.conf import settings


        if model._meta.app_label == 'payments':

            return None


        if 'replica1' in settings.DATABASES:

            return 'replica1'


        return 'default'


    def db_for_write(self, model, **hints):

        if model._meta.app_label == 'payments':

            return None


        return 'default'


    def allow_relation(self, obj1, obj2, **hints):

        return True


    def allow_migrate(self, db, app_label, model_name=None, **hints):

        if app_label == 'payments':

            return None                                  


        return db == 'default'

