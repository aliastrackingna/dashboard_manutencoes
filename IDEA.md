# IDEA.md — Dashboard de Manutenção de Frota

> Documento de especificação técnica e funcional do projeto.  
> Versão 1.4 · codigo_item definido como código de produto (não único); PK incremental adicionada ao ItemOrcamento; estratégia de upsert por delete+reinsert documentada.

---

## 1. Visão Geral

Sistema web para gestão visual de manutenção de frota, acessível via browser, com atualização de dados por upload de arquivos CSV exportados do sistema de OS. O gestor faz o upload dos relatórios e o dashboard é recalculado instantaneamente — sem precisar de um desenvolvedor.

**Princípios do projeto:**
- O **banco de dados SQLite é a fonte da verdade** — dashboard, relatórios e todas as consultas leem exclusivamente do banco.
- O CSV é apenas o **canal de entrada de atualizações**. Após processado, os dados vivem no banco. O sistema nunca lê CSV para exibir informação.
- Veículos, manutenções, orçamentos e itens ficam persistidos no SQLite e são consultados via Django ORM.
- KPIs configuráveis ficam no banco com página de edição dedicada.
- Alertas 100% determinísticos — sem IA, sem heurísticas.
- Interface limpa, executiva, com suporte a tema claro e escuro.
- Zero dependência de serviços externos obrigatórios.
- Legibilidade e organização do código acima de micro-otimizações.

---

## 2. Stack Tecnológica

| Camada              | Tecnologia                        | Versão          |
|---------------------|-----------------------------------|-----------------|
| Backend             | Django                            | 5.x (LTS)       |
| Banco de Dados      | SQLite (via Django ORM)           | latest          |
| FTS                 | SQLite FTS5                       | nativo          |
| Frontend CSS        | Tailwind CSS                      | 4.x (CDN/dev)   |
| Frontend JS         | Vanilla JS + Chart.js             | Chart.js 4.4    |
| Processamento CSV   | pandas + python-dateutil          | latest          |
| Servidor dev        | `python manage.py runserver`      | —               |
| Servidor prod       | Gunicorn + Nginx                  | —               |
| Python              | 3.12+                             | —               |

> **Nota sobre Django 5 vs 6:** Django 6.0 ainda não existe. Use Django 5.2 LTS — suporte até 2028.

---

## 3. Estrutura dos Dados de Origem (CSVs)

### 3.1 `veiculos.csv`
Arquivo de carga inicial, depois gerenciado via CRUD.

| Campo   | Tipo   | Observação                     |
|---------|--------|--------------------------------|
| Placa   | string | Chave natural do veículo       |
| Marca   | string |                                |
| Modelo  | string |                                |
| unidade | string | Pode estar vazio               |

---

### 3.2 `manutencoes.csv`
Arquivo **sem cabeçalho**. Mapeamento identificado na análise:

| Posição | Nome Interno        | Exemplo                    | Observação                                   |
|---------|---------------------|----------------------------|----------------------------------------------|
| col3    | `tipo`              | `3`, `N`, `1`              | Tipo/prioridade da OS                        |
| col4    | `numero_os`         | `2026 - 59`                | **Chave natural** — identificador único da OS |
| col5    | `empresa`           | `FUNDAÇÃO UNIVERSIDADE...` |                                              |
| col6    | `setor`             | `Serviços Gerais`          |                                              |
| col7    | `placa`             | `PLACA77`                  | FK → Veiculo                                 |
| col9    | `modelo_veiculo`    | `Kombi 1.4 flex`           | Denormalizado no CSV                         |
| col10   | `data_abertura`     | `04/02/2026 13:01`         |                                              |
| col11   | `data_previsao`     | `27/02/2026 11:30`         | Previsão de encerramento                     |
| col13   | `data_encerramento` | `27/01/2026 10:04`         | Preenchido quando executada/cancelada        |
| col14   | `descricao`         | `Troca de óleo e filtros…` | Texto livre de serviços solicitados          |
| col15   | `status`            | `Orçamentação`, `Executada`| Ver domínio abaixo                           |
| col16   | `flag_especial`     | `S`                        | Significado a confirmar com o cliente        |
| col17   | `valor_pecas`       | `0,00`                     | Formato BR — converter para Decimal          |
| col18   | `valor_servicos`    | `0,00`                     |                                              |
| col19   | `valor_total`       | `0,00`                     |                                              |

