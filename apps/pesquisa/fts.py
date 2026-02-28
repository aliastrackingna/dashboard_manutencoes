from django.db import connection


def criar_tabela_fts():
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='itens_fts'")
        if cursor.fetchone():
            return

        # FTS5 content table vinculada à tabela real
        cursor.execute("""
            CREATE VIRTUAL TABLE itens_fts USING fts5(
                descricao,
                marca,
                codigo_item,
                grupo,
                tipo UNINDEXED,
                content='manutencoes_itemorcamento',
                content_rowid='id'
            )
        """)

        # Triggers de sincronização automática
        cursor.execute("""
            CREATE TRIGGER itens_fts_ai AFTER INSERT ON manutencoes_itemorcamento BEGIN
                INSERT INTO itens_fts(rowid, descricao, marca, grupo, tipo, codigo_item)
                VALUES (new.id, new.descricao, new.marca, new.grupo, new.tipo, new.codigo_item);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER itens_fts_ad AFTER DELETE ON manutencoes_itemorcamento BEGIN
                INSERT INTO itens_fts(itens_fts, rowid, descricao, marca, grupo, tipo, codigo_item)
                VALUES ('delete', old.id, old.descricao, old.marca, old.grupo, old.tipo, old.codigo_item);
            END
        """)
        cursor.execute("""
            CREATE TRIGGER itens_fts_au AFTER UPDATE ON manutencoes_itemorcamento BEGIN
                INSERT INTO itens_fts(itens_fts, rowid, descricao, marca, grupo, tipo, codigo_item)
                VALUES ('delete', old.id, old.descricao, old.marca, old.grupo, old.tipo, old.codigo_item);
                INSERT INTO itens_fts(rowid, descricao, marca, grupo, tipo, codigo_item)
                VALUES (new.id, new.descricao, new.marca, new.grupo, new.tipo, new.codigo_item);
            END
        """)


def rebuild_fts():
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='itens_fts'")
        if not cursor.fetchone():
            criar_tabela_fts()

        # Rebuild completo do índice a partir da content table
        cursor.execute("INSERT INTO itens_fts(itens_fts) VALUES ('rebuild')")


def buscar_itens(query, tipo=None, grupo=None):
    criar_tabela_fts()

    with connection.cursor() as cursor:
        if query:
            terms = query.strip().split()
            fts_query = ' '.join(f'"{t}"*' for t in terms if t)

            sql = """
                SELECT rowid as item_id, descricao, marca, grupo, tipo, codigo_item,
                       rank
                FROM itens_fts
                WHERE itens_fts MATCH %s
            """
            params = [fts_query]
        else:
            sql = """
                SELECT rowid as item_id, descricao, marca, grupo, tipo, codigo_item,
                       0 as rank
                FROM itens_fts
                WHERE 1=1
            """
            params = []

        if tipo:
            sql += " AND tipo = %s"
            params.append(tipo)

        sql += " ORDER BY rank LIMIT 200"
        cursor.execute(sql, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_grupos():
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='itens_fts'")
        if not cursor.fetchone():
            return []
        cursor.execute("SELECT DISTINCT grupo FROM itens_fts WHERE grupo != '' ORDER BY grupo")
        return [row[0] for row in cursor.fetchall()]
