from datetime import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.veiculos.models import Veiculo
from apps.manutencoes.models import Manutencao, Orcamento, ItemOrcamento
from .kpis import calcular_kpis, dados_graficos, _periodo_anterior


class KPIsTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Veiculo.objects.create(placa='TST0001', marca='VW', modelo='Gol')
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def _criar_os(self, numero, status='Executada', valor=Decimal('1000'), **kwargs):
        defaults = {
            'numero_os': numero,
            'veiculo': self.v,
            'data_abertura': timezone.make_aware(datetime(2026, 2, 10)),
            'status': status,
            'valor_total': valor,
        }
        defaults.update(kwargs)
        return Manutencao.objects.create(**defaults)

    def test_total_os(self):
        self._criar_os('OS-1')
        self._criar_os('OS-2', status='Orçamentação')
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertEqual(kpis['total_os'], 2)

    def test_valor_total_executado(self):
        self._criar_os('OS-1', valor=Decimal('500'))
        self._criar_os('OS-2', valor=Decimal('300'))
        self._criar_os('OS-3', status='Orçamentação', valor=Decimal('9999'))
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertAlmostEqual(kpis['valor_total_executado'], 800.0)

    def test_ticket_medio(self):
        self._criar_os('OS-1', valor=Decimal('200'))
        self._criar_os('OS-2', valor=Decimal('400'))
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertAlmostEqual(kpis['ticket_medio'], 300.0)

    def test_pct_prazo(self):
        self._criar_os('OS-1',
            data_previsao=timezone.make_aware(datetime(2026, 2, 20)),
            data_encerramento=timezone.make_aware(datetime(2026, 2, 18)),
        )
        self._criar_os('OS-2',
            data_previsao=timezone.make_aware(datetime(2026, 2, 15)),
            data_encerramento=timezone.make_aware(datetime(2026, 2, 25)),
        )
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertEqual(kpis['pct_prazo'], 50.0)

    def test_tempo_medio_resolucao(self):
        self._criar_os('OS-1',
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)),
            data_encerramento=timezone.make_aware(datetime(2026, 2, 11)),
        )
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertAlmostEqual(kpis['tempo_medio_dias'], 10.0)

    def test_sem_dados(self):
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertEqual(kpis['total_os'], 0)
        self.assertEqual(kpis['ticket_medio'], 0)
        self.assertEqual(kpis['pct_prazo'], 0)


class DadosGraficosTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Veiculo.objects.create(placa='TST0001', marca='VW', modelo='Gol')
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_os_por_status(self):
        Manutencao.objects.create(numero_os='OS-1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Executada')
        Manutencao.objects.create(numero_os='OS-2', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Orçamentação')
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertIn('Executada', graficos['os_por_status'])
        self.assertIn('Orçamentação', graficos['os_por_status'])

    def test_evolucao_mensal(self):
        Manutencao.objects.create(numero_os='OS-1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 1, 15)), status='Executada')
        Manutencao.objects.create(numero_os='OS-2', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 15)), status='Executada')
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertEqual(len(graficos['evolucao_mensal']['labels']), 2)

    def test_top_veiculos(self):
        Manutencao.objects.create(numero_os='OS-1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)),
            status='Executada', valor_total=Decimal('5000'))
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertEqual(len(graficos['top_veiculos']), 1)
        self.assertEqual(graficos['top_veiculos'][0]['placa'], 'TST0001')

    def test_os_por_setor(self):
        Manutencao.objects.create(numero_os='OS-1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)),
            status='Executada', setor='Garagem')
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertIn('Garagem', graficos['os_por_setor'])


class DashboardViewsTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

    def test_index(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('kpis', response.context)
        self.assertIn('graficos', response.context)

    def test_index_periodo_30d(self):
        response = self.client.get(reverse('dashboard:index'), {'periodo': '30d'})
        self.assertEqual(response.status_code, 200)

    def test_api_kpis(self):
        response = self.client.get(reverse('dashboard:api_kpis'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_os', data)

    def test_api_graficos(self):
        response = self.client.get(reverse('dashboard:api_graficos'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('os_por_status', data)

    def test_lista_drilldown(self):
        response = self.client.get(reverse('dashboard:lista'))
        self.assertEqual(response.status_code, 200)

    def test_lista_drilldown_filtro_status(self):
        v = Veiculo.objects.create(placa='TST0001', marca='VW', modelo='Gol')
        Manutencao.objects.create(numero_os='OS-1', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Executada')
        Manutencao.objects.create(numero_os='OS-2', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Orçamentação')
        response = self.client.get(reverse('dashboard:lista'), {'filtro': 'status', 'valor': 'Executada'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)

    def test_lista_drilldown_filtro_setor(self):
        v = Veiculo.objects.create(placa='TST0002', marca='FIAT', modelo='Uno')
        Manutencao.objects.create(numero_os='OS-S1', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 5)), status='Executada', setor='Transporte')
        Manutencao.objects.create(numero_os='OS-S2', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 6)), status='Executada', setor='Garagem')
        response = self.client.get(reverse('dashboard:lista'), {'filtro': 'setor', 'valor': 'Transporte'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)
        self.assertEqual(response.context['titulo'], 'OS — Setor: Transporte')

    def test_lista_drilldown_filtro_veiculo(self):
        v = Veiculo.objects.create(placa='VEI0001', marca='VW', modelo='Gol')
        Manutencao.objects.create(numero_os='OS-V1', veiculo=v,
            data_abertura=timezone.now(), status='Executada')
        response = self.client.get(reverse('dashboard:lista'), {'filtro': 'veiculo', 'valor': 'VEI0001'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)
        self.assertEqual(response.context['titulo'], 'OS — Veículo: VEI0001')

    def test_lista_drilldown_filtro_mes(self):
        v = Veiculo.objects.create(placa='MES0001', marca='FORD', modelo='Ka')
        Manutencao.objects.create(numero_os='OS-M1', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)), status='Executada')
        Manutencao.objects.create(numero_os='OS-M2', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 3, 10)), status='Executada')
        response = self.client.get(reverse('dashboard:lista'), {'filtro': 'mes', 'valor': 'Feb/2026'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)

    def test_lista_drilldown_filtro_mes_invalido(self):
        response = self.client.get(reverse('dashboard:lista'), {'filtro': 'mes', 'valor': 'invalido'})
        self.assertEqual(response.status_code, 200)


class GetPeriodoTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

    def test_periodo_60d(self):
        response = self.client.get(reverse('dashboard:index'), {'periodo': '60d'})
        self.assertEqual(response.status_code, 200)

    def test_periodo_90d(self):
        response = self.client.get(reverse('dashboard:index'), {'periodo': '90d'})
        self.assertEqual(response.status_code, 200)

    def test_periodo_custom(self):
        response = self.client.get(reverse('dashboard:index'), {
            'periodo': 'custom', 'inicio': '2026-01-01', 'fim': '2026-06-30',
        })
        self.assertEqual(response.status_code, 200)

    def test_periodo_custom_invalido(self):
        response = self.client.get(reverse('dashboard:index'), {
            'periodo': 'custom', 'inicio': 'abc', 'fim': 'xyz',
        })
        self.assertEqual(response.status_code, 200)


class FiltroUnidadeTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.v_abc = Veiculo.objects.create(placa='UNI0001', marca='VW', modelo='Gol', unidade='ABC')
        self.v_xyz = Veiculo.objects.create(placa='UNI0002', marca='FIAT', modelo='Uno', unidade='XYZ')
        self.v_sem = Veiculo.objects.create(placa='UNI0003', marca='FORD', modelo='Ka', unidade='')
        dt_abertura = timezone.make_aware(datetime(2026, 2, 10))
        Manutencao.objects.create(numero_os='OS-U1', veiculo=self.v_abc,
            data_abertura=dt_abertura, status='Executada', valor_total=Decimal('100'))
        Manutencao.objects.create(numero_os='OS-U2', veiculo=self.v_xyz,
            data_abertura=dt_abertura, status='Executada', valor_total=Decimal('200'))
        Manutencao.objects.create(numero_os='OS-U3', veiculo=self.v_sem,
            data_abertura=dt_abertura, status='Executada', valor_total=Decimal('300'))

    def test_dashboard_sem_filtro_retorna_tudo(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['kpis']['total_os'], 3)

    def test_dashboard_filtro_unidade(self):
        response = self.client.get(reverse('dashboard:index'), {'unidade': 'ABC'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['kpis']['total_os'], 1)

    def test_dashboard_filtro_sem_unidade(self):
        response = self.client.get(reverse('dashboard:index'), {'unidade': '__sem__'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['kpis']['total_os'], 1)

    def test_lista_drilldown_filtro_unidade(self):
        response = self.client.get(reverse('dashboard:lista'), {'unidade': 'XYZ'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)
        placas = [os.veiculo.placa for os in response.context['page']]
        self.assertEqual(placas, ['UNI0002'])

    def test_lista_drilldown_filtro_sem_unidade(self):
        response = self.client.get(reverse('dashboard:lista'), {'unidade': '__sem__'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)
        placas = [os.veiculo.placa for os in response.context['page']]
        self.assertEqual(placas, ['UNI0003'])

    def test_lista_drilldown_filtro_drilldown_unidade(self):
        response = self.client.get(reverse('dashboard:lista'), {'filtro': 'unidade', 'valor': 'ABC'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)
        placas = [os.veiculo.placa for os in response.context['page']]
        self.assertEqual(placas, ['UNI0001'])
        self.assertIn('Unidade', response.context['titulo'])

    def test_api_kpis_filtro_unidade(self):
        response = self.client.get(reverse('dashboard:api_kpis'), {'unidade': 'ABC'})
        data = response.json()
        self.assertEqual(data['total_os'], 1)

    def test_api_graficos_filtro_unidade(self):
        response = self.client.get(reverse('dashboard:api_graficos'), {'unidade': 'ABC'})
        data = response.json()
        self.assertEqual(sum(data['os_por_status'].values()), 1)

    def test_unidades_no_contexto(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertIn('unidades', response.context)
        self.assertIn('ABC', response.context['unidades'])
        self.assertIn('XYZ', response.context['unidades'])
        self.assertNotIn('', response.context['unidades'])

    def test_kpis_direto_com_unidade(self):
        inicio = timezone.make_aware(datetime(2026, 1, 1))
        fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))
        kpis = calcular_kpis(inicio, fim, unidade='ABC')
        self.assertEqual(kpis['total_os'], 1)
        self.assertAlmostEqual(kpis['valor_total_executado'], 100.0)

    def test_kpis_direto_sem_unidade(self):
        inicio = timezone.make_aware(datetime(2026, 1, 1))
        fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))
        kpis = calcular_kpis(inicio, fim, unidade='')
        self.assertEqual(kpis['total_os'], 1)
        self.assertAlmostEqual(kpis['valor_total_executado'], 300.0)


class DadosGraficosInsightsTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Veiculo.objects.create(placa='INS0001', marca='VW', modelo='Gol')
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_oficinas_insight(self):
        m = Manutencao.objects.create(numero_os='OS-OFC1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Executada')
        Orcamento.objects.create(manutencao=m, codigo_orcamento=7001,
            data=datetime(2026, 2, 2).date(), oficina='MECANICA CENTRAL', valor=Decimal('500'), status='Escolhido')
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertIn('MECANICA CENTRAL', graficos['oficinas_insight'])

    def test_tipo_insight_pecas(self):
        m = Manutencao.objects.create(numero_os='OS-TIP1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Executada')
        orc = Orcamento.objects.create(manutencao=m, codigo_orcamento=7002,
            data=datetime(2026, 2, 2).date(), oficina='OFICINA X', valor=Decimal('1000'), status='Escolhido')
        ItemOrcamento.objects.create(orcamento=orc, tipo='PCA', descricao='FILTRO',
            valor_unit=Decimal('100'), qtd=Decimal('3'), total=Decimal('300'))
        ItemOrcamento.objects.create(orcamento=orc, tipo='SRV', descricao='MAO DE OBRA',
            valor_unit=Decimal('50'), qtd=Decimal('1'), total=Decimal('50'))
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertIn('Peças', graficos['tipo_insight'])

    def test_tipo_insight_servicos(self):
        m = Manutencao.objects.create(numero_os='OS-TIP2', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Executada')
        orc = Orcamento.objects.create(manutencao=m, codigo_orcamento=7003,
            data=datetime(2026, 2, 2).date(), oficina='OFICINA Y', valor=Decimal('1000'), status='Executado')
        ItemOrcamento.objects.create(orcamento=orc, tipo='PCA', descricao='PARAFUSO',
            valor_unit=Decimal('5'), qtd=Decimal('1'), total=Decimal('5'))
        ItemOrcamento.objects.create(orcamento=orc, tipo='SRV', descricao='RETIFICA',
            valor_unit=Decimal('500'), qtd=Decimal('1'), total=Decimal('500'))
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertIn('Serviços', graficos['tipo_insight'])

    def test_sem_dados_insights_vazios(self):
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertEqual(graficos['status_insight'], '')
        self.assertEqual(graficos['evolucao_insight'], '')
        self.assertEqual(graficos['veiculos_insight'], '')
        self.assertEqual(graficos['oficinas_insight'], '')
        self.assertEqual(graficos['tipo_insight'], '')
        self.assertEqual(graficos['setor_insight'], '')


class PeriodoAnteriorTest(TestCase):
    def test_periodo_anterior_calculo(self):
        inicio = timezone.make_aware(datetime(2026, 3, 1))
        fim = timezone.make_aware(datetime(2026, 3, 31, 23, 59, 59))
        ant_inicio, ant_fim = _periodo_anterior(inicio, fim)
        # Duração ~31 dias, anterior deveria terminar em inicio
        self.assertEqual(ant_fim, inicio)
        self.assertTrue(ant_inicio < ant_fim)

    def test_periodo_anterior_none_quando_todos(self):
        ant_inicio, ant_fim = _periodo_anterior(None, timezone.now())
        self.assertIsNone(ant_inicio)
        self.assertIsNone(ant_fim)


class TendenciasTest(TestCase):
    def setUp(self):
        self.v = Veiculo.objects.create(placa='TND0001', marca='VW', modelo='Gol')

    def test_tendencias_com_dados_em_dois_periodos(self):
        # Período anterior: jan
        Manutencao.objects.create(
            numero_os='OS-T1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 1, 15)),
            status='Executada', valor_total=Decimal('1000'),
        )
        # Período atual: fev
        Manutencao.objects.create(
            numero_os='OS-T2', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 15)),
            status='Executada', valor_total=Decimal('2000'),
        )
        inicio = timezone.make_aware(datetime(2026, 2, 1))
        fim = timezone.make_aware(datetime(2026, 2, 28, 23, 59, 59))
        kpis = calcular_kpis(inicio, fim)
        self.assertIsNotNone(kpis['tendencias'])
        self.assertEqual(kpis['tendencias']['valor_total_executado'], 100.0)

    def test_tendencia_none_quando_periodo_todos(self):
        kpis = calcular_kpis(None, timezone.now())
        self.assertIsNone(kpis['tendencias'])


class CustoPorVeiculoTest(TestCase):
    def setUp(self):
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_custo_por_veiculo_multiplos(self):
        v1 = Veiculo.objects.create(placa='CPV0001', marca='VW', modelo='Gol')
        v2 = Veiculo.objects.create(placa='CPV0002', marca='FIAT', modelo='Uno')
        Manutencao.objects.create(
            numero_os='OS-C1', veiculo=v1,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('1000'),
        )
        Manutencao.objects.create(
            numero_os='OS-C2', veiculo=v2,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('3000'),
        )
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertAlmostEqual(kpis['custo_por_veiculo'], 2000.0)

    def test_custo_por_veiculo_sem_dados(self):
        kpis = calcular_kpis(self.inicio, self.fim)
        self.assertEqual(kpis['custo_por_veiculo'], 0)


class CacheKPIsTest(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Veiculo.objects.create(placa='CAC0001', marca='VW', modelo='Gol')
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_cache_e_usado(self):
        from django.core.cache import cache
        Manutencao.objects.create(
            numero_os='OS-CC1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('500'),
        )
        kpis1 = calcular_kpis(self.inicio, self.fim)
        # Segundo call deve vir do cache (mesmo resultado)
        kpis2 = calcular_kpis(self.inicio, self.fim)
        self.assertEqual(kpis1, kpis2)

    def test_cache_invalidado_apos_clear(self):
        from django.core.cache import cache
        from apps.dashboard.kpis import _cache_key, CACHE_TIMEOUT
        # Colocar valor manualmente no cache
        chave = _cache_key('kpis', self.inicio, self.fim, None)
        cache.set(chave, {'fake': True}, CACHE_TIMEOUT)
        self.assertEqual(cache.get(chave), {'fake': True})
        # Limpar cache (como faz o pipeline)
        cache.clear()
        self.assertIsNone(cache.get(chave))


class EvolucaoTipoTest(TestCase):
    """Feature 4: Evolução mensal peças vs serviços."""
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Veiculo.objects.create(placa='EVT0001', marca='VW', modelo='Gol')
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_evolucao_tipo_com_itens(self):
        m1 = Manutencao.objects.create(numero_os='OS-ET1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 1, 15)), status='Executada')
        orc1 = Orcamento.objects.create(manutencao=m1, codigo_orcamento=8001,
            data=datetime(2026, 1, 16).date(), oficina='OFC1', valor=Decimal('500'), status='Escolhido')
        ItemOrcamento.objects.create(orcamento=orc1, tipo='PCA', descricao='FILTRO',
            valor_unit=Decimal('100'), qtd=Decimal('2'), total=Decimal('200'))
        ItemOrcamento.objects.create(orcamento=orc1, tipo='SRV', descricao='MAO DE OBRA',
            valor_unit=Decimal('150'), qtd=Decimal('1'), total=Decimal('150'))

        m2 = Manutencao.objects.create(numero_os='OS-ET2', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 15)), status='Executada')
        orc2 = Orcamento.objects.create(manutencao=m2, codigo_orcamento=8002,
            data=datetime(2026, 2, 16).date(), oficina='OFC1', valor=Decimal('300'), status='Executado')
        ItemOrcamento.objects.create(orcamento=orc2, tipo='PCA', descricao='OLEO',
            valor_unit=Decimal('80'), qtd=Decimal('1'), total=Decimal('80'))

        graficos = dados_graficos(self.inicio, self.fim)
        self.assertEqual(len(graficos['evolucao_tipo']['labels']), 2)
        self.assertEqual(len(graficos['evolucao_tipo']['pca']), 2)
        self.assertAlmostEqual(graficos['evolucao_tipo']['pca'][0], 200.0)


class ScatterVeiculosTest(TestCase):
    """Feature 5: Scatter plot outliers por veículo."""
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_scatter_com_multiplos_veiculos(self):
        v1 = Veiculo.objects.create(placa='SCA0001', marca='VW', modelo='Gol')
        v2 = Veiculo.objects.create(placa='SCA0002', marca='FIAT', modelo='Uno')
        Manutencao.objects.create(numero_os='OS-SC1', veiculo=v1,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('1000'))
        Manutencao.objects.create(numero_os='OS-SC2', veiculo=v1,
            data_abertura=timezone.make_aware(datetime(2026, 3, 10)),
            status='Executada', valor_total=Decimal('2000'))
        Manutencao.objects.create(numero_os='OS-SC3', veiculo=v2,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('500'))
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertEqual(len(graficos['scatter_veiculos']), 2)
        # v1 tem maior custo, deve ser primeiro
        self.assertEqual(graficos['scatter_veiculos'][0]['placa'], 'SCA0001')
        self.assertEqual(graficos['scatter_veiculos'][0]['qtd_os'], 2)
        self.assertAlmostEqual(graficos['scatter_veiculos'][0]['custo_total'], 3000.0)


class ValorMedioOficinaTest(TestCase):
    """Feature 6: Valor médio por oficina."""
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Veiculo.objects.create(placa='VMO0001', marca='VW', modelo='Gol')
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_valor_medio_presente(self):
        m = Manutencao.objects.create(numero_os='OS-VM1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1)), status='Executada')
        Orcamento.objects.create(manutencao=m, codigo_orcamento=9001,
            data=datetime(2026, 2, 2).date(), oficina='OFICINA TESTE', valor=Decimal('500'), status='Escolhido')
        Orcamento.objects.create(manutencao=m, codigo_orcamento=9002,
            data=datetime(2026, 2, 3).date(), oficina='OFICINA TESTE', valor=Decimal('300'), status='Recusado')
        graficos = dados_graficos(self.inicio, self.fim)
        self.assertTrue(len(graficos['top_oficinas']) > 0)
        ofc = graficos['top_oficinas'][0]
        self.assertIn('valor_medio', ofc)
        self.assertAlmostEqual(ofc['valor_medio'], 400.0)


class MediaMovelTest(TestCase):
    """Feature 7: Média móvel 3 meses na evolução."""
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.v = Veiculo.objects.create(placa='MMA0001', marca='VW', modelo='Gol')
        self.inicio = timezone.make_aware(datetime(2026, 1, 1))
        self.fim = timezone.make_aware(datetime(2026, 12, 31, 23, 59, 59))

    def test_media_movel_com_dados_suficientes(self):
        for i, m in enumerate([1, 2, 3, 4], 1):
            Manutencao.objects.create(
                numero_os=f'OS-MM{i}', veiculo=self.v,
                data_abertura=timezone.make_aware(datetime(2026, m, 15)),
                status='Executada',
            )
        # Adicionar mais uma OS em março para variação
        Manutencao.objects.create(
            numero_os='OS-MM5', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 3, 20)),
            status='Executada',
        )
        graficos = dados_graficos(self.inicio, self.fim)
        mm = graficos['evolucao_mensal']['media_movel']
        self.assertEqual(len(mm), 4)
        self.assertIsNone(mm[0])
        self.assertIsNone(mm[1])
        # Mês 3 (index 2): média de [1, 1, 2] = 1.3
        self.assertAlmostEqual(mm[2], 1.3, places=1)

    def test_media_movel_dados_insuficientes(self):
        Manutencao.objects.create(
            numero_os='OS-MMI1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 1, 15)),
            status='Executada',
        )
        graficos = dados_graficos(self.inicio, self.fim)
        mm = graficos['evolucao_mensal']['media_movel']
        self.assertEqual(len(mm), 1)
        self.assertIsNone(mm[0])


class ThresholdsTest(TestCase):
    """Feature 8: Thresholds visuais nos KPI cards."""
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.v = Veiculo.objects.create(placa='THR0001', marca='VW', modelo='Gol')
        Manutencao.objects.create(
            numero_os='OS-TH1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('5000'),
        )

    def test_thresholds_no_contexto(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertIn('thresholds', response.context)

    def test_threshold_borda_vermelha_quando_acima(self):
        from apps.configuracoes.models import KPIConfig
        # ticket_medio é menor=melhor, valor atual = 5000, threshold = 1000 → vermelho
        KPIConfig.objects.create(chave='ticket_medio', descricao='Ticket', valor=Decimal('1000'))
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.context['thresholds']['ticket_medio'], 'border-red-500')

    def test_threshold_borda_verde_quando_abaixo(self):
        from apps.configuracoes.models import KPIConfig
        # ticket_medio é menor=melhor, valor atual = 5000, threshold = 10000 → verde
        KPIConfig.objects.create(chave='ticket_medio', descricao='Ticket', valor=Decimal('10000'))
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.context['thresholds']['ticket_medio'], 'border-green-500')


class ExportarCSVTest(TestCase):
    """Feature 9: Exportação de dados para CSV."""
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.v = Veiculo.objects.create(placa='EXP0001', marca='VW', modelo='Gol', unidade='ABC')
        Manutencao.objects.create(
            numero_os='OS-EX1', veiculo=self.v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('500'),
        )

    def test_csv_content_type(self):
        response = self.client.get(reverse('dashboard:exportar_csv'))
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_csv_contem_dados(self):
        response = self.client.get(reverse('dashboard:exportar_csv'))
        content = response.content.decode('utf-8')
        self.assertIn('OS-EX1', content)
        self.assertIn('EXP0001', content)

    def test_csv_com_filtro_unidade(self):
        v2 = Veiculo.objects.create(placa='EXP0002', marca='FIAT', modelo='Uno', unidade='XYZ')
        Manutencao.objects.create(
            numero_os='OS-EX2', veiculo=v2,
            data_abertura=timezone.make_aware(datetime(2026, 2, 10)),
            status='Executada', valor_total=Decimal('300'),
        )
        response = self.client.get(reverse('dashboard:exportar_csv'), {'unidade': 'ABC'})
        content = response.content.decode('utf-8')
        self.assertIn('OS-EX1', content)
        self.assertNotIn('OS-EX2', content)


class TooltipsTest(TestCase):
    """Feature 10: Tooltips de contexto nos KPIs."""
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

    def test_tooltips_presentes_no_html(self):
        response = self.client.get(reverse('dashboard:index'))
        content = response.content.decode('utf-8')
        self.assertIn('title="', content)
        self.assertIn('(i)', content)
