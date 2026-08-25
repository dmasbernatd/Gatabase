"""Datos de demostración: una clínica chilena entera, inventada de cabo a rabo.

Existe para tres cosas que sin volumen no se pueden hacer: desarrollar contra un
listado que tarda lo que va a tardar, medir si la búsqueda del mostrador aguanta,
y enseñarle el sistema a la clínica piloto sin abrir la ficha de un cliente real.

Vive en `imports` y no en `tenancy` porque hace falta escribir Tutores y
Pacientes, y `tenancy` no importa de ninguna app de dominio (`CLAUDE.md`): todas
importan de ella. De las que sí pueden verlo todo, esta es la que mueve datos en
bloque hacia dentro y hacia fuera de una Clínica, que es exactamente lo que aquí
se hace.

**Dos Clínicas y no una**, y es la decisión que da forma al resto. El aislamiento
por Clínica (ADR-0003) se prueba en `tests/test_aislamiento_por_clinica.py`, pero
un test comprueba lo que se le ocurrió a quien lo escribió; con dos Clínicas
pobladas, cualquiera que entre con un Usuario de una y no encuentre a los Tutores
de la otra lo está comprobando a mano, sin proponérselo.

**Verosímil quiere decir que no se distingue del dato real al mirarlo**: RUT con
dígito verificador que cuadra, teléfonos chilenos en E.164, nombres y apellidos
que se leen en una sala de espera de Santiago, y una mezcla de especies con
perros y gatos delante, porque es lo que entra por la puerta. Un dato de mentira
que se nota —«Tutor de prueba 412»— sirve para un test y no sirve para ninguna de
las tres cosas de arriba: ni el listado pesa lo mismo, ni la demostración se
sostiene, ni la búsqueda se prueba con lo que la gente teclea.

**Los casos límite se ponen a propósito**, no se esperan del azar. Un Paciente
sin chip, uno fallecido, un Tutor sin RUT, un Tutor extranjero, dos Tutores con
el mismo teléfono, un Paciente con dos Tutores: son los que rompen las pantallas,
y con volumen suficiente el azar los produce solos, pero no hay que depender de
eso — con `--tutores 20` también tienen que estar, y el resumen dice dónde.

**No se borra la Clínica para volver a empezar.** El Registro de acceso no admite
`DELETE` (ADR-0004, migración `audit/0002`), así que el borrado en cascada de una
Clínica con accesos anotados falla, y con él la transacción entera. Lo que se
rehace son sus Tutores y sus Pacientes, que es donde está el volumen; la Clínica,
su Sede y sus Usuarios se reaprovechan, de modo que las contraseñas de la
demostración siguen sirviendo y el Registro de acceso conserva lo que anotó. Para
que no quede ni la Clínica hay que rehacer la base — `dropdb` y `migrate`, o el
contenedor de `scripts/db.sh` otra vez.
"""

import datetime as dt
import random
import unicodedata
from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.patients.catalogo import MESTIZO, Especie, la_ley_exige_identificar, razas_de
from apps.patients.estados import EstadoDelPaciente
from apps.patients.models import EstadoDeIdentificacion, Paciente, Sexo
from apps.tenancy.models import Clinica, Rol, Sede, Usuario
from apps.tutors.consentimiento import Canal
from apps.tutors.models import Consentimiento, Tutor, Vinculo
from apps.tutors.rut import digito_verificador

# La contraseña de todos los Usuarios de demostración. Es única y se dice en voz
# alta —el comando la imprime— porque el secreto aquí no protege nada: estas
# Clínicas no existen y la base donde viven se tira. Lo que sí importa es que sea
# la misma siempre, para que quien enseñe el sistema no tenga que ir a buscarla.
CONTRASENA = "gatabase-demo-2026"

# Cuántos Tutores tiene la Clínica grande si nadie dice otra cosa. Es el tamaño
# de una clínica de una sede con unos años de historia, y está elegido para que
# un listado o una búsqueda mal resueltos se noten al abrirlos: con doscientos
# Tutores todo va rápido, incluido lo que no debería.
TUTORES_POR_DEFECTO = 3000

# La semilla por defecto. Fija a propósito: dos ejecuciones seguidas producen la
# misma clínica, así que un fallo que aparece con estos datos se vuelve a ver, y
# una captura de pantalla de la demostración sigue valiendo mañana.
SEMILLA = 2026


