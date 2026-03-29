from django.db import models

from .normalizacao import construir_chave_item_canonica


class Manutencao(models.Model):
    numero_os = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=10, blank=True, default='')
    empresa = models.CharField(max_length=200, blank=True, default='')
    setor = models.CharField(max_length=100, blank=True, default='')
    veiculo = models.ForeignKey(
        'veiculos.Veiculo',
        on_delete=models.PROTECT,
        to_field='placa',
        db_column='placa',
        related_name='manutencoes',
    )
    modelo_veiculo = models.CharField(max_length=200, blank=True, default='')
    data_abertura = models.DateTimeField()
    data_previsao = models.DateTimeField(null=True, blank=True)
    data_encerramento = models.DateTimeField(null=True, blank=True)
    data_integracao = models.DateTimeField(null=True, blank=True)
    inicio_execucao = models.DateTimeField(null=True, blank=True)
    fim_execucao = models.DateTimeField(null=True, blank=True)
    descricao = models.TextField(blank=True, default='')
    status = models.CharField(max_length=50)
    flag_especial = models.BooleanField(default=False)
    valor_pecas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_servicos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_abertura']
        verbose_name = 'Manutenção'
        verbose_name_plural = 'Manutenções'

    def __str__(self):
        return f'OS {self.numero_os} — {self.status}'


class Orcamento(models.Model):
    manutencao = models.ForeignKey(
        Manutencao,
        on_delete=models.CASCADE,
        related_name='orcamentos',
    )
    codigo_orcamento = models.IntegerField(unique=True)
    data = models.DateField()
    oficina = models.CharField(max_length=300)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30)
    previsao_em_dias = models.IntegerField(default=0)

    class Meta:
        ordering = ['codigo_orcamento']
        verbose_name = 'Orçamento'

    def __str__(self):
        return f'Orçamento {self.codigo_orcamento} — {self.oficina}'


class ItemOrcamento(models.Model):
    orcamento = models.ForeignKey(
        Orcamento,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    tipo = models.CharField(max_length=3)  # PCA | SRV
    grupo = models.CharField(max_length=100, blank=True, default='')
    codigo_item = models.CharField(max_length=50, blank=True, default='')
    codigo_item_normalizado = models.CharField(max_length=80, blank=True, default='', db_index=True)
    descricao = models.CharField(max_length=300)
    descricao_normalizada = models.CharField(max_length=350, blank=True, default='', db_index=True)
    chave_item_canonica = models.CharField(max_length=420, blank=True, default='', db_index=True)
    marca = models.CharField(max_length=100, blank=True, default='')
    valor_unit = models.DecimalField(max_digits=12, decimal_places=2)
    qtd = models.DecimalField(max_digits=10, decimal_places=3)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    garantia = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['tipo', 'descricao']
        verbose_name = 'Item de Orçamento'
        verbose_name_plural = 'Itens de Orçamento'

    def __str__(self):
        return f'{self.tipo} — {self.descricao}'

    def save(self, *args, **kwargs):
        normalizado = construir_chave_item_canonica(self.tipo, self.codigo_item, self.descricao)
        self.codigo_item_normalizado = normalizado['codigo_item_normalizado']
        self.descricao_normalizada = normalizado['descricao_normalizada']
        self.chave_item_canonica = normalizado['chave_item_canonica']
        super().save(*args, **kwargs)
