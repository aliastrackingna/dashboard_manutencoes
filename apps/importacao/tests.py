import io
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from apps.veiculos.models import Veiculo
from apps.manutencoes.models import Manutencao, Orcamento, ItemOrcamento
from .parsers.base import parse_decimal_br, parse_datetime_br, parse_date_br, parse_bool_flag
from .parsers.veiculos import importar_veiculos
from .parsers.manutencoes import importar_manutencoes
from .parsers.orcamentos import importar_orcamentos
from .parsers.itens import importar_itens
from .pipeline import executar_pipeline


class ParsersBaseTest(TestCase):
    def test_parse_decimal_br(self):
        self.assertEqual(parse_decimal_br('1.234,56'), Decimal('1234.56'))
        self.assertEqual(parse_decimal_br('0,00'), Decimal('0.00'))
        self.assertEqual(parse_decimal_br(''), Decimal('0'))
        self.assertEqual(parse_decimal_br('2.306,05'), Decimal('2306.05'))

    def test_parse_datetime_br(self):
        dt = parse_datetime_br('04/02/2026 13:01')
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 2)
        self.assertEqual(dt.day, 4)
        self.assertEqual(dt.hour, 13)
        self.assertEqual(dt.minute, 1)

    def test_parse_datetime_br_date_only(self):
        dt = parse_datetime_br('04/02/2026')
        self.assertEqual(dt.day, 4)
        self.assertEqual(dt.month, 2)

    def test_parse_datetime_br_empty(self):
        self.assertIsNone(parse_datetime_br(''))
        self.assertIsNone(parse_datetime_br(None))

    def test_parse_date_br(self):
        d = parse_date_br('14/05/2026')
        self.assertEqual(d.year, 2026)
        self.assertEqual(d.month, 5)
        self.assertEqual(d.day, 14)

    def test_parse_date_br_empty(self):
        self.assertIsNone(parse_date_br(''))

    def test_parse_bool_flag(self):
        self.assertTrue(parse_bool_flag('S'))
        self.assertTrue(parse_bool_flag('s'))
        self.assertFalse(parse_bool_flag(''))
        self.assertFalse(parse_bool_flag('N'))


class ImportarVeiculosTest(TestCase):
    def test_importar_veiculos_csv(self):
        csv_content = "Placa,Marca,Modelo,unidade\nABC1234,HONDA,FIT,Garagem\nXYZ5678,VW,Gol,\n"
        f = io.StringIO(csv_content)
        resultado = importar_veiculos(f)
        self.assertEqual(resultado['inseridos'], 2)
        self.assertEqual(Veiculo.objects.count(), 2)

    def test_importar_veiculos_idempotente(self):
        csv_content = "Placa,Marca,Modelo,unidade\nABC1234,HONDA,FIT,Garagem\n"
        importar_veiculos(io.StringIO(csv_content))
        importar_veiculos(io.StringIO(csv_content))
        self.assertEqual(Veiculo.objects.count(), 1)


