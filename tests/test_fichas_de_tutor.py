"""La ficha de un Tutor: registrarlo, encontrarlo, abrirlo y corregirlo.

Es el primer punto donde la clínica deja de depender de la planilla para saber a
quién atiende, así que los tests entran por HTTP como entra recepción: con un
Usuario autenticado, mirando lo que la página enseña y lo que queda guardado.

Lo que se anota en el Registro de acceso al servir estas páginas se comprueba
aquí y en `test_registro_de_acceso.py`; lo que no se ve de otra Clínica, en
`test_aislamiento_por_clinica.py`.
"""

import html as marcado
import re

import pytest
from django.urls import reverse

from apps.audit.models import Accion, RegistroDeAcceso
from apps.tutors.listado import COLUMNAS, TUTORES_POR_PAGINA
from apps.tutors.models import Tutor
from tests.factories import ClinicaFactory, TutorFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

DATOS_DE_CONTACTO = {
    "nombre": "Camila",
    "apellidos": "Rojas Pizarro",
    "telefono": "+56912345678",
    "email": "camila.rojas@correo.example",
    "direccion": "Av. Providencia 1234, depto. 52, Santiago",
}


def recepcion(client):
    """Quien está en el mostrador: el rol que registra y corrige fichas."""
    usuario = UsuarioFactory(rol="recepcion")
    client.force_login(usuario)
    return usuario


def enlace(contenido, rotulo):
    """El `href` del enlace que dice eso, listo para pedirlo.

    Seguir el enlace y no componer la URL a mano es lo que comprueba que lo que
    la página ofrece lleva de verdad adonde dice.
    """
    encontrado = re.search(rf'href="([^"]+)"[^>]*>{rotulo}<', contenido)
    assert encontrado, f"La página no ofrece ningún enlace «{rotulo}»"
    return marcado.unescape(encontrado.group(1))


def campos_del_formulario_de_busqueda(contenido):
    """Lo que el navegador enviaría al buscar: los campos del formulario servido.

    Componer los parámetros a mano comprobaría lo que el test cree que la página
    lleva dentro; esto comprueba lo que lleva.
    """
    formulario = re.search(r"<form[^>]*>(.*?)</form>", contenido, re.S)
    assert formulario, "El listado no ofrece ningún formulario de búsqueda"
    return {
        nombre: marcado.unescape(valor)
        for nombre, valor in re.findall(
            r'name="([^"]+)"[^>]*value="([^"]*)"', formulario.group(1)
        )
    }


def anotaciones_sobre(tutor, accion):
    return RegistroDeAcceso.de_todas_las_clinicas.filter(
        tipo_de_objeto="tutors.Tutor", identificador=str(tutor.pk), accion=accion
    )


# --- Registrar un Tutor ---------------------------------------------------


def test_recepcion_registra_un_tutor_con_sus_datos_de_contacto(client):
    usuario = recepcion(client)

    respuesta = client.post(reverse("tutors:crear"), DATOS_DE_CONTACTO)

    tutor = Tutor.de_todas_las_clinicas.get()
    assert tutor.clinic == usuario.clinic
    assert tutor.nombre == "Camila"
    assert tutor.apellidos == "Rojas Pizarro"
    assert tutor.telefono == "+56912345678"
    assert tutor.email == "camila.rojas@correo.example"
    assert tutor.direccion == "Av. Providencia 1234, depto. 52, Santiago"
    assert respuesta.status_code == 302
    assert respuesta["Location"] == reverse("tutors:ficha", args=[tutor.pk])


def test_registrar_un_tutor_deja_constancia_de_la_creacion(client):
    usuario = recepcion(client)

    client.post(reverse("tutors:crear"), DATOS_DE_CONTACTO)

    tutor = Tutor.de_todas_las_clinicas.get()
    anotacion = anotaciones_sobre(tutor, Accion.CREACION).get()
    assert anotacion.usuario == usuario
    assert anotacion.clinic == usuario.clinic


def test_un_tutor_sin_nombre_no_se_guarda(client):
    recepcion(client)

    respuesta = client.post(reverse("tutors:crear"), {"telefono": "+56912345678"})

    assert respuesta.status_code == 200
    assert not Tutor.de_todas_las_clinicas.exists()
    assert not RegistroDeAcceso.de_todas_las_clinicas.exists()


