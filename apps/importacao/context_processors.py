from .models import RegistroImportacao


def ultima_importacao(request):
    registro = RegistroImportacao.objects.order_by('-realizado_em').first()
    return {'ultima_importacao': registro}
