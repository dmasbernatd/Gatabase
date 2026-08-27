from django.apps import AppConfig


class ImportsConfig(AppConfig):
    """Importación de planillas de la Clínica, y los datos de demostración.

    Llevárselos hacia fuera es de `apps.exports`: son dos gestos con dos páginas,
    dos formatos y dos permisos distintos, y el único código que comparten —qué
    formato de planilla entiende un Excel chileno— vive en `planilla.py`, que es
    donde ya estaba para leerlas.
    """

    name = "apps.imports"
    label = "imports"