class ImportarManutencoesTest(TestCase):
    def setUp(self):
        Veiculo.objects.create(placa='PLACA77', marca='VW', modelo='Kombi')

    def _make_csv(self, rows):
        lines = []
        for row in rows:
            lines.append(';'.join(f'"{c}"' for c in row))
        return io.StringIO('\n'.join(lines))

    def test_importar_manutencao_basica(self):
        csv = self._make_csv([
            ['', '', '', '3', '2026 - 59', 'EMPRESA TICO', 'Serviços Gerais',
             'PLACA77', '', 'Kombi 1.4 flex', '04/02/2026 13:01', '', '', '',
             'Troca de óleo', 'Orçamentação', '', '0,00', '0,00', '0,00'],
        ])
        resultado = importar_manutencoes(csv)
        self.assertEqual(resultado['inseridos'], 1)
        m = Manutencao.objects.get(numero_os='2026 - 59')
        self.assertEqual(m.status, 'Orçamentação')
        self.assertEqual(m.veiculo.placa, 'PLACA77')

    def test_importar_manutencao_update(self):
        csv1 = self._make_csv([
            ['', '', '', '3', '2026 - 59', 'UNB', 'SG', 'PLACA77', '',
             'Kombi', '04/02/2026 13:01', '', '', '', 'Desc', 'Lançada', '', '0,00', '0,00', '0,00'],
        ])
        csv2 = self._make_csv([
            ['', '', '', '3', '2026 - 59', 'UNB', 'SG', 'PLACA77', '',
             'Kombi', '04/02/2026 13:01', '', '', '', 'Desc', 'Executada', '', '100,00', '50,00', '150,00'],
        ])
        importar_manutencoes(csv1)
        resultado = importar_manutencoes(csv2)
        self.assertEqual(resultado['atualizados'], 1)
        m = Manutencao.objects.get(numero_os='2026 - 59')
        self.assertEqual(m.status, 'Executada')
        self.assertEqual(m.valor_total, Decimal('150.00'))

    def test_status_integrada_financeiro_vira_executada(self):
        csv = self._make_csv([
            ['', '', '', '3', '2026 - 70', 'UNB', 'SG', 'PLACA77', '',
             'Kombi', '04/02/2026 13:01', '', '', '', 'Desc', 'Integrada Financeiro', '', '0,00', '0,00', '0,00'],
        ])
        importar_manutencoes(csv)
        m = Manutencao.objects.get(numero_os='2026 - 70')
        self.assertEqual(m.status, 'Executada')

    def test_status_xpto_vira_executada(self):
        csv = self._make_csv([
            ['', '', '', '3', '2026 - 71', 'UNB', 'SG', 'PLACA77', '',
             'Kombi', '04/02/2026 13:01', '', '', '', 'Desc', 'XPTO', '', '0,00', '0,00', '0,00'],
        ])
        importar_manutencoes(csv)
        m = Manutencao.objects.get(numero_os='2026 - 71')
        self.assertEqual(m.status, 'Executada')

    def test_auto_criar_veiculo_se_nao_existir(self):
        csv = self._make_csv([
            ['', '', '', '3', '2026 - 99', 'UNB', 'SG', 'NEW1234', '',
             'Novo Modelo', '04/02/2026 13:01', '', '', '', 'Desc', 'Lançada', '', '0,00', '0,00', '0,00'],
        ])
        importar_manutencoes(csv)
        self.assertTrue(Veiculo.objects.filter(placa='NEW1234').exists())


class ImportarOrcamentosTest(TestCase):
    def setUp(self):
        v = Veiculo.objects.create(placa='PLACA13', marca='HONDA', modelo='FIT')
        from django.utils import timezone
        from datetime import datetime
        Manutencao.objects.create(
            numero_os='2026 - 85',
            veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 12, 10, 16)),
            status='Em Execução',
        )

    def test_importar_orcamento(self):
        csv = "numero_os,codigo_orcamento,data,oficina,valor,status\n"
        csv += '2026 - 85,426,13/02/2026,UNION AUTO PARTS,"2.883,60",Recusado\n'
        resultado = importar_orcamentos(io.StringIO(csv))
        self.assertEqual(resultado['inseridos'], 1)
        orc = Orcamento.objects.get(codigo_orcamento=426)
        self.assertEqual(orc.valor, Decimal('2883.60'))
        self.assertEqual(orc.status, 'Recusado')

    def test_orcamento_fk_ausente(self):
        csv = "numero_os,codigo_orcamento,data,oficina,valor,status\n"
        csv += '9999 - 99,999,13/02/2026,Oficina,"100,00",Lançado\n'
        resultado = importar_orcamentos(io.StringIO(csv))
        self.assertEqual(resultado['inseridos'], 0)
        self.assertEqual(len(resultado['erros']), 1)
        self.assertEqual(resultado['erros'][0]['tipo'], 'FK_AUSENTE')


