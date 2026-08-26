"""Importar la planilla con la que una clínica lleva hoy sus animales.

Es la segunda mitad de la migración y la difícil, y lo difícil no es el animal:
es **de quién es**. La planilla de Pacientes de una clínica de verdad nombra a su
Tutor con un nombre escrito a mano —«Sra. Rojas», «camila rojas»—, no con un
identificador, y de ese nombre hay que sacar al Tutor que se importó antes o
decir que no se pudo.

De ahí salen las decisiones de este módulo. Todo lo demás —cómo se lee un CSV de
Excel, cómo se cuentan las filas, qué es un microchip o una raza— ya estaba
escrito y se usa tal cual.

**El Tutor se resuelve por tres vías, y en este orden: RUT, teléfono, nombre.**
El RUT decide solo, porque es único dentro de la Clínica por diseño (ADR-0003):
si la fila lo trae, no hay nada más que preguntar, y si ese RUT no es de nadie de
la Clínica la fila se rechaza en vez de caer al nombre. Un RUT que no cuadra es
un dato que alguien tecleó mal, y resolverlo por el nombre sería colgarle el
animal a quien más se le parezca.

Las otras dos vías se acumulan en vez de turnarse: una familia comparte teléfono
—tres Tutores con el mismo número es lo corriente— y el nombre es lo que
desempata. Por eso lo que se resuelve es la intersección de lo que la fila trae,
y no la primera vía que devuelva algo.

**Cuando quedan dos, la fila se rechaza diciendo entre quiénes dudó**, con el RUT
de cada uno al lado para que se puedan distinguir en la planilla. Elegir el
primero sería la clase de error que nadie ve: el animal queda colgado de la
persona equivocada, y quien lo descubre es el veterinario que llama a un número
que no contesta.

**Qué es el mismo animal**: el microchip, y si no lo hay, su nombre junto con su
Tutor. El chip identifica al animal en todo Chile, así que decide solo dentro de
la Clínica (ADR-0001). Sin chip, dos animales que se llaman igual y son del mismo
Tutor son el mismo animal, y el mismo nombre en dos Tutores distintos son dos
animales —que es como se llama a los perros en Chile: hay un Rocky por cuadra—.

Y de ahí sale la única fila que se rechaza por repetida: **un chip que ya es de
otro Paciente**, uno que no se llama como este. No es una fila que ya estaba: es
el mismo número en dos animales, que la base de datos no admite y que nadie
puede resolver desde aquí sin adivinar cuál de los dos lo lleva puesto. Se
rechaza nombrando al Paciente que ya lo tiene, que es por donde se empieza a
mirar.

**El histórico clínico no se importa y no hay columna que lo traiga.** Migrar
historias en texto libre es un pozo sin fondo —lo que se importaría no serviría
para atender ni valdría como historia— y la digitalización empieza en la primera
Consulta nueva. Una columna que lo intente se ignora como cualquier otra
desconocida.

**El estado de identificación no se deduce del chip.** Tener el número apuntado
no es estar inscrito en el Registro Nacional, y la planilla no dice cuál de las
dos cosas pasó: la casilla se queda vacía, que es lo que significa que nadie lo
ha preguntado todavía.
"""

import re
from dataclasses import dataclass
from functools import partial

from django import forms
from django.db import transaction
from django.utils.translation import gettext as _

from apps.busqueda import sin_tildes
from apps.campos import EntradaDeTelefono
from apps.imports.informe import FilaExaminada, Informe, lo_que_esta_mal
from apps.imports.models import Importacion, LoQueSeImporta
from apps.imports.planilla import Columna, Planilla, ejemplo_de
from apps.patients.catalogo import Especie, canonica
from apps.patients.forms import sin_fechas_futuras
from apps.patients.models import Paciente, Sexo
from apps.tenancy.aislamiento import FormularioDeLaClinica
from apps.tutors.campos import EntradaDeRut
from apps.tutors.models import Tutor, Vinculo
from apps.tutors.rut import digito_verificador, formateado

