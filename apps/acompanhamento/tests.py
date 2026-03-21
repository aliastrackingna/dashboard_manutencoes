from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from apps.manutencoes.models import Manutencao
from apps.veiculos.models import Veiculo

from .models import Acompanhamento


class AcompanhamentoTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.user2 = User.objects.create_user(username='otheruser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

        self.veiculo = Veiculo.objects.create(
            placa='ABC1D23',
            marca='FIAT',
            modelo='UNO',
        )
        self.manutencao = Manutencao.objects.create(
            numero_os='OS-001',
            veiculo=self.veiculo,
            status='Aberta',
            data_abertura=timezone.now(),
            valor_total=1000,
        )
        self.manutencao2 = Manutencao.objects.create(
            numero_os='OS-002',
            veiculo=self.veiculo,
            status='Em Execução',
            data_abertura=timezone.now(),
            valor_total=2000,
        )

    def test_toggle_criar_acompanhamento(self):
        resp = self.client.post(f'/acompanhamento/toggle/{self.manutencao.numero_os}/')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Acompanhamento.objects.filter(usuario=self.user, manutencao=self.manutencao).exists())

    def test_toggle_remover_acompanhamento(self):
        Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)
        resp = self.client.post(f'/acompanhamento/toggle/{self.manutencao.numero_os}/')
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Acompanhamento.objects.filter(usuario=self.user, manutencao=self.manutencao).exists())

    def test_toggle_get_nao_permitido(self):
        resp = self.client.get(f'/acompanhamento/toggle/{self.manutencao.numero_os}/')
        self.assertEqual(resp.status_code, 405)

    def test_listar_apenas_do_usuario(self):
        Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)
        Acompanhamento.objects.create(usuario=self.user2, manutencao=self.manutencao2)

        resp = self.client.get('/acompanhamento/?somente_ativas=0')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['page'].paginator.count, 1)

    def test_filtrar_somente_ativas(self):
        Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)
        Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao2, finalizado=True, finalizado_em=timezone.now())

        resp = self.client.get('/acompanhamento/?somente_ativas=1')
        self.assertEqual(resp.context['page'].paginator.count, 1)

        resp = self.client.get('/acompanhamento/?somente_ativas=0')
        self.assertEqual(resp.context['page'].paginator.count, 2)

    def test_editar_acompanhamento(self):
        acomp = Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)
        resp = self.client.post(f'/acompanhamento/{acomp.pk}/editar/', {
            'motivo': 'VALOR_ALTO',
            'prioridade': 1,
            'observacao': 'Valor muito alto',
            'data_limite': '2026-04-01',
        })
        self.assertEqual(resp.status_code, 302)
        acomp.refresh_from_db()
        self.assertEqual(acomp.motivo, 'VALOR_ALTO')
        self.assertEqual(acomp.prioridade, 1)
        self.assertEqual(acomp.observacao, 'Valor muito alto')

    def test_finalizar_acompanhamento(self):
        acomp = Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)
        resp = self.client.post(f'/acompanhamento/{acomp.pk}/editar/', {
            'motivo': 'OUTRO',
            'prioridade': 2,
            'observacao': '',
            'finalizado': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        acomp.refresh_from_db()
        self.assertTrue(acomp.finalizado)
        self.assertIsNotNone(acomp.finalizado_em)

    def test_unique_constraint(self):
        Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)
        with self.assertRaises(Exception):
            Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)

    def test_editar_de_outro_usuario_retorna_404(self):
        acomp = Acompanhamento.objects.create(usuario=self.user2, manutencao=self.manutencao)
        resp = self.client.get(f'/acompanhamento/{acomp.pk}/editar/')
        self.assertEqual(resp.status_code, 404)

    def test_busca_por_os(self):
        Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao)
        Acompanhamento.objects.create(usuario=self.user, manutencao=self.manutencao2)

        resp = self.client.get('/acompanhamento/?somente_ativas=0&q=OS-001')
        self.assertEqual(resp.context['page'].paginator.count, 1)
