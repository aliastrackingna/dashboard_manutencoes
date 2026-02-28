# AGENTS.md - QFrotas Dashboard

## Project Overview
- **Framework**: Django 6.0
- **Language**: Python 3.x
- **Database**: SQLite3 (db.sqlite3)
- **Template Engine**: Django Templates (Jinja-like syntax)
- **Frontend**: TailwindCSS (via CDN)

## Project Structure
```
qfrotas_dashboard/
├── apps/                    # Django applications
│   ├── configuracoes/       # Settings app
│   ├── dashboard/           # Main dashboard
│   ├── importacao/          # CSV import functionality
│   ├── manutencoes/         # Maintenance module
│   ├── pesquisa/            # Search functionality
│   └── veiculos/            # Vehicle management
├── config/                  # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py                # Django management CLI
├── requirements.txt         # Python dependencies
├── static/                  # Static files (CSS, JS)
└── templates/               # Global templates
```

---

## Build / Run / Test Commands

### Development Server
```bash
python manage.py runserver
```

### Running Tests
Run all tests:
```bash
python manage.py test
```

Run tests for a specific app:
```bash
python manage.py test apps.veiculos
python manage.py test apps.manutencoes
```

Run a single test class:
```bash
python manage.py test apps.veiculos.tests.VeiculoModelTest
```

Run a single test method:
```bash
python manage.py test apps.veiculos.tests.VeiculoModelTest.test_criar_veiculo
```

### Migrations
Create migrations:
```bash
python manage.py makemigrations
```

Apply migrations:
```bash
python manage.py migrate
```

### Shell
```bash
python manage.py shell
```

---

## Code Style Guidelines

### General Conventions

- **Language**: Portuguese (Brazilian) - variable names, model fields, views, and UI text are in Portuguese
- **Line length**: Maximum 120 characters
- **Indentation**: 4 spaces (no tabs)
- **Encoding**: UTF-8

### Python Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) with the following modifications:
  - Maximum line length: 120 (configured in tools if available)
  - Use single quotes for strings unless double quotes are needed

### Imports

Order imports alphabetically within groups:
```python
# Standard library
import os
import sys
from datetime import date

# Third-party
from django.contrib import admin
from django.db import models
from django.http import JsonResponse

# Local apps
from .models import Veiculo
from .forms import VeiculoForm
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Models | PascalCase | `class Veiculo(models.Model)` |
| Model Fields | snake_case | `placa = models.CharField(...)` |
| Methods | snake_case | `def lista(request):` |
| Variables | snake_case | `qs = Veiculo.objects.all()` |
| Constants | UPPER_SNAKE_CASE | `PAGE_SIZE = 25` |
| URLs | snake_case | `path('novo/', views.criar, name='criar')` |
| URL Names | snake_case | `app_name = 'veiculos'` |

### Models

- Use `models.Model` as base class
- Always define `__str__` method
- Define `Meta` class with `ordering` for consistent querysets
- Use verbose names for Portuguese labels:
  ```python
  class Meta:
      verbose_name = 'Manutenção'
      verbose_name_plural = 'Manutenções'
  ```
- Use `on_delete=models.PROTECT` for foreign keys to prevent accidental deletions
- Use `related_name` for reverse relationships
- Default values for optional fields: `blank=True, default=''` or `null=True, blank=True`

### Views

- Use function-based views (FBVs) - not class-based views
- Use `get_object_or_404` for single object retrieval
- Use Django's pagination:
  ```python
  paginator = Paginator(qs, 25)
  page = paginator.get_page(request.GET.get('page'))
  ```
- Return appropriate HTTP status codes (200, 302, 404)
- Use `messages` framework for user feedback:
  ```python
  messages.success(request, 'Veículo criado com sucesso.')
  ```

### Forms

- Use `forms.ModelForm` for model-backed forms
- Define widgets with TailwindCSS classes for styling
- Placeholder text in Portuguese

### Templates

- Use `.html` extension
- Organize in app-level `templates/<app_name>/` directories
- Use TailwindCSS classes for styling
- Use Django template inheritance with `{% extends %}` and `{% block %}`
- Use `{% url %}` tag for reversing URLs

### Error Handling

- Use Django's `get_object_or_404` for 404 handling
- Use try/except for operations that may fail:
  ```python
  try:
      form.save()
  except Exception as e:
      messages.error(request, f'Erro ao salvar: {e}')
  ```
- Let Django's built-in validation handle form errors

### Testing

- Use Django's `TestCase` class
- Use `Client()` for view testing
- Follow naming: `test_<description>` for test methods
- Group tests in classes: `<ModelOrFeature>Test`
- Use `setUp()` method to create test data
- Test both positive and negative cases
- Use `reverse()` for URL resolution

### Admin

- Use `@admin.register(Model)` decorator
- Define `list_display`, `list_filter`, and `search_fields`

### Database

- Use migrations for schema changes (`makemigrations` + `migrate`)
- Foreign keys should reference `to_field` when using non-PK fields (e.g., `placa`)
- Use `DecimalField` for monetary values

### Type Hints

- Not strictly required but encouraged for complex functions:
  ```python
  def get_veiculos() -> QuerySet[Veiculo]:
      return Veiculo.objects.all()
  ```

### Comments

- Avoid unnecessary comments; code should be self-documenting
- Use comments to explain complex business logic or non-obvious decisions
- Write docstrings only for complex functions/classes

### Security

- Never commit secrets (API keys, passwords) to version control
- Use environment variables for sensitive configuration
- Use Django's CSRF protection (`{% csrf_token %}` in forms)
- Use parameterized queries (Django ORM handles this automatically)

---

## Common Patterns

### Filter Querysets
```python
qs = Model.objects.all()

q = request.GET.get('q', '').strip()
if q:
    qs = qs.filter(campo__icontains=q)

ativo = request.GET.get('ativo')
if ativo == '1':
    qs = qs.filter(ativo=True)
elif ativo == '0':
    qs = qs.filter(ativo=False)
```

### JSON Response
```python
return JsonResponse([
    {'placa': v.placa, 'label': f'{v.placa} — {v.marca}'}
    for v in veiculos
], safe=False)
```

### Form Handling
```python
if request.method == 'POST':
    form = MyForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, 'Sucesso!')
        return redirect('app:url_name')
else:
    form = MyForm()
return render(request, 'template.html', {'form': form})
```

---

## Database Configuration

- **Path**: `BASE_DIR / 'db.sqlite3'`
- **Environment Variables**:
  - `DJANGO_SECRET_KEY`: Secret key for Django
  - `DJANGO_DEBUG`: Set to 'False' in production
  - `DJANGO_ALLOWED_HOSTS`: Comma-separated hosts

---

## Useful Commands

```bash
# Create new app
python manage.py startapp myapp

# Check for issues
python manage.py check

# Show SQL for migrations
python manage.py sqlmigrate app_name migration_name

# Collect static files
python manage.py collectstatic
```