# El rótulo de cada columna sale del campo del Paciente (`Columna.etiqueta`).
DelPaciente = partial(Columna, modelo=Paciente)

# Las columnas que dicen de quién es el animal. Se agrupan porque basta con una:
# una planilla que traiga cualquiera de las tres se puede leer, y una que no
# traiga ninguna no se lee, porque ninguna de sus filas podría entrar.
DE_QUIEN_ES = "de quién es"

# Los RUT del archivo de ejemplo, que son los mismos que trae el ejemplo de
# Tutores: los dos ejemplos se importan uno detrás de otro, que es el orden en
# que va una migración de verdad.
_RUT_DE_CAMILA = f"12345678{digito_verificador('12345678')}"
_RUT_DE_DIEGO = f"9876543{digito_verificador('9876543')}"

# El formato de la planilla, y la única definición que hay de él. El orden es el
# de las columnas del archivo de ejemplo.
#
# Solo el nombre y la especie son obligatorios, por lo mismo que en la ficha del
# mostrador: de la especie dependen protocolos y formularios, y el resto se
# completa cuando se sepa.
COLUMNAS_DE_LA_PLANILLA = (
    DelPaciente(
        "nombre",
        "nombre",
        ("Rocky", "Michi", "Pelusa"),
        obligatoria=True,
        alias=("mascota", "paciente", "animal"),
    ),
    DelPaciente("especie", "especie", ("perro", "gato", "conejo"), obligatoria=True),
    DelPaciente("raza", "raza", ("Poodle", "Siamés", "Belier")),
    DelPaciente("sexo", "sexo", ("macho", "hembra", "")),
    DelPaciente(
        "fecha_de_nacimiento",
        "fecha_de_nacimiento",
        ("13/05/2019", "2021-08-30", ""),
        alias=("nacimiento", "fecha_nacimiento", "fecha_de_nac", "nacio"),
    ),
    DelPaciente("color", "color", ("Negro", "Atigrado", "Blanco")),
    DelPaciente(
        "microchip",
        "microchip",
        ("900123456789012", "", "900 123 456 789 013"),
        alias=("chip", "numero_de_chip", "n_chip"),
    ),
    Columna(
        "rut_tutor",
        "rut_tutor",
        (_RUT_DE_CAMILA, _RUT_DE_DIEGO, ""),
        rotulo=_("RUT del Tutor"),
        alias=("rut_del_tutor", "rut_dueno", "rut_propietario"),
        alguna_de=DE_QUIEN_ES,
    ),
    Columna(
        "telefono_tutor",
        "telefono_tutor",
        ("", "", "22 345 6789"),
        rotulo=_("teléfono del Tutor"),
        alias=("telefono_del_tutor", "fono_tutor", "telefono_dueno"),
        alguna_de=DE_QUIEN_ES,
    ),
    Columna(
        "tutor",
        "tutor",
        ("", "", "Ignacia Vera"),
        rotulo=_("nombre del Tutor"),
        alias=("dueno", "duena", "propietario", "responsable", "cliente"),
        alguna_de=DE_QUIEN_ES,
    ),
)

# Lo que este módulo es para las vistas: un importador de Pacientes. El contrato
# —qué nombres tiene que declarar— lo cuenta `importadores.py`.
QUE = LoQueSeImporta.PACIENTES
MODELO = Paciente
PLANTILLA = "imports/pacientes.html"
URL_DE_LA_SUBIDA = "imports:pacientes"
URL_DEL_EJEMPLO = "imports:ejemplo_de_pacientes"
# Adonde se vuelve al confirmar. A esta misma página, y no a un fichero de
# Pacientes que no existe: al animal se llega por su Tutor o por la caja del
# mostrador, y lo que hace falta ver después de importar es la tanda que acaba
# de entrar, que es lo que esta página enseña.
VUELVE_A = "imports:pacientes"

