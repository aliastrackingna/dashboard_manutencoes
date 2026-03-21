from django.db import models


class KPIConfig(models.Model):
    chave = models.CharField(max_length=100, unique=True)
    descricao = models.CharField(max_length=300)
    valor = models.DecimalField(max_digits=14, decimal_places=2)
    unidade = models.CharField(max_length=30, blank=True, default='')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração de KPI'
        verbose_name_plural = 'Configurações de KPI'

    def __str__(self):
        return f'{self.chave}: {self.valor} {self.unidade}'


class ConfigGeral(models.Model):
    chave = models.CharField(max_length=100, unique=True)
    valor = models.CharField(max_length=500, blank=True, default='')
    descricao = models.CharField(max_length=300, blank=True, default='')
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chave']
        verbose_name = 'Configuração geral'
        verbose_name_plural = 'Configurações gerais'

    def __str__(self):
        return f'{self.chave}: {self.valor}'
