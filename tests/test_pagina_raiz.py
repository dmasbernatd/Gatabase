"""La página raíz responde y se sirve en es-CL.

Que sus textos pasen por gettext lo comprueba `test_plantillas_en_gettext.py`.
"""

from django.urls import reverse


def test_la_pagina_raiz_responde(client):
    respuesta = client.get(reverse("home"))

    assert respuesta.status_code == 200


def test_la_pagina_raiz_muestra_el_nombre_del_sistema(client):
    respuesta = client.get(reverse("home"))

    assert "Gatabase" in respuesta.content.decode()


def test_la_pagina_raiz_se_sirve_en_es_cl(client):
    respuesta = client.get(reverse("home"))

    assert respuesta["Content-Language"] == "es-cl"
