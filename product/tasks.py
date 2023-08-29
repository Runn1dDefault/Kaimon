import time
from typing import Iterable

from django.conf import settings
from django.db.models import Count, Q
from libretranslatepy import LibreTranslateAPI

from kaimon.celery import app
from utils.helpers import import_model

from .models import Genre
from .utils import get_last_children


@app.task()
def translate_to_fields(instance_id: int, model_path: str, fields: Iterable[str], languages: Iterable[str] = ()):
    model = import_model(model_path)
    instance = model.objects.get(id=instance_id)
    translator = LibreTranslateAPI("https://translate.argosopentech.com/")
    save = False

    for field in fields:
        for lang, to_lang in settings.TRANSLATE_LANGUAGES.items():
            if languages and lang not in languages:
                continue

            field_name = f'{field}_{lang}'
            if not hasattr(instance, field) or not hasattr(instance, field_name):
                print('Not found field to saving translated value %s or %s' % (field, field_name))
                continue

            time.sleep(settings.TRANSLATE_DELAY)  # waiting will increase the chances of success
            to_translate = getattr(instance, field)
            try:
                translator.translate(to_translate, source='ja', target=to_lang)
                translated = translator.translate(to_translate)
            except Exception as e:
                print(str(e))
            else:
                setattr(instance, field_name, translated)
                save = True
                time.sleep(0.1)

    if save:
        instance.save()


@app.task()
def translate_genres(genre_ids: Iterable[int] = None):
    genres = Genre.objects.all() if not genre_ids else Genre.objects.filter(id__in=genre_ids)

    for genre in genres:
        translate_to_fields.delay(genre.id, settings.GENRE_MODEL_PATH, settings.GENRE_TRANSLATE_FIELDS)

        if genre.children.exists():
            child_ids = list(genre.children.values_list('child__id', flat=True))
            translate_genres.delay(child_ids)


@app.task()
def deactivate_empty_genres():
    base_genres = Genre.objects.filter(level=1)
    to_full_deactivate = []

    for base_genre in base_genres:
        last_children_ids = get_last_children(base_genre)
        to_deactivate_genres = Genre.objects.filter(id__in=last_children_ids).annotate(
            products_qty=Count('products', filter=Q(products__is_active=True))
        ).filter(products_qty=0)

        deactivated_rows = to_deactivate_genres.update(deactivated=True)
        if len(deactivated_rows) == last_children_ids:
            base_genre.deactivated = True
            to_full_deactivate.append(base_genre)

    if to_full_deactivate:
        Genre.objects.bulk_update(to_full_deactivate, ('deactivated',))
