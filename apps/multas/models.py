from django.db import models


class Multa(models.Model):
    SITUACAO_CHOICES = [
        ('EM ABERTO', 'Em Aberto'),
        ('PAGA', 'Paga'),
        ('CONTESTADA', 'Contestada'),
        ('BAIXADA', 'Baixada'),
    ]

    auto_infracao = models.CharField(max_length=50, unique=True)
    veiculo = models.ForeignKey(
        'veiculos.Veiculo',
        on_delete=models.PROTECT,
        to_field='placa',
        db_column='placa',
        related_name='multas',
    )
    orgao_autuador = models.CharField(max_length=200, blank=True, default='')
    data_infracao = models.DateField()
    hora_infracao = models.TimeField(null=True, blank=True)
    descricao_infracao = models.TextField(blank=True, default='')
    local_infracao = models.CharField(max_length=300, blank=True, default='')
    data_notificacao = models.DateField(null=True, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    protocolo_sei = models.CharField(max_length=100, blank=True, default='')
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default='EM ABERTO')
    observacao = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-data_infracao']
        verbose_name = 'Multa'
        verbose_name_plural = 'Multas'

    def __str__(self):
        return f'Auto {self.auto_infracao} — {self.veiculo_id}'