@dataclass(frozen=True)
class Plantilla:
    """Una de las Clínicas de demostración: quién es y de qué tamaño."""

    nombre: str
    sede: str
    direccion: str
    dominio: str
    # Qué parte del tamaño pedido le toca. La segunda Clínica es pequeña porque
    # su trabajo no es pesar, es estar: sirve para ver que sus Tutores no salen
    # cuando se busca desde la primera.
    proporcion: float = 1.0


CLINICAS = (
    Plantilla(
        nombre="Clínica Veterinaria Los Andes (demostración)",
        sede="Providencia",
        direccion="Av. Providencia 2134, Providencia, Santiago",
        dominio="losandes.demo",
    ),
    Plantilla(
        nombre="Clínica Veterinaria Bellavista (demostración)",
        sede="Recoleta",
        direccion="Av. Recoleta 445, Recoleta, Santiago",
        dominio="bellavista.demo",
        proporcion=0.2,
    ),
)

NOMBRES_DE_LAS_CLINICAS = tuple(plantilla.nombre for plantilla in CLINICAS)

# Los Usuarios que se crean en cada Clínica: los tres roles, y más de uno donde
# en una clínica de verdad hay más de uno. Con un solo veterinario no se ve qué
# cambia al mirar la misma ficha desde dos cuentas distintas.
USUARIOS = (
    ("admin", "Marcela", "Fuentes Aravena", Rol.ADMIN),
    ("vet1", "Ignacio", "Cárdenas Riquelme", Rol.VETERINARIO),
    ("vet2", "Josefa", "Tapia Neira", Rol.VETERINARIO),
    ("recepcion1", "Camila", "Rojas Muñoz", Rol.RECEPCION),
    ("recepcion2", "Bastián", "Salinas Vergara", Rol.RECEPCION),
)

NOMBRES_DE_PERSONA = (
    "Camila", "Valentina", "Josefa", "Antonia", "Martina", "Fernanda", "Catalina",
    "Javiera", "Constanza", "Francisca", "Isidora", "Emilia", "Trinidad", "Paula",
    "Carolina", "Marcela", "Daniela", "Pamela", "Andrea", "Claudia", "Ximena",
    "Benjamín", "Matías", "Vicente", "Agustín", "Tomás", "Joaquín", "Sebastián",
    "Cristóbal", "Ignacio", "Diego", "Felipe", "Rodrigo", "Álvaro", "Nicolás",
    "Patricio", "Gonzalo", "Mauricio", "Esteban", "Hernán", "Óscar", "Rubén",
)

APELLIDOS = (
    "González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva",
    "Martínez", "Sepúlveda", "Morales", "Rodríguez", "López", "Fuentes", "Hernández",
    "Torres", "Araya", "Flores", "Espinoza", "Valenzuela", "Castillo", "Tapia",
    "Reyes", "Gutiérrez", "Castro", "Vargas", "Álvarez", "Vásquez", "Sánchez",
    "Fernández", "Carrasco", "Gómez", "Cortés", "Herrera", "Núñez", "Riquelme",
    "Vergara", "Miranda", "Bravo", "Campos", "Orellana", "Salinas", "Cárdenas",
    "Aravena", "Figueroa", "Godoy", "Guzmán", "Navarrete", "Ortiz", "Peña",
)

CALLES = (
    "Av. Providencia", "Av. Irarrázaval", "Manuel Montt", "Av. Vicuña Mackenna",
    "Av. Grecia", "Los Leones", "Av. Pedro de Valdivia", "Av. Matta", "Bilbao",
    "Av. Recoleta", "Av. Independencia", "Santa Rosa", "Av. La Florida",
    "Av. Departamental", "Av. Macul", "Av. Las Condes", "Gran Avenida",
)

COMUNAS = (
    "Providencia", "Ñuñoa", "Santiago", "Recoleta", "Independencia", "La Florida",
    "Macul", "Peñalolén", "San Miguel", "La Cisterna", "Maipú", "Puente Alto",
    "Las Condes", "La Reina", "Estación Central", "Quinta Normal",
)

