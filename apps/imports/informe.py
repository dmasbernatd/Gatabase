"""Qué pasaría con cada línea de la planilla, antes de que se guarde nada.

Es lo que la vista previa enseña y lo que el admin se descarga para corregir su
archivo, y es la otra mitad del importador que no sabe de Tutores ni de
Pacientes: aquí solo se cuenta y se ordena lo que quien lee la planilla haya
decidido de cada fila.

Las líneas que no se crean se separan en dos montones, y esa separación es la
decisión de este módulo:

- **Las que están mal** —el RUT no cuadra, el teléfono no se entiende, falta el
  nombre— son las que hay que corregir en el Excel y volver a subir. Son las que
  se descarga el admin.
- **Las repetidas** —la persona ya está en la Clínica, o venía dos veces en la
  misma planilla— no son un error de nadie: son lo que hace que reimportar el
  mismo archivo no duplique a nadie, y por eso se cuentan aparte y no se
  presentan como algo que arreglar.

El informe descargable lleva las dos, porque el que se lo descarga viene a
entender por qué de sus mil filas entraron novecientas, y una fila que no entró
sin decir por qué es exactamente lo que obliga a comparar dos planillas a mano.
"""

from dataclasses import dataclass, field

from django.utils.translation import gettext as _

from apps.imports.planilla import como_la_lee_un_excel


@dataclass(frozen=True)
class FilaExaminada:
    """Lo que pasaría con una línea de la planilla, y por qué.

    `ficha` es el objeto que se crearía —sin guardar todavía—, y va aquí y no en
    una lista aparte para que la vista previa y la importación no puedan discrepar:
    lo que se enseña es exactamente lo que se guardaría.
    """

    numero: int
    resumen: str = ""
    motivo: str = ""
    es_un_error: bool = False
    ficha: object = None

    @property
    def se_crea(self):
        return not self.motivo


@dataclass(frozen=True)
class Informe:
    """Lo que pasaría con la planilla entera: cuántas filas y cuáles.

    Los tres montones se derivan uno de otro y no cada uno de la fila, para que
    no puedan solaparse ni dejarse una fuera: lo que no se crea son las que no
    entran, y de esas, las que no son un error es que ya estaban.
    """

    filas: list = field(default_factory=list)

    @property
    def creables(self):
        return [fila for fila in self.filas if fila.se_crea]

    @property
    def no_se_crean(self):
        """Todo lo que no entra, en el orden de la planilla: es como se lee."""
        return [fila for fila in self.filas if not fila.se_crea]

    @property
    def erroneas(self):
        """Las que hay que corregir en el Excel."""
        return [fila for fila in self.no_se_crean if fila.es_un_error]

    @property
    def repetidas(self):
        """Las que no se crean y no son culpa de nadie: ya estaban."""
        return [fila for fila in self.no_se_crean if not fila.es_un_error]

    @property
    def trae_algo_que_crear(self):
        return bool(self.creables)

    def como_csv(self):
        """El informe como planilla, para abrirlo al lado del archivo que se corrige."""
        return como_la_lee_un_excel([
            [_("línea"), _("fila"), _("qué pasa"), _("motivo")],
            *(
                [
                    fila.numero,
                    fila.resumen,
                    _("hay que corregirla") if fila.es_un_error else _("ya estaba"),
                    fila.motivo,
                ]
                for fila in self.no_se_crean
            ),
        ])
