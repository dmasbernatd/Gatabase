"""Qué se lleva una Clínica cuando se lleva sus datos: una hoja por cada cosa.

La exportación no es una funcionalidad técnica. Es lo que hace que una clínica se
atreva a poner su archivador en un sistema ajeno: si puede sacarlo cuando quiera
y sin pedir permiso, quedarse es una decisión suya y no del proveedor.

De ahí salen las tres decisiones de este módulo.

**Una hoja por cosa, y no un volcado.** Lo que se descarga es un zip de
planillas, y cada una se abre en el Excel de la clínica y se entiende sin manual:
`tutores.csv` tiene una fila por Tutor con las columnas que ya tenía su
archivador. Un JSON con la base entera dentro también sería un formato abierto, y
no serviría para lo que esto es: nadie migra su clínica leyendo llaves anidadas.

**Las filas salen de a poco.** Cada hoja es un iterador, nunca una lista: son
miles de Tutores y de Pacientes, y armar la planilla entera para escribirla sería
tener en memoria justo lo que se está tratando de no tener (`paquete.py`). Por
eso `.iterator()` y no `list()`, y por eso los tests comprueban que pedirle sus
filas a una hoja no consulta todavía la base de datos.

**Cada hoja cruza la frontera a mano.** Se lee con `de_todas_las_clinicas`
filtrando por la Clínica que se recibe, y no con el manager que filtra solo
(ADR-0003). No es un descuido: la exportación se escribe **después** de que la
petición HTTP haya terminado —la respuesta va saliendo por trozos—, y para
entonces la Clínica activa que puso el middleware ya no está. Sacarla del
argumento es además lo que hace que la casilla del ticket —«solo datos de su
Clínica»— se pueda leer en cada consulta en vez de deducirse de un contexto.

**Los códigos van tal cual, y con ellos su catálogo.** En `pacientes.csv` la
especie dice `perro` y el estado de identificación dice `sin_chip`, que es lo que
guarda la base; `especies.csv` y `razas.csv` van dentro del mismo zip para que se
sepa qué valores existen y cómo se llaman. Traducir los códigos al vuelo dejaría
una planilla bonita e imposible de volver a cargar en ninguna parte.

Lo que **no** va: los Usuarios de la Clínica y el Registro de acceso. Los
primeros porque no son datos de la clínica sobre sus Tutores y sus Pacientes,
sino las cuentas con que su gente entra —y una Clínica que se cierra las pierde
(`cierre.py`)—. El segundo porque es evidencia ante la Ley 21.719 y no material
de migración: se consulta desde su propia página, y el derecho de acceso de un
Tutor concreto a lo que se vio de él es del ticket 20.
"""

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from apps.patients.catalogo import RAZAS, Especie
from apps.patients.models import Paciente
from apps.tenancy.horarios import Dia
from apps.tenancy.models import (
    ClinicaDeDerivacion,
    ExcepcionDeAtencion,
    FranjaDeAtencion,
    Sede,
)
from apps.tutors.models import Consentimiento, Tutor, Vinculo

# De cuántas en cuántas filas se pide a la base de datos. Bastantes para que no
# sea una consulta por Tutor, pocas para que lo que hay en memoria a la vez sea
# una tanda y no una Clínica.
POR_TANDAS = 500

# Cómo se escribe en una planilla un sí y un no. Con todas sus letras y no con
# `True`: lo abre una persona, y una columna de `True`/`False` en castellano se
# lee como un error del sistema.
SI = _("sí")
NO = _("no")

# Un hueco. La cadena vacía y no un guion: un guion es un dato que alguien
# escribió, y lo que hay aquí es que no hay nada.
NADA = ""


def _si_o_no(valor):
    return SI if valor else NO


def _hora(valor):
    """Una hora como se lee en el cartel de la puerta: `09:00`. Vacía si no hay.

    Al lado de `_fecha` y por lo mismo: las Excepciones de atención tienen horas
    que pueden faltar —el día que la Sede cierra entero no las lleva—, y decidir
    en cada lector qué se escribe entonces acabaría con dos respuestas distintas.
    """
    return f"{valor:%H:%M}" if valor else NADA


def _fecha(valor):
    """Una fecha como la entiende cualquier planilla del mundo: `2026-08-26`.

    En ISO y no a la chilena aunque la aplicación las presente a la chilena
    (`CONTEXT.md`): esto no lo lee una persona en una pantalla, lo lee el Excel
    de otro sistema, y `03-04-2026` es dos fechas distintas según quién abra.
    """
    return valor.isoformat() if valor else NADA


