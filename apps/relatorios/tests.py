from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.manutencoes.models import Manutencao, Orcamento
from apps.veiculos.models import Veiculo


class RelatoriosTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test', password='test')
        cls.veiculo = Veiculo.objects.create(
            placa='ABC1234', marca='Fiat', modelo='Uno', unidade='Matriz',
        )
        cls.agora = timezone.now().replace(day=15)
        cls.os_executada = Manutencao.objects.create(
            numero_os='OS-001',
            veiculo=cls.veiculo,
            data_abertura=cls.agora,
            data_encerramento=cls.agora + timedelta(days=3),
            data_integracao=cls.agora + timedelta(days=4),
            status='Executada',
            valor_total=1500,
            inicio_execucao=cls.agora,
            fim_execucao=cls.agora + timedelta(days=3),
        )
        cls.os_aberta = Manutencao.objects.create(
            numero_os='OS-002',
            veiculo=cls.veiculo,
            data_abertura=cls.agora,
            status='Aberta',
            valor_total=500,
        )

    def setUp(self):
        self.client.login(username='test', password='test')

    def test_index_sem_mes(self):
        resp = self.client.get('/relatorios/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Selecione um mês')
        self.assertEqual(len(resp.context['ordens']), 0)

    def test_index_com_mes(self):
        mes = self.agora.strftime('%Y-%m')
        resp = self.client.get(f'/relatorios/?mes={mes}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['ordens']), 1)
        self.assertEqual(resp.context['ordens'][0]['os'].numero_os, 'OS-001')

    def test_meses_disponiveis(self):
        resp = self.client.get('/relatorios/')
        valores = [m['valor'] for m in resp.context['meses_disponiveis']]
        mes_esperado = self.agora.strftime('%Y-%m')
        self.assertIn(mes_esperado, valores)

    def test_atraso_calculado(self):
        orcamento = Orcamento.objects.create(
            manutencao=self.os_executada,
            codigo_orcamento=9001,
            data=self.agora.date(),
            oficina='Oficina Teste',
            valor=1500,
            status='Executado',
            previsao_em_dias=2,
        )
        mes = self.agora.strftime('%Y-%m')
        resp = self.client.get(f'/relatorios/?mes={mes}')
        # 3 dias de execução > 2 dias previstos = atraso
        self.assertTrue(resp.context['ordens'][0]['em_atraso'])

        # Ajustar previsão para que não haja atraso
        orcamento.previsao_em_dias = 5
        orcamento.save()
        resp = self.client.get(f'/relatorios/?mes={mes}')
        self.assertFalse(resp.context['ordens'][0]['em_atraso'])

    def test_valor_total_soma(self):
        mes = self.agora.strftime('%Y-%m')
        resp = self.client.get(f'/relatorios/?mes={mes}')
        self.assertEqual(resp.context['valor_total_soma'], 1500)