# Los nombres que se gritan en una sala de espera chilena. Se reparten entre
# especies porque nadie llama «Pelusa» a una iguana.
NOMBRES_DE_MASCOTA = (
    "Pelusa", "Luna", "Simba", "Rocky", "Nala", "Mia", "Toby", "Coco", "Bella",
    "Max", "Kira", "Lola", "Zeus", "Maya", "Bruno", "Sol", "Negro", "Manchas",
    "Copito", "Canela", "Pancho", "Chocolate", "Peluche", "Tomás", "Milo",
    "Blanquita", "Michi", "Guagua", "Osita", "Duque", "Lucky", "Nube", "Pepa",
    "Trufa", "Motita", "Roco", "Cholito", "Frida", "Bruna", "Kiwi", "Mora",
    "Tuna", "Rambo", "Chispa", "Curro", "Runa", "Titi", "Lalo", "Pituca", "Ñoño",
)

COLORES = (
    "Negro", "Blanco", "Café", "Atigrado", "Negro con blanco", "Dorado", "Gris",
    "Tricolor", "Café con blanco", "Naranjo", "Crema", "Carey", "Manchado",
)

# Qué entra por la puerta de una clínica de barrio, en proporción. Los perros y
# los gatos son casi todo, y por eso son casi todo aquí: una mezcla repartida a
# partes iguales daría un listado que no se parece a ninguna clínica y escondería
# justo lo que hay que ver — que las pantallas están llenas de perros.
MEZCLA_DE_ESPECIES = {
    Especie.PERRO: 58,
    Especie.GATO: 31,
    Especie.CONEJO: 4,
    Especie.ROEDOR: 3,
    Especie.AVE: 2,
    Especie.REPTIL: 1,
    Especie.HURON: 1,
}

# Cuántos de los perros, gatos y conejos son mestizos. En Chile es el caso
# corriente y no la excepción (`patients/catalogo.py`), y un catálogo de razas
# repartido por igual daría una estadística falsa.
PROPORCION_DE_MESTIZOS = 0.62

# Cuántos Pacientes tiene un Tutor. La mayoría uno; algunos, una casa entera.
CUANTOS_PACIENTES = ((1, 62), (2, 26), (3, 9), (4, 3))

# Los prefijos con que empieza un microchip de los que se leen en Chile: el 152
# es el código de país, y los del rango 900 son de fabricante (ISO 11784).
PREFIJOS_DE_MICROCHIP = ("152", "900", "981", "985", "956")


@dataclass
class Resumen:
    """Lo que quedó escrito, para que el comando lo cuente y un test lo mire."""

    clinica: Clinica
    sede: Sede
    usuarios: list = field(default_factory=list)
    tutores: int = 0
    pacientes: int = 0
    vinculos: int = 0
    consentimientos: int = 0
    # Qué caso límite quedó en qué ficha. Es lo que hace la diferencia entre
    # «están puestos» y «se pueden mirar»: quien enseña el sistema necesita
    # saber a quién buscar para que la pantalla rara salga a la primera.
    casos_limite: list = field(default_factory=list)


def por_que_no_se_puede_poblar(aunque_no_sea_desarrollo=False):
    """Lo que hay que decirle a quien lo intente, o `None` si se puede.

    Lo que se protege es **el despliegue**, no la base de nadie: en desarrollo el
    comando tiene que correr sin pedir permiso, porque es donde se usa cada día y
    porque una base de desarrollo tiene siempre Clínicas hechas a mano que no son
    estas. No las toca — `limpiar` solo alcanza a las Clínicas de demostración —,
    así que no hay nada de lo que avisar.

    Con `DEBUG` apagado esto parece un despliegue, y ahí hay dos casos que no son
    el mismo:

    - **Con Clínicas que no son de demostración**, hay clientes dentro, y eso no
      lo levanta ninguna opción de la línea de órdenes. Escribir miles de fichas
      inventadas en la base de una clínica de verdad no es un error recuperable.
    - **Sin ellas**, es el despliegue de la demostración a la clínica piloto, que
      corre con la configuración de producción y sin un solo cliente. Ese caso
      existe y se pide explícito: pedirlo a mano es lo que lo separa de escribir
      en la base equivocada por costumbre.

    Se devuelve el motivo y no un `False` a secas por lo mismo que en
    `Vinculo.por_que_no_se_puede_cerrar`: quien se lleva la negativa tiene que
    poder leer qué hacer con ella.
    """
    if settings.DEBUG:
        return None

    ajenas = Clinica.objects.exclude(nombre__in=NOMBRES_DE_LAS_CLINICAS).order_by("nombre")
    if ajenas.exists():
        return _(
            "DJANGO_DEBUG está apagado y esta base tiene Clínicas que no son de "
            "demostración (%(cuales)s): son datos de clientes. Este comando no se "
            "ejecuta contra ellos."
        ) % {"cuales": ", ".join(clinica.nombre for clinica in ajenas[:3])}

    if not aunque_no_sea_desarrollo:
        return _(
            "DJANGO_DEBUG está apagado, así que esto parece un despliegue. Si de "
            "verdad es el de la demostración y no tiene clientes, repítelo con "
            "--aunque-no-sea-desarrollo."
        )
    return None