# Cómo se llama el archivo de ejemplo cuando se descarga.
EJEMPLO = "planilla-de-pacientes-de-ejemplo.csv"

# Cómo escribe una fecha el Excel de una clínica. Es una lista cerrada y no un
# lector que adivine: entre «03/04/2019» y «04/03/2019» no hay nada que
# distinguir, así que se lee a la chilena —día primero— y punto. Un lector que
# adivinara acabaría poniéndole a un animal una fecha de nacimiento de otro mes,
# que es un dato falso indistinguible de uno bueno.
FORMATOS_DE_FECHA = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%y",
    "%d-%m-%y",
)

# Cómo escribe el sexo una planilla. La inicial sola es lo más frecuente, y no es
# ambigua en español: «M» de macho y «H» de hembra.
SEXOS = {
    "macho": Sexo.MACHO,
    "m": Sexo.MACHO,
    "hembra": Sexo.HEMBRA,
    "h": Sexo.HEMBRA,
    "f": Sexo.HEMBRA,
}


# Lo que separa las palabras de un nombre escrito a mano, además del espacio: la
# coma de «Rojas, Camila» y el punto de una inicial. Se quita antes de comparar,
# y por eso da igual en qué orden vengan.
PUNTUACION = re.compile(r"[^\w]+", re.UNICODE)


def _como_se_lee(escrito):
    """Lo escrito plegado como se pliega para buscar, para compararlo con una lista."""
    return sin_tildes(escrito).strip()


class FilaDePacienteForm(FormularioDeLaClinica):
    """Una fila de la planilla leída como la ficha que crearía, y de quién es.

    Es la ficha del Paciente menos la detección de coincidencias —el chip
    repetido lo decide `examinar`, que mira la Clínica entera de una vez— y más
    las tres columnas que dicen de quién es el animal, que no son campos de
    ningún modelo: son la manera en que una planilla nombra a una persona.

    Lo que sí se hereda es lo que importa: el microchip entra por
    `CampoDeMicrochip` y el RUT y el teléfono del Tutor por los mismos campos con
    que se teclean en el mostrador, así que aquí no hay una segunda idea de qué
    es ninguno de los tres.
    """

    # La especie no se declara como el desplegable del modelo: el mensaje de
    # Django —«escoja una opción válida»— no dice cuáles son, y el catálogo es
    # cerrado justamente para que haya que mirarlo.
    especie = forms.CharField(label=Paciente._meta.get_field("especie").verbose_name)
    sexo = forms.CharField(
        label=Paciente._meta.get_field("sexo").verbose_name, required=False
    )
    fecha_de_nacimiento = forms.DateField(
        label=Paciente._meta.get_field("fecha_de_nacimiento").verbose_name,
        required=False,
        input_formats=FORMATOS_DE_FECHA,
    )

    rut_tutor = EntradaDeRut(label=_("RUT del Tutor"), required=False)
    telefono_tutor = EntradaDeTelefono(label=_("teléfono del Tutor"), required=False)
    tutor = forms.CharField(label=_("nombre del Tutor"), required=False)

    class Meta:
        model = Paciente
        fields = ["nombre", "especie", "raza", "sexo", "fecha_de_nacimiento", "color", "microchip"]

    def clean_especie(self):
        """La especie del catálogo que se escribió, o el catálogo entero como error.

        Se compara plegado —sin tildes ni mayúsculas— porque nadie escribe
        «hurón» con el acento a las siete de la tarde, pero no se admite nada que
        no esté: de la especie dependen protocolos y formularios, y un «canino»
        importado sería una especie para las estadísticas y ninguna para los
        protocolos (`apps/patients/catalogo.py`).
        """
        escrita = _como_se_lee(self.cleaned_data["especie"])
        for especie in Especie:
            if _como_se_lee(especie.value) == escrita or _como_se_lee(especie.label) == escrita:
                return especie.value
        raise forms.ValidationError(
            _("«%(escrita)s» no es una especie del catálogo. Las que hay son: %(cuales)s."),
            code="especie_que_no_esta_en_el_catalogo",
            params={
                "escrita": self.cleaned_data["especie"],
                "cuales": ", ".join(str(especie.label) for especie in Especie),
            },
        )

    def clean_sexo(self):
        """El sexo como lo escribe una planilla, o un error si no se entiende.

        El hueco es una respuesta —de un animal recogido en la calle no se sabe—
        y entra como hueco. Lo que no se entiende no: dejarlo en blanco en
        silencio sería tirar un dato que la clínica sí tenía, y ponerlo a ojo
        sería inventarlo.
        """
        escrito = _como_se_lee(self.cleaned_data["sexo"])
        if not escrito:
            return ""
        if escrito in SEXOS:
            return SEXOS[escrito]
        raise forms.ValidationError(
            _("«%(escrito)s» no dice el sexo. Se escribe macho o hembra."),
            code="sexo_que_no_se_entiende",
            params={"escrito": self.cleaned_data["sexo"]},
        )

    def clean_fecha_de_nacimiento(self):
        """Un Paciente no puede haber nacido mañana. La regla es la del mostrador."""
        return sin_fechas_futuras(self.cleaned_data["fecha_de_nacimiento"])

    def clean(self):
        """Deja la raza con la ortografía del catálogo cuando se le parece.

        Y solo eso: la raza que no está en el catálogo se guarda tal como venía
        —es la opción «otra»— en vez de rechazar la fila. Un catálogo de razas
        nunca está completo, y el mestizo con algo raro llega igual.
        """
        datos = super().clean()
        if datos.get("raza"):
            datos["raza"] = canonica(datos.get("especie"), datos["raza"])
        return datos


