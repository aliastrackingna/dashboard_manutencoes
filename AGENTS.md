# AGENTS.md - Manutenção Frota Dashboard

## Project Overview
- **Framework**: Django 6.0
- **Language**: Python 3.x
- **Database**: SQLite3
- **Frontend**: TailwindCSS (via CDN)

## Project Structure
```
frotas_dashboard/
├── apps/                    # Django applications
│   ├── configuracoes/       # Settings
│   ├── dashboard/           # Main dashboard
│   ├── importacao/          # CSV import
│   ├── manutencoes/         # Maintenance
│   ├── pesquisa/            # Search
│   └── veiculos/            # Vehicle management
├── config/                  # Django settings
├── manage.py
├── requirements.txt
├── static/
└── templates/
```

---

## Build / Run / Test Commands

**IMPORTANTE:** Sempre ative o virtual environment antes de executar qualquer comando:
```bash
source venv/bin/activate
```

```bash
# Development server
python manage.py runserver

# Run all tests (paralelo, 1 banco por processo)
python manage.py test --parallel $(nproc)

# Run tests for specific app
python manage.py test apps.veiculos

# Run single test class
python manage.py test apps.veiculos.tests.VeiculoModelTest

# Run single test method
python manage.py test apps.veiculos.tests.VeiculoModelTest.test_criar_veiculo

# Migrations
python manage.py makemigrations
python manage.py migrate

# Check for issues
python manage.py check
python manage.py shell
```

---

## Code Style Guidelines

### General
- **Language**: Portuguese (Brazilian) for variables, fields, views, UI
- **Line length**: Max 120 characters
- **Indentation**: 4 spaces
- **Quotes**: Single quotes unless double needed

### Imports (alphabetical within groups)
```python
# Standard library
import os
from datetime import date

# Third-party
from django.contrib import admin
from django.db import models

# Local apps
from .models import Veiculo
```

### Naming Conventions
| Element | Convention | Example |
|---------|------------|---------|
| Models | PascalCase | `Veiculo` |
| Fields/Methods | snake_case | `placa`, `criar()` |
| Constants | UPPER_SNAKE | `PAGE_SIZE = 25` |
| URLs | snake_case | `path('lista/', ...)` |

### Models
- Base: `models.Model`
- Always define `__str__` and `Meta` with `ordering`
- Use verbose names in Portuguese
- Foreign keys: `on_delete=models.PROTECT`, use `related_name`
- Optional fields: `blank=True, default=''` or `null=True, blank=True`

### Views (Function-Based)
- Use `get_object_or_404` for single objects
- Use Django pagination:
  ```python
  paginator = Paginator(qs, 25)
  page = paginator.get_page(request.GET.get('page'))
  ```
- Use `messages` for feedback:
  ```python
  messages.success(request, 'Veículo criado com sucesso.')
  ```

### Forms
- Use `forms.ModelForm`
- Define widgets with TailwindCSS classes

### Templates
- Use `.html` extension
- App-level `templates/<app_name>/` directories
- Use `{% extends %}`, `{% block %}`, `{% url %}`

### Error Handling
- Use `get_object_or_404` for 404s
- Try/except for operations that may fail:
  ```python
  try:
      form.save()
  except Exception as e:
      messages.error(request, f'Erro ao salvar: {e}')
  ```

### Testing
- **Toda feature nova deve ser acompanhada de testes**
- Use Django `TestCase`
- Use `Client()` for view tests
- Name: `test_<description>`
- Group in classes: `<ModelOrFeature>Test`
- Use `setUp()` and `reverse()`

### Admin
- Use `@admin.register(Model)` decorator
- Define `list_display`, `list_filter`, `search_fields`

### Security
- Never commit secrets
- Use environment variables
- Use `{% csrf_token %}` in forms

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

## Database
- Path: `BASE_DIR / 'db.sqlite3'`
- Env vars: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- Use `DecimalField` for monetary values
