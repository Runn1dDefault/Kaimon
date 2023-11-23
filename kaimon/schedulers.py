import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, DatabaseError, router, close_old_connections
from django_celery_beat.schedulers import DatabaseScheduler


class MyDatabaseScheduler(DatabaseScheduler):
    def sync(self):
        logging.info('Writing entries...')
        _tried = set()
        db = router.db_for_write(self.Model)
        try:
            close_old_connections()
            with transaction.atomic(using=db):
                while self._dirty:
                    try:
                        name = self._dirty.pop()
                        _tried.add(name)
                        self.schedule[name].save()
                    except (KeyError, ObjectDoesNotExist):
                        pass
        except DatabaseError as exc:
            # retry later
            self._dirty |= _tried
            logging.exception('Database error while sync: %r', exc)

    def schedule_changed(self):
        try:
            # If MySQL is running with transaction isolation level
            # REPEATABLE-READ (default), then we won't see changes done by
            # other transactions until the current transaction is
            # committed (Issue #41).
            db = router.db_for_write(self.Model)
            try:
                transaction.commit(using=db)
            except transaction.TransactionManagementError:
                pass  # not in transaction management.

            last, ts = self._last_timestamp, self.Changes.last_change()
        except DatabaseError as exc:
            logging.exception('Database gave error: %r', exc)
            return False
        try:
            if ts and ts > (last if last else ts):
                return True
        finally:
            self._last_timestamp = ts
        return False