@dataclass(frozen=True)
class Duda:
    """Por qué no se pudo decir de quién es el animal de una fila.

    `nombra` son los modelos de los que el motivo dice algo, para el Registro de
    acceso: dudar entre dos Tutores es enseñar sus nombres y sus RUT, y no
    dudar de nada no enseña nada de nadie (ADR-0004).
    """

    motivo: str
    nombra: tuple = ()


@dataclass(frozen=True)
class ACargoDe:
    """Lo que se crearía de una fila: el Paciente y el Tutor que responde por él.

    Van juntos porque se guardan juntos o no se guardan: un Paciente importado
    sin nadie detrás sería justo la ficha de trabajo que no dice a quién llamar,
    y el Vínculo no se puede escribir hasta que el Paciente exista.
    """

    paciente: object
    tutor: object


def _como_se_nombra_a_una_persona(escrito):
    """El nombre plegado, sin puntuación y con sus palabras ordenadas.

    Ordenadas y sin puntuación porque una planilla escribe «Rojas, Camila» tan a
    menudo como «Camila Rojas», y son el mismo Tutor escrito de dos maneras.
    Plegado porque el mismo Tutor aparece como «Muñoz» y como «Munoz».

    Lo que **no** se hace es partir el nombre en trozos y buscar por el que más
    se parezca, ni quitar tratamientos: «Sra. Rojas» no nombra a nadie en
    particular —un «Rojas» a secas se parece a media clínica— y colgarle el
    animal al primero sería el error que nadie ve. Esa fila se rechaza diciendo
    que no hay ningún Tutor que se llame así, y el admin escribe el nombre
    entero o pone el RUT.
    """
    return " ".join(sorted(PUNTUACION.sub(" ", sin_tildes(escrito)).split()))


def _como_se_distingue(tutor):
    """Cómo se nombra a un Tutor cuando hay que distinguirlo de otro igual.

    Con su RUT al lado, que es lo único que separa a dos personas del mismo
    nombre. Sin RUT no hay nada que añadir, y decirlo así —el nombre a secas— es
    más honesto que un paréntesis vacío.
    """
    return f"{tutor} ({tutor.rut_a_la_chilena})" if tutor.rut else str(tutor)