def limpiar(clinica):
    """Borra los Tutores y los Pacientes de esa Clínica; no la Clínica.

    Ver el módulo: la Clínica no se puede borrar mientras tenga accesos anotados,
    porque el Registro de acceso no admite `DELETE` (ADR-0004). Y tampoco haría
    falta: lo que ocupa y lo que se rehace son los Tutores y los Pacientes. Los
    Vínculos y los Consentimientos se van en cascada detrás de ellos.
    """
    Paciente.de_todas_las_clinicas.filter(clinic=clinica).delete()
    Tutor.de_todas_las_clinicas.filter(clinic=clinica).delete()


def _sin_tildes(texto):
    """El texto reducido a lo que cabe en un correo: sin tildes y en minúsculas."""
    descompuesto = unicodedata.normalize("NFKD", texto)
    limpio = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return "".join(c for c in limpio.lower() if c.isalnum())


class Poblador:
    """Quien inventa una Clínica entera. Un `random.Random` propio y nada más.

    Es una clase y no un puñado de funciones sueltas porque casi todo lo que hace
    depende de dos cosas que tienen que ser las mismas de principio a fin: el
    azar sembrado —para que dos ejecuciones den la misma clínica— y lo que ya
    lleva escrito, que es lo que impide repetir un RUT o un microchip dentro de
    la misma Clínica, donde son únicos (ADR-0001).
    """

    def __init__(self, azar, hoy):
        self.azar = azar
        self.hoy = hoy
        self.ruts = set()
        self.microchips = set()
        self.telefonos = []

    # -- Personas --------------------------------------------------------

    def persona(self):
        """Un nombre y dos apellidos, a la chilena."""
        return (
            self.azar.choice(NOMBRES_DE_PERSONA),
            f"{self.azar.choice(APELLIDOS)} {self.azar.choice(APELLIDOS)}",
        )

    def rut(self):
        """Un RUT que cuadra de verdad y que no se repite en esta Clínica.

        Con su dígito verificador calculado y no inventado: el campo lo comprueba
        pase por donde pase el dato (`tutors/rut.py`), así que un RUT de mentira
        ni siquiera se guardaría — y, sobre todo, un RUT que no cuadra no sirve
        para probar el mostrador, que es donde se teclean mal todos los días.
        """
        while True:
            cuerpo = str(self.azar.randint(5_000_000, 25_999_999))
            rut = cuerpo + digito_verificador(cuerpo)
            if rut not in self.ruts:
                self.ruts.add(rut)
                return rut

    def telefono(self):
        """Un celular chileno en E.164, como se guarda (`apps/telefono.py`)."""
        numero = f"+569{self.azar.randint(10_000_000, 99_999_999)}"
        self.telefonos.append(numero)
        return numero

    def telefono_de_otro(self):
        """El teléfono de un Tutor ya escrito: la familia que comparte número."""
        return self.azar.choice(self.telefonos) if self.telefonos else self.telefono()

    def telefono_extranjero(self):
        """Un número de fuera, con su + y su código de país."""
        pais = self.azar.choice(("54911", "51", "5939", "573", "5218"))
        return f"+{pais}{self.azar.randint(1_000_000, 99_999_999)}"

    def direccion(self):
        return (
            f"{self.azar.choice(CALLES)} {self.azar.randint(100, 9999)}, "
            f"{self.azar.choice(COMUNAS)}"
        )

    def correo(self, nombre, apellidos, cuantos):
        return f"{_sin_tildes(nombre)}.{_sin_tildes(apellidos.split()[0])}{cuantos}@correo.demo"

    # -- Animales --------------------------------------------------------

    def especie(self):
        especies, pesos = zip(*MEZCLA_DE_ESPECIES.items())
        return self.azar.choices(especies, weights=pesos)[0]

    def raza(self, especie):
        """La raza que le toca: mestizo casi siempre donde mestizo significa algo.

        Vacía cuando su especie no tiene catálogo —el hurón—, porque escribir ahí
        cualquier cosa sería inventar un dato que después se cuenta.
        """
        catalogo = razas_de(especie)
        if not catalogo:
            return ""
        if MESTIZO in catalogo and self.azar.random() < PROPORCION_DE_MESTIZOS:
            return MESTIZO
        return self.azar.choice([raza for raza in catalogo if raza != MESTIZO] or [MESTIZO])

    def microchip(self):
        """Quince dígitos que no se repiten en esta Clínica (`patients/microchip.py`)."""
        while True:
            chip = self.azar.choice(PREFIJOS_DE_MICROCHIP) + "".join(
                str(self.azar.randint(0, 9)) for _digito in range(12)
            )
            if chip not in self.microchips:
                self.microchips.add(chip)
                return chip

    def fecha_de_nacimiento(self):
        """Un cumpleaños de los últimos dieciséis años, o ninguno.

        Ninguno es un caso corriente y no un descuido: al animal recogido en la
        calle nadie le sabe la edad, y la ficha tiene que aguantar el hueco.
        """
        if self.azar.random() < 0.12:
            return None
        return self.hoy - dt.timedelta(days=self.azar.randint(60, 16 * 365))

    def hace(self, dias_como_mucho):
        return self.hoy - dt.timedelta(days=self.azar.randint(1, dias_como_mucho))


