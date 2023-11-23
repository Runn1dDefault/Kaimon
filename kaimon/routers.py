import random


class PrimaryReplicaRouter:
    primary = "default"
    replicates = ("replica1", "replica2")

    def db_for_read(self, model, **hints):
        """
        Reads go to a randomly-chosen replica.
        """
        return random.choice(self.replicates)

    def db_for_write(self, model, **hints):
        """
        Writes always go to primary.
        """
        return self.primary

    def allow_relation(self, obj1, obj2, **hints):
        """
        Relations between objects are allowed if both objects are
        in the primary/replica pool.
        """
        db_set = (self.primary, *self.replicates)
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True
