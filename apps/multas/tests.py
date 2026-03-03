import io
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse

from apps.veiculos.models import Veiculo
from apps.importacao.parsers.multas import importar_multas
from .models import Multa


def _make_csv(rows):
    header = 'Placa;Auto Infração;Orgão Autuador;Data Infração;Hora Infração;Descrição da Infração;Local Infração;Data da Notif. de Autuação;Valor da Multa'
    lines = [header]
    for row in rows:
        lines.append(';'.join(row))
    return io.StringIO('\n'.join(lines))


class ImportarMultasTest(TestCase):
    def setUp(self):
        Veiculo.objects.create(placa='ABC1234', marca='VW', modelo='Gol')

    def test_importar_multa_basica(self):
        csv = _make_csv([
            ['ABC1234', 'AI-001', 'DETRAN-DF', '15/01/2026', '14:30',
             'Avançar sinal vermelho', 'QNL 1', '20/01/2026', '293,47'],
        ])
        resultado = importar_multas(csv)
        self.assertEqual(resultado['inseridos'], 1)
        self.assertEqual(resultado['ignorados'], 0)
        multa = Multa.objects.get(auto_infracao='AI-001')
        self.assertEqual(multa.veiculo.placa, 'ABC1234')
        self.assertEqual(multa.valor, Decimal('293.47'))
        self.assertEqual(multa.situacao, 'EM ABERTO')
        self.assertEqual(multa.data_infracao.day, 15)
        self.assertIsNotNone(multa.hora_infracao)

    def test_duplicata_ignorada(self):
        csv1 = _make_csv([
            ['ABC1234', 'AI-002', 'DETRAN-DF', '10/02/2026', '08:00',
             'Excesso de velocidade', 'BR-040 km 5', '15/02/2026', '880,41'],
        ])
        importar_multas(csv1)
        csv2 = _make_csv([
            ['ABC1234', 'AI-002', 'DETRAN-DF', '10/02/2026', '08:00',
             'Excesso de velocidade', 'BR-040 km 5', '15/02/2026', '880,41'],
        ])
        resultado = importar_multas(csv2)
        self.assertEqual(resultado['inseridos'], 0)
        self.assertEqual(resultado['ignorados'], 1)
        self.assertEqual(Multa.objects.filter(auto_infracao='AI-002').count(), 1)

    def test_placa_inexistente_gera_erro(self):
        csv = _make_csv([
            ['ZZZ9999', 'AI-003', 'DETRAN-DF', '10/02/2026', '',
             'Estacionar em local proibido', 'SQN 308', '', '195,23'],
        ])
        resultado = importar_multas(csv)
        self.assertEqual(resultado['inseridos'], 0)
        self.assertEqual(len(resultado['erros']), 1)
        self.assertEqual(resultado['erros'][0]['tipo'], 'FK_AUSENTE')

    def test_campos_opcionais_vazios(self):
        csv = _make_csv([
            ['ABC1234', 'AI-004', '', '20/01/2026', '', '', '', '', '100,00'],
        ])
        resultado = importar_multas(csv)
        self.assertEqual(resultado['inseridos'], 1)
        multa = Multa.objects.get(auto_infracao='AI-004')
        self.assertIsNone(multa.hora_infracao)
        self.assertIsNone(multa.data_notificacao)
        self.assertEqual(multa.orgao_autuador, '')

    def test_auto_infracao_vazio_gera_erro(self):
        csv = _make_csv([
            ['ABC1234', '', 'DETRAN-DF', '10/02/2026', '', 'Desc', '', '', '100,00'],
        ])
        resultado = importar_multas(csv)
        self.assertEqual(resultado['inseridos'], 0)
        self.assertEqual(len(resultado['erros']), 1)
        self.assertEqual(resultado['erros'][0]['tipo'], 'CAMPO_OBRIGATORIO')


class MultaViewTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        User.objects.create_user(username='testuser', password='testpass')
        v = Veiculo.objects.create(placa='ABC1234', marca='VW', modelo='Gol', unidade='Sede')
        Multa.objects.create(
            auto_infracao='AI-100', veiculo=v, data_infracao='2026-01-15',
            descricao_infracao='Avançar sinal vermelho', valor=Decimal('293.47'),
        )
        Multa.objects.create(
            auto_infracao='AI-101', veiculo=v, data_infracao='2026-02-10',
            descricao_infracao='Excesso de velocidade', valor=Decimal('880.41'),
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

    def test_lista_carrega(self):
        response = self.client.get(reverse('multas:lista'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 2)

    def test_pesquisa_por_placa(self):
        response = self.client.get(reverse('multas:lista'), {'q': 'ABC1234'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 2)

    def test_pesquisa_por_descricao(self):
        response = self.client.get(reverse('multas:lista'), {'q': 'velocidade'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 1)

    def test_pesquisa_sem_resultado(self):
        response = self.client.get(reverse('multas:lista'), {'q': 'XYZINEXISTENTE'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page'].paginator.count, 0)

    def test_por_pagina(self):
        response = self.client.get(reverse('multas:lista'), {'por_pagina': '15'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['por_pagina'], '15')

    def test_por_pagina_invalido_usa_padrao(self):
        response = self.client.get(reverse('multas:lista'), {'por_pagina': '99'})
        self.assertEqual(response.context['por_pagina'], '20')

    def test_editar_carrega(self):
        response = self.client.get(reverse('multas:editar', args=['AI-100']))
        self.assertEqual(response.status_code, 200)

    def test_editar_salva(self):
        response = self.client.post(reverse('multas:editar', args=['AI-100']), {
            'protocolo_sei': 'SEI-2026/001',
            'situacao': 'PAGA',
            'observacao': 'Paga via GRU',
        })
        self.assertRedirects(response, reverse('multas:lista'))
        multa = Multa.objects.get(auto_infracao='AI-100')
        self.assertEqual(multa.protocolo_sei, 'SEI-2026/001')
        self.assertEqual(multa.situacao, 'PAGA')
        self.assertEqual(multa.observacao, 'Paga via GRU')

    def test_editar_nao_altera_campos_csv(self):
        """Campos importados do CSV não são editáveis pelo form."""
        response = self.client.post(reverse('multas:editar', args=['AI-100']), {
            'protocolo_sei': '',
            'situacao': 'CONTESTADA',
            'observacao': '',
            'valor': '999.99',
            'descricao_infracao': 'Hackeado',
        })
        multa = Multa.objects.get(auto_infracao='AI-100')
        self.assertEqual(multa.valor, Decimal('293.47'))
        self.assertEqual(multa.descricao_infracao, 'Avançar sinal vermelho')
