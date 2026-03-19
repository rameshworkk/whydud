"""Database router for replica -> primary write routing.

On the REPLICA node, reads go to the local postgres (default) and writes are
routed to the PRIMARY postgres via WireGuard (the 'write' database).

Only active when DATABASE_WRITE_URL is set in the environment.

Auth-critical models (accounts, auth, sessions, admin) always read from the
primary to avoid stale password hashes / sessions on the replica.
"""

# Apps whose reads MUST go to the primary database to avoid stale auth data.
# If the replica has replication lag, reading auth data locally causes login
# failures because the password hash or session may not have replicated yet.
_PRIMARY_READ_APPS = frozenset({
    "accounts",      # Custom User model
    "auth",          # Permissions, groups
    "sessions",      # Django sessions (cached_db backend)
    "admin",         # Admin log entries
    "account",       # allauth email addresses / verification
    "socialaccount", # allauth social accounts
})


class PrimaryReplicaRouter:

    def _primary_db(self):
        from django.conf import settings
        return "write" if "write" in settings.DATABASES else "default"

    def db_for_read(self, model, **hints):
        if model._meta.app_label in _PRIMARY_READ_APPS:
            return self._primary_db()
        return "default"

    def db_for_write(self, model, **hints):
        return self._primary_db()

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Migrations only run on the default (primary) database
        return db == "default"