@dataclass(frozen=True)
class Hoja:
    """Una de las planillas del zip: cómo se llama, qué columnas trae y qué filas.

    `de` recibe la Clínica y devuelve un iterador de filas — no una lista, ver el
    docstring del módulo. `modelo` dice de quién son los datos, y solo lo llevan
    las hojas con datos de un Tutor o de un Paciente: es lo que se anota en el
    Registro de acceso (ADR-0004). Un catálogo de especies no es dato de nadie, y
    anotar su lectura sería ruido en la tabla que tiene que valer como prueba.
    """

    nombre: str
    cabecera: tuple
    de: callable
    modelo: object = None

    def filas(self, clinica):
        """La cabecera y detrás las filas, según se van leyendo."""
        yield self.cabecera
        yield from self.de(clinica)


def _de_la_clinica(modelo, clinica, *relacionados):
    """Los objetos de ese modelo que son de esa Clínica, de a tandas.

    Cruza la frontera a mano y a propósito: ver el docstring del módulo. Por el
    manager que lo ve todo cuando el modelo lo tiene, y por `objects` cuando no
    —la Sede no lo lleva, porque el suyo no filtra por la Clínica activa: se
    resuelve quién entra antes de que haya ninguna
    (`apps/tenancy/comprobaciones.py`)—. En los dos casos la Clínica la pone el
    `filter`, que es lo único que aquí importa.

    El `.iterator()` vive aquí y no en cada lector porque es la decisión que
    sostiene la casilla de la memoria: repartida por ocho sitios, el noveno lector
    que se escriba se la salta sin que nadie lo note. `relacionados` es lo que
    cada uno necesita traído de una vez —el Tutor de un Vínculo, la Sede de una
    Franja—, para que leer de a tandas no signifique una consulta por fila.
    """
    manager = getattr(modelo, "de_todas_las_clinicas", None) or modelo.objects
    de_la_clinica = manager.filter(clinic=clinica)
    if relacionados:
        de_la_clinica = de_la_clinica.select_related(*relacionados)
    return de_la_clinica.iterator(chunk_size=POR_TANDAS)


def _tutores(clinica):
    for tutor in _de_la_clinica(Tutor, clinica):
        yield (
            tutor.pk,
            tutor.nombre,
            tutor.apellidos,
            # El RUT como se dicta y no como se guarda: es la columna que alguien
            # va a mirar para reconocer a una persona, y `123456785` no se
            # reconoce. Vuelve a entrar por el importador igual (`apps/imports`).
            tutor.rut_a_la_chilena,
            tutor.telefono,
            tutor.email,
            tutor.direccion,
        )


def _pacientes(clinica):
    for paciente in _de_la_clinica(Paciente, clinica):
        yield (
            paciente.pk,
            paciente.nombre,
            paciente.especie,
            paciente.raza,
            paciente.sexo,
            _fecha(paciente.fecha_de_nacimiento),
            paciente.color,
            paciente.microchip,
            paciente.estado_de_identificacion,
            paciente.estado,
            _fecha(paciente.fecha_de_fallecimiento),
            paciente.observaciones,
        )


def _vinculos(clinica):
    """Quién responde por qué animal, y quién respondió antes.

    Van los cerrados también, y no es opcional: un Vínculo cerrado es quien trajo
    al animal hasta tal día, y eso es parte de la Historia del Paciente
    (ADR-0001). Una exportación que solo trajera los abiertos se llevaría la
    clínica de hoy y dejaría atrás la de siempre.

    Con el nombre del Tutor y del Paciente al lado del identificador: el
    identificador es lo que une las tres planillas, y el nombre es lo que hace
    que la del medio se pueda leer sin cruzarla con las otras dos.
    """
    for vinculo in _de_la_clinica(Vinculo, clinica, "tutor", "paciente"):
        yield (
            vinculo.tutor_id,
            str(vinculo.tutor),
            vinculo.paciente_id,
            vinculo.paciente.nombre,
            _si_o_no(vinculo.responsable),
            _fecha(vinculo.fecha_de_cierre),
        )


def _consentimientos(clinica):
    """Todo lo que cada Tutor ha dicho sobre que se le escriba, no lo último.

    La historia entera, por lo mismo que se guarda entera: lo exigible no es qué
    acepta hoy, sino desde cuándo lo aceptaba el día que se le escribió. Una
    exportación con una columna de sí o no por canal dejaría a la clínica que se
    lleva sus datos sin nada detrás de los mensajes que ya envió.
    """
    for dicho in _de_la_clinica(Consentimiento, clinica, "tutor"):
        yield (
            dicho.tutor_id,
            str(dicho.tutor),
            dicho.canal,
            _si_o_no(dicho.otorgado),
            _fecha(dicho.fecha),
        )


