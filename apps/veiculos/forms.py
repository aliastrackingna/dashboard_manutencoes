from django import forms
from .models import Veiculo


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = ['placa', 'marca', 'modelo', 'unidade', 'ativo']
        widgets = {
            'placa': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2',
                'placeholder': 'ABC1234',
            }),
            'marca': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2',
            }),
            'modelo': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2',
            }),
            'unidade': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-gray-300 bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white px-3 py-2',
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'rounded border border-gray-300 text-primary focus:ring-primary',
            }),
        }