def test_el_resto_de_los_datos_de_contacto_son_opcionales(client):
    """En el mostrador a veces solo hay un nombre y un teléfono; exigir más
    empujaría a recepción a inventarse los demás datos."""
    recepcion(client)

    client.post(reverse("tutors:crear"), {"nombre": "Camila", "telefono": "+56912345678"})

    assert Tutor.de_todas_las_clinicas.get().apellidos == ""


def test_el_alta_no_deja_elegir_la_clinica(client):
    """La Clínica sale del Usuario, nunca del formulario."""
    usuario = recepcion(client)
    ajena = ClinicaFactory()

    client.post(reverse("tutors:crear"), DATOS_DE_CONTACTO | {"clinic": ajena.pk})

    assert Tutor.de_todas_las_clinicas.get().clinic == usuario.clinic


# --- Ver y corregir la ficha ----------------------------------------------


def test_la_ficha_muestra_los_datos_de_contacto(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, **DATOS_DE_CONTACTO)

    contenido = client.get(reverse("tutors:ficha", args=[tutor.pk])).content.decode()

    assert "Camila" in contenido
    assert "Rojas Pizarro" in contenido
    assert "+56912345678" in contenido
    assert "camila.rojas@correo.example" in contenido
    assert "Av. Providencia 1234" in contenido


def test_recepcion_corrige_la_ficha_de_un_tutor(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, **DATOS_DE_CONTACTO)

    respuesta = client.post(
        reverse("tutors:editar", args=[tutor.pk]),
        DATOS_DE_CONTACTO | {"telefono": "+56987654321"},
    )

    tutor.refresh_from_db()
    assert tutor.telefono == "+56987654321"
    assert respuesta["Location"] == reverse("tutors:ficha", args=[tutor.pk])


def test_corregir_la_ficha_deja_constancia_de_la_modificacion(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, **DATOS_DE_CONTACTO)

    client.post(
        reverse("tutors:editar", args=[tutor.pk]),
        DATOS_DE_CONTACTO | {"telefono": "+56987654321"},
    )

    assert anotaciones_sobre(tutor, Accion.MODIFICACION).get().usuario == usuario


def test_abrir_el_formulario_de_edicion_deja_constancia_de_la_lectura(client):
    """El formulario de edición trae los datos del Tutor rellenados: quien lo
    abre los ha visto, aunque no llegue a guardar nada."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, **DATOS_DE_CONTACTO)

    contenido = client.get(reverse("tutors:editar", args=[tutor.pk])).content.decode()

    assert "+56912345678" in contenido
    assert anotaciones_sobre(tutor, Accion.LECTURA).get().usuario == usuario
    assert not anotaciones_sobre(tutor, Accion.MODIFICACION).exists()


def test_una_correccion_que_no_se_guarda_no_consta_como_modificacion(client):
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, **DATOS_DE_CONTACTO)

    respuesta = client.post(
        reverse("tutors:editar", args=[tutor.pk]), DATOS_DE_CONTACTO | {"nombre": ""}
    )

    tutor.refresh_from_db()
    assert respuesta.status_code == 200
    assert tutor.nombre == "Camila"
    assert not anotaciones_sobre(tutor, Accion.MODIFICACION).exists()


# --- Listado --------------------------------------------------------------


def poblar(clinica, cuantos, prefijo="Paginado"):
    """Tutores numerados, para contar filas y comprobar el orden."""
    return [
        TutorFactory(clinic=clinica, nombre="Tutor", apellidos=f"{prefijo}{numero:02d}")
        for numero in range(cuantos)
    ]


def test_el_listado_pagina_los_tutores(client):
    """Una clínica con cientos de Tutores no sirve su fichero entero de una vez."""
    usuario = recepcion(client)
    poblar(usuario.clinic, TUTORES_POR_PAGINA + 5)

    primera = client.get(reverse("tutors:lista")).content.decode()
    segunda = client.get(reverse("tutors:lista"), {"pagina": 2}).content.decode()

    assert primera.count("Paginado") == TUTORES_POR_PAGINA
    assert segunda.count("Paginado") == 5
    assert "Paginado00" in primera
    assert "Paginado00" not in segunda


def test_el_listado_se_ordena_por_apellidos(client):
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Ignacio", apellidos="Zapata")
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Alvarez")

    contenido = client.get(reverse("tutors:lista")).content.decode()

    assert contenido.index("Alvarez") < contenido.index("Zapata")


def test_el_listado_se_puede_ordenar_al_reves(client):
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Ignacio", apellidos="Zapata")
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Alvarez")

    contenido = client.get(reverse("tutors:lista"), {"orden": "-apellidos"}).content.decode()

    assert contenido.index("Zapata") < contenido.index("Alvarez")


def test_el_listado_se_puede_ordenar_por_otra_columna(client):
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Ignacio", apellidos="Alvarez")
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Zapata")

    contenido = client.get(reverse("tutors:lista"), {"orden": "nombre"}).content.decode()

    assert contenido.index("Camila") < contenido.index("Ignacio")


def test_un_orden_que_no_existe_no_ordena_por_el(client):
    """Lo que llega por la URL no puede convertirse en un `ORDER BY` cualquiera:
    solo se ordena por las columnas que el listado enseña."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Ignacio", apellidos="Zapata")
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Alvarez")

    respuesta = client.get(reverse("tutors:lista"), {"orden": "clinic__nombre; drop table"})

    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert contenido.index("Alvarez") < contenido.index("Zapata")


