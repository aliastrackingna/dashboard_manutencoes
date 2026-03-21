from django.conf import settings
from django.db import models


class LogAuditoria(models.Model):
    TIPO_CHOICES = [
        ('ADICAO', 'Adição'),
        ('ALTERACAO', 'Alteração'),
        ('IMPORTACAO', 'Importação'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='logs_auditoria',
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descricao = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'

    def __str__(self):
        return f'{self.criado_em:%d/%m/%Y %H:%M} — {self.descricao}'
