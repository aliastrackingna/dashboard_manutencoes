from django.db import models


class RegistroImportacao(models.Model):
    realizado_em = models.DateTimeField(auto_now=True, verbose_name='realizado em')

    class Meta:
        verbose_name = 'registro de importação'
        verbose_name_plural = 'registros de importação'

    def __str__(self):
        return f'Importação em {self.realizado_em:%d/%m/%Y %H:%M}'