def test_la_cabecera_de_la_columna_ordenada_lleva_al_orden_contrario(client):
    """Pulsar dos veces la misma columna da la vuelta al listado; pulsar otra
    empieza por la A."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Alvarez")

    contenido = client.get(reverse("tutors:lista"), {"orden": "apellidos"}).content.decode()

    assert "orden=-apellidos" in contenido
    assert 'aria-sort="ascending"' in contenido
    assert "orden=nombre" in contenido


def celdas_de_las_filas(contenido):
    """Cuántas celdas trae cada fila del cuerpo de la tabla."""
    cuerpo = re.search(r"<tbody>(.*?)</tbody>", contenido, re.S)
    assert cuerpo, "El listado no sirve ninguna tabla"
    filas = re.findall(r"<tr>(.*?)</tr>", cuerpo.group(1), re.S)
    return [len(re.findall(r"<td\b", fila)) for fila in filas]


def test_cada_fila_trae_una_celda_por_cabecera(client):
    """Cabeceras y celdas salen las dos de `COLUMNAS`, y este test es lo que lo
    sostiene: escribir las celdas a mano en la plantilla dejaba que una columna
    nueva descuadrara la tabla sin que fallara nada."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, **DATOS_DE_CONTACTO)

    contenido = client.get(reverse("tutors:lista")).content.decode()

    cabeceras = len(re.findall(r"<th\b", contenido))
    assert cabeceras == len(COLUMNAS)
    assert celdas_de_las_filas(contenido) == [cabeceras]


def test_la_fila_de_sin_resultados_ocupa_toda_la_tabla(client):
    """El `colspan` se cuenta, no se escribe: si no, una columna nueva deja el
    aviso de «no hay nada» a media tabla."""
    recepcion(client)

    contenido = client.get(reverse("tutors:lista")).content.decode()

    assert f'colspan="{len(COLUMNAS)}"' in contenido
    assert "Todavía no hay Tutores registrados." in contenido


def test_el_orden_y_la_busqueda_sobreviven_al_cambio_de_pagina(client):
    usuario = recepcion(client)
    poblar(usuario.clinic, TUTORES_POR_PAGINA + 5, prefijo="Rojas")

    primera = client.get(
        reverse("tutors:lista"), {"q": "Rojas", "orden": "-apellidos"}
    ).content.decode()
    segunda = client.get(enlace(primera, "Siguiente")).content.decode()

    # Treinta Tutores de la Z a la A: la segunda página son los cinco últimos,
    # y siguen en ese orden. Si el enlace hubiera perdido el orden, esta página
    # empezaría por «Rojas25».
    assert "Rojas04" in segunda
    assert "Rojas05" not in segunda
    assert segunda.index("Rojas04") < segunda.index("Rojas00")


def test_buscar_despues_de_ordenar_conserva_el_orden(client):
    """La caja de búsqueda arrastra el orden actual en un campo oculto, y por eso
    viaja dentro del trozo que htmx sustituye: fuera de él seguiría llevando el
    orden de antes, y la búsqueda siguiente desharía lo que se acaba de pedir.

    Son dos peticiones porque el fallo eran dos: por separado, ordenar funciona
    y buscar funciona. Se envía lo que el formulario ofrece de verdad, no unos
    parámetros compuestos a mano, que es donde el fallo se escondía.
    """
    usuario = recepcion(client)
    for apellidos in ("Alvarez", "Mora", "Zapata"):
        TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos=apellidos)

    ordenado = client.get(
        reverse("tutors:lista"), {"orden": "-apellidos"}, headers={"hx-request": "true"}
    ).content.decode()
    busqueda = campos_del_formulario_de_busqueda(ordenado)
    busqueda["q"] = "Camila"
    buscado = client.get(
        reverse("tutors:lista"), busqueda, headers={"hx-request": "true"}
    ).content.decode()

    # De la Z a la A, como se acababa de pedir. Con el campo oculto rancio, la
    # búsqueda volvería al orden de siempre y Alvarez saldría primero.
    assert buscado.index("Zapata") < buscado.index("Alvarez")
    assert busqueda["orden"] == "-apellidos"


