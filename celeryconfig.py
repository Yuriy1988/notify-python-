from celery.schedules import crontab

BROKER_URL = 'amqp://guest:guest@localhost:5672//'  # RabbitMQ URL
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

CELERYBEAT_SCHEDULE = {
    'update_currencyes': {
        'task': 'tasks.currency_update',
        'schedule': crontab(minute=0, hour='0,6,12,18'),
    },
}
