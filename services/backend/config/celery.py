import os

from celery import Celery

from celery.schedules import crontab

from decouple import config


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


app = Celery('ecommerce')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


app.conf.beat_schedule = {

    'update-daily-sales': {

        'task': 'apps.analytics.tasks.update_daily_sales',

        'schedule': crontab(hour=1, minute=0),

    },

    'update-product-analytics': {

        'task': 'apps.analytics.tasks.update_product_analytics',

        'schedule': crontab(hour=2, minute=0),

    },

    'cleanup-abandoned-carts': {

        'task': 'apps.orders.tasks.cleanup_abandoned_carts',

        'schedule': crontab(hour=3, minute=0),

    },

    'cleanup-old-notifications': {

        'task': 'apps.notifications.tasks.cleanup_old_notifications',

        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),

    },

    'check-low-stock': {

        'task': 'apps.products.tasks.check_low_stock',

        'schedule': crontab(hour='*/6'),

    },

}


app.conf.update(

    task_serializer='json',

    accept_content=['json'],

    result_serializer='json',

    timezone='UTC',

    enable_utc=True,

    task_track_started=True,

    task_time_limit=30 * 60,

    worker_prefetch_multiplier=4,

    worker_max_tasks_per_child=1000,

)