**Domínio de `status`:** `Lançada` → `Orçamentação` → `Análise Solicitante` → `Controladoria` → `Autorizada Execução` → `Em Execução` → `Executada` | `Cancelada pelo Usuário`

**Regra de importação:** `numero_os` é a chave. Se já existe no banco, **atualiza** todos os campos (exceto a PK interna). Nunca duplica.

---

### 3.3 `orcamentos.csv`
Arquivo **com cabeçalho**.

| Campo             | Tipo    | Observação                                              |
|-------------------|---------|---------------------------------------------------------|
| `numero_os`       | string  | FK → Manutencao. **Se a OS não existir, ignora o registro e loga o erro.** |
| `codigo_orcamento`| int     | **Chave natural** do orçamento                          |
| `data`            | date    | Formato `DD/MM/YYYY`                                    |
| `oficina`         | string  | Nome + CNPJ + Cidade/UF concatenados                   |
| `valor`           | string  | Formato BR `1.234,56` — converter para Decimal          |
| `status`          | string  | `Lançado`, `Escolhido`, `Em Execução`, `Executado`, `Recusado`, `Cancelado` |

---

### 3.4 `itens_orcamento.csv`
Arquivo **com cabeçalho**.

| Campo              | Tipo    | Observação                                                   |
|--------------------|---------|--------------------------------------------------------------|
| `codigo_orcamento` | int     | FK → Orcamento. **Se orçamento não existir, ignora e loga.** |
| `tipo`             | string  | `PCA` (peça) ou `SRV` (serviço)                             |
| `grupo`            | string  | Agrupamento/categoria do item — ex: `FILTROS`, `FREIOS`     |
| `codigo_item`      | string  | Código do produto no catálogo da oficina — **não é único**; o mesmo produto pode aparecer em vários orçamentos |
| `descricao`        | string  | Campo principal para FTS5 — ex: `FILTRO DE OLEO`, `ALINHAMENTO` |
| `marca`            | string  | Marca do produto — indexado no FTS5                         |
| `valor_unit`       | string  | Formato BR                                                   |
| `qtd`              | string  | Pode ter decimais — converter para Decimal                   |
| `total`            | string  | Formato BR                                                   |
| `garantia`         | string  | Data `DD/MM/YYYY` — pode ser nulo                           |

> **Estratégia de upsert dos itens:** como não existe chave natural confiável por item, a cada importação o pipeline **deleta todos os itens do orçamento** e reinsere a lista completa recebida no CSV. O `id` incremental (AutoField do Django) é interno ao sistema e não tem correspondência no arquivo de origem.

---

## 4. Arquitetura do Projeto Django

```
frota/                          ← raiz do projeto Django
├── manage.py
├── config/                     ← configurações do projeto
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── veiculos/               ← CRUD de veículos + importação CSV inicial
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── forms.py
│   │   └── templates/
│   │
│   ├── manutencoes/            ← core: OS, orçamentos, itens
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │
│   ├── importacao/             ← pipeline de upload e processamento CSV
│   │   ├── pipeline.py         ← orquestrador principal
│   │   ├── parsers/
│   │   │   ├── base.py
│   │   │   ├── manutencoes.py
│   │   │   ├── orcamentos.py
│   │   │   └── itens.py
│   │   ├── validators.py       ← regras de integridade referencial
│   │   ├── views.py
│   │   └── templates/
│   │
│   ├── dashboard/              ← views de KPIs, gráficos e filtros
│   │   ├── views.py
│   │   ├── kpis.py             ← lógica de cálculo dos KPIs
│   │   ├── urls.py
│   │   └── templates/
│   │
│   ├── pesquisa/               ← FTS5 sobre itens de orçamento
│   │   ├── models.py           ← tabela virtual FTS5
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/
│   │
│   └── configuracoes/          ← edição dos valores de KPI e preferências
│       ├── models.py
│       ├── views.py
│       ├── urls.py
│       └── templates/
│
├── static/
│   ├── css/                    ← Tailwind output
│   ├── js/
│   │   ├── charts.js           ← instâncias Chart.js + click-through
│   │   ├── theme.js            ← toggle claro/escuro
│   │   └── filters.js          ← lógica do filtro de período
│   └── icons/
│
└── templates/                  ← base.html, partials (navbar, sidebar, alerts)
    ├── base.html
    ├── partials/
    └── components/
```

