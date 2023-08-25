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
    Queue(name='rakuten_requests', routing_key='rakuten_requests', exchange=Exchange('rakuten_requests')),
    Queue(name='item_saving', routing_key='item_saving', exchange=Exchange('item_saving')),
    Queue(name='translating', routing_key='translating', exchange=Exchange('translating')),
)

BASE_DEFAULT_QUEUE_ROUTE = {'queue': 'default', 'routing_key': 'default'}
MAILING_QUEUE_ROUTE = {'queue': 'mailing', 'routing_key': 'mailing'}
RAKUTEN_REQUESTS_QUEUE_ROUTE = {'queue': 'rakuten_requests', 'routing_key': 'rakuten_requests'}
ITEM_SAVING_QUEUE_ROUTE = {'queue': 'item_saving', 'routing_key': 'item_saving'}
TRANSLATING_QUEUE_ROUTE = {'queue': 'translating', 'routing_key': 'translating'}

# bind routing with queues
app.conf.task_routes = {
    'users.tasks.*': MAILING_QUEUE_ROUTE,
    'rakuten_scraping.tasks.parse_and_save_genres': RAKUTEN_REQUESTS_QUEUE_ROUTE,
    'rakuten_scraping.tasks.parse_and_save_products': RAKUTEN_REQUESTS_QUEUE_ROUTE,
    'rakuten_scraping.tasks.save_genre_from_search': ITEM_SAVING_QUEUE_ROUTE,
    'rakuten_scraping.tasks.save_product_from_search': ITEM_SAVING_QUEUE_ROUTE,
    'rakuten_scraping.tasks.update_product_after_scrape': ITEM_SAVING_QUEUE_ROUTE,
    'rakuten_scraping.tasks.parse_products': BASE_DEFAULT_QUEUE_ROUTE,
    'product.tasks.translate_to_fields': TRANSLATING_QUEUE_ROUTE,
    'product.tasks.translate_genres': BASE_DEFAULT_QUEUE_ROUTE,
    'product.tasks.deactivate_empty_genres': BASE_DEFAULT_QUEUE_ROUTE,
}