# Los casos límite garantizados van en las primeras fichas de cada Clínica, y no
# se dejan al azar: con volumen alto salen solos, pero el comando tiene que dar
# lo mismo con `--tutores 20`, que es como se corre mientras se programa. Aquí
# están los índices donde se ponen, para que se lean juntos.
CASO_SIN_RUT = 0
CASO_EXTRANJERO = 1
CASO_TELEFONO_COMPARTIDO = (2, 3)
CASO_SE_DESDIJO = 4
CASO_SIN_CONSENTIMIENTO = 5
CASO_SIN_CHIP = 0
CASO_FALLECIDO = 1
CASO_CON_DOS_TUTORES = 2
CASO_CAMBIO_DE_MANOS = 3

# Por debajo de esto no caben los casos límite garantizados, así que no hay
# clínica que enseñar: es el suelo, no una recomendación.
MINIMO_DE_TUTORES = 8

# Quienes llegan a un mostrador chileno sin RUT. Los nombres son de verdad los
# que se leen, y eso es lo que se quiere probar: un apellido compuesto, una
# ficha sin RUT y un teléfono con otro código de país rompen pantallas.
EXTRANJEROS = (
    ("Rosa", "Quispe Mamani"),
    ("Jean", "Baptiste Pierre"),
    ("Yusleidy", "Rondón Bracho"),
    ("Marta", "Ramírez Ospina"),
    ("Wilfredo", "Huamán Chávez"),
    ("Dieuseul", "Joseph Cadet"),
)


def _la_clinica(plantilla):
    """La Clínica de demostración y su única Sede, creadas o reaprovechadas.

    Se reaprovechan a propósito (ver el módulo): la Clínica no se puede borrar
    mientras el Registro de acceso tenga algo anotado de ella, y tampoco
    interesa — así las contraseñas de la demostración siguen sirviendo entre una
    ejecución y la siguiente.
    """
    clinica, _creada = Clinica.objects.get_or_create(nombre=plantilla.nombre)
    sede, _tambien = Sede.objects.get_or_create(
        clinic=clinica, nombre=plantilla.sede, defaults={"direccion": plantilla.direccion}
    )
    return clinica, sede


def _los_usuarios(clinica, sede, plantilla):
    """Los Usuarios de los tres roles, con la contraseña de demostración.

    Se buscan por correo antes de crearlos: el correo identifica al Usuario en
    todo el sistema, así que volver a ejecutar el comando no puede intentar dar
    de alta el mismo dos veces.
    """
    usuarios = []
    for buzon, nombre, apellidos, rol in USUARIOS:
        email = f"{buzon}@{plantilla.dominio}"
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            usuario = Usuario.objects.create_user(
                email=email,
                clinic=clinica,
                contrasena=CONTRASENA,
                nombre=nombre,
                apellidos=apellidos,
                rol=rol,
            )
        usuario.sedes.add(sede)
        usuarios.append(usuario)
    return usuarios