---

## 5. Modelos de Dados (Django ORM)

```python
# apps/veiculos/models.py
class Veiculo(models.Model):
    placa   = models.CharField(max_length=10, unique=True, primary_key=False)
    marca   = models.CharField(max_length=100)
    modelo  = models.CharField(max_length=200)
    unidade = models.CharField(max_length=100, blank=True)
    ativo   = models.BooleanField(default=True)

    class Meta:
        ordering = ['placa']


# apps/manutencoes/models.py
class Manutencao(models.Model):
    numero_os         = models.CharField(max_length=20, unique=True)  # "2026 - 59"
    tipo              = models.CharField(max_length=10)
    empresa           = models.CharField(max_length=200)
    setor             = models.CharField(max_length=100, blank=True)
    veiculo           = models.ForeignKey('veiculos.Veiculo', on_delete=models.PROTECT,
                                          to_field='placa', db_column='placa')
    data_abertura     = models.DateTimeField()
    data_previsao     = models.DateTimeField(null=True, blank=True)
    data_encerramento = models.DateTimeField(null=True, blank=True)
    descricao         = models.TextField(blank=True)
    status            = models.CharField(max_length=50)
    flag_especial     = models.BooleanField(default=False)
    valor_pecas       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_servicos    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    atualizado_em     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_abertura']


class Orcamento(models.Model):
    manutencao       = models.ForeignKey(Manutencao, on_delete=models.CASCADE,
                                         related_name='orcamentos')
    codigo_orcamento = models.IntegerField(unique=True)
    data             = models.DateField()
    oficina          = models.CharField(max_length=300)
    valor            = models.DecimalField(max_digits=12, decimal_places=2)
    status           = models.CharField(max_length=30)

    class Meta:
        ordering = ['codigo_orcamento']


class ItemOrcamento(models.Model):
    # id AutoField gerado pelo Django (PK incremental) — chave interna do sistema
    orcamento   = models.ForeignKey(Orcamento, on_delete=models.CASCADE,
                                    related_name='itens')
    tipo        = models.CharField(max_length=3)   # PCA | SRV
    grupo       = models.CharField(max_length=100, blank=True)
    codigo_item = models.CharField(max_length=50, blank=True)  # código do produto, não único
    descricao   = models.CharField(max_length=300)
    marca       = models.CharField(max_length=100, blank=True)
    valor_unit  = models.DecimalField(max_digits=12, decimal_places=2)
    qtd         = models.DecimalField(max_digits=10, decimal_places=3)
    total       = models.DecimalField(max_digits=12, decimal_places=2)
    garantia    = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['tipo', 'descricao']


# apps/configuracoes/models.py
class KPIConfig(models.Model):
    chave       = models.CharField(max_length=100, unique=True)
    descricao   = models.CharField(max_length=300)
    valor       = models.DecimalField(max_digits=14, decimal_places=2)
    unidade     = models.CharField(max_length=30, blank=True)  # "R$", "%", "dias"
    atualizado_em = models.DateTimeField(auto_now=True)
```

---

## 6. Pipeline de Importação

### Fluxo Geral

```
Upload (3 CSVs) → Validação de Formato → Parse → Validação Referencial → Upsert → Relatório
```

