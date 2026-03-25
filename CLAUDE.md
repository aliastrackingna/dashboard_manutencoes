# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Manutenção Frota Dashboard — a Django 6.0 fleet maintenance dashboard for tracking vehicles, maintenance orders (OS), budgets, and KPIs. All code and UI text are in Brazilian Portuguese.

## Commands

Activate the virtualenv first: `source venv/bin/activate`

```bash
python manage.py runserver                    # Dev server on :8000
python manage.py test --parallel $(nproc)     # All tests (parallel)
python manage.py test apps.importacao         # Tests for one app
python manage.py test apps.importacao.tests.ImportarVeiculosTest.test_criar_veiculo  # Single test
python manage.py makemigrations && python manage.py migrate  # Schema changes
python manage.py check                        # System checks
python manage.py backup_excel                 # Manual Excel backup export
```

## Architecture

**Django project layout:** `config/` holds settings/urls/wsgi/middleware. Ten apps live under `apps/`:

- **dashboard** — KPI calculations (`kpis.py`: `calcular_kpis_raw()`, `dados_graficos()` with 10-min cache) and JSON API endpoints for Chart.js frontend; period filter supports anual/30d/60d/90d/180d/360d/custom/todos
- **veiculos** — Vehicle CRUD; `placa` (license plate) is the natural key used as `to_field` in FKs
- **manutencoes** — Maintenance orders (OS), budgets (`Orcamento`), budget items (`ItemOrcamento`); cascade delete from OS→budgets→items
- **importacao** — CSV import pipeline (`pipeline.py` orchestrates parsers in `parsers/`); uses `update_or_create` for idempotent upserts; items use delete+reinsert strategy; FTS5 rebuild and KPI cache clear triggered after import; provides `ultima_importacao` context processor
- **pesquisa** — SQLite FTS5 full-text search on budget items; `fts.py` manages the virtual table and triggers
- **configuracoes** — KPI threshold settings (`KPIConfig`) and general settings (`ConfigGeral`); management command `backup_excel` exports all data to Excel with email delivery
- **multas** — Traffic fines tracking; `Multa` model with `auto_infracao` as unique key, FK to Veiculo via `to_field='placa'`; situação states: EM ABERTO, PAGA, CONTESTADA, BAIXADA
- **auditoria** — Audit logging; `LogAuditoria` model with types ADICAO, ALTERACAO, IMPORTACAO; FK to User
- **acompanhamento** — OS follow-up tracking; `Acompanhamento` model with motivos (VALOR_ALTO, PRAZO_EXCEDIDO, REINCIDENCIA, etc.) and prioridades (Alta/Média/Baixa); unique_together on usuario+manutencao
- **relatorios** — Monthly maintenance reports; no own models, queries `Manutencao` from manutencoes app

**Frontend:** Vanilla JS + Chart.js + Tailwind CSS, all via CDN. Dark mode toggle via localStorage. Period filter state persisted in localStorage. Chart clicks drill down to `/dashboard/lista/` with query params.

**Templates:** `templates/base.html` with partials (`navbar.html`, `sidebar.html`, `theme_toggle.html`). Each app has its own `templates/<app_name>/` directory.

**Middleware:** Custom `LoginRequiredMiddleware` (`config/middleware.py`) — all views require authentication except `/login`. WhiteNoise serves static files.

**Data flow:** CSV upload → pandas parsing → Django ORM upsert → SQLite → FTS5 rebuild → KPI cache invalidation. The database is the single source of truth; CSVs are not read for display.

**Deployment:** Docker Compose with 3 services: `dashboard_web` (Gunicorn, 2 workers), `dashboard_cron` (daily Excel backup at 3 AM), `dashboard_nginx` (reverse proxy). `entrypoint.sh` runs migrations, collectstatic, and creates default admin superuser.

## Key Conventions

- **Language:** All variable names, model fields, URLs, and UI strings in Brazilian Portuguese
- **Views:** Function-based only (no CBVs)
- **Style:** PEP 8, 120-char line limit, single quotes, 4-space indent
- **Imports:** Grouped (stdlib → third-party → local), alphabetical within groups
- **Models:** Always define `__str__`, `Meta.ordering`, `verbose_name`/`verbose_name_plural`; use `on_delete=PROTECT` for FKs; `DecimalField` for monetary values
- **FK references:** Use `to_field='placa'` or `to_field='numero_os'` (natural keys, not auto PKs)
- **Pagination:** 25 items per page via `Paginator`
- **User feedback:** Django `messages` framework
- **Forms:** `ModelForm` with Tailwind CSS widget classes

## Environment Variables

- `SECRET_KEY`, `DEBUG` (default `True`), `ALLOWED_HOSTS` (comma-separated, default `localhost,127.0.0.1`)
- `DB_PATH` defaults to `BASE_DIR / 'db.sqlite3'`
- `CSV_FILES_DIR` defaults to `BASE_DIR / 'csv_files'`
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` — SMTP config for backup delivery (defaults to Gmail)
- Session timeout: 10,800 seconds (3 hours)
- Timezone: `America/Sao_Paulo`

## Testing

- Django `TestCase` + `Client`; test naming: `test_<description>`, class naming: `<Feature>Test`
- Import pipeline has the most comprehensive tests (`apps/importacao/tests.py`)
- Run with `coverage run manage.py test --parallel $(nproc)` for coverage reports

## Reference Docs

- `AGENTS.md` — Full code style guide with patterns and examples
- `IDEA.md` — Complete technical specification, KPI formulas, page layouts, and roadmap
