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
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
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


class CompararOrcamentosViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        v = Veiculo.objects.create(placa='CMP0001', marca='FIAT', modelo='UNO')
        self.m = Manutencao.objects.create(
            numero_os='2026 - 100', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 15, 9, 0)),
            status='Orçamentação',
        )
        self.orc1 = Orcamento.objects.create(
            manutencao=self.m, codigo_orcamento=901,
            data=datetime(2026, 2, 16).date(),
            oficina='OFICINA ALPHA', valor=Decimal('1500.00'), status='Lançado',
        )
        self.orc2 = Orcamento.objects.create(
            manutencao=self.m, codigo_orcamento=902,
            data=datetime(2026, 2, 17).date(),
            oficina='OFICINA BETA', valor=Decimal('1200.00'), status='Escolhido',
        )
        # Item presente em ambos orçamentos
        ItemOrcamento.objects.create(
            orcamento=self.orc1, tipo='PCA', codigo_item='FLT001',
            descricao='FILTRO DE OLEO', valor_unit=Decimal('45.00'),
            qtd=Decimal('1'), total=Decimal('45.00'),
        )
        ItemOrcamento.objects.create(
            orcamento=self.orc2, tipo='PCA', codigo_item='FLT001',
            descricao='FILTRO DE OLEO', valor_unit=Decimal('38.00'),
            qtd=Decimal('1'), total=Decimal('38.00'),
        )
        # Item exclusivo do orc1
        ItemOrcamento.objects.create(
            orcamento=self.orc1, tipo='SRV', descricao='ALINHAMENTO',
            valor_unit=Decimal('80.00'), qtd=Decimal('1'), total=Decimal('80.00'),
        )

    def _criar_historico_item(self, descricao, data_abertura, status_os='Executada', placa='CMP0001'):
        veiculo = Veiculo.objects.get(placa=placa)
        manutencao_hist = Manutencao.objects.create(
            numero_os=f'2025 - {Manutencao.objects.count() + 100}',
            veiculo=veiculo,
            data_abertura=timezone.make_aware(data_abertura),
            data_encerramento=timezone.make_aware(data_abertura),
            status=status_os,
        )
        orc_hist = Orcamento.objects.create(
            manutencao=manutencao_hist,
            codigo_orcamento=9000 + Orcamento.objects.count(),
            data=data_abertura.date(),
            oficina='OFICINA HISTORICO',
            valor=Decimal('200.00'),
            status='Executado',
        )
        ItemOrcamento.objects.create(
            orcamento=orc_hist,
            tipo='PCA',
            descricao=descricao,
            valor_unit=Decimal('40.00'),
            qtd=Decimal('1'),
            total=Decimal('40.00'),
        )

    def test_comparar_pagina_carrega(self):
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'manutencoes/comparar.html')

    def test_comparar_redireciona_com_menos_de_2(self):
        v2 = Veiculo.objects.create(placa='CMP0002', marca='VW', modelo='GOL')
        m2 = Manutencao.objects.create(
            numero_os='2026 - 101', veiculo=v2,
            data_abertura=timezone.make_aware(datetime(2026, 2, 18, 10, 0)),
            status='Lançada',
        )
        Orcamento.objects.create(
            manutencao=m2, codigo_orcamento=903,
            data=datetime(2026, 2, 19).date(),
            oficina='OFICINA GAMA', valor=Decimal('500.00'), status='Lançado',
        )
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 101']))
        self.assertRedirects(response, reverse('manutencoes:detalhe', args=['2026 - 101']))

    def test_comparar_mostra_oficinas(self):
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']))
        self.assertContains(response, 'OFICINA ALPHA')
        self.assertContains(response, 'OFICINA BETA')

    def test_comparar_identifica_item_exclusivo(self):
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']))
        # O item ALINHAMENTO só existe no orc1, então a linha deve ser marcada como exclusiva
        for linha in response.context['linhas']:
            if linha['descricao'] == 'ALINHAMENTO':
                self.assertTrue(linha['exclusivo'])
                break
        else:
            self.fail('Item ALINHAMENTO não encontrado nas linhas de comparação')

    def test_comparar_404(self):
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['INEXISTENTE']))
        self.assertEqual(response.status_code, 404)

    def test_comparar_itens_mesmo_valor(self):
        """Itens com valores iguais não devem ter classe menor/maior."""
        ItemOrcamento.objects.create(
            orcamento=self.orc2, tipo='SRV', descricao='BALANCEAMENTO',
            valor_unit=Decimal('60.00'), qtd=Decimal('1'), total=Decimal('60.00'),
        )
        ItemOrcamento.objects.create(
            orcamento=self.orc1, tipo='SRV', descricao='BALANCEAMENTO',
            valor_unit=Decimal('60.00'), qtd=Decimal('1'), total=Decimal('60.00'),
        )
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']))
        for linha in response.context['linhas']:
            if linha['descricao'] == 'BALANCEAMENTO':
                for celula in linha['celulas']:
                    self.assertEqual(celula['classe'], '')
                break

    def test_comparar_ordenacao_alfabetica(self):
        """Linhas devem estar em ordem alfabética pela descrição."""
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']))
        descricoes = [l['descricao'] for l in response.context['linhas']]
        self.assertEqual(descricoes, sorted(descricoes))

    def test_comparar_descricao_uppercase(self):
        """Descrições devem estar em uppercase."""
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']))
        for linha in response.context['linhas']:
            self.assertEqual(linha['descricao'], linha['descricao'].upper())

    def test_comparar_oficina_curta(self):
        """Oficina curta deve cortar no primeiro - ou =."""
        v2 = Veiculo.objects.create(placa='CMP0003', marca='RENAULT', modelo='SANDERO')
        m2 = Manutencao.objects.create(
            numero_os='2026 - 102', veiculo=v2,
            data_abertura=timezone.make_aware(datetime(2026, 2, 20, 8, 0)),
            status='Orçamentação',
        )
        orc_a = Orcamento.objects.create(
            manutencao=m2, codigo_orcamento=910,
            data=datetime(2026, 2, 21).date(),
            oficina='AUTO PECAS - CENTRO', valor=Decimal('800.00'), status='Lançado',
        )
        orc_b = Orcamento.objects.create(
            manutencao=m2, codigo_orcamento=911,
            data=datetime(2026, 2, 22).date(),
            oficina='MECANICA SILVA = FILIAL 2', valor=Decimal('900.00'), status='Lançado',
        )
        ItemOrcamento.objects.create(
            orcamento=orc_a, tipo='PCA', descricao='PASTILHA FREIO',
            valor_unit=Decimal('120.00'), qtd=Decimal('1'), total=Decimal('120.00'),
        )
        ItemOrcamento.objects.create(
            orcamento=orc_b, tipo='PCA', descricao='PASTILHA FREIO',
            valor_unit=Decimal('130.00'), qtd=Decimal('1'), total=Decimal('130.00'),
        )
        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 102']))
        oficinas_curtas = [o.oficina_curta for o in response.context['orcamentos']]
        self.assertIn('AUTO PECAS', oficinas_curtas)
        self.assertIn('MECANICA SILVA', oficinas_curtas)

    def test_comparar_historico_mesmo_veiculo_os_executada(self):
        self._criar_historico_item(
            descricao='FILTRO DE OLEO',
            data_abertura=datetime(2025, 12, 20, 8, 0),
            status_os='Executada',
            placa='CMP0001',
        )

        response = self.client.get(
            reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']),
        )

        linha = next(l for l in response.context['linhas'] if l['descricao'] == 'FILTRO DE OLEO')
        self.assertIsNotNone(linha['historico'])
        self.assertEqual(linha['historico']['oficina'], 'OFICINA HISTORICO')
        self.assertTrue(linha['historico']['alerta_repeticao'])

    def test_comparar_historico_ignora_os_nao_executada(self):
        self._criar_historico_item(
            descricao='FILTRO DE OLEO',
            data_abertura=datetime(2025, 12, 20, 8, 0),
            status_os='Orçamentação',
            placa='CMP0001',
        )

        response = self.client.get(
            reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']),
        )

        linha = next(l for l in response.context['linhas'] if l['descricao'] == 'FILTRO DE OLEO')
        self.assertIsNone(linha['historico'])

    def test_comparar_historico_fora_da_janela_sem_alerta(self):
        self._criar_historico_item(
            descricao='FILTRO DE OLEO',
            data_abertura=datetime(2023, 1, 10, 8, 0),
            status_os='Executada',
            placa='CMP0001',
        )

        response = self.client.get(
            reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']),
        )

        linha = next(l for l in response.context['linhas'] if l['descricao'] == 'FILTRO DE OLEO')
        self.assertIsNotNone(linha['historico'])
        self.assertFalse(linha['historico']['alerta_repeticao'])

    def test_comparar_historico_ignora_outro_veiculo(self):
        Veiculo.objects.create(placa='CMP9999', marca='GM', modelo='ONIX')
        self._criar_historico_item(
            descricao='FILTRO DE OLEO',
            data_abertura=datetime(2025, 12, 20, 8, 0),
            status_os='Executada',
            placa='CMP9999',
        )

        response = self.client.get(
            reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']),
        )

        linha = next(l for l in response.context['linhas'] if l['descricao'] == 'FILTRO DE OLEO')
        self.assertIsNone(linha['historico'])

    def test_comparar_historico_duas_trocas_lista_somente_ultima(self):
        self._criar_historico_item(
            descricao='FILTRO DE OLEO',
            data_abertura=datetime(2025, 6, 10, 8, 0),
            status_os='Executada',
            placa='CMP0001',
        )
        self._criar_historico_item(
            descricao='FILTRO DE OLEO',
            data_abertura=datetime(2025, 12, 20, 8, 0),
            status_os='Executada',
            placa='CMP0001',
        )

        response = self.client.get(reverse('manutencoes:comparar_orcamentos', args=['2026 - 100']))

        linha = next(l for l in response.context['linhas'] if l['descricao'] == 'FILTRO DE OLEO')
        self.assertIsNotNone(linha['historico'])
        self.assertEqual(linha['historico']['data'].date(), datetime(2025, 12, 20).date())


class AnalisePrecosViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        v = Veiculo.objects.create(placa='ANL0001', marca='FIAT', modelo='UNO')
        self.m = Manutencao.objects.create(
            numero_os='2026 - 200', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 3, 1, 9, 0)),
            status='Orçamentação',
        )
        self.orc = Orcamento.objects.create(
            manutencao=self.m, codigo_orcamento=2001,
            data=datetime(2026, 3, 2).date(),
            oficina='OFICINA TESTE', valor=Decimal('500.00'), status='Escolhido',
        )
        self.item = ItemOrcamento.objects.create(
            orcamento=self.orc, tipo='PCA', descricao='FILTRO DE OLEO',
            marca='TECFIL', valor_unit=Decimal('50.00'),
            qtd=Decimal('1'), total=Decimal('50.00'),
        )

        # Criar histórico: outra OS com orçamento aprovado e mesmo item
        v2 = Veiculo.objects.create(placa='ANL0002', marca='VW', modelo='GOL')
        self.m_hist = Manutencao.objects.create(
            numero_os='2026 - 201', veiculo=v2,
            data_abertura=timezone.make_aware(datetime(2026, 1, 10, 8, 0)),
            status='Executada',
        )
        orc_hist = Orcamento.objects.create(
            manutencao=self.m_hist, codigo_orcamento=2002,
            data=datetime(2026, 1, 11).date(),
            oficina='OFICINA HIST', valor=Decimal('300.00'), status='Executado',
        )
        ItemOrcamento.objects.create(
            orcamento=orc_hist, tipo='PCA', descricao='FILTRO DE OLEO',
            marca='MANN', valor_unit=Decimal('40.00'),
            qtd=Decimal('1'), total=Decimal('40.00'),
        )

    def test_analise_precos_sem_orcamentos(self):
        v = Veiculo.objects.create(placa='ANL0003', marca='CHEVROLET', modelo='ONIX')
        m = Manutencao.objects.create(
            numero_os='2026 - 202', veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 3, 5, 10, 0)),
            status='Aberta',
        )
        response = self.client.get(reverse('manutencoes:analise_precos', args=['2026 - 202']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_itens'], 0)

    def test_analise_precos_com_historico(self):
        response = self.client.get(reverse('manutencoes:analise_precos', args=['2026 - 200']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_itens'], 1)
        analise = response.context['analise']
        item_analise = analise[0]
        self.assertEqual(item_analise['ocorrencias'], 1)
        self.assertIsNotNone(item_analise['valor_mediana'])
        self.assertIn(item_analise['alerta'], ['baixo', 'medio', 'alto'])
        # Preço atual 50, média 40 → variação +25%
        self.assertAlmostEqual(float(item_analise['variacao']), 25.0, places=1)
        self.assertEqual(item_analise['classificacao'], 'acima')

    def test_analise_precos_sem_historico(self):
        # Item novo sem ocorrências anteriores
        ItemOrcamento.objects.create(
            orcamento=self.orc, tipo='SRV', descricao='SERVICO EXCLUSIVO',
            valor_unit=Decimal('200.00'), qtd=Decimal('1'), total=Decimal('200.00'),
        )
        response = self.client.get(reverse('manutencoes:analise_precos', args=['2026 - 200']))
        analise = response.context['analise']
        item_novo = next(a for a in analise if a['descricao'] == 'SERVICO EXCLUSIVO')
        self.assertEqual(item_novo['classificacao'], 'sem_historico')
        self.assertIsNone(item_novo['variacao'])

    def test_analise_precos_exclui_propria_os(self):
        # Adicionar outro orçamento aprovado na mesma OS com mesmo item
        orc2 = Orcamento.objects.create(
            manutencao=self.m, codigo_orcamento=2003,
            data=datetime(2026, 3, 3).date(),
            oficina='OFICINA OUTRA', valor=Decimal('600.00'), status='Executado',
        )
        ItemOrcamento.objects.create(
            orcamento=orc2, tipo='PCA', descricao='FILTRO DE OLEO',
            marca='WEGA', valor_unit=Decimal('999.00'),
            qtd=Decimal('1'), total=Decimal('999.00'),
        )
        response = self.client.get(reverse('manutencoes:analise_precos', args=['2026 - 200']))
        analise = response.context['analise']
        item_analise = next(a for a in analise if a['descricao'] == 'FILTRO DE OLEO')
        # Histórico deve ter apenas 1 ocorrência (da outra OS), não incluir a própria
        self.assertEqual(item_analise['ocorrencias'], 1)
        self.assertAlmostEqual(float(item_analise['valor_medio']), 40.0, places=2)

    def test_analise_precos_apenas_aprovados(self):
        # Criar orçamento recusado em outra OS — não deve entrar no histórico
        v3 = Veiculo.objects.create(placa='ANL0004', marca='TOYOTA', modelo='COROLLA')
        m3 = Manutencao.objects.create(
            numero_os='2026 - 203', veiculo=v3,
            data_abertura=timezone.make_aware(datetime(2026, 2, 1, 8, 0)),
            status='Orçamentação',
        )
        orc_recusado = Orcamento.objects.create(
            manutencao=m3, codigo_orcamento=2004,
            data=datetime(2026, 2, 2).date(),
            oficina='OFICINA RECUSADA', valor=Decimal('800.00'), status='Recusado',
        )
        ItemOrcamento.objects.create(
            orcamento=orc_recusado, tipo='PCA', descricao='FILTRO DE OLEO',
            marca='FRAM', valor_unit=Decimal('999.00'),
            qtd=Decimal('1'), total=Decimal('999.00'),
        )
        response = self.client.get(reverse('manutencoes:analise_precos', args=['2026 - 200']))
        analise = response.context['analise']
        item_analise = next(a for a in analise if a['descricao'] == 'FILTRO DE OLEO')
        # Só deve contar a ocorrência aprovada (valor_medio=40), não a recusada (999)
        self.assertEqual(item_analise['ocorrencias'], 1)
        self.assertAlmostEqual(float(item_analise['valor_medio']), 40.0, places=2)

    def test_analise_precos_usa_chave_canonica_para_variacoes(self):
        v3 = Veiculo.objects.create(placa='ANL0005', marca='FORD', modelo='KA')
        m3 = Manutencao.objects.create(
            numero_os='2026 - 204', veiculo=v3,
            data_abertura=timezone.make_aware(datetime(2026, 2, 5, 8, 0)),
            status='Executada',
        )
        orc_hist = Orcamento.objects.create(
            manutencao=m3, codigo_orcamento=2005,
            data=datetime(2026, 2, 6).date(),
            oficina='OFICINA VARIACAO', valor=Decimal('350.00'), status='Executado',
        )
        ItemOrcamento.objects.create(
            orcamento=orc_hist, tipo='PCA', descricao='FILTRO / DE OLEO',
            marca='BOSCH', valor_unit=Decimal('60.00'),
            qtd=Decimal('1'), total=Decimal('60.00'),
        )

        response = self.client.get(reverse('manutencoes:analise_precos', args=['2026 - 200']))
        analise = response.context['analise']
        item_analise = next(a for a in analise if a['descricao'] == 'FILTRO DE OLEO')

        self.assertEqual(item_analise['ocorrencias'], 2)
        self.assertAlmostEqual(float(item_analise['valor_medio']), 50.0, places=2)
