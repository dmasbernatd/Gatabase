"""Qué planillas se saben importar, y qué tiene que declarar cada una.

Las dos importaciones —Tutores y Pacientes— son el mismo gesto en tres páginas:
subir, mirar qué entraría, confirmar. Lo único que cambia entre ellas es qué se
lee de cada fila y qué se guarda, y eso vive entero en su módulo. Así que las
vistas no saben de Tutores ni de Pacientes: preguntan aquí por el importador de
lo que la planilla que espera decía traer.

**El contrato es un módulo**, no una clase: cada importador declara estos
nombres, y quien añada un tercero —el ticket 19 exporta, pero un día habrá que
importar Vacunas— sabe qué tiene que escribir sin heredar de nada.

    QUE                     de `LoQueSeImporta`; es la clave de este mapa
    MODELO                  qué se crea, para nombrarlo en singular y en plural
    COLUMNAS_DE_LA_PLANILLA la definición del formato (`planilla.Columna`)
    PLANTILLA               la página de subida, que documenta ese formato
    EJEMPLO                 cómo se llama el archivo de ejemplo al descargarlo
    URL_DEL_EJEMPLO         y dónde se descarga
    VUELVE_A                adónde se va al confirmar
    examinar(contenido, clinica) -> Informe
    importar(informe, clinica, usuario, planilla) -> Importacion
    ejemplo() -> str

De que los dos módulos lo cumplan responde `tests/test_estructura.py`: un
importador nuevo al que le falte un nombre rompe ahí y no en la página.
"""

from apps.imports import pacientes, tutores

IMPORTADORES = {importador.QUE: importador for importador in (tutores, pacientes)}


def el_de(que):
    """El importador de lo que traía esa planilla."""
    return IMPORTADORES[que]