### Ordem obrigatória de processamento

1. **Manutenções** — independem de FK externa (exceto Veiculo)
2. **Orçamentos** — dependem de `numero_os` existente
3. **Itens** — dependem de `codigo_orcamento` existente

### Regras de Upsert

```python
# Pseudo-código do pipeline
def importar_manutencao(row):
    Manutencao.objects.update_or_create(
        numero_os=row['numero_os'],
        defaults={campo: valor for campo, valor in row.items() if campo != 'numero_os'}
    )

def importar_orcamento(row):
    if not Manutencao.objects.filter(numero_os=row['numero_os']).exists():
        erros.append(ErroImportacao(tipo='FK_AUSENTE', entidade='Orcamento',
                                    chave=row['codigo_orcamento'],
                                    motivo=f"OS '{row['numero_os']}' não encontrada"))
        return  # pula, continua com os outros

def importar_item(row):
    if not Orcamento.objects.filter(codigo_orcamento=row['codigo_orcamento']).exists():
        erros.append(...)
        return
```

### Modelo de Relatório de Importação

```python
@dataclass
class RelatorioImportacao:
    manutencoes_inseridas:  int
    manutencoes_atualizadas: int
    orcamentos_inseridos:   int
    orcamentos_atualizados: int
    itens_inseridos:        int
    itens_atualizados:      int
    erros: list[ErroImportacao]   # exibidos ao gestor ao final
```

---

## 7. Páginas e Funcionalidades

### 7.1 Dashboard Principal (`/dashboard/`)

**Filtro de período** (persiste no `localStorage` da sessão):
- Anual (padrão) — ano corrente
- Últimos 30 / 60 / 90 dias
- Período personalizado (date picker)

**Cards de KPI (linha superior):**

| KPI                        | Cálculo                                      |
|----------------------------|----------------------------------------------|
| Total de OS no período     | `COUNT(Manutencao)`                          |
| Valor total aprovado       | `SUM(valor_total)` onde status=Executada     |
| Ticket médio por OS        | Valor total / OS executadas                  |
| OS dentro do prazo         | `data_encerramento <= data_previsao` (%)     |
| Tempo médio de resolução   | `AVG(data_encerramento - data_abertura)`     |

**Gráficos (todos com click-through):**

| Gráfico                     | Tipo       | Drill-down para                      |
|-----------------------------|------------|--------------------------------------|
| OS por Status               | Bar horiz. | Lista de OS filtradas por status     |
| Evolução mensal de OS       | Bar vert.  | Lista de OS do mês clicado           |
| Top 10 veículos por gasto   | Bar horiz. | Página do veículo                    |
| Top 10 oficinas por volume  | Bar horiz. | Lista de orçamentos da oficina       |
| Distribuição Peças vs Serv. | Donut      | Lista de itens por tipo              |
| OS por Setor                | Bar horiz. | Lista de OS do setor                 |

> **Princípio de Storytelling:** cada gráfico tem um subtítulo curto com o insight principal recalculado dinamicamente (ex: *"Orçamentação concentra 46% das OS — 52 aguardando aprovação"*).

### Paleta de Cores Semânticas

Todas as cores dos gráficos seguem significado semântico fixo — nunca aleatório.

| Cor | Hex | Significado | Uso |
|-----|---------|-------------|-----|
| Cinza | `#9ca3af` | Em trâmite / neutro | Lançada, Análise Solicitante, Controladoria |
| Amarelo | `#d97706` | Aguardando ação / atenção | Orçamentação, Top Oficinas |
| Azul | `#2563eb` | Ação em progresso | Autorizada Execução, Em Execução, Evolução Mensal, Peças |
| Verde | `#16a34a` | Concluído / valor positivo | Executada, Top Veículos (gasto), Serviços |
| Vermelho | `#dc2626` | Atenção negativa | Cancelada pelo Usuário |
| Roxo | `#8b5cf6` | Categorização / setor | OS por Setor |

