"""Importar la planilla con la que una clínica lleva hoy sus Tutores.

Es lo primero que hace una clínica que llega: sin esto el sistema arranca vacío y
compite con un archivador que sí tiene los datos. Lo que se sube es la planilla
que ya tenían, no un formato que se inventa aquí, así que este módulo decide tres
cosas y delega todo lo demás.

**Qué es un dato bueno no se decide aquí.** El RUT lo sigue leyendo
`apps/tutors/rut.py` y el teléfono `apps/telefono.py`, y llegan por el mismo
camino que desde el mostrador: los campos del formulario del Tutor
(`apps/campos.py`). Una segunda idea de qué es un RUT válido —una más laxa, que
es lo que siempre se acaba escribiendo en un importador para que la migración
«entre entera»— dejaría en la base fichas que el formulario no habría dejado
escribir, y el día que alguien las abriera no se podrían guardar.

**Qué es la misma persona sí se decide aquí**, porque es lo que sostiene la
promesa de poder importar por tandas: reimportar el mismo archivo no crea a nadie
dos veces. Se reconoce por dos cosas a la vez y no por una: por el RUT —que es
único dentro de la Clínica por diseño (ADR-0003)— y por el nombre completo junto
con el teléfono, que es lo que distingue a dos personas en una planilla de
clínica. Por las dos, porque la segunda tanda casi nunca trae las mismas
columnas que la primera: quien entró con su RUT y vuelve en una planilla que no
tiene esa columna se reconoce por el nombre y el teléfono, y al revés. Reconocer
por una sola sería duplicar a media clínica en la segunda tanda.

Cuando las dos dicen cosas distintas manda el RUT: dos fichas con el mismo
nombre y el mismo teléfono pero con RUT distinto son dos personas —una casa con
madre e hija del mismo nombre—, y el RUT es lo único que lo dice sin adivinar.

Y de ahí sale la tercera decisión, que es la incómoda: **una fila sin RUT y sin
teléfono se rechaza**. No hay nada malo en ella —el mostrador registra a diario
Tutores de los que solo se sabe el nombre— pero no hay manera de reconocerla si
la planilla se vuelve a subir, así que aceptarla sería prometer idempotencia y no
cumplirla en silencio. Se rechaza diciéndolo, que deja al admin añadir el
teléfono en su Excel o dar de alta esa ficha a mano.

Nada de esto elige Clínica: la pone `FormularioDeLaClinica` a partir de quien
sube el archivo, igual que en el alta del mostrador, y por eso no hay ninguna
columna de la planilla que pueda decir otra cosa (ADR-0003).
"""

from dataclasses import dataclass
from functools import partial

from django.db import transaction
from django.utils.translation import gettext as _

from apps.busqueda import sin_tildes
from apps.imports.informe import FilaExaminada, Informe, lo_que_esta_mal
from apps.imports.models import Importacion, LoQueSeImporta
from apps.imports.planilla import Columna, Planilla, ejemplo_de
from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tutors.models import Tutor
from apps.tutors.rut import digito_verificador


def _rut_de_ejemplo(cuerpo):
    """Un RUT que cuadra de verdad, para que el archivo de ejemplo se pueda importar."""
    return f"{cuerpo}{digito_verificador(cuerpo)}"


# El rótulo de cada columna sale del campo del Tutor, que es quien sabe cómo se
# llama ese dato en el dominio (`Columna.etiqueta`).
DelTutor = partial(Columna, modelo=Tutor)


# El formato de la planilla, y la única definición que hay de él. El orden es el
# de las columnas del archivo de ejemplo.
#
# Solo el nombre es obligatorio, por lo mismo que en la ficha del mostrador: una
# planilla de clínica trae filas a medias, y exigir el resto obligaría a
# rellenarlas con cualquier cosa antes de subirlas.
COLUMNAS_DE_LA_PLANILLA = (
    DelTutor(
        "nombre",
        "nombre",
        ("Camila", "Diego", "Ignacia"),
        obligatoria=True,
        alias=("nombres",),
    ),
    DelTutor(
        "apellidos",
        "apellidos",
        ("Rojas Pizarro", "Muñoz Soto", "Vera"),
        alias=("apellido",),
    ),
    DelTutor(
        "rut",
        "rut",
        (_rut_de_ejemplo("12345678"), _rut_de_ejemplo("9876543"), ""),
        alias=("run", "cedula"),
    ),
    DelTutor(
        "telefono",
        "telefono",
        ("+56 9 1234 5678", "912345679", "22 345 6789"),
        alias=("fono", "celular", "movil"),
    ),
    DelTutor(
        "correo",
        "email",
        ("camila.rojas@correo.example", "", "ignacia.vera@correo.example"),
        alias=("email", "mail", "e_mail"),
    ),
    DelTutor(
        "direccion",
        "direccion",
        ("Av. Providencia 1234, depto. 52, Santiago", "Los Alerces 88, Ñuñoa", ""),
        alias=("domicilio",),
    ),
)

