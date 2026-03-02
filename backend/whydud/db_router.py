"""Database router for replica -> primary write routing.

On the REPLICA node, reads go to the local postgres (default) and writes are
routed to the PRIMARY postgres via WireGuard (the 'write' database).

Only active when DATABASE_WRITE_URL is set in the environment.
"""


class PrimaryReplicaRouter:

    def db_for_read(self, model, **hints):
        return "default"

    def db_for_write(self, model, **hints):
        from django.conf import settings
        if "write" in settings.DATABASES:
            return "write"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Migrations only run on the default (primary) database
        return db == "default"
