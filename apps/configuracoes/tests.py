from decimal import Decimal
from django.test import TestCase, Client
from django.db import IntegrityError
from django.urls import reverse
from .models import KPIConfig


class KPIConfigModelTest(TestCase):
    def setUp(self):
        self.kpi = KPIConfig.objects.create(
            chave='custo_maximo_os',
            descricao='Custo máximo aceitável por OS',
            valor=Decimal('5000.00'),
            unidade='R$',
        )

    def test_criar_kpi(self):
        self.assertEqual(self.kpi.chave, 'custo_maximo_os')
        self.assertEqual(self.kpi.valor, Decimal('5000.00'))

    def test_chave_unica(self):
        with self.assertRaises(IntegrityError):
            KPIConfig.objects.create(
                chave='custo_maximo_os', descricao='Dup', valor=Decimal('1000'),
            )

    def test_str(self):
        self.assertIn('custo_maximo_os', str(self.kpi))


class KPIConfigViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_kpis_page_loads(self):
        response = self.client.get(reverse('configuracoes:kpis'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Configurações de KPI')

    def test_defaults_criados(self):
        self.client.get(reverse('configuracoes:kpis'))
        self.assertTrue(KPIConfig.objects.filter(chave='custo_maximo_os').exists())
        self.assertTrue(KPIConfig.objects.filter(chave='sla_dias_execucao').exists())

    def test_editar_valor(self):
        self.client.get(reverse('configuracoes:kpis'))  # create defaults
        kpi = KPIConfig.objects.get(chave='custo_maximo_os')
        response = self.client.post(reverse('configuracoes:kpis'), {
            f'valor_{kpi.id}': '7500.00',
        })
        self.assertEqual(response.status_code, 302)
        kpi.refresh_from_db()
        self.assertEqual(kpi.valor, Decimal('7500.00'))

    def test_editar_valor_formato_br(self):
        self.client.get(reverse('configuracoes:kpis'))
        kpi = KPIConfig.objects.get(chave='sla_dias_execucao')
        self.client.post(reverse('configuracoes:kpis'), {
            f'valor_{kpi.id}': '20,50',
        })
        kpi.refresh_from_db()
        self.assertEqual(kpi.valor, Decimal('20.50'))
