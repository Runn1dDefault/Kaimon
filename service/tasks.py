import logging

from django.conf import settings

from kaimon.celery import app
from service.enums import Spider

from scrapyd_api import ScrapydAPI


scrapyd = ScrapydAPI(settings.CRAWLER_URL)


@app.task()
def start_spider(spider_name: str = None):
    if spider_name is None:
        for spider in Spider:
            logging.info(f'Launch scraping {spider.value}...')
            scrapyd.schedule('default', spider.value)
        return

    spider_names = (i.value for i in Spider)
    if spider_name.lower() not in spider_names:
        raise ValueError('Spider %s not supported!'.format(spider_name))

    logging.info(f'Launch scraping {spider_name}...')
    scrapyd.schedule('default', spider_name.lower())
