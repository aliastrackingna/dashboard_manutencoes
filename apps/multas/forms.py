from django import forms
from .models import Multa


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
