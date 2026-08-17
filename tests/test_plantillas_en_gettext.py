"""Ninguna plantilla lleva texto visible fuera de gettext.

El catálogo `locale/es_CL` y el uso de `{% translate %}` son fáciles de
cumplir hoy y fáciles de olvidar mañana. Este test recorre las plantillas,
quita el marcado y falla si queda texto que un Usuario vería sin haber
pasado por gettext.
"""

import re

from django.conf import settings
from django.template.base import Lexer, TokenType

# `{% translate %}` y `{{ var }}` son tokens propios; lo que queda como texto
# es marcado, espacios o una cadena que alguien escribió a mano.
MARCADO_HTML = re.compile(r"<[^>]*>|&[a-zA-Z]+;", re.DOTALL)
LETRAS = re.compile(r"[^\W\d_]", re.UNICODE)

# Dentro de un blocktranslate el texto plano sí está traducido.
APERTURA_DE_BLOQUE = ("blocktranslate", "blocktrans", "comment")
CIERRE_DE_BLOQUE = ("endblocktranslate", "endblocktrans", "endcomment")


def _quitar_marcado(texto, dentro_de_etiqueta):
    """Quita el HTML de un fragmento, sabiendo si venía dentro de una etiqueta.

    Una etiqueta puede partirse en varios tokens — `<html lang="{{ x }}">` —,
    así que hay que arrastrar el estado de un fragmento al siguiente.
    """
    if dentro_de_etiqueta:
        _, cierra, texto = texto.partition(">")
        if not cierra:
            return "", True

    texto = MARCADO_HTML.sub(" ", texto)

    abierta = texto.rfind("<")
    if abierta != -1:
        return texto[:abierta], True
    return texto, False


def _texto_sin_traducir(plantilla):
    """Devuelve los fragmentos de texto visible que no pasan por gettext."""
    sueltos = []
    dentro_de_bloque = False
    dentro_de_etiqueta = False

    for token in Lexer(plantilla.read_text(encoding="utf-8")).tokenize():
        if token.token_type is TokenType.BLOCK:
            etiqueta = token.contents.split()[0] if token.contents.split() else ""
            if etiqueta in APERTURA_DE_BLOQUE:
                dentro_de_bloque = True
            elif etiqueta in CIERRE_DE_BLOQUE:
                dentro_de_bloque = False
            continue

        if token.token_type is not TokenType.TEXT:
            continue

        resto, dentro_de_etiqueta = _quitar_marcado(token.contents, dentro_de_etiqueta)
        if not dentro_de_bloque and LETRAS.search(resto.strip()):
            sueltos.append(resto.strip())

    return sueltos


def _plantillas():
    for directorio in settings.TEMPLATES[0]["DIRS"]:
        yield from sorted(directorio.rglob("*.html"))


def test_hay_plantillas_que_revisar():
    assert list(_plantillas()), "No se encontró ninguna plantilla que revisar"


def test_ninguna_plantilla_tiene_texto_fuera_de_gettext():
    hallazgos = {
        plantilla.relative_to(settings.BASE_DIR): sueltos
        for plantilla in _plantillas()
        if (sueltos := _texto_sin_traducir(plantilla))
    }

    assert not hallazgos, f"Texto visible sin gettext: {hallazgos}"
