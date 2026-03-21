from django import forms

from .models import Multa

_INPUT = 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2'


class MultaForm(forms.ModelForm):
    class Meta:
        model = Multa
        fields = [
            'auto_infracao', 'veiculo', 'orgao_autuador',
            'data_infracao', 'hora_infracao', 'descricao_infracao',
            'local_infracao', 'data_notificacao', 'valor',
            'protocolo_sei', 'situacao', 'observacao',
        ]
        widgets = {
            'auto_infracao': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nº do auto de infração'}),
            'veiculo': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Placa do veículo (ex: ABC1D23)', 'id': 'id_veiculo', 'autocomplete': 'off'}),
            'orgao_autuador': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Órgão autuador'}),
            'data_infracao': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}, format='%Y-%m-%d'),
            'hora_infracao': forms.TimeInput(attrs={'class': _INPUT, 'type': 'time'}, format='%H:%M'),
            'descricao_infracao': forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
            'local_infracao': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Local da infração'}),
            'data_notificacao': forms.DateInput(attrs={'class': _INPUT, 'type': 'date'}, format='%Y-%m-%d'),
            'valor': forms.NumberInput(attrs={'class': _INPUT, 'placeholder': '0.00', 'step': '0.01'}),
            'protocolo_sei': forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Nº do protocolo SEI'}),
            'situacao': forms.Select(attrs={'class': _INPUT}),
            'observacao': forms.Textarea(attrs={'class': _INPUT, 'rows': 3}),
        }


class MultaEditForm(forms.ModelForm):
    class Meta:
        model = Multa
        fields = ['protocolo_sei', 'situacao', 'observacao']
        widgets = {
            'protocolo_sei': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2',
                'placeholder': 'Nº do protocolo SEI',
            }),
            'situacao': forms.Select(attrs={
                'class': 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2',
            }),
            'observacao': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2',
                'rows': 4,
            }),
        }