**Regras visuais (Storytelling com Dados):**
- Barras horizontais ordenadas por valor (desc) para facilitar comparação
- Datalabels inline ao final de cada barra — eixo de valores oculto
- Subtítulo dinâmico com insight calculado no backend (`status_insight`, `evolucao_insight`, etc.)
- Donut mantido apenas para Peças vs Serviços (2 fatias — comparação parte/todo válida)

---

### 7.2 Lista Drill-down (`/dashboard/lista/`)

Página genérica ativada pelo click nos gráficos. Recebe parâmetros via query string:
- `?filtro=status&valor=Executada&periodo=anual`

Exibe tabela com colunas configuráveis por contexto, com paginação e exportação CSV.

---

### 7.3 Pesquisa por Veículo (`/veiculos/<placa>/`)

- Campo de busca por placa (autocomplete)
- Card do veículo (dados cadastrais)
- Timeline de manutenções ordenada por data
- Cada manutenção: número OS, status badge, valor total, link para detalhe
- Gráfico de linha: evolução de gastos do veículo ao longo do tempo

---

### 7.4 Detalhe da Manutenção (`/manutencoes/<numero_os>/`)

- Header: número OS, placa, modelo, status badge, datas (abertura / previsão / encerramento)
- Descrição dos serviços solicitados
- Accordion de orçamentos, cada um com:
  - Cabeçalho: código, oficina, data, valor, status badge
  - Tabela de itens: seq, tipo (badge PCA/SRV), descrição, qtd, valor unit, total, garantia
- Orçamento escolhido/executado destacado visualmente

---

### 7.5 Pesquisa por Itens — FTS5 (`/pesquisa/itens/`)

**Campos indexados no FTS5:** `descricao` (peso alto) + `marca` (peso médio) + `grupo` (peso baixo) + `tipo` e `codigo_item` (filtro/busca exata)

**Campos de busca e filtro:**
- Campo texto livre → query FTS5 (`descricao`, `marca`, `grupo`)
- Filtro tipo: Todos / Peças (PCA) / Serviços (SRV)
- Filtro grupo: lista dinâmica dos grupos existentes

**Resultado por item encontrado:**
- Descrição e marca (com highlight do termo buscado)
- Tipo badge + grupo
- Todas as ocorrências agrupadas: quantidade de vezes usado, valor mínimo, valor máximo, valor médio
- Link para o orçamento e para a OS relacionada

**Implementação FTS5:**
```sql
-- migration raw SQL
CREATE VIRTUAL TABLE itens_fts USING fts5(
    descricao,
    marca,
    grupo,
    tipo       UNINDEXED,
    codigo_item UNINDEXED,
    item_id    UNINDEXED,        -- FK para ItemOrcamento.id
    content='manutencoes_itemorcamento',
    content_rowid='id'
);

-- trigger de sincronização via Django signal post_save/post_delete
```

---

### 7.6 CRUD de Veículos (`/veiculos/`)

- Lista paginada com filtro por placa/marca/modelo
- Carga inicial: upload do `veiculos.csv`
- Formulário de criação e edição
- Soft delete (campo `ativo`)

---

### 7.7 Upload / Importação (`/importacao/`)

- Formulário com **3 campos de arquivo** (manutenções, orçamentos, itens) — todos opcionais individualmente
- Botão "Processar"
- Após processamento: exibe `RelatorioImportacao` com contadores e lista de erros com destaque visual
- Histórico das últimas importações (data, usuário, contadores)

---

### 7.8 Configurações de KPI (`/configuracoes/kpis/`)

- Tabela editável inline com os valores de referência dos KPIs
- Ex: "Custo máximo aceitável por OS", "SLA de dias para execução"
- Esses valores alimentam os alertas e as faixas coloridas dos cards

---

## 8. Componentes de Frontend

### Tema Claro/Escuro
- Toggle no navbar salva preferência em `localStorage`
- Tailwind classes `dark:` aplicadas no `<html>` com classe `dark`

