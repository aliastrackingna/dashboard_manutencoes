from django.db import models


class Veiculo(models.Model):
    placa = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=200)
    unidade = models.CharField(max_length=100, blank=True, default='FUB')
    ativo = models.BooleanField(default=True)
    observacao = models.TextField(blank=True, default='', verbose_name='Observação')

    class Meta:
        ordering = ['placa']

    def __str__(self):
        return f'{self.placa} — {self.marca} {self.modelo}'
