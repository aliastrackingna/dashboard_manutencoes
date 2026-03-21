from django.conf import settings
from django.db import models


class Acompanhamento(models.Model):
    MOTIVO_CHOICES = [
        ('VALOR_ALTO', 'Valor alto'),
        ('PRAZO_EXCEDIDO', 'Prazo excedido'),
        ('REINCIDENCIA', 'Reincidência de problema'),
        ('GARANTIA', 'Em garantia'),
        ('VEICULO_CRITICO', 'Veículo crítico'),
        ('ORCAMENTO_DIVERGENTE', 'Orçamento divergente'),
        ('OUTRO', 'Outro'),
    ]

    PRIORIDADE_CHOICES = [
        (1, 'Alta'),
        (2, 'Média'),
        (3, 'Baixa'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='acompanhamentos',
    )
    manutencao = models.ForeignKey(
        'manutencoes.Manutencao',
        on_delete=models.CASCADE,
        to_field='numero_os',
        related_name='acompanhamentos',
    )
    motivo = models.CharField(max_length=30, choices=MOTIVO_CHOICES, default='OUTRO')
    prioridade = models.IntegerField(choices=PRIORIDADE_CHOICES, default=2)
    observacao = models.TextField(blank=True, default='')
    data_limite = models.DateField(null=True, blank=True)
    finalizado = models.BooleanField(default=False)
    finalizado_em = models.DateTimeField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['usuario', 'manutencao']
        ordering = ['finalizado', 'prioridade', 'data_limite']
        verbose_name = 'Acompanhamento'
        verbose_name_plural = 'Acompanhamentos'

    def __str__(self):
        return f'Acompanhamento OS {self.manutencao_id} — {self.get_motivo_display()}'