def _los_tutores(poblador, clinica, cuantos, resumen):
    """Los Tutores de la Clínica, con sus casos límite puestos delante."""
    azar = poblador.azar
    tutores = []
    for indice in range(cuantos):
        garantizado = indice <= max(CASO_TELEFONO_COMPARTIDO)
        extranjero = indice == CASO_EXTRANJERO or (not garantizado and azar.random() < 0.03)
        if extranjero:
            nombre, apellidos = azar.choice(EXTRANJEROS)
        else:
            nombre, apellidos = poblador.persona()

        # Sin RUT: el extranjero que no tiene, y quien no quiso darlo. Las dos
        # razones dejan la misma casilla vacía y las dos se atienden igual.
        sin_rut = extranjero or indice == CASO_SIN_RUT or (not garantizado and azar.random() < 0.09)

        if indice == CASO_TELEFONO_COMPARTIDO[1]:
            telefono = tutores[CASO_TELEFONO_COMPARTIDO[0]].telefono
        elif extranjero:
            telefono = poblador.telefono_extranjero()
        elif not garantizado and azar.random() < 0.04:
            telefono = poblador.telefono_de_otro()
        else:
            telefono = poblador.telefono()

        tutores.append(
            Tutor(
                clinic=clinica,
                nombre=nombre,
                apellidos=apellidos,
                rut="" if sin_rut else poblador.rut(),
                telefono=telefono,
                email=(
                    "" if azar.random() < 0.18 else poblador.correo(nombre, apellidos, indice)
                ),
                direccion="" if azar.random() < 0.08 else poblador.direccion(),
            )
        )

    Tutor.de_todas_las_clinicas.bulk_create(tutores, batch_size=500)
    resumen.tutores = len(tutores)
    resumen.casos_limite += [
        (_("Tutor sin RUT"), str(tutores[CASO_SIN_RUT])),
        (_("Tutor extranjero, sin RUT y con teléfono de fuera"), str(tutores[CASO_EXTRANJERO])),
        (
            _("Dos Tutores con el mismo teléfono (%(telefono)s)")
            % {"telefono": tutores[CASO_TELEFONO_COMPARTIDO[0]].telefono},
            " / ".join(str(tutores[i]) for i in CASO_TELEFONO_COMPARTIDO),
        ),
    ]
    return tutores


def _un_paciente(poblador, clinica):
    """Un animal cualquiera de los que entran por la puerta."""
    azar = poblador.azar
    especie = poblador.especie()

    # El chip lo llevan sobre todo los perros y los gatos, que son a quienes la
    # Ley 21.020 se lo exige (`patients/catalogo.py`). Ponerlo por igual en todas
    # las especies daría una estadística que le diría a recepción que hay iguanas
    # chipeadas, que es un consejo falso desde detrás del mostrador.
    lleva_chip = azar.random() < (0.78 if la_ley_exige_identificar(especie) else 0.05)

    if lleva_chip:
        # Tener el número apuntado no es estar inscrito: por eso son dos campos
        # y por eso aquí se reparten (`patients/models.py`).
        identificacion = azar.choices(
            (EstadoDeIdentificacion.INSCRITO, EstadoDeIdentificacion.IMPLANTADO),
            weights=(62, 38),
        )[0]
    elif la_ley_exige_identificar(especie):
        # En blanco significa que nadie lo ha preguntado todavía, y eso no es
        # `sin chip`. Los dos casos existen en una clínica y los dos tienen que
        # estar aquí, porque la ficha los enseña distinto.
        identificacion = azar.choices(
            (EstadoDeIdentificacion.SIN_CHIP, ""), weights=(72, 28)
        )[0]
    else:
        identificacion = ""

    estado = azar.choices(
        (EstadoDelPaciente.ACTIVO, EstadoDelPaciente.INACTIVO, EstadoDelPaciente.FALLECIDO),
        weights=(86, 10, 4),
    )[0]
    # Fallecido sin fecha es lo corriente: el Tutor avisa meses después y no
    # siempre recuerda el día. La combinación imposible —fecha en quien no consta
    # fallecido— la rechaza la base de datos, y aquí no se produce.
    murio = (
        poblador.hace(3 * 365)
        if estado == EstadoDelPaciente.FALLECIDO and azar.random() < 0.7
        else None
    )

    return Paciente(
        clinic=clinica,
        nombre=azar.choice(NOMBRES_DE_MASCOTA),
        especie=especie,
        raza=poblador.raza(especie),
        sexo=azar.choices((Sexo.MACHO, Sexo.HEMBRA, ""), weights=(47, 47, 6))[0],
        fecha_de_nacimiento=poblador.fecha_de_nacimiento(),
        color=azar.choice(COLORES),
        microchip=poblador.microchip() if lleva_chip else "",
        estado_de_identificacion=identificacion,
        estado=estado,
        fecha_de_fallecimiento=murio,
    )