def _sedes(clinica):
    for sede in _de_la_clinica(Sede, clinica):
        yield (
            sede.nombre,
            sede.direccion,
            _si_o_no(sede.atiende_urgencias),
            sede.telefono_de_urgencias,
        )


def _horarios(clinica):
    for franja in _de_la_clinica(FranjaDeAtencion, clinica, "sede"):
        yield (
            franja.sede.nombre,
            # El día por su nombre y no por el número con que se guarda: aquí el
            # código no lo decodifica ningún catálogo del zip, y «0» en la
            # planilla del horario de una clínica no significa nada.
            Dia(franja.dia).label,
            _hora(franja.desde),
            _hora(franja.hasta),
        )


def _excepciones(clinica):
    for excepcion in _de_la_clinica(ExcepcionDeAtencion, clinica, "sede"):
        yield (
            excepcion.sede.nombre,
            _fecha(excepcion.fecha),
            excepcion.motivo,
            _hora(excepcion.desde),
            _hora(excepcion.hasta),
        )


def _derivaciones(clinica):
    for derivacion in _de_la_clinica(ClinicaDeDerivacion, clinica):
        yield (derivacion.nombre, derivacion.telefono, derivacion.direccion)


def _especies(_clinica):
    """El catálogo cerrado de especies, para que se sepa qué dice `pacientes.csv`.

    No es dato de la Clínica —es código (`apps/patients/catalogo.py`)— y va
    dentro igual: sin él, la columna «especie» es una lista de palabras sueltas
    sin manera de saber si están todas las que hay.
    """
    for especie in Especie:
        yield (especie.value, especie.label)


def _razas(_clinica):
    """Las razas que la clínica tenía sugeridas, por especie.

    Sugeridas y no obligatorias: la raza admite texto libre, así que en
    `pacientes.csv` hay razas que no están aquí, y eso no es un error del archivo
    sino cómo funciona el catálogo abierto.
    """
    for especie, razas in RAZAS.items():
        for raza in razas:
            yield (especie.value, raza)


# Lo que va dentro del zip, en el orden en que se escribe. Primero las personas y
# los animales, que es lo que la clínica viene a buscar; detrás lo que la Clínica
# declara de sí misma; al final los catálogos, que explican a los primeros.
HOJAS = (
    Hoja(
        "tutores.csv",
        (_("id"), _("nombre"), _("apellidos"), _("RUT"), _("teléfono"), _("correo"), _("dirección")),
        _tutores,
        modelo=Tutor,
    ),
    Hoja(
        "pacientes.csv",
        (
            _("id"),
            _("nombre"),
            _("especie"),
            _("raza"),
            _("sexo"),
            _("fecha de nacimiento"),
            _("color"),
            _("microchip"),
            _("estado de identificación"),
            _("estado"),
            _("fecha de fallecimiento"),
            _("observaciones"),
        ),
        _pacientes,
        modelo=Paciente,
    ),
    Hoja(
        "vinculos.csv",
        (
            _("id del Tutor"),
            _("Tutor"),
            _("id del Paciente"),
            _("Paciente"),
            _("es el responsable"),
            _("hasta"),
        ),
        _vinculos,
        modelo=Vinculo,
    ),
    Hoja(
        "consentimientos.csv",
        (_("id del Tutor"), _("Tutor"), _("canal"), _("autoriza"), _("fecha")),
        _consentimientos,
        modelo=Consentimiento,
    ),
    Hoja(
        "sedes.csv",
        (_("nombre"), _("dirección"), _("atiende urgencias"), _("teléfono de urgencias")),
        _sedes,
    ),
    Hoja(
        "horarios.csv",
        (_("Sede"), _("día"), _("desde"), _("hasta")),
        _horarios,
    ),
    Hoja(
        "excepciones.csv",
        (_("Sede"), _("fecha"), _("motivo"), _("desde"), _("hasta")),
        _excepciones,
    ),
    Hoja(
        "clinicas_de_derivacion.csv",
        (_("nombre"), _("teléfono"), _("dirección")),
        _derivaciones,
    ),
    Hoja("especies.csv", (_("código"), _("especie")), _especies),
    Hoja("razas.csv", (_("especie"), _("raza")), _razas),
)


def de_quienes_son_los_datos():
    """Los modelos cuyos datos sirve la exportación, para el Registro de acceso.

    Solo los que llevan datos de un Tutor o de un Paciente: es lo que ADR-0004
    manda anotar, y anotar además la lectura de un catálogo de especies llenaría
    de ruido la tabla que tiene que valer como prueba.
    """
    return [hoja.modelo for hoja in HOJAS if hoja.modelo is not None]
