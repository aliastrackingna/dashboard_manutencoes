# AGENTS.md - qfrotas_dashboard

## Project Snapshot
- Stack: Django 6.0, Python 3.12, SQLite, TailwindCSS/Chart.js via CDN.
- App language: Brazilian Portuguese for model fields, variables, UI labels, URLs.
- Architecture: function-based views across apps in `apps/`; shared config in `config/`.
- Main data flow: CSV import (`apps/importacao`) -> ORM upsert -> SQLite -> KPI/FTS refresh.

## Agent Rule Sources
- `.cursor/rules/`: not present.
- `.cursorrules`: not present.
- `.github/copilot-instructions.md`: not present.
- This file and `CLAUDE.md` are the active agent guidance in this repository.

## Environment Setup
```bash
# from repository root
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Build / Run / Lint / Test Commands

### Core local commands
```bash
# dev server
source venv/bin/activate
python manage.py runserver

# database
python manage.py makemigrations
python manage.py migrate

# django checks (closest thing to lint in this repo)
python manage.py check

# django shell
python manage.py shell

# optional coverage
coverage run manage.py test --parallel $(nproc)
coverage report -m
```

### Tests (including single test execution)
```bash
# all tests
python manage.py test --parallel $(nproc)

# one app
python manage.py test apps.veiculos

# one module
python manage.py test apps.importacao.tests

# one test class
python manage.py test apps.veiculos.tests.VeiculoModelTest

# one test method (most important for quick iteration)
python manage.py test apps.veiculos.tests.VeiculoModelTest.test_criar_veiculo
```

### Docker commands
```bash
# build and run stack (gunicorn + nginx + cron)
docker-compose up -d --build

# stop stack
docker-compose down

# logs
docker-compose logs -f dashboard_web
```

## Project Layout
```text
apps/
  acompanhamento/  auditoria/  configuracoes/  dashboard/  importacao/
  manutencoes/     multas/     pesquisa/       relatorios/ veiculos/
config/            # settings, urls, middleware
templates/         # base templates + app templates
static/            # static assets
```

## Code Style Guidelines

### Formatting and structure
- Follow PEP 8 with max line length 120 and 4-space indentation.
- Prefer single quotes unless double quotes improve readability.
- Keep views function-based (project convention); avoid introducing CBVs unless asked.
- Keep functions focused and short; extract helpers for repeated filter/pagination logic.

### Imports
- Group imports in this order: stdlib -> third-party -> local app imports.
- Keep alphabetical order inside each group.
- Use one import per line (except `from x import a, b` when tightly related).

Example:
```python
from datetime import datetime

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.auditoria.models import LogAuditoria
from .forms import VeiculoForm
from .models import Veiculo
```

### Naming conventions
- Models/classes: `PascalCase` (example: `Veiculo`, `LogAuditoria`).
- Functions, methods, variables, fields: `snake_case` in Portuguese.
- Constants: `UPPER_SNAKE_CASE`.
- URL names and paths: short `snake_case` (`lista`, `criar`, `detalhe`).
- Test classes: `<Feature>Test`; test methods: `test_<comportamento>`.

### Types and annotations
- Type hints are used selectively; keep them where they add clarity.
- Prefer explicit return annotations for parser/helper functions.
- Use modern union syntax (`datetime | None`) where appropriate.
- Do not add heavy typing boilerplate to simple Django views/forms.

### Django model conventions
- Always define `__str__`.
- Define `Meta.ordering`; include `verbose_name`/`verbose_name_plural` when useful.
- Monetary values must use `DecimalField` and `Decimal` in Python code.
- Prefer `on_delete=models.PROTECT` for critical relations; keep existing CASCADE where domain already relies on it.
- For optional text fields, use `blank=True, default=''`; for optional dates, `null=True, blank=True`.
- Keep explicit `related_name` on foreign keys.

### Views, forms, templates
- Use `get_object_or_404` for object lookup endpoints.
- Paginate list pages with `Paginator(..., 25)`.
- Use `django.contrib.messages` for user feedback after POST actions.
- Follow POST/redirect/GET for successful form submissions.
- Use `ModelForm` for CRUD; keep Tailwind classes in widget attrs.
- Templates: app-local `templates/<app_name>/...`; use `{% extends %}`, `{% block %}`, `{% url %}`.

### Error handling and robustness
- Validate all query params (`q`, `ativo`, period filters) before filtering.
- Use narrow exceptions (`ValueError`, `IntegrityError`) where possible.
- Avoid broad `except Exception` unless converting to user-facing errors/messages.
- For import pipelines, collect row-level errors instead of failing entire file when possible.
- Preserve idempotency patterns (`update_or_create`, delete-and-reinsert strategy where already used).

### Security and config
- Never commit secrets or real credentials.
- Use environment variables from `config/settings.py` (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_PATH`, email vars).
- Include `{% csrf_token %}` in every POST form.
- Keep login requirement behavior compatible with `config/middleware.py`.

## Testing Conventions
- New feature or bug fix should include/adjust tests.
- Use `django.test.TestCase` and `Client` for view integration tests.
- Prefer `reverse('app:view_name')` over hardcoded URLs in tests.
- Assert status code, template context, and key persisted side effects.
- Keep fixtures in `setUp()` and use deterministic values (plates, OS numbers, dates).

## Agent Workflow Expectations
- Before finishing: run at least targeted tests for touched app/module.
- If models changed: generate migration, run migrate, and ensure tests still pass.
- If command output reveals unrelated pre-existing failures, report clearly and do not hide them.
- Keep commits focused and small when asked to commit.
