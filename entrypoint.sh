#!/bin/bash
set -e

echo "Executando migrações do banco de dados..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

echo "Criando superusuário admin se não existir..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superusuário admin/admin criado com sucesso!')
else:
    print('Superusuário admin já existe.')
EOF

echo "Iniciando aplicação..."
exec "$@"
