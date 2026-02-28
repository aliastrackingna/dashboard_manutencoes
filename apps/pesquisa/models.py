from django.db import models


class ItensFTS(models.Model):
    """Proxy model for raw SQL FTS5 queries. Not managed by Django migrations."""
    class Meta:
        managed = False
        db_table = 'itens_fts'