# Lo que este módulo es para las vistas: un importador de Tutores. El contrato
# —qué nombres tiene que declarar— lo cuenta `importadores.py`.
QUE = LoQueSeImporta.TUTORES
MODELO = Tutor
PLANTILLA = "imports/tutores.html"
URL_DE_LA_SUBIDA = "imports:tutores"
URL_DEL_EJEMPLO = "imports:ejemplo_de_tutores"
# Adonde se vuelve al confirmar: al fichero de Tutores, que es lo que el admin
# acaba de llenar.
VUELVE_A = "tutors:lista"

# Cómo se llama el archivo de ejemplo cuando se descarga.
EJEMPLO = "planilla-de-tutores-de-ejemplo.csv"


class FilaDeTutorForm(FormularioDeLaClinica):
    """Una fila de la planilla leída como la ficha que crearía.

    Es el formulario del Tutor menos la detección de coincidencias, y esa resta
    es deliberada: para el mostrador, el RUT que ya existe es un error que hay
    que enseñar al lado del campo; aquí es una fila que ya estaba y que hay que
    saltarse sin molestar a nadie. Quién es la misma persona lo decide `examinar`,
    que puede mirar la Clínica entera de una vez en lugar de una consulta por
    fila.

    Lo que sí se hereda —y es lo que importa— son los campos: el RUT y el
    teléfono entran por `CampoDeRut` y `CampoDeTelefono`, así que la planilla se
    valida con las mismas reglas que el mostrador y no con una copia suya.
    """

    class Meta:
        model = Tutor
        fields = list(Tutor.DATOS_PERSONALES)


# Las dos maneras de reconocer a la misma persona. Son dos y no una porque una
# tanda posterior casi nunca trae las mismas columnas que la primera.
POR_EL_RUT = "rut"
POR_EL_NOMBRE = "nombre y teléfono"


@dataclass(frozen=True)
class Conocido:
    """Un Tutor que ya se conoce, y de dónde: de la Clínica o de esta planilla.

    `linea` es la línea de la planilla en que se le vio, o `None` si estaba en la
    Clínica desde antes. Es lo único que separa los dos motivos que se le dan al
    admin, y va junto al Tutor porque es siempre lo mismo que hay que saber de él.
    """

    tutor: object
    linea: int = None


def claves_de(tutor):
    """Todo aquello por lo que se puede reconocer a este Tutor, por cada manera.

    El nombre se pliega como se pliega para buscar (`sin_tildes`), porque la
    misma persona aparece en dos planillas como «Muñoz» y como «Munoz».

    Vacío cuando no hay por dónde: sin RUT y sin teléfono, la fila no se puede
    reconocer, y decirlo es lo que evita duplicarla en la tanda siguiente.
    """
    claves = {}
    if tutor.rut:
        claves[POR_EL_RUT] = (POR_EL_RUT, tutor.rut)
    if tutor.telefono:
        claves[POR_EL_NOMBRE] = (
            POR_EL_NOMBRE,
            sin_tildes(f"{tutor.nombre} {tutor.apellidos}".strip()),
            tutor.telefono,
        )
    return claves


def anotar_como_conocido(conocidos, tutor, linea=None):
    """Deja a ese Tutor apuntado por todas sus claves. El primero se queda el sitio."""
    for clave in claves_de(tutor).values():
        conocidos.setdefault(clave, Conocido(tutor, linea))


def a_quien_ya_se_conocia(ficha, conocidos):
    """El Tutor ya conocido que es esta misma persona, o `None` si es alguien nuevo.

    El RUT se mira primero y decide solo: si la ficha lo trae y ese RUT ya está,
    es esa persona y no hay nada más que preguntar.

    El nombre con el teléfono decide después, y con una reserva: si los dos traen
    RUT y no es el mismo, no son la misma persona por mucho que compartan casa y
    nombre. Sin esa reserva, una madre y una hija que se llaman igual acabarían
    siendo una sola ficha, que es un daño que ya no se deshace.
    """
    claves = claves_de(ficha)
    if (por_el_rut := claves.get(POR_EL_RUT)) in conocidos:
        return conocidos[por_el_rut]

    conocido = conocidos.get(claves.get(POR_EL_NOMBRE))
    if conocido is None or (ficha.rut and conocido.tutor.rut and ficha.rut != conocido.tutor.rut):
        return None
    return conocido


