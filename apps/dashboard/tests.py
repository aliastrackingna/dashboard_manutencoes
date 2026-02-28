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
