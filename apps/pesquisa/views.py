from django.shortcuts import render
from django.db.models import Count, Min, Max, Avg
from apps.manutencoes.models import ItemOrcamento
from .fts import buscar_itens, get_grupos


def itens(request):
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '')
    grupo = request.GET.get('grupo', '')

    resultados = []
    grupos_disponiveis = get_grupos()

    if q or tipo:
        resultados_fts = buscar_itens(q, tipo=tipo if tipo else None)
        item_ids = [r['item_id'] for r in resultados_fts]

        if item_ids:
            # Aggregate results by description
            items_qs = ItemOrcamento.objects.filter(id__in=item_ids)
            if grupo:
                items_qs = items_qs.filter(grupo=grupo)

            agrupados = (
                items_qs
                .values('descricao', 'marca', 'tipo', 'grupo', 'codigo_item')
                .annotate(
                    ocorrencias=Count('id'),
                    valor_min=Min('valor_unit'),
                    valor_max=Max('valor_unit'),
                    valor_medio=Avg('valor_unit'),
                )
                .order_by('-ocorrencias')
            )

            for item in agrupados:
                # Get related OS info
                sample_items = ItemOrcamento.objects.filter(
                    descricao=item['descricao'],
                    tipo=item['tipo'],
                    id__in=item_ids,
                ).select_related('orcamento__manutencao')[:5]

                item['exemplos'] = [
                    {
                        'os': si.orcamento.manutencao.numero_os,
                        'orcamento': si.orcamento.codigo_orcamento,
                        'orcamento_status': si.orcamento.status,
                        'valor': si.valor_unit,
                        'qtd': si.qtd,
                    }
                    for si in sample_items
                ]
                resultados.append(item)

    return render(request, 'pesquisa/itens.html', {
        'q': q,
        'tipo': tipo,
        'grupo': grupo,
        'resultados': resultados,
        'grupos_disponiveis': grupos_disponiveis,
    })