class Tutores:
    """Los Tutores de la Clínica, apuntados por todo aquello por lo que se los nombra.

    De una vez y no una consulta por fila: una migración son miles de filas, y
    preguntar por cada una convertiría la vista previa en algo que nadie espera.
    """

    def __init__(self, clinica):
        self.por_el_rut = {}
        self.por_el_telefono = {}
        self.por_el_nombre = {}
        for tutor in Tutor.de_todas_las_clinicas.filter(clinic=clinica):
            if tutor.rut:
                self.por_el_rut[tutor.rut] = tutor
            if tutor.telefono:
                self.por_el_telefono.setdefault(tutor.telefono, []).append(tutor)
            self.por_el_nombre.setdefault(
                _como_se_nombra_a_una_persona(str(tutor)), []
            ).append(tutor)

    def de_quien_es(self, valores):
        """El Tutor que la fila nombra, o la `Duda` que impide decirlo.

        Devuelve siempre uno de los dos y nunca los dos: o se sabe de quién es el
        animal, o la fila no entra. Vincularlo a nadie sería crear la ficha
        activa que no dice a quién llamar, y eso es lo que el importador no puede
        dejar en la Clínica de nadie.
        """
        if rut := valores.get("rut_tutor"):
            tutor = self.por_el_rut.get(rut)
            if tutor is None:
                return None, Duda(
                    # A la chilena, que es como está escrito en la planilla que
                    # hay que ir a corregir; guardado va de corrido.
                    _("Ningún Tutor de la Clínica tiene el RUT %(rut)s.")
                    % {"rut": formateado(rut)}
                )
            return tutor, None

        # Las dos vías que quedan se acumulan: el teléfono acota a la casa y el
        # nombre dice a quién de la casa. Turnarlas dejaría fuera justo el caso
        # corriente —tres Tutores con el mismo número—, que es el que hay que
        # resolver.
        candidatos = None
        if telefono := valores.get("telefono_tutor"):
            candidatos = self.por_el_telefono.get(telefono, [])
        if nombre := valores.get("tutor"):
            por_el_nombre = self.por_el_nombre.get(_como_se_nombra_a_una_persona(nombre), [])
            if candidatos is None:
                candidatos = por_el_nombre
            else:
                candidatos = [tutor for tutor in candidatos if tutor in por_el_nombre]

        if candidatos is None:
            return None, Duda(
                _(
                    "La fila no dice de quién es el animal: pon el RUT, el teléfono o el "
                    "nombre de su Tutor."
                )
            )
        if not candidatos:
            return None, Duda(
                _("No hay ningún Tutor que se llame o conteste así: %(cual)s.")
                % {"cual": " ".join(filter(None, (nombre, telefono)))}
            )
        if len(candidatos) > 1:
            return None, Duda(
                _("Hay %(cuantos)s Tutores que podrían ser: %(cuales)s. Pon el RUT en la fila.")
                % {
                    "cuantos": len(candidatos),
                    "cuales": ", ".join(_como_se_distingue(tutor) for tutor in candidatos),
                },
                # El motivo enseña el nombre y el RUT de esos Tutores, y eso es
                # servir sus datos personales aunque nadie haya abierto su ficha.
                nombra=(Tutor,),
            )
        return candidatos[0], None


# Las dos maneras de reconocer al mismo animal. El chip primero, que decide solo.
# Se llaman como las del importador de Tutores, y dicen en su nombre por dónde
# reconocen: los dos módulos se leen como uno.
POR_EL_CHIP = "microchip"
POR_EL_NOMBRE_Y_EL_TUTOR = "nombre y Tutor"