# --- Búsqueda -------------------------------------------------------------


def test_la_busqueda_encuentra_por_apellido_telefono_o_correo(client):
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, **DATOS_DE_CONTACTO)
    TutorFactory(
        clinic=usuario.clinic,
        nombre="Ignacio",
        apellidos="Fuentes",
        telefono="+56922223333",
        email="ignacio.fuentes@correo.example",
    )

    def encontrados(buscado):
        return client.get(reverse("tutors:lista"), {"q": buscado}).content.decode()

    assert "Pizarro" in encontrados("Pizarro")
    assert "Fuentes" not in encontrados("Pizarro")
    assert "Pizarro" in encontrados("912345678")
    assert "Fuentes" not in encontrados("912345678")
    assert "Pizarro" in encontrados("camila.rojas@correo.example")
    assert "Fuentes" not in encontrados("camila.rojas@correo.example")


def test_la_busqueda_reune_el_nombre_y_el_apellido(client):
    """Recepción escribe el nombre como lo diría, no como está partido en campos."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas Pizarro")
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Fuentes")

    contenido = client.get(reverse("tutors:lista"), {"q": "camila rojas"}).content.decode()

    assert "Rojas Pizarro" in contenido
    assert "Fuentes" not in contenido


def test_una_busqueda_sin_resultados_lo_dice_y_no_revienta(client):
    recepcion(client)

    respuesta = client.get(reverse("tutors:lista"), {"q": "nadie con ese nombre"})

    assert respuesta.status_code == 200


# --- HTMX -----------------------------------------------------------------


def test_buscar_por_htmx_devuelve_solo_los_resultados(client):
    """La búsqueda, el orden y el paginado cambian la tabla, no la página entera."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas Pizarro")

    contenido = client.get(
        reverse("tutors:lista"), {"q": "Rojas"}, headers={"hx-request": "true"}
    ).content.decode()

    assert "Rojas Pizarro" in contenido
    assert "<html" not in contenido


def test_sin_htmx_el_listado_sigue_sirviendo_la_pagina_entera(client):
    """Sin JavaScript el formulario y los enlaces siguen funcionando solos."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Camila", apellidos="Rojas Pizarro")

    contenido = client.get(reverse("tutors:lista"), {"q": "Rojas"}).content.decode()

    assert "<html" in contenido
    assert "Rojas Pizarro" in contenido


# --- Separación de los datos personales -----------------------------------


def test_los_datos_personales_del_tutor_viven_todos_en_su_modelo():
    """Anonimizar un Tutor sin tocar la Historia clínica (ADR-0004, ticket 20)
    solo es posible si sus datos personales están todos aquí y nada más está.

    Un campo nuevo en el Tutor obliga a decidir si es dato personal —y entra en
    `DATOS_PERSONALES`, y desaparecerá al anonimizar— o no lo es. Este test es
    quien fuerza esa decisión el día que se escriba el campo.
    """
    campos = {
        campo.name
        # Los dos: un `ManyToManyField` no está en `local_fields`, y es justo la
        # forma que tendría un dato personal traído de otra tabla — un domicilio
        # compartido, un contacto alternativo —, que es lo que este test vigila.
        for campo in Tutor._meta.local_fields + Tutor._meta.local_many_to_many
    }

    assert campos == {"id", "clinic"} | set(Tutor.DATOS_PERSONALES)


# --- RUT ------------------------------------------------------------------
#
# Cómo se lee un RUT escrito de cualquier manera se prueba en
# `test_rut_y_telefono.py`. Aquí se prueba lo que la Clínica hace con él:
# guardarlo de una sola forma, presentarlo de otra, y no dejar que dos fichas
# sean la misma persona.

RUT_ESCRITO = "12.345.678-5"
RUT_GUARDADO = "123456785"


def test_el_rut_se_guarda_normalizado_y_se_presenta_a_la_chilena(client):
    usuario = recepcion(client)

    client.post(reverse("tutors:crear"), DATOS_DE_CONTACTO | {"rut": RUT_ESCRITO})

    tutor = Tutor.de_todas_las_clinicas.get()
    assert tutor.rut == RUT_GUARDADO
    contenido = client.get(reverse("tutors:ficha", args=[tutor.pk])).content.decode()
    assert RUT_ESCRITO in contenido
    assert RUT_GUARDADO not in contenido


def test_el_formulario_de_correccion_trae_el_rut_a_la_chilena(client):
    """Quien va a corregir una ficha tiene que reconocer el RUT que ve: de
    corrido, como se guarda, no lo reconoce nadie de un vistazo."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO)

    contenido = client.get(reverse("tutors:editar", args=[tutor.pk])).content.decode()

    assert f'value="{RUT_ESCRITO}"' in contenido


