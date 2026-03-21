from django.core.paginator import Paginator
from django.shortcuts import render

from .models import LogAuditoria

OPCOES_POR_PAGINA = [15, 25, 50, 100]


def lista(request):
    qs = LogAuditoria.objects.select_related('usuario').all()

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(descricao__icontains=q)

    por_pagina = request.GET.get('por_pagina', '25')
    try:
        por_pagina_int = int(por_pagina)
        if por_pagina_int not in OPCOES_POR_PAGINA:
            por_pagina_int = 25
    except ValueError:
        por_pagina_int = 25

    paginator = Paginator(qs, por_pagina_int)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'auditoria/lista.html', {
        'page': page,
        'q': q,
        'por_pagina': str(por_pagina_int),
        'opcoes_por_pagina': OPCOES_POR_PAGINA,
    })
