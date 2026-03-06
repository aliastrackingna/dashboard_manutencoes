# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Manutenção Frota Dashboard — a Django 6.0 fleet maintenance dashboard for tracking vehicles, maintenance orders (OS), budgets, and KPIs. All code and UI text are in Brazilian Portuguese.

## Commands

```bash
python manage.py runserver                    # Dev server on :8000
python manage.py test                         # All tests
python manage.py test apps.importacao         # Tests for one app
python manage.py test apps.importacao.tests.ImportarVeiculosTest.test_criar_veiculo  # Single test
python manage.py makemigrations && python manage.py migrate  # Schema changes
python manage.py check                        # System checks
```

## Architecture

**Django project layout:** `config/` holds settings/urls/wsgi. Eight apps live under `apps/`:

- **dashboard** — KPI calculations (`kpis.py`: `calcular_kpis()`, `dados_graficos()` with 10-min cache) and JSON API endpoints for Chart.js frontend; period filter supports anual/30d/60d/90d/180d/360d/custom/todos
- **veiculos** — Vehicle CRUD; `placa` (license plate) is the natural key used as `to_field` in FKs
- **manutencoes** — Maintenance orders (OS), budgets (`Orcamento`), budget items (`ItemOrcamento`); cascade delete from OS→budgets→items
- **importacao** — CSV import pipeline (`pipeline.py` orchestrates parsers in `parsers/`); uses `update_or_create` for idempotent upserts; items use delete+reinsert strategy; provides `ultima_importacao` context processor
- **pesquisa** — SQLite FTS5 full-text search on budget items; `fts.py` manages the virtual table and triggers
- **configuracoes** — KPI threshold settings stored in `KPIConfig` model
- **multas** — Traffic fines tracking; `Multa` model with `auto_infracao` as unique key, FK to Veiculo via `to_field='placa'`; situação states: EM ABERTO, PAGA, CONTESTADA, BAIXADA
- **relatorios** — Monthly maintenance reports; no own models, queries `Manutencao` from manutencoes app

**Frontend:** Vanilla JS + Chart.js + Tailwind CSS, all via CDN. Dark mode toggle via localStorage. Period filter state persisted in localStorage. Chart clicks drill down to `/dashboard/lista/` with query params.

**Templates:** `templates/base.html` with partials (`navbar.html`, `sidebar.html`, `theme_toggle.html`). Each app has its own `templates/<app_name>/` directory.

**Middleware:** Custom `LoginRequiredMiddleware` — all views require authentication. WhiteNoise serves static files.

**Data flow:** CSV upload → pandas parsing → Django ORM upsert → SQLite. The database is the single source of truth; CSVs are not read for display.

**Deployment:** Docker Compose with Gunicorn + Nginx reverse proxy. See `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`.

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

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- `CSV_FILES_DIR` defaults to `BASE_DIR / 'csv_files'`

## Testing

- Django `TestCase` + `Client`; test naming: `test_<description>`, class naming: `<Feature>Test`
- Import pipeline has the most comprehensive tests (`apps/importacao/tests.py`)

## Reference Docs

- `AGENTS.md` — Full code style guide with patterns and examples
- `IDEA.md` — Complete technical specification, KPI formulas, page layouts, and roadmap
