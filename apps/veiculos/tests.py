from django.test import TestCase, Client
from django.db import IntegrityError
from django.urls import reverse
from .models import Veiculo


class VeiculoModelTest(TestCase):
    def setUp(self):
        self.veiculo = Veiculo.objects.create(
            placa='ABC1234', marca='HONDA', modelo='FIT LXL 1.4', unidade='Serviços Gerais',
        )

    def test_criar_veiculo(self):
        self.assertEqual(self.veiculo.placa, 'ABC1234')
        self.assertTrue(self.veiculo.ativo)

    def test_placa_unica(self):
        with self.assertRaises(IntegrityError):
            Veiculo.objects.create(placa='ABC1234', marca='VW', modelo='Gol')

    def test_str(self):
        self.assertIn('ABC1234', str(self.veiculo))

    def test_ordering(self):
        Veiculo.objects.create(placa='AAA0001', marca='FORD', modelo='Ka')
        veiculos = list(Veiculo.objects.values_list('placa', flat=True))
        self.assertEqual(veiculos[0], 'AAA0001')

    def test_unidade_blank(self):
        v = Veiculo.objects.create(placa='XYZ9999', marca='NISSAN', modelo='Frontier')
        self.assertEqual(v.unidade, '')


class VeiculoListaViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        for i in range(30):
            Veiculo.objects.create(placa=f'TST{i:04d}', marca='VW', modelo='Gol')

    def test_lista_status_200(self):
        response = self.client.get(reverse('veiculos:lista'))
        self.assertEqual(response.status_code, 200)

    def test_lista_paginacao(self):
        response = self.client.get(reverse('veiculos:lista'))
        self.assertEqual(len(response.context['page']), 25)

    def test_lista_filtro_busca(self):
        Veiculo.objects.create(placa='HONDA001', marca='HONDA', modelo='Civic')
        response = self.client.get(reverse('veiculos:lista'), {'q': 'HONDA'})
        self.assertTrue(any('HONDA' in str(v.placa) or 'HONDA' in v.marca for v in response.context['page']))

    def test_lista_filtro_ativo(self):
        Veiculo.objects.create(placa='INATIVO1', marca='FORD', modelo='Ka', ativo=False)
        response = self.client.get(reverse('veiculos:lista'), {'ativo': '0'})
        for v in response.context['page']:
            self.assertFalse(v.ativo)


class VeiculoCriarViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_criar_get(self):
        response = self.client.get(reverse('veiculos:criar'))
        self.assertEqual(response.status_code, 200)

    def test_criar_post_valido(self):
        response = self.client.post(reverse('veiculos:criar'), {
            'placa': 'NEW1234',
            'marca': 'TOYOTA',
            'modelo': 'Corolla',
            'unidade': '',
            'ativo': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Veiculo.objects.filter(placa='NEW1234').exists())

    def test_criar_post_placa_duplicada(self):
        Veiculo.objects.create(placa='DUP1234', marca='VW', modelo='Gol')
        response = self.client.post(reverse('veiculos:criar'), {
            'placa': 'DUP1234',
            'marca': 'FORD',
            'modelo': 'Ka',
            'ativo': True,
        })
        self.assertEqual(response.status_code, 200)  # Form re-rendered with errors


class VeiculoEditarViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.veiculo = Veiculo.objects.create(placa='EDT1234', marca='VW', modelo='Gol')

    def test_editar_get(self):
        response = self.client.get(reverse('veiculos:editar', args=['EDT1234']))
        self.assertEqual(response.status_code, 200)

    def test_editar_post(self):
        response = self.client.post(reverse('veiculos:editar', args=['EDT1234']), {
            'placa': 'EDT1234',
            'marca': 'FORD',
            'modelo': 'Ka',
            'unidade': 'Nova Unidade',
            'ativo': True,
        })
        self.assertEqual(response.status_code, 302)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.marca, 'FORD')


class VeiculoDetalheViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.veiculo = Veiculo.objects.create(placa='DET1234', marca='VW', modelo='Gol')

    def test_detalhe(self):
        response = self.client.get(reverse('veiculos:detalhe', args=['DET1234']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DET1234')

    def test_detalhe_404(self):
        response = self.client.get(reverse('veiculos:detalhe', args=['NAOEXISTE']))
        self.assertEqual(response.status_code, 404)


class AutocompleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        Veiculo.objects.create(placa='PLACA13', marca='HONDA', modelo='FIT')
        Veiculo.objects.create(placa='PLACA17', marca='HONDA', modelo='FIT')

    def test_autocomplete_curto(self):
        response = self.client.get(reverse('veiculos:autocomplete'), {'q': 'J'})
        self.assertEqual(response.json(), [])

    def test_autocomplete_resultados(self):
        response = self.client.get(reverse('veiculos:autocomplete'), {'q': 'PLA'})
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertIn('placa', data[0])
