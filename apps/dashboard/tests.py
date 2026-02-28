from datetime import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from apps.veiculos.models import Veiculo
from apps.manutencoes.models import Manutencao, Orcamento, ItemOrcamento
from .kpis import calcular_kpis, dados_graficos


class KPIsTest(TestCase):
    def setUp(self):
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
        self.client = Client()

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
        self.client = Client()

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


class DadosGraficosInsightsTest(TestCase):
    def setUp(self):
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
