from __future__ import absolute_import
import os

from celery import Celery
from kombu import Exchange, Queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kaimon.settings')

app = Celery('kaimon')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_exchange_type = 'default'
app.conf.task_default_routing_key = 'default'

app.conf.task_queues = (
    Queue(name='default', routing_key='default', exchange=Exchange('default')),
    Queue(name='mailing', routing_key='mailing', exchange=Exchange('mailing')),
)

DEFAULT_QUEUE_ROUTE = {'queue': 'default', 'routing_key': 'default'}
MAILING_QUEUE_ROUTE = {'queue': 'mailing', 'routing_key': 'mailing'}

# bind routing with queues
app.conf.task_routes = {
    'users.tasks.send_mail_template': MAILING_QUEUE_ROUTE,
    'users.tasks.send_code_template': MAILING_QUEUE_ROUTE,
    'users.tasks.send_notification_template': MAILING_QUEUE_ROUTE,
    'products.tasks.*': DEFAULT_QUEUE_ROUTE,
    'orders.tasks.*': DEFAULT_QUEUE_ROUTE,
    'service.tasks.*': DEFAULT_QUEUE_ROUTE,
}
