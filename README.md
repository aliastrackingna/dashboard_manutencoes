# QFrotas Dashboard

Sistema de gestão de frotas com Dashboard Django.

## Tecnologias

- **Backend**: Django 6.0 + Gunicorn (2 workers)
- **Frontend**: TailwindCSS + Chart.js
- **Web Server**: Nginx (proxy reverso)
- **Database**: SQLite3

## Configuração Docker

### Pré-requisitos

- Docker
- Docker Compose
- Portainer (opcional)

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
DJANGO_SECRET_KEY=sua-chave-secreta-aqui
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,seu-dominio.com
```

### Executando com Docker Compose

```bash
# Build e inicialização
docker-compose up -d

# Verificar logs
docker-compose logs -f

# Parar containers
docker-compose down
```

A aplicação estará disponível em: `http://localhost:8000`

---

## Deploy no Portainer

### Opção 1: Stack via Web Editor

1. Acesse o Portainer
2. Vá para **Stacks** > **Add stack**
3. Selecione **Web Editor**
4. Copie e cole o conteúdo do arquivo `docker-compose.yml`:

```yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    image: qfrotas-dashboard
    container_name: qfrotas-web
    restart: unless-stopped
    environment:
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY:-django-insecure-change-in-production}
      - DJANGO_DEBUG=${DJANGO_DEBUG:-False}
      - DJANGO_ALLOWED_HOSTS=${DJANGO_ALLOWED_HOSTS:-*}
    volumes:
      - staticfiles:/app/staticfiles
      - mediafiles:/app/media
      - ./db.sqlite3:/app/db.sqlite3
    networks:
      - qfrotas-network
    depends_on:
      - nginx

  nginx:
    image: nginx:alpine
    container_name: qfrotas-nginx
    restart: unless-stopped
    ports:
      - "8000:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - staticfiles:/app/staticfiles:ro
      - mediafiles:/app/media:ro
    networks:
      - qfrotas-network
    depends_on:
      - web

networks:
  qfrotas-network:
    driver: bridge

volumes:
  staticfiles:
  mediafiles:
```

5. Clique em **Deploy the stack**

### Opção 2: Stack via Git Repository

1. Faça push do código para um repositório Git
2. No Portainer, vá para **Stacks** > **Add stack**
3. Selecione **Git repository**
4. Preencha:
   - **Repository URL**: URL do seu repositório
   - **Repository Reference**: `refs/heads/main`
   - **Compose path**: `docker-compose.yml`
5. Em **Environment variables**, adicione:
   - `DJANGO_SECRET_KEY` = sua chave secreta
   - `DJANGO_DEBUG` = `False`
   - `DJANGO_ALLOWED_HOSTS` = `*`
6. Clique em **Deploy**

### Criando o Primeiro Usuário

Após subir os containers, crie um superusuário:

```bash
docker exec -it qfrotas-web python manage.py createsuperuser
```

### Volumes Persistentes

O Portainer criará automaticamente os volumes:
- `qfrotas_staticfiles` - Arquivos estáticos do Django
- `qfrotas_mediafiles` - Arquivos de mídia/upload

Para verificar os volumes no Portainer:
1. Vá em **Volumes**
2. Localize os volumes relacionados ao stack

### Logs e Troubleshooting

Verificar logs no Portainer:
1. Vá em **Containers**
2. Clique no container desejado
3. Selecione a aba **Logs**

Comandos úteis:
```bash
# Reiniciar stack
docker-compose restart

# Rebuild após alterações
docker-compose up -d --build

# Acessar shell do container
docker exec -it qfrotas-web sh
```

### Estrutura de Arquivos Docker

```
qfrotas_dashboard/
├── Dockerfile           # Multi-stage build para Django
├── docker-compose.yml   # Orquestração de containers
├── nginx.conf          # Configuração Nginx
├── entrypoint.sh       # Script de inicialização
├── requirements.txt    # Dependências Python
└── .env               # Variáveis de ambiente (criar)
```

## Configurações de Segurança

O Nginx inclui:
- **Rate Limiting**: 20 requisições/segundo por IP
- **Headers de Segurança**:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection
- **Compressão Gzip** habilitada
- **Server Tokens** desabilitados

## Desenvolvimento Local

```bash
# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Executar migrações
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser

# Servidor de desenvolvimento
python manage.py runserver
```

Acesse em: `http://localhost:8000`