@dataclass(frozen=True)
class Conocido:
    """Un Paciente que ya se conoce, y de dónde: de la Clínica o de esta planilla.

    `linea` es la línea de la planilla en que se le vio, o `None` si estaba en la
    Clínica desde antes, igual que en el importador de Tutores.
    """

    paciente: object
    linea: int = None


def claves_de(paciente, tutor):
    """Todo aquello por lo que se puede reconocer a este animal, por cada manera.

    Nunca vacío, al revés que en el importador de Tutores: el Tutor hace falta
    para que la fila entre, así que siempre hay al menos por dónde reconocerla.
    """
    claves = {POR_EL_NOMBRE_Y_EL_TUTOR: (POR_EL_NOMBRE_Y_EL_TUTOR, sin_tildes(paciente.nombre), tutor.pk)}
    if paciente.microchip:
        claves[POR_EL_CHIP] = (POR_EL_CHIP, paciente.microchip)
    return claves


def anotar_como_conocido(conocidos, paciente, tutor, linea=None):
    """Deja a ese Paciente apuntado por todas sus claves. El primero se queda el sitio."""
    for clave in claves_de(paciente, tutor).values():
        conocidos.setdefault(clave, Conocido(paciente, linea))


def _los_que_ya_estan(clinica):
    """Por qué se reconoce a cada Paciente que la Clínica ya tiene.

    Por su chip, y por su nombre junto a cada Tutor que ha respondido por él: un
    animal puede tener varios —una pareja que se turna—, y la planilla puede
    nombrar a cualquiera de ellos.

    También por los Vínculos **cerrados**, y eso es deliberado: el animal que
    cambió de manos sigue siendo el mismo animal, y una planilla vieja que lo
    nombra con su Tutor de antes está hablando de él. Mirar solo los abiertos lo
    duplicaría en la tanda siguiente —que es justo lo que la reimportación
    promete que no pasa— y de paso le abriría un Vínculo con quien ya no
    responde por él.
    """
    conocidos = {}
    for paciente in Paciente.de_todas_las_clinicas.filter(clinic=clinica):
        if paciente.microchip:
            conocidos.setdefault(
                (POR_EL_CHIP, paciente.microchip), Conocido(paciente)
            )
    vinculos = Vinculo.de_todas_las_clinicas.filter(clinic=clinica).select_related("paciente")
    for vinculo in vinculos:
        conocidos.setdefault(
            (POR_EL_NOMBRE_Y_EL_TUTOR, sin_tildes(vinculo.paciente.nombre), vinculo.tutor_id),
            Conocido(vinculo.paciente),
        )
    return conocidos


def _resumen(valores):
    """Cómo se reconoce la fila en la planilla, para nombrarla en el informe.

    Sale de lo tecleado y no de la ficha —la fila que hay que corregir es justo
    la que no llegó a ser ninguna ficha—, y lleva de quién dice ser el animal
    porque es lo que hay que buscar en el Excel para arreglarla.
    """
    de_quien = valores.get("tutor") or valores.get("rut_tutor") or valores.get("telefono_tutor")
    return " — ".join(filter(None, (valores.get("nombre", ""), de_quien)))