def _los_pacientes(poblador, clinica, tutores, resumen):
    """Los Pacientes y de quién es cada uno, con sus casos límite delante.

    Devuelve la lista de Pacientes ya escritos y, en paralelo, el índice del
    Tutor que responde por cada uno: es lo que después arma los Vínculos sin
    tener que volver a preguntarle nada a la base de datos.
    """
    azar = poblador.azar
    cuantos, pesos = zip(*CUANTOS_PACIENTES)
    pacientes, de_quien = [], []
    for indice, _tutor in enumerate(tutores):
        for _cual in range(azar.choices(cuantos, weights=pesos)[0]):
            pacientes.append(_un_paciente(poblador, clinica))
            de_quien.append(indice)

    sin_chip = pacientes[CASO_SIN_CHIP]
    sin_chip.especie = Especie.PERRO
    sin_chip.raza = MESTIZO
    sin_chip.microchip = ""
    sin_chip.estado_de_identificacion = EstadoDeIdentificacion.SIN_CHIP

    fallecido = pacientes[CASO_FALLECIDO]
    fallecido.estado = EstadoDelPaciente.FALLECIDO
    fallecido.fecha_de_fallecimiento = poblador.hace(400)

    Paciente.de_todas_las_clinicas.bulk_create(pacientes, batch_size=500)
    resumen.pacientes = len(pacientes)
    resumen.casos_limite += [
        (_("Paciente sin microchip"), str(sin_chip)),
        (_("Paciente fallecido, con su fecha"), str(fallecido)),
    ]
    return pacientes, de_quien


def _otro_tutor(azar, tutores, salvo):
    """Un Tutor al azar que no sea ninguno de esos.

    Se sortea y se avanza hasta dar con uno, en vez de repetir el sorteo hasta
    que salga: así el caso garantizado ocurre siempre, y no «casi siempre». Con
    `MINIMO_DE_TUTORES` por delante, la vuelta siempre encuentra a alguien.
    """
    indice = azar.randrange(len(tutores))
    while tutores[indice] in salvo:
        indice = (indice + 1) % len(tutores)
    return tutores[indice]


def _los_vinculos(poblador, clinica, tutores, pacientes, de_quien, resumen):
    """Quién responde por cada Paciente, y quién respondió antes.

    El primer Vínculo de cada Paciente es el del responsable, que es lo que
    `Tutor.se_hace_cargo_de` haría una a una; aquí se escribe en bloque porque
    son miles y la regla es la misma. Los Vínculos cerrados son los cambios de
    manos ya ocurridos: se guardan con fecha y no se borran nunca (ticket 10).
    """
    azar = poblador.azar
    vinculos = []
    con_dos = cambio_de_manos = None
    for indice, paciente in enumerate(pacientes):
        responsable = tutores[de_quien[indice]]
        # Sin acompañante, el responsable cuenta por los dos: es lo que impide
        # que el Tutor de antes salga siendo el mismo que lo tiene ahora.
        acompana = responsable
        vinculos.append(
            Vinculo(clinic=clinica, tutor=responsable, paciente=paciente, responsable=True)
        )

        # La casa donde el animal es de dos: la pareja que se turna, la hija que
        # lo trae al control. Uno solo de los dos es el responsable, y lo
        # garantiza la base de datos.
        if indice == CASO_CON_DOS_TUTORES or azar.random() < 0.11:
            acompana = _otro_tutor(azar, tutores, (responsable,))
            vinculos.append(
                Vinculo(clinic=clinica, tutor=acompana, paciente=paciente, responsable=False)
            )
            if indice == CASO_CON_DOS_TUTORES:
                con_dos = f"{paciente} — {responsable} / {acompana}"

        # El animal que cambió de manos: el Tutor de antes se queda con su
        # Vínculo cerrado y su fecha, que es lo que después contesta a quién se
        # le hizo qué mientras lo tenía.
        if indice == CASO_CAMBIO_DE_MANOS or azar.random() < 0.04:
            anterior = _otro_tutor(azar, tutores, (responsable, acompana))
            cerrado = poblador.hace(4 * 365)
            vinculos.append(
                Vinculo(
                    clinic=clinica,
                    tutor=anterior,
                    paciente=paciente,
                    responsable=False,
                    fecha_de_cierre=cerrado,
                )
            )
            if indice == CASO_CAMBIO_DE_MANOS:
                cambio_de_manos = f"{paciente} — {anterior}, hasta el {cerrado}"

    Vinculo.de_todas_las_clinicas.bulk_create(vinculos, batch_size=500)
    resumen.vinculos = len(vinculos)
    resumen.casos_limite += [
        (_("Paciente con dos Tutores (responsable primero)"), con_dos),
        (_("Paciente que cambió de manos, con el Tutor de antes"), cambio_de_manos),
    ]
    return vinculos


