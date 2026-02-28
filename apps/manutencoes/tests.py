from datetime import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from apps.veiculos.models import Veiculo
from .models import Manutencao, Orcamento, ItemOrcamento


class ManutencaoModelTest(TestCase):
    def setUp(self):
        self.veiculo = Veiculo.objects.create(
            placa='PLACA77', marca='VW', modelo='Kombi 1.4 flex'
        )
        self.manutencao = Manutencao.objects.create(
            numero_os='2026 - 59',
            tipo='3',
            empresa='EMPRESA FANTASMA',
            setor='Serviços Gerais',
            veiculo=self.veiculo,
            data_abertura=timezone.make_aware(datetime(2026, 2, 4, 13, 1)),
            descricao='Troca de óleo e filtros',
            status='Orçamentação',
        )

    def test_criar_manutencao(self):
        self.assertEqual(self.manutencao.numero_os, '2026 - 59')

    def test_numero_os_unico(self):
        with self.assertRaises(IntegrityError):
            Manutencao.objects.create(
                numero_os='2026 - 59', veiculo=self.veiculo,
                data_abertura=timezone.now(), status='Lançada',
            )

    def test_str(self):
        self.assertIn('2026 - 59', str(self.manutencao))

    def test_fk_veiculo_protect(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.veiculo.delete()


class OrcamentoModelTest(TestCase):
    def setUp(self):
        self.veiculo = Veiculo.objects.create(placa='PLACA13', marca='HONDA', modelo='FIT')
        self.manutencao = Manutencao.objects.create(
            numero_os='2026 - 85', veiculo=self.veiculo,
            data_abertura=timezone.make_aware(datetime(2026, 2, 12, 10, 16)),
            status='Em Execução',
        )
        self.orcamento = Orcamento.objects.create(
            manutencao=self.manutencao, codigo_orcamento=426,
            data=datetime(2026, 2, 13).date(),
            oficina='UNION AUTO PARTS', valor=Decimal('2883.60'), status='Recusado',
        )

    def test_criar_orcamento(self):
        self.assertEqual(self.orcamento.codigo_orcamento, 426)

    def test_codigo_orcamento_unico(self):
        with self.assertRaises(IntegrityError):
            Orcamento.objects.create(
                manutencao=self.manutencao, codigo_orcamento=426,
                data=datetime(2026, 2, 13).date(),
                oficina='Outra', valor=Decimal('100'), status='Lançado',
            )

    def test_cascade_delete(self):
        self.manutencao.delete()
        self.assertEqual(Orcamento.objects.count(), 0)


class ItemOrcamentoModelTest(TestCase):
    def setUp(self):
        veiculo = Veiculo.objects.create(placa='PLACA13', marca='HONDA', modelo='FIT')
        manutencao = Manutencao.objects.create(
            numero_os='2026 - 85', veiculo=veiculo,
            data_abertura=timezone.make_aware(datetime(2026, 2, 12, 10, 16)),
            status='Em Execução',
        )
        self.orcamento = Orcamento.objects.create(
            manutencao=manutencao, codigo_orcamento=426,
            data=datetime(2026, 2, 13).date(),
            oficina='UNION', valor=Decimal('2883.60'), status='Recusado',
        )
        self.item = ItemOrcamento.objects.create(
            orcamento=self.orcamento, tipo='PCA', grupo='Original',
            codigo_item='10W30', descricao='OLEO MOTOR', marca='TOTAL',
            valor_unit=Decimal('31.15'), qtd=Decimal('4.000'),
            total=Decimal('124.60'), garantia=datetime(2026, 5, 14).date(),
        )

    def test_criar_item(self):
        self.assertEqual(self.item.tipo, 'PCA')

    def test_cascade_orcamento(self):
        self.orcamento.delete()
        self.assertEqual(ItemOrcamento.objects.count(), 0)

    def test_str(self):
        self.assertIn('OLEO MOTOR', str(self.item))


class ManutencaoDetalheViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        v = Veiculo.objects.create(placa='PLACA13', marca='HONDA', modelo='FIT')
        self.m = Manutencao.objects.create(
            numero_os='2026 - 85', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 12, 10, 16)),
            status='Em Execução', descricao='Troca de óleo',
            valor_total=Decimal('2306.05'),
        )
        orc = Orcamento.objects.create(
            manutencao=self.m, codigo_orcamento=438,
            data=datetime(2026, 2, 19).date(),
            oficina='TOTAUTO', valor=Decimal('2306.05'), status='Em Execução',
        )
        ItemOrcamento.objects.create(
            orcamento=orc, tipo='PCA', descricao='OLEO MOTOR',
            valor_unit=Decimal('41.16'), qtd=Decimal('4'), total=Decimal('164.65'),
        )

    def test_detalhe_status_200(self):
        response = self.client.get(reverse('manutencoes:detalhe', args=['2026 - 85']))
        self.assertEqual(response.status_code, 200)

    def test_detalhe_conteudo(self):
        response = self.client.get(reverse('manutencoes:detalhe', args=['2026 - 85']))
        self.assertContains(response, '2026 - 85')
        self.assertContains(response, 'OLEO MOTOR')
        self.assertContains(response, 'TOTAUTO')

    def test_detalhe_404(self):
        response = self.client.get(reverse('manutencoes:detalhe', args=['INEXISTENTE']))
        self.assertEqual(response.status_code, 404)

    def test_detalhe_orcamentos_context(self):
        response = self.client.get(reverse('manutencoes:detalhe', args=['2026 - 85']))
        self.assertEqual(len(response.context['orcamentos']), 1)