def test_un_rut_con_el_digito_verificador_cambiado_no_se_guarda(client):
    recepcion(client)

    respuesta = client.post(reverse("tutors:crear"), DATOS_DE_CONTACTO | {"rut": "12.345.678-4"})

    assert respuesta.status_code == 200
    assert not Tutor.de_todas_las_clinicas.exists()
    # El aviso dice cuál tendría que ser: el error casi nunca está en el
    # verificador, sino en un dígito del cuerpo.
    assert "12.345.678-4" in respuesta.content.decode()
    assert "dígito verificador" in respuesta.content.decode()


def test_un_tutor_sin_rut_se_registra_igual(client):
    """Un Tutor extranjero no tiene, y quien no lo quiera dar tiene derecho a
    que se le atienda igual."""
    recepcion(client)

    client.post(reverse("tutors:crear"), DATOS_DE_CONTACTO | {"rut": ""})

    assert Tutor.de_todas_las_clinicas.get().rut == ""


def test_dos_tutores_sin_rut_no_son_el_mismo_tutor(client):
    """El hueco se guarda como cadena vacía, y la restricción de unicidad lo
    deja fuera: si no, la segunda ficha sin RUT sería imposible de crear."""
    recepcion(client)

    client.post(reverse("tutors:crear"), {"nombre": "Camila"})
    client.post(reverse("tutors:crear"), {"nombre": "Ignacio"})

    assert Tutor.de_todas_las_clinicas.count() == 2


def test_un_rut_que_ya_esta_en_la_clinica_no_se_guarda_y_lleva_a_la_ficha(client):
    usuario = recepcion(client)
    ya_registrada = TutorFactory(
        clinic=usuario.clinic, nombre="Camila", apellidos="Rojas Pizarro", rut=RUT_GUARDADO
    )

    respuesta = client.post(
        reverse("tutors:crear"),
        {"nombre": "Camila", "apellidos": "Rojas", "rut": RUT_ESCRITO},
    )

    assert respuesta.status_code == 200
    assert Tutor.de_todas_las_clinicas.count() == 1
    # El enlace se sigue, no se compone: lo que importa es que lleve de verdad
    # a la ficha que ya existe, que es a lo que recepción venía.
    destino = enlace(respuesta.content.decode(), "Camila Rojas Pizarro")
    assert destino == reverse("tutors:ficha", args=[ya_registrada.pk])


def test_avisar_de_un_rut_repetido_deja_constancia_de_la_lectura(client):
    """El aviso dice el nombre del otro Tutor y enlaza a su ficha: quien lo lee
    ha visto un dato personal suyo sin haber abierto nada (ADR-0004)."""
    usuario = recepcion(client)
    ya_registrada = TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO)

    client.post(reverse("tutors:crear"), {"nombre": "Camila", "rut": RUT_ESCRITO})

    assert anotaciones_sobre(ya_registrada, Accion.LECTURA).get().usuario == usuario


def test_el_mismo_rut_en_otra_clinica_no_estorba(client):
    """El RUT es único dentro de la Clínica, nunca a nivel global: dos Clínicas
    atienden a la misma persona sin saber la una de la otra (ADR-0003)."""
    usuario = recepcion(client)
    TutorFactory(clinic=ClinicaFactory(), rut=RUT_GUARDADO)

    client.post(reverse("tutors:crear"), DATOS_DE_CONTACTO | {"rut": RUT_ESCRITO})

    assert Tutor.de_todas_las_clinicas.filter(clinic=usuario.clinic).get().rut == RUT_GUARDADO


