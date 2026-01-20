

import os

from datetime import timedelta

from kombu import Exchange, Queue

from celery.schedules import crontab







broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')



result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')



broker_connection_retry_on_startup = True

broker_connection_retry = True

broker_connection_max_retries = 10









worker_concurrency = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))






worker_prefetch_multiplier = int(os.getenv('CELERY_WORKER_PREFETCH_MULTIPLIER', '4'))




worker_pool = os.getenv('CELERY_WORKER_POOL', 'prefork')




worker_max_tasks_per_child = int(os.getenv('CELERY_WORKER_MAX_TASKS_PER_CHILD', '1000'))




worker_max_memory_per_child = int(os.getenv('CELERY_WORKER_MAX_MEMORY_PER_CHILD', str(200 * 1024)))          





worker_autoscaler = os.getenv('CELERY_WORKER_AUTOSCALER')                








task_time_limit = int(os.getenv('CELERY_TASK_TIME_LIMIT', str(30 * 60)))              



task_soft_time_limit = int(os.getenv('CELERY_TASK_SOFT_TIME_LIMIT', str(25 * 60)))              





task_acks_late = True                                               

task_reject_on_worker_lost = True                                  




result_expires = int(os.getenv('CELERY_RESULT_EXPIRES', str(24 * 3600)))            




task_ignore_result = False



result_compression = 'gzip'

result_extended = True







task_autoretry_for = (Exception,)                          

task_retry_backoff = True                           

task_retry_backoff_max = 600                                      

task_retry_jitter = True                                                



task_max_retries = int(os.getenv('CELERY_TASK_MAX_RETRIES', '3'))







default_exchange = Exchange('default', type='direct')

priority_exchange = Exchange('priority', type='direct')



task_queues = (


    Queue(

        'high_priority',

        exchange=priority_exchange,

        routing_key='high_priority',

        queue_arguments={'x-max-priority': 10}

    ),



    Queue(

        'default',

        exchange=default_exchange,

        routing_key='default',

        queue_arguments={'x-max-priority': 5}

    ),



    Queue(

        'low_priority',

        exchange=default_exchange,

        routing_key='low_priority',

        queue_arguments={'x-max-priority': 1}

    ),



    Queue(

        'email',

        exchange=default_exchange,

        routing_key='email',

        queue_arguments={'x-max-priority': 3}

    ),



    Queue(

        'ai_processing',

        exchange=default_exchange,

        routing_key='ai_processing',

        queue_arguments={'x-max-priority': 5}

    ),



    Queue(

        'reports',

        exchange=default_exchange,

        routing_key='reports',

        queue_arguments={'x-max-priority': 2}

    ),

)



task_default_queue = 'default'

task_default_exchange = 'default'

task_default_routing_key = 'default'



task_routes = {


    'apps.orders.tasks.process_payment': {'queue': 'high_priority', 'priority': 10},

    'apps.orders.tasks.send_order_confirmation': {'queue': 'high_priority', 'priority': 9},



    'apps.notifications.tasks.*': {'queue': 'email', 'priority': 5},



    'apps.products.tasks.generate_recommendations': {'queue': 'ai_processing', 'priority': 5},

    'apps.products.tasks.analyze_product_images': {'queue': 'ai_processing', 'priority': 4},



    'apps.analytics.tasks.generate_sales_report': {'queue': 'reports', 'priority': 2},

    'apps.analytics.tasks.export_data': {'queue': 'reports', 'priority': 1},



    'apps.products.tasks.update_search_index': {'queue': 'low_priority', 'priority': 1},

    'apps.products.tasks.cleanup_old_data': {'queue': 'low_priority', 'priority': 1},

}






beat_schedule = {


    'cleanup-expired-sessions': {

        'task': 'apps.users.tasks.cleanup_expired_sessions',

        'schedule': crontab(minute=0),

        'options': {'queue': 'low_priority'}

    },



    'daily-sales-report': {

        'task': 'apps.analytics.tasks.generate_daily_sales_report',

        'schedule': crontab(hour=2, minute=0),

        'options': {'queue': 'reports'}

    },



    'update-product-recommendations': {

        'task': 'apps.products.tasks.update_product_recommendations',

        'schedule': timedelta(minutes=15),

        'options': {'queue': 'ai_processing'}

    },



    'process-pending-notifications': {

        'task': 'apps.notifications.tasks.process_pending_notifications',

        'schedule': timedelta(minutes=5),

        'options': {'queue': 'email'}

    },



    'cleanup-old-logs': {

        'task': 'apps.core.tasks.cleanup_old_logs',

        'schedule': crontab(hour=3, minute=0),

        'options': {'queue': 'low_priority'}

    },



    'weekly-analytics-report': {

        'task': 'apps.analytics.tasks.generate_weekly_report',

        'schedule': crontab(hour=1, minute=0, day_of_week=1),

        'options': {'queue': 'reports'}

    },

}



timezone = 'UTC'

enable_utc = True







task_serializer = 'json'

accept_content = ['json']

result_serializer = 'json'



task_always_eager = False                                      







worker_send_task_events = True

task_send_sent_event = True



task_track_started = True



task_store_eager_result = False







task_default_rate_limit = None



broker_pool_limit = int(os.getenv('CELERY_BROKER_POOL_LIMIT', '10'))

broker_heartbeat = 30

broker_heartbeat_checkrate = 2



result_backend_transport_options = {

    'master_name': os.getenv('REDIS_SENTINEL_MASTER', 'mymaster'),

}



redis_backend_health_check_interval = 30

redis_socket_keepalive = True

redis_socket_timeout = 5.0







task_annotations = {


    'apps.orders.tasks.process_payment': {

        'rate_limit': '100/m',

        'time_limit': 300,

        'soft_time_limit': 240,

        'max_retries': 5,

    },

    'apps.analytics.tasks.generate_sales_report': {

        'time_limit': 3600,

        'soft_time_limit': 3300,

        'max_retries': 1,

    },

}






if os.getenv('DJANGO_ENV') == 'development':


    task_always_eager = False                                  

    task_eager_propagates = True

    worker_concurrency = 2

    worker_prefetch_multiplier = 1






def configure_celery(app):

    app.config_from_object(__name__)


    app.autodiscover_tasks()


    return app







class BaseTask:


    autoretry_for = (Exception,)

    retry_kwargs = {'max_retries': 3}

    retry_backoff = True

    retry_backoff_max = 600

    retry_jitter = True



class CriticalTask(BaseTask):


    queue = 'high_priority'

    priority = 10

    max_retries = 5

    time_limit = 600              

    soft_time_limit = 540             



class BackgroundTask(BaseTask):


    queue = 'low_priority'

    priority = 1

    ignore_result = True

    time_limit = 3600          

    soft_time_limit = 3300              

