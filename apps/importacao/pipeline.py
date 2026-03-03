from dataclasses import dataclass, field
from .parsers.veiculos import importar_veiculos
from .parsers.manutencoes import importar_manutencoes
from .parsers.orcamentos import importar_orcamentos
from .parsers.itens import importar_itens
from .parsers.multas import importar_multas


@dataclass
class RelatorioImportacao:
    veiculos_inseridos: int = 0
    veiculos_atualizados: int = 0
    manutencoes_inseridas: int = 0
    manutencoes_atualizadas: int = 0
    orcamentos_inseridos: int = 0
    orcamentos_atualizados: int = 0
    itens_inseridos: int = 0
    multas_inseridas: int = 0
    multas_ignoradas: int = 0
    erros: list = field(default_factory=list)

    @property
    def total_processados(self):
        return (
            self.veiculos_inseridos + self.veiculos_atualizados +
            self.manutencoes_inseridas + self.manutencoes_atualizadas +
            self.orcamentos_inseridos + self.orcamentos_atualizados +
            self.itens_inseridos +
            self.multas_inseridas
        )

    @property
    def tem_erros(self):
        return len(self.erros) > 0


def executar_pipeline(veiculos_file=None, manutencoes_file=None,
                      orcamentos_file=None, itens_file=None,
                      multas_file=None):
    relatorio = RelatorioImportacao()

    # 0. Veículos (se fornecido)
    if veiculos_file:
        resultado = importar_veiculos(veiculos_file)
        relatorio.veiculos_inseridos = resultado['inseridos']
        relatorio.veiculos_atualizados = resultado['atualizados']
        relatorio.erros.extend(resultado['erros'])

    # 1. Manutenções
    if manutencoes_file:
        resultado = importar_manutencoes(manutencoes_file)
        relatorio.manutencoes_inseridas = resultado['inseridos']
        relatorio.manutencoes_atualizadas = resultado['atualizados']
        relatorio.erros.extend(resultado['erros'])

    # 2. Orçamentos
    if orcamentos_file:
        resultado = importar_orcamentos(orcamentos_file)
        relatorio.orcamentos_inseridos = resultado['inseridos']
        relatorio.orcamentos_atualizados = resultado['atualizados']
        relatorio.erros.extend(resultado['erros'])

    # 3. Itens
    if itens_file:
        resultado = importar_itens(itens_file)
        relatorio.itens_inseridos = resultado['inseridos']
        relatorio.erros.extend(resultado['erros'])

    # 4. Multas
    if multas_file:
        resultado = importar_multas(multas_file)
        relatorio.multas_inseridas = resultado['inseridos']
        relatorio.multas_ignoradas = resultado['ignorados']
        relatorio.erros.extend(resultado['erros'])

    # Rebuild FTS5 index after import
    if itens_file or orcamentos_file:
        from apps.pesquisa.fts import rebuild_fts
        rebuild_fts()

    # Invalidar cache de KPIs e gráficos
    from django.core.cache import cache
    cache.clear()

    return relatorio