def test_corregir_una_ficha_no_choca_con_su_propio_rut(client):
    """Un Tutor no se duplica a sí mismo: corregirle el apellido no puede
    tropezar con el RUT que ya tenía."""
    usuario = recepcion(client)
    tutor = TutorFactory(clinic=usuario.clinic, rut=RUT_GUARDADO)

    respuesta = client.post(
        reverse("tutors:editar", args=[tutor.pk]),
        {"nombre": "Camila", "apellidos": "Rojas Pizarro", "rut": RUT_ESCRITO},
    )

    tutor.refresh_from_db()
    assert respuesta.status_code == 302
    assert tutor.apellidos == "Rojas Pizarro"
    assert tutor.rut == RUT_GUARDADO


def test_el_listado_enseña_el_rut_a_la_chilena_y_se_busca_por_el(client):
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, apellidos="Rojas Pizarro", rut=RUT_GUARDADO)
    # Con otro teléfono: el de la fábrica lleva los mismos ocho dígitos que este
    # RUT, y saldría en la búsqueda por el campo que no se está probando.
    TutorFactory(clinic=usuario.clinic, apellidos="Fuentes", telefono="+56987654321")

    contenido = client.get(reverse("tutors:lista"), {"q": "12.345.678"}).content.decode()

    assert RUT_ESCRITO in contenido
    assert "Rojas Pizarro" in contenido
    assert "Fuentes" not in contenido


def test_buscar_un_nombre_no_lo_busca_entre_los_rut(client):
    """La «k» de «Karla» traería a todos los Tutores cuyo RUT acaba en K."""
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, nombre="Karla", apellidos="Soto", rut="12000008K")
    TutorFactory(clinic=usuario.clinic, nombre="Ignacio", apellidos="Fuentes", rut="12000011K")

    contenido = client.get(reverse("tutors:lista"), {"q": "Karla"}).content.decode()

    assert "Soto" in contenido
    assert "Fuentes" not in contenido


# --- Teléfono -------------------------------------------------------------


def test_el_telefono_se_guarda_en_e164_se_dicte_como_se_dicte(client):
    recepcion(client)

    client.post(reverse("tutors:crear"), {"nombre": "Camila", "telefono": "9 1234 5678"})

    assert Tutor.de_todas_las_clinicas.get().telefono == "+56912345678"


def test_un_telefono_que_no_se_entiende_no_se_guarda(client):
    recepcion(client)

    respuesta = client.post(reverse("tutors:crear"), {"nombre": "Camila", "telefono": "1234"})

    assert respuesta.status_code == 200
    assert not Tutor.de_todas_las_clinicas.exists()
    assert "9 1234 5678" in respuesta.content.decode()


def test_dos_tutores_pueden_compartir_el_telefono_y_se_avisa(client):
    """Una familia comparte número: impedirlo obligaría a recepción a
    inventarse un teléfono falso para el segundo Tutor."""
    usuario = recepcion(client)
    hermana = TutorFactory(
        clinic=usuario.clinic, nombre="Camila", apellidos="Rojas", telefono="+56912345678"
    )

    respuesta = client.post(
        reverse("tutors:crear"),
        {"nombre": "Ignacio", "apellidos": "Rojas", "telefono": "9 1234 5678"},
        follow=True,
    )

    assert Tutor.de_todas_las_clinicas.count() == 2
    destino = enlace(respuesta.content.decode(), "Camila Rojas")
    assert destino == reverse("tutors:ficha", args=[hermana.pk])


def test_avisar_de_un_telefono_compartido_deja_constancia_de_la_lectura(client):
    usuario = recepcion(client)
    hermana = TutorFactory(clinic=usuario.clinic, telefono="+56912345678")

    client.post(
        reverse("tutors:crear"), {"nombre": "Ignacio", "telefono": "+56912345678"}, follow=True
    )

    assert anotaciones_sobre(hermana, Accion.LECTURA).get().usuario == usuario


def test_un_telefono_que_no_tiene_nadie_mas_no_avisa_de_nada(client):
    usuario = recepcion(client)
    TutorFactory(clinic=usuario.clinic, telefono="+56911111111")

    respuesta = client.post(
        reverse("tutors:crear"),
        {"nombre": "Ignacio", "telefono": "+56922222222"},
        follow=True,
    )

    assert "es también el de" not in respuesta.content.decode()