class ImportarItensTest(TestCase):
    def setUp(self):
        v = Veiculo.objects.create(placa='PLACA13', marca='HONDA', modelo='FIT')
        from django.utils import timezone
        from datetime import datetime
        m = Manutencao.objects.create(
            numero_os='2026 - 85',
            veiculo=v,
            data_abertura=timezone.make_aware(datetime(2026, 2, 12, 10, 16)),
            status='Em Execução',
        )
        Orcamento.objects.create(
            manutencao=m,
            codigo_orcamento=426,
            data=datetime(2026, 2, 13).date(),
            oficina='UNION AUTO PARTS',
            valor=Decimal('2883.60'),
            status='Recusado',
        )

    def test_importar_item(self):
        csv = "codigo_orcamento,tipo,grupo,codigo_item,descricao,marca,valor_unit,qtd,total,garantia\n"
        csv += '426,PCA,Original,10W30,OLEO MOTOR,TOTAL,"31,15",4,"124,60",14/05/2026\n'
        resultado = importar_itens(io.StringIO(csv))
        self.assertEqual(resultado['inseridos'], 1)
        item = ItemOrcamento.objects.first()
        self.assertEqual(item.descricao, 'OLEO MOTOR')
        self.assertEqual(item.valor_unit, Decimal('31.15'))

    def test_delete_reinsert(self):
        csv = "codigo_orcamento,tipo,grupo,codigo_item,descricao,marca,valor_unit,qtd,total,garantia\n"
        csv += '426,PCA,Original,10W30,OLEO MOTOR,TOTAL,"31,15",4,"124,60",14/05/2026\n'
        importar_itens(io.StringIO(csv))
        self.assertEqual(ItemOrcamento.objects.count(), 1)
        # Reimport should delete old items and reinsert
        csv2 = "codigo_orcamento,tipo,grupo,codigo_item,descricao,marca,valor_unit,qtd,total,garantia\n"
        csv2 += '426,PCA,Original,10W30,OLEO MOTOR,TOTAL,"35,00",4,"140,00",\n'
        csv2 += '426,SRV,Serviço,SERV,ALINHAMENTO,-,"178,00",1,"178,00",\n'
        importar_itens(io.StringIO(csv2))
        self.assertEqual(ItemOrcamento.objects.count(), 2)
        self.assertEqual(
            ItemOrcamento.objects.filter(tipo='PCA').first().valor_unit,
            Decimal('35.00'),
        )

    def test_item_fk_ausente(self):
        csv = "codigo_orcamento,tipo,grupo,codigo_item,descricao,marca,valor_unit,qtd,total,garantia\n"
        csv += '9999,PCA,X,X,X,X,"10,00",1,"10,00",\n'
        resultado = importar_itens(io.StringIO(csv))
        self.assertEqual(resultado['inseridos'], 0)
        self.assertEqual(len(resultado['erros']), 1)


class PipelineIntegracaoTest(TestCase):
    def test_pipeline_completo(self):
        veiculos_csv = io.StringIO("Placa,Marca,Modelo,unidade\nPLACA13,HONDA,FIT,\n")
        manutencoes_csv = io.StringIO(
            '"";"";"";\"3\";\"2026 - 85\";\"UNB\";\"SG\";\"PLACA13\";\"\";\"FIT\";\"12/02/2026 10:16\";\"\";\"\";\"\";\"Desc\";\"Em Execução\";\"\";\"1.938,92\";\"367,13\";\"2.306,05\"'
        )
        orcamentos_csv = io.StringIO(
            'numero_os,codigo_orcamento,data,oficina,valor,status\n'
            '2026 - 85,426,13/02/2026,UNION,"2.883,60",Recusado\n'
        )
        itens_csv = io.StringIO(
            'codigo_orcamento,tipo,grupo,codigo_item,descricao,marca,valor_unit,qtd,total,garantia\n'
            '426,PCA,Original,10W30,OLEO MOTOR,TOTAL,"31,15",4,"124,60",14/05/2026\n'
        )

        relatorio = executar_pipeline(
            veiculos_file=veiculos_csv,
            manutencoes_file=manutencoes_csv,
            orcamentos_file=orcamentos_csv,
            itens_file=itens_csv,
        )

        self.assertEqual(relatorio.veiculos_inseridos, 1)
        self.assertEqual(relatorio.manutencoes_inseridas, 1)
        self.assertEqual(relatorio.orcamentos_inseridos, 1)
        self.assertEqual(relatorio.itens_inseridos, 1)
        self.assertFalse(relatorio.tem_erros)


class UploadViewTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_upload_page_get(self):
        client = Client()
        client.login(username='testuser', password='testpass')
        response = client.get(reverse('importacao:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Importação')

    def test_upload_sem_arquivo(self):
        client = Client()
        client.login(username='testuser', password='testpass')
        response = client.post(reverse('importacao:upload'))
        self.assertEqual(response.status_code, 200)


class RegistroImportacaoTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_str(self):
        from .models import RegistroImportacao
        registro = RegistroImportacao.objects.create()
        self.assertIn('Importação em', str(registro))

    def test_upload_cria_registro_importacao(self):
        from .models import RegistroImportacao
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.assertEqual(RegistroImportacao.objects.count(), 0)

        csv_content = b'Placa,Marca,Modelo,unidade\nABC1234,HONDA,FIT,Garagem\n'
        veiculos_file = SimpleUploadedFile('veiculos.csv', csv_content, content_type='text/csv')

        client = Client()
        client.login(username='testuser', password='testpass')
        client.post(reverse('importacao:upload'), {'veiculos': veiculos_file})

        self.assertEqual(RegistroImportacao.objects.count(), 1)
        registro = RegistroImportacao.objects.first()
        self.assertIsNotNone(registro.realizado_em)

    def test_upload_atualiza_registro_existente(self):
        from .models import RegistroImportacao
        from django.core.files.uploadedfile import SimpleUploadedFile

        RegistroImportacao.objects.create(pk=1)
        primeiro_timestamp = RegistroImportacao.objects.get(pk=1).realizado_em

        csv_content = b'Placa,Marca,Modelo,unidade\nXYZ5678,VW,Gol,\n'
        veiculos_file = SimpleUploadedFile('veiculos.csv', csv_content, content_type='text/csv')

        client = Client()
        client.login(username='testuser', password='testpass')
        client.post(reverse('importacao:upload'), {'veiculos': veiculos_file})

        self.assertEqual(RegistroImportacao.objects.count(), 1)
        segundo_timestamp = RegistroImportacao.objects.get(pk=1).realizado_em
        self.assertGreaterEqual(segundo_timestamp, primeiro_timestamp)


class ContextProcessorUltimaImportacaoTest(TestCase):
    def test_sem_importacao(self):
        from .context_processors import ultima_importacao
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        contexto = ultima_importacao(request)
        self.assertIsNone(contexto['ultima_importacao'])

    def test_com_importacao(self):
        from .context_processors import ultima_importacao
        from .models import RegistroImportacao
        from django.test import RequestFactory

        RegistroImportacao.objects.create()
        request = RequestFactory().get('/')
        contexto = ultima_importacao(request)
        self.assertIsNotNone(contexto['ultima_importacao'])
        self.assertIsNotNone(contexto['ultima_importacao'].realizado_em)

    def test_footer_mostra_nenhuma_importacao(self):
        from django.contrib.auth.models import User
        User.objects.create_user(username='testuser', password='testpass')
        client = Client()
        client.login(username='testuser', password='testpass')
        response = client.get(reverse('importacao:upload'))
        self.assertContains(response, 'Nenhuma importação realizada')

    def test_footer_mostra_data_importacao(self):
        from .models import RegistroImportacao
        from django.contrib.auth.models import User
        User.objects.create_user(username='testuser', password='testpass')
        RegistroImportacao.objects.create()

        client = Client()
        client.login(username='testuser', password='testpass')
        response = client.get(reverse('importacao:upload'))
        self.assertContains(response, 'Dados atualizados em')
        self.assertNotContains(response, 'Nenhuma importação realizada')
