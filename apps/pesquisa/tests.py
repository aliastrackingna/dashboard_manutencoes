from datetime import datetime
from decimal import Decimal
from django.test import TransactionTestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.db import connection
from apps.veiculos.models import Veiculo
from apps.manutencoes.models import Manutencao, Orcamento, ItemOrcamento
from .fts import criar_tabela_fts, rebuild_fts, buscar_itens, get_grupos


def _drop_fts():
    with connection.cursor() as c:
        c.execute("DROP TABLE IF EXISTS itens_fts")
        for t in ['itens_fts_ai', 'itens_fts_ad', 'itens_fts_au']:
            c.execute(f"DROP TRIGGER IF EXISTS {t}")


def _setup_data():
    v = Veiculo.objects.create(placa='TST0001', marca='VW', modelo='Gol')
    m = Manutencao.objects.create(
        numero_os='OS-1', veiculo=v,
        data_abertura=timezone.make_aware(datetime(2026, 2, 1)),
        status='Executada',
    )
    orc = Orcamento.objects.create(
        manutencao=m, codigo_orcamento=100,
        data=datetime(2026, 2, 1).date(),
        oficina='Oficina Test', valor=Decimal('1000'), status='Executado',
    )
    ItemOrcamento.objects.create(
        orcamento=orc, tipo='PCA', grupo='Filtros',
        codigo_item='10W30', descricao='OLEO MOTOR', marca='TOTAL',
        valor_unit=Decimal('31.15'), qtd=Decimal('4'), total=Decimal('124.60'),
    )
    ItemOrcamento.objects.create(
        orcamento=orc, tipo='SRV', grupo='Serviço Geral',
        codigo_item='SERV', descricao='ALINHAMENTO E BALANCEAMENTO', marca='-',
        valor_unit=Decimal('178.00'), qtd=Decimal('1'), total=Decimal('178.00'),
    )
    ItemOrcamento.objects.create(
        orcamento=orc, tipo='PCA', grupo='Filtros',
        codigo_item='PLACA12', descricao='FILTRO DE OLEO', marca='WEGA',
        valor_unit=Decimal('53.40'), qtd=Decimal('1'), total=Decimal('53.40'),
    )
    # Orçamento recusado com item exclusivo
    orc_recusado = Orcamento.objects.create(
        manutencao=m, codigo_orcamento=101,
        data=datetime(2026, 2, 1).date(),
        oficina='Oficina Recusada', valor=Decimal('2000'), status='Recusado',
    )
    ItemOrcamento.objects.create(
        orcamento=orc_recusado, tipo='PCA', grupo='Filtros',
        codigo_item='PLACA99', descricao='PASTILHA DE FREIO', marca='FRAS-LE',
        valor_unit=Decimal('120.00'), qtd=Decimal('2'), total=Decimal('240.00'),
    )
    return orc