def examinar(contenido, clinica):
    """Qué pasaría con cada línea de esa planilla en esa Clínica. No guarda nada.

    Es lo que enseña la vista previa y lo que después se confirma, y es la misma
    función las dos veces, por lo mismo que en el importador de Tutores: una
    vista previa que no fuera exactamente el ensayo de la importación sería peor
    que no tenerla.
    """
    tutores = Tutores(clinica)
    # Un solo diccionario para la Clínica y para la planilla: el animal que
    # acaba de entrar por la línea 4 se reconoce igual que el que llevaba ahí
    # dos años.
    conocidos = _los_que_ya_estan(clinica)
    examinadas = []

    for fila in Planilla.leer(contenido, columnas=COLUMNAS_DE_LA_PLANILLA):
        resumen = _resumen(fila.valores)
        formulario = FilaDePacienteForm(fila.valores, clinica=clinica)
        if not formulario.is_valid():
            examinadas.append(
                FilaExaminada(fila.numero, resumen, lo_que_esta_mal(formulario), es_un_error=True)
            )
            continue

        tutor, duda = tutores.de_quien_es(formulario.cleaned_data)
        if duda:
            examinadas.append(
                FilaExaminada(
                    fila.numero, resumen, duda.motivo, es_un_error=True, nombra=duda.nombra
                )
            )
            continue

        ficha = formulario.save(commit=False)
        claves = claves_de(ficha, tutor)
        conocido = conocidos.get(claves.get(POR_EL_CHIP)) or conocidos.get(claves[POR_EL_NOMBRE_Y_EL_TUTOR])

        if conocido is None:
            anotar_como_conocido(conocidos, ficha, tutor, fila.numero)
            examinadas.append(
                FilaExaminada(fila.numero, resumen, ficha=ACargoDe(ficha, tutor))
            )
        elif sin_tildes(conocido.paciente.nombre) != sin_tildes(ficha.nombre):
            # Solo se llega aquí por el chip: el otro camino compara el nombre.
            # Dos animales con el mismo número no es una fila repetida, es un
            # dato imposible que la base tampoco admitiría (ADR-0001).
            examinadas.append(
                FilaExaminada(
                    fila.numero,
                    resumen,
                    _("Ese microchip ya es el de %(cual)s.") % {"cual": conocido.paciente},
                    es_un_error=True,
                    nombra=() if conocido.linea else (Paciente,),
                )
            )
        elif conocido.linea:
            examinadas.append(
                FilaExaminada(
                    fila.numero,
                    resumen,
                    _("El mismo animal ya venía en la línea %(cual)s de esta planilla.")
                    % {"cual": conocido.linea},
                )
            )
        else:
            examinadas.append(
                FilaExaminada(
                    fila.numero,
                    resumen,
                    _("Ya está en la Clínica: %(cual)s.") % {"cual": conocido.paciente},
                    # El motivo dice cómo se llama un animal que ya estaba, y a
                    # su ficha se llega a su Tutor (ADR-0004).
                    nombra=(Paciente,),
                )
            )

    return Informe(examinadas)


def importar(informe, clinica, usuario, planilla):
    """Guarda las fichas que el informe daba por creables, con su Vínculo, y deja
    constancia.

    En una sola transacción con la anotación del Registro, igual que en el
    importador de Tutores: una importación que constara sin haber entrado, o que
    entrara sin constar, valdría lo mismo que ninguna de las dos (ADR-0004).

    El Vínculo lo escribe el Tutor (`se_hace_cargo_de`) y no un `bulk_create` de
    Vínculos, aunque sean una consulta por fila: quién responde por un Paciente
    —y que el primero que aparece se queda el cargo— es una regla del dominio, y
    escribirla otra vez aquí para ahorrar consultas dejaría dos definiciones de
    lo que es hacerse cargo de un animal.
    """
    with transaction.atomic():
        acargo = [fila.ficha for fila in informe.creables]
        Paciente.de_todas_las_clinicas.bulk_create([cual.paciente for cual in acargo])
        for cual in acargo:
            cual.tutor.se_hace_cargo_de(cual.paciente)
        return Importacion.de_lo_que_entro(QUE, clinica, usuario, planilla, informe)


def ejemplo():
    """El archivo de ejemplo. Tres animales inventados, en el formato de arriba.

    Son de los tres Tutores del ejemplo de Tutores, y cada uno los nombra de una
    manera distinta —por RUT, por RUT, y por nombre el que no tiene—: así el par
    de archivos se importa uno detrás de otro, que es el orden de una migración
    de verdad, y de paso enseña las tres vías.
    """
    return ejemplo_de(COLUMNAS_DE_LA_PLANILLA)
