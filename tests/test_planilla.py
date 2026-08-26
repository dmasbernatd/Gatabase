"""Leer una planilla: de los bytes que sube el admin a filas con su número de línea.

Es la mitad del importador que no sabe de Tutores ni de Pacientes. Se prueba
aparte porque lo que decide —qué codificación, qué separador, cómo se llama cada
columna— es justo lo que cambia entre la planilla que exporta un Excel chileno y
la que sale de un sistema anterior, y ninguno de esos casos se ve desde un test
que entra por HTTP con un archivo bien formado.
"""

import pytest

from apps.imports.planilla import Columna, Planilla, PlanillaIlegible

# Un formato inventado, con lo justo para probar cómo se lee un archivo: una
# columna obligatoria, una que no lo es y una que se escribe de dos maneras.
COLUMNAS = (
    Columna("nombre", "nombre", (), obligatoria=True),
    Columna("apellidos", "apellidos", ()),
    Columna("fono", "telefono", ()),
)


def leer(texto, codificacion="utf-8", columnas=COLUMNAS):
    return Planilla.leer(texto.encode(codificacion), columnas=columnas)


def test_una_planilla_separada_por_comas_se_lee():
    filas = list(leer("nombre,apellidos\nCamila,Rojas\n"))

    assert [fila.valores for fila in filas] == [{"nombre": "Camila", "apellidos": "Rojas"}]


def test_una_planilla_separada_por_punto_y_coma_tambien():
    """Es lo que exporta un Excel configurado en español, y es la mitad de las
    planillas que llegan de una clínica."""
    filas = list(leer("nombre;apellidos\nCamila;Rojas\n"))

    assert [fila.valores for fila in filas] == [{"nombre": "Camila", "apellidos": "Rojas"}]


def test_la_cabecera_se_reconoce_con_tildes_mayusculas_y_espacios():
    filas = list(leer(" Nombre ,APELLIDOS\nCamila,Rojas\n"))

    assert filas[0].valores == {"nombre": "Camila", "apellidos": "Rojas"}


def test_una_columna_se_reconoce_por_el_nombre_con_que_la_escribieron():
    """`fono` es `telefono`: la planilla la escribió alguien, no el sistema."""
    filas = list(leer("nombre,Fono\nCamila,912345678\n"))

    assert filas[0].valores["telefono"] == "912345678"


def test_una_columna_que_no_se_reconoce_se_ignora():
    filas = list(leer("nombre,observaciones\nCamila,cliente antiguo\n"))

    assert filas[0].valores == {"nombre": "Camila"}


def test_el_numero_de_fila_es_el_de_la_linea_de_la_planilla():
    """La cabecera es la línea 1, así que el primer Tutor es la 2: es lo que hay
    que teclear en el Excel para ir a corregirla."""
    filas = list(leer("nombre\nCamila\nDiego\n"))

    assert [fila.numero for fila in filas] == [2, 3]


def test_una_linea_en_blanco_no_es_una_fila_pero_sí_cuenta_como_linea():
    filas = list(leer("nombre\nCamila\n\nDiego\n"))

    assert [(fila.numero, fila.valores["nombre"]) for fila in filas] == [
        (2, "Camila"),
        (4, "Diego"),
    ]


def test_a_una_fila_con_menos_celdas_le_faltan_datos_no_columnas():
    filas = list(leer("nombre,apellidos\nCamila\n"))

    assert filas[0].valores == {"nombre": "Camila", "apellidos": ""}


def test_las_celdas_de_mas_se_ignoran():
    filas = list(leer("nombre\nCamila,Rojas\n"))

    assert filas[0].valores == {"nombre": "Camila"}


def test_una_planilla_guardada_desde_excel_en_windows_se_lee_igual():
    """`cp1252` es lo que escribe un Excel en español que no guarda en UTF-8, y
    llega sin ninguna marca que lo anuncie."""
    filas = list(Planilla.leer(
        "nombre\nMuñoz\n".encode("cp1252"), columnas=COLUMNAS
    ))

    assert filas[0].valores["nombre"] == "Muñoz"


def test_la_marca_de_orden_de_bytes_no_se_cuela_en_la_primera_columna():
    filas = list(leer("nombre,apellidos\nCamila,Rojas\n", codificacion="utf-8-sig"))

    assert filas[0].valores["nombre"] == "Camila"


def test_una_planilla_sin_una_columna_obligatoria_no_se_lee():
    with pytest.raises(PlanillaIlegible) as ilegible:
        leer("apellidos\nRojas\n")

    assert "nombre" in str(ilegible.value)


def test_una_planilla_a_la_que_le_falta_el_grupo_entero_no_se_lee():
    """Hay datos que se pueden dar de varias maneras y basta con una —de quién es
    el animal, en la planilla de Pacientes—: la planilla se lee si trae alguna, y
    no se lee si no trae ninguna."""
    columnas = (
        *COLUMNAS,
        Columna("rut_tutor", "rut_tutor", (), alguna_de="de quién es"),
        Columna("tutor", "tutor", (), alguna_de="de quién es"),
    )

    with pytest.raises(PlanillaIlegible) as ilegible:
        leer("nombre\nRocky\n", columnas=columnas)

    assert "rut_tutor o tutor" in str(ilegible.value)


def test_basta_con_una_columna_del_grupo_para_que_la_planilla_se_lea():
    columnas = (
        *COLUMNAS,
        Columna("rut_tutor", "rut_tutor", (), alguna_de="de quién es"),
        Columna("tutor", "tutor", (), alguna_de="de quién es"),
    )

    filas = list(leer("nombre,tutor\nRocky,Camila Rojas\n", columnas=columnas))

    assert filas[0].valores == {"nombre": "Rocky", "tutor": "Camila Rojas"}


def test_una_planilla_vacia_no_se_lee():
    with pytest.raises(PlanillaIlegible):
        leer("")


def test_una_planilla_sin_ninguna_fila_se_lee_y_no_trae_nada():
    """Cabecera correcta y nada debajo no es un error de formato: es una planilla
    que no traía a nadie, y eso lo dice la vista previa."""
    assert list(leer("nombre,apellidos\n")) == []


def test_una_direccion_con_un_salto_de_linea_dentro_llega_entera():
    """Un Excel escribe entre comillas la celda que trae un salto, y partir el
    archivo por líneas antes de leerlo pegaría las dos mitades de corrido."""
    filas = list(leer('nombre,apellidos\nCamila,"Rojas\nPizarro"\n'))

    assert filas[0].valores["apellidos"] == "Rojas\nPizarro"


def test_una_fila_de_varias_lineas_se_anuncia_por_donde_empieza():
    """Es la línea a la que hay que ir en el Excel; la de más abajo no es la fila."""
    filas = list(leer('nombre\n"Camila\nAndrea"\nDiego\n'))

    assert [fila.numero for fila in filas] == [2, 4]
