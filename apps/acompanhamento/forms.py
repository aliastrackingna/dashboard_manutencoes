from django import forms

from .models import Acompanhamento

_INPUT = 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2'


class AcompanhamentoForm(forms.ModelForm):
    class Meta:
        model = Acompanhamento
        fields = ['motivo', 'prioridade', 'observacao', 'data_limite', 'finalizado']
        widgets = {
            'motivo': forms.Select(attrs={'class': _INPUT}),
            'prioridade': forms.Select(attrs={'class': _INPUT}),
            'observacao': forms.Textarea(attrs={'class': _INPUT, 'rows': 4, 'placeholder': 'Observações sobre o acompanhamento'}),
            'data_limite': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}, format='%Y-%m-%d'),
            'finalizado': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 dark:border-gray-600'}),
        }