### Filtro de Período
- Componente JS isolado (`filters.js`) que emite um evento customizado `periodoAtualizado`
- Todas as views de dashboard escutam esse evento e recarregam via `fetch` (JSON endpoint)

### Gráficos com Click-through
```javascript
// charts.js — padrão para todos os gráficos
chart.options.onClick = (event, elements) => {
    if (elements.length === 0) return;
    const label = chart.data.labels[elements[0].index];
    const params = buildDrillParams(chartType, label, currentPeriodo);
    window.location.href = `/dashboard/lista/?${params}`;
};
```

---

## 9. Conversão de Dados BR → Python

```python
# apps/importacao/parsers/base.py

import re
from decimal import Decimal
from datetime import datetime

def parse_decimal_br(valor: str) -> Decimal:
    """'1.234,56' → Decimal('1234.56')"""
    limpo = re.sub(r'[^\d,]', '', str(valor)).replace(',', '.')
    return Decimal(limpo) if limpo else Decimal('0')

def parse_datetime_br(valor: str) -> datetime | None:
    """'04/02/2026 13:01' → datetime"""
    for fmt in ('%d/%m/%Y %H:%M', '%d/%m/%Y'):
        try:
            return datetime.strptime(str(valor).strip(), fmt)
        except ValueError:
            continue
    return None
```

---

## 10. Roadmap de Implementação

| Fase | Entregável                                          | Pré-requisito |
|------|-----------------------------------------------------|---------------|
| 0    | Setup do projeto, settings, base.html, tema         | —             |
| 1    | Models + migrations + admin básico                  | Fase 0        |
| 2    | Pipeline de importação + tela de upload             | Fase 1        |
| 3    | CRUD de Veículos + carga inicial via CSV            | Fase 1        |
| 4    | Dashboard principal (cards + gráficos sem filtro)   | Fase 2        |
| 5    | Filtro de período + JSON endpoints                  | Fase 4        |
| 6    | Click-through + página de lista drill-down          | Fase 5        |
| 7    | Detalhe da Manutenção                               | Fase 2        |
| 8    | Pesquisa por veículo                                | Fase 3        |
| 9    | FTS5 — pesquisa por itens                           | Fase 2        |
| 10   | Configurações de KPI                                | Fase 4        |
| 11   | Polimento visual + tema escuro completo             | Fase 10       |
| 12   | Deploy (Gunicorn + Nginx + collectstatic)           | Fase 11       |

---

## 11. Decisões de Arquitetura — Justificativas

| Decisão                         | Motivo                                                                   |
|---------------------------------|--------------------------------------------------------------------------|
| `update_or_create` no upsert    | Garante idempotência: rodar o mesmo CSV duas vezes não duplica dados     |
| FK por `numero_os` (string)     | Chave natural do sistema de origem — evita JOIN extra para exibição      |
| FTS5 nativo do SQLite           | Zero dependência externa, busca full-text suficiente para o volume atual |
| JSON endpoints para gráficos    | Permite filtro dinâmico sem recarregar a página inteira                  |
| Relatório de erros ao final     | Importações parciais são válidas — gestor decide o que corrigir          |
| `flag_especial` como BooleanField | Col16 só contém `S` ou nulo — semantica a confirmar com o cliente      |

---

## 12. Pontos em Aberto (a confirmar com o cliente)

1. O que significa `col3` (valores `3`, `N`, `1`) em manutenções? É tipo ou prioridade?
2. O que significa `col16` (`flag_especial = S`)? Urgência? Garantia?
3. Os campos `col11` e `col13` foram interpretados como `data_previsao` e `data_encerramento` — confirmar.
4. Existe autenticação de usuários? (login/logout) ou o sistema é interno sem auth?
5. O campo `unidade` em veículos deve virar um cadastro próprio (FK) ou string livre?
6. É necessário exportação dos relatórios para Excel/PDF?

---

*Documento mantido junto ao repositório. Atualizar a versão a cada decisão arquitetural relevante.*