def _resumen(valores):
    """Cómo se reconoce la fila en la planilla, para nombrarla en el informe.

    Sale de lo tecleado y no de la ficha, porque la fila que hay que corregir es
    justo la que no llegó a ser ninguna ficha.
    """
    return " ".join(filter(None, (valores.get("nombre", ""), valores.get("apellidos", ""))))


def _los_que_ya_estan(clinica):
    """Por qué se reconoce a cada Tutor que la Clínica ya tiene.

    De una vez y no una consulta por fila: una migración son miles de filas, y
    preguntar por cada una convertiría la vista previa en algo que nadie espera.
    """
    conocidos = {}
    for tutor in Tutor.de_todas_las_clinicas.filter(clinic=clinica):
        anotar_como_conocido(conocidos, tutor)
    return conocidos


def examinar(contenido, clinica):
    """Qué pasaría con cada línea de esa planilla en esa Clínica. No guarda nada.

    Es lo que enseña la vista previa y lo que después se confirma, y es la misma
    función las dos veces: una vista previa que no fuera exactamente el ensayo de
    la importación sería peor que no tenerla.
    """
    # Un solo diccionario para la Clínica y para la planilla: quien acaba de
    # entrar por la línea 4 se conoce igual que quien llevaba ahí dos años, y
    # llevar dos listas sería preguntar dos veces lo mismo con dos respuestas.
    conocidos = _los_que_ya_estan(clinica)
    examinadas = []

    for fila in Planilla.leer(contenido, columnas=COLUMNAS_DE_LA_PLANILLA):
        resumen = _resumen(fila.valores)
        formulario = FilaDeTutorForm(fila.valores, clinica=clinica)
        if not formulario.is_valid():
            examinadas.append(
                FilaExaminada(fila.numero, resumen, lo_que_esta_mal(formulario), es_un_error=True)
            )
            continue

        ficha = formulario.save(commit=False)
        if not claves_de(ficha):
            examinadas.append(
                FilaExaminada(
                    fila.numero,
                    resumen,
                    _(
                        "Sin RUT y sin teléfono no hay manera de reconocer esta fila si la "
                        "planilla se vuelve a subir. Añade uno de los dos, o registra la "
                        "ficha a mano."
                    ),
                    es_un_error=True,
                )
            )
        elif (conocido := a_quien_ya_se_conocia(ficha, conocidos)) is None:
            anotar_como_conocido(conocidos, ficha, fila.numero)
            examinadas.append(FilaExaminada(fila.numero, resumen, ficha=ficha))
        elif conocido.linea:
            examinadas.append(
                FilaExaminada(
                    fila.numero,
                    resumen,
                    _("La misma persona ya venía en la línea %(cual)s de esta planilla.")
                    % {"cual": conocido.linea},
                )
            )
        else:
            examinadas.append(
                FilaExaminada(
                    fila.numero,
                    resumen,
                    _("Ya está en la Clínica: %(quien)s.") % {"quien": conocido.tutor},
                    # El motivo dice cómo se llama un Tutor que ya estaba, y eso
                    # es servir un dato personal suyo (ADR-0004). La línea de
                    # arriba no nombra a nadie de la Clínica: las dos filas que
                    # compara son las dos de la planilla que se acaba de subir.
                    nombra=(Tutor,),
                )
            )

    return Informe(examinadas)


def importar(informe, clinica, usuario, planilla):
    """Guarda las fichas que el informe daba por creables y deja constancia.

    En una sola transacción con la anotación del Registro: una importación que
    constara sin haber entrado, o que entrara sin constar, valdría lo mismo que
    ninguna de las dos cosas (ADR-0004).
    """
    with transaction.atomic():
        Tutor.de_todas_las_clinicas.bulk_create([fila.ficha for fila in informe.creables])
        return Importacion.de_lo_que_entro(QUE, clinica, usuario, planilla, informe)


def ejemplo():
    """El archivo de ejemplo. Tres personas inventadas, en el formato de arriba."""
    return ejemplo_de(COLUMNAS_DE_LA_PLANILLA)
