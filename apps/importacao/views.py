from django.shortcuts import render
from django.contrib import messages

from .models import RegistroImportacao
from .pipeline import executar_pipeline


def upload(request):
    relatorio = None

    if request.method == 'POST':
        veiculos_file = request.FILES.get('veiculos')
        manutencoes_file = request.FILES.get('manutencoes')
        complemento_file = request.FILES.get('complemento')
        orcamentos_file = request.FILES.get('orcamentos')
        itens_file = request.FILES.get('itens')
        multas_file = request.FILES.get('multas')

        if not any([veiculos_file, manutencoes_file, complemento_file, orcamentos_file, itens_file, multas_file]):
            messages.warning(request, 'Selecione pelo menos um arquivo para importar.')
        else:
            relatorio = executar_pipeline(
                veiculos_file=veiculos_file,
                manutencoes_file=manutencoes_file,
                complemento_file=complemento_file,
                orcamentos_file=orcamentos_file,
                itens_file=itens_file,
                multas_file=multas_file,
            )
            RegistroImportacao.objects.update_or_create(
                pk=1,
                defaults={},
            )

            if relatorio.tem_erros:
                messages.warning(
                    request,
                    f'Importação concluída com {len(relatorio.erros)} erro(s).'
                )
            else:
                messages.success(request, 'Importação concluída com sucesso!')

    return render(request, 'importacao/upload.html', {'relatorio': relatorio})