class FTSBaseTest(TransactionTestCase):
    def setUp(self):
        _drop_fts()
        criar_tabela_fts()
        _setup_data()
        rebuild_fts()

    def tearDown(self):
        _drop_fts()

    def test_criar_tabela(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='itens_fts'")
            self.assertIsNotNone(cursor.fetchone())

    def test_triggers_criados(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'itens_fts%'")
            triggers = [r[0] for r in cursor.fetchall()]
        self.assertIn('itens_fts_ai', triggers)
        self.assertIn('itens_fts_ad', triggers)
        self.assertIn('itens_fts_au', triggers)

    def test_buscar_por_descricao(self):
        resultados = buscar_itens('OLEO')
        self.assertTrue(len(resultados) > 0)
        self.assertEqual(resultados[0]['descricao'], 'OLEO MOTOR')

    def test_buscar_por_marca(self):
        resultados = buscar_itens('WEGA')
        self.assertTrue(len(resultados) > 0)

    def test_buscar_filtro_tipo(self):
        resultados = buscar_itens('', tipo='SRV')
        self.assertTrue(all(r['tipo'] == 'SRV' for r in resultados))

    def test_buscar_sem_resultado(self):
        resultados = buscar_itens('XYZINEXISTENTE')
        self.assertEqual(len(resultados), 0)

    def test_get_grupos(self):
        grupos = get_grupos()
        self.assertIn('Filtros', grupos)
        self.assertIn('Serviço Geral', grupos)

    def test_buscar_prefixo(self):
        resultados = buscar_itens('FILT')
        self.assertTrue(len(resultados) > 0)

    def test_trigger_insert_sync(self):
        """Novo item inserido após criar FTS deve aparecer automaticamente via trigger."""
        orc = Orcamento.objects.first()
        ItemOrcamento.objects.create(
            orcamento=orc, tipo='PCA', grupo='Baterias',
            descricao='BATERIA 60AH', marca='MOURA',
            valor_unit=Decimal('450'), qtd=Decimal('1'), total=Decimal('450'),
        )
        resultados = buscar_itens('BATERIA')
        self.assertTrue(len(resultados) > 0)

    def test_trigger_delete_sync(self):
        """Item deletado deve sumir do FTS via trigger."""
        item = ItemOrcamento.objects.filter(descricao='OLEO MOTOR').first()
        item.delete()
        resultados = buscar_itens('OLEO MOTOR')
        self.assertEqual(len(resultados), 0)


class PesquisaViewTest(TransactionTestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        User.objects.create_user(username='testuser', password='testpass')
        _drop_fts()
        criar_tabela_fts()
        _setup_data()
        rebuild_fts()
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

    def tearDown(self):
        _drop_fts()

    def test_pagina_carrega(self):
        response = self.client.get(reverse('pesquisa:itens'))
        self.assertEqual(response.status_code, 200)

    def test_busca_retorna_resultados(self):
        response = self.client.get(reverse('pesquisa:itens'), {'q': 'FILTRO'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['resultados']) > 0)

    def test_busca_sem_resultados(self):
        response = self.client.get(reverse('pesquisa:itens'), {'q': 'XYZINEXISTENTE'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['resultados']), 0)

    def test_filtro_tipo(self):
        response = self.client.get(reverse('pesquisa:itens'), {'tipo': 'PCA'})
        self.assertEqual(response.status_code, 200)

    def test_filtro_aprovado_exclui_recusado(self):
        """Com aprovado=1, itens de orçamentos recusados não aparecem."""
        response = self.client.get(reverse('pesquisa:itens'), {'q': 'PASTILHA', 'aprovado': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['resultados']), 0)

    def test_filtro_aprovado_mantem_executado(self):
        """Com aprovado=1, itens de orçamentos aprovados continuam aparecendo."""
        response = self.client.get(reverse('pesquisa:itens'), {'q': 'OLEO', 'aprovado': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['resultados']) > 0)
        descricoes = [r['descricao'] for r in response.context['resultados']]
        self.assertIn('OLEO MOTOR', descricoes)

    def test_sem_filtro_aprovado_mostra_todos(self):
        """Sem aprovado, itens de todos os orçamentos aparecem."""
        response = self.client.get(reverse('pesquisa:itens'), {'q': 'PASTILHA'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context['resultados']) > 0)
        descricoes = [r['descricao'] for r in response.context['resultados']]
        self.assertIn('PASTILHA DE FREIO', descricoes)

    def test_agrupar_variacoes_por_chave_canonica(self):
        orc = Orcamento.objects.get(codigo_orcamento=100)
        ItemOrcamento.objects.create(
            orcamento=orc,
            tipo='PCA',
            grupo='Filtros',
            codigo_item='PLACA-12',
            descricao='FILTRO / DE OLEO',
            marca='WEGA',
            valor_unit=Decimal('60.00'),
            qtd=Decimal('1'),
            total=Decimal('60.00'),
        )

        response = self.client.get(reverse('pesquisa:itens'), {'q': 'FILTRO'})
        self.assertEqual(response.status_code, 200)

        alvo = [r for r in response.context['resultados'] if r['codigo_item'] in ['PLACA12', 'PLACA-12']]
        self.assertEqual(len(alvo), 1)
        self.assertEqual(alvo[0]['ocorrencias'], 2)

    def test_exemplos_prioriza_cancelado_recusado_para_analise(self):
        orc_recusado = Orcamento.objects.get(codigo_orcamento=101)
        ItemOrcamento.objects.create(
            orcamento=orc_recusado,
            tipo='PCA',
            grupo='Filtros',
            codigo_item='PLACA12',
            descricao='FILTRO DE OLEO',
            marca='WEGA',
            valor_unit=Decimal('999.00'),
            qtd=Decimal('1'),
            total=Decimal('999.00'),
        )

        response = self.client.get(reverse('pesquisa:itens'), {'q': 'FILTRO'})
        self.assertEqual(response.status_code, 200)

        alvo = next(r for r in response.context['resultados'] if r['codigo_item'] == 'PLACA12')
        os_unicas = {e['os'] for e in alvo['exemplos']}
        self.assertEqual(len(os_unicas), 1)
        self.assertEqual(alvo['exemplos'][0]['orcamento'], 101)

    def test_busca_por_termos_separados_encontra_variacoes_numericas(self):
        orc = Orcamento.objects.get(codigo_orcamento=100)
        ItemOrcamento.objects.create(
            orcamento=orc,
            tipo='PCA',
            grupo='Pneus',
            codigo_item='1956515',
            descricao='PNEU DUNLOP',
            marca='DUNLOP',
            valor_unit=Decimal('650.00'),
            qtd=Decimal('1'),
            total=Decimal('650.00'),
        )
        ItemOrcamento.objects.create(
            orcamento=orc,
            tipo='PCA',
            grupo='Pneus',
            codigo_item='195 65 15',
            descricao='PNEU 195 65 15R DUNLOP',
            marca='DUNLOP',
            valor_unit=Decimal('670.00'),
            qtd=Decimal('1'),
            total=Decimal('670.00'),
        )
        ItemOrcamento.objects.create(
            orcamento=orc,
            tipo='PCA',
            grupo='Pneus',
            codigo_item='195/65/15',
            descricao='PNEU 195/65/15R DUNLOP',
            marca='DUNLOP',
            valor_unit=Decimal('690.00'),
            qtd=Decimal('1'),
            total=Decimal('690.00'),
        )
        rebuild_fts()

        response = self.client.get(reverse('pesquisa:itens'), {'q': 'DUNLOP 195 65'})
        self.assertEqual(response.status_code, 200)

        pneus = [r for r in response.context['resultados'] if 'DUNLOP' in r['descricao']]
        self.assertTrue(len(pneus) > 0)
        self.assertGreaterEqual(max(r['ocorrencias'] for r in pneus), 2)

    def test_agrupar_mesmo_item_com_e_sem_codigo(self):
        orc = Orcamento.objects.get(codigo_orcamento=100)
        ItemOrcamento.objects.create(
            orcamento=orc,
            tipo='PCA',
            grupo='Pneus',
            codigo_item='1956515',
            descricao='PNEU 195/65/15R DUNLOP',
            marca='DUNLOP',
            valor_unit=Decimal('700.00'),
            qtd=Decimal('1'),
            total=Decimal('700.00'),
        )
        ItemOrcamento.objects.create(
            orcamento=orc,
            tipo='PCA',
            grupo='Pneus',
            codigo_item='',
            descricao='PNEU 195 65 15R DUNLOP',
            marca='DUNLOP',
            valor_unit=Decimal('710.00'),
            qtd=Decimal('1'),
            total=Decimal('710.00'),
        )
        rebuild_fts()

        response = self.client.get(reverse('pesquisa:itens'), {'q': 'DUNLOP 195 65'})
        self.assertEqual(response.status_code, 200)

        pneus = [r for r in response.context['resultados'] if 'DUNLOP' in r['descricao']]
        self.assertTrue(len(pneus) > 0)
        self.assertGreaterEqual(max(r['ocorrencias'] for r in pneus), 2)