def _los_consentimientos(poblador, clinica, tutores, resumen):
    """Lo que cada Tutor dijo de cada canal, y algunos que se desdijeron.

    Un canal del que no consta nada es el caso más frecuente y por eso se deja en
    blanco a menudo: **no consta** no es **revocado**, y las dos pantallas se ven
    distintas (`tutors/consentimiento.py`). Quien se desdijo deja dos filas, la
    segunda encima de la primera, que es como se revoca de verdad — nada se
    borra ni se corrige.
    """
    azar = poblador.azar
    declaraciones = []
    for indice, tutor in enumerate(tutores):
        # De este no consta nada de ningún canal, y es el caso más frecuente de
        # todos: nadie se lo ha preguntado. Se pone a mano por lo mismo que los
        # demás casos límite — la ficha lo enseña distinto de una negativa.
        if indice == CASO_SIN_CONSENTIMIENTO:
            continue
        for canal in Canal:
            se_desdijo = indice == CASO_SE_DESDIJO
            if not se_desdijo and azar.random() < 0.28:
                continue
            otorgado = se_desdijo or azar.random() < 0.82
            cuando = poblador.hace(3 * 365)
            declaraciones.append(
                Consentimiento(
                    clinic=clinica, tutor=tutor, canal=canal, otorgado=otorgado, fecha=cuando
                )
            )
            # Revocar es decir algo nuevo encima, nunca borrar lo dicho: dos
            # filas, y la segunda es la que vale (`tutors/consentimiento.py`).
            if otorgado and (se_desdijo or azar.random() < 0.07):
                declaraciones.append(
                    Consentimiento(
                        clinic=clinica,
                        tutor=tutor,
                        canal=canal,
                        otorgado=False,
                        fecha=cuando + dt.timedelta(days=azar.randint(1, 200)),
                    )
                )

    Consentimiento.de_todas_las_clinicas.bulk_create(declaraciones, batch_size=500)
    resumen.consentimientos = len(declaraciones)
    resumen.casos_limite += [
        (_("Tutor que se desdijo del contacto"), str(tutores[CASO_SE_DESDIJO])),
        (_("Tutor del que no consta nada del contacto"), str(tutores[CASO_SIN_CONSENTIMIENTO])),
    ]
    return declaraciones


def poblar(plantilla, tutores=TUTORES_POR_DEFECTO, semilla=SEMILLA, hoy=None):
    """Llena una Clínica de demostración de arriba abajo y cuenta qué quedó.

    Rehace lo de la ejecución anterior antes de escribir (`limpiar`), así que
    correrlo dos veces seguidas deja la misma clínica y no el doble de Tutores.

    El azar se siembra con la semilla **y con el nombre de la Clínica**: así las
    dos Clínicas de demostración no salen calcadas la una de la otra —que es lo
    que haría inútil mirarlas para comprobar el aislamiento— y las dos vuelven a
    salir iguales mañana.
    """
    hoy = hoy or timezone.localdate()
    azar = random.Random(f"{semilla}:{plantilla.nombre}")
    poblador = Poblador(azar, hoy)
    cuantos = max(MINIMO_DE_TUTORES, round(tutores * plantilla.proporcion))

    clinica, sede = _la_clinica(plantilla)
    limpiar(clinica)

    resumen = Resumen(clinica=clinica, sede=sede)
    resumen.usuarios = _los_usuarios(clinica, sede, plantilla)
    los_tutores = _los_tutores(poblador, clinica, cuantos, resumen)
    los_pacientes, de_quien = _los_pacientes(poblador, clinica, los_tutores, resumen)
    _los_vinculos(poblador, clinica, los_tutores, los_pacientes, de_quien, resumen)
    _los_consentimientos(poblador, clinica, los_tutores, resumen)
    return resumen
