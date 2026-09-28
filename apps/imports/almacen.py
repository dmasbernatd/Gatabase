"""Dónde espera la planilla subida entre la vista previa y la confirmación.

La vista previa promete que no se guarda nada hasta confirmar, así que entre las
dos páginas el archivo tiene que estar en alguna parte, y ninguna de las dos
opciones evidentes sirve:

- **En la base de datos no**, porque la planilla es una copia de los datos
  personales de cientos de Tutores. El derecho de supresión (ticket 20) se cumple
  vaciando la tabla del Tutor «sin tocar ninguna otra», y esa copia sobreviviría a
  ello en silencio.
- **En la sesión tampoco**: la sesión de Gatabase vive en la base de datos, así
  que sería lo mismo de arriba con una fila más rara.

Queda el disco, que es donde ya estaba el archivo antes de subirlo: en
`DIRECTORIO_DE_IMPORTACIONES`, que el `.gitignore` excluye desde antes de que
existiera este módulo. De la sesión cuelga solo el nombre inventado del archivo
—nunca el que escribió el navegador, que puede traer barras—, así que una planilla
solo la puede leer quien la subió y desde la misma sesión.

**Se barre lo viejo al subir algo nuevo, y además cuando lo pida un cron.** Un
archivo cuya sesión ya caducó no lo puede recuperar nadie —el nombre inventado
vivía ahí dentro— y quedaría en el disco para siempre. Barrerlo al subir cuesta
un listado de un directorio con muy pocas entradas, pero depende de que alguien
suba la siguiente planilla, y una clínica que importa una vez al llegar no sube
ninguna más: la última se quedaría ahí con los datos de cientos de Tutores,
incluidos los que después pidan que los borren (ticket 20). Por eso el mismo
barrido lo corre también `manage.py barrer_importaciones`, que es lo que el
despliegue programa.

Lo viejo se mide como lo mide la sesión, y por eso **recuperar la planilla la
rejuvenece**: la sesión de Gatabase caduca por inactividad y se renueva en cada
petición (`SESSION_SAVE_EVERY_REQUEST`), así que quien está mirando su vista
previa desde hace una hora sigue teniendo sesión. Sin rejuvenecer el archivo, el
barrido se llevaría por delante justo la planilla que esa persona está a punto de
confirmar.
"""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

# De qué cuelga en la sesión lo que se está por importar.
CLAVE_EN_LA_SESION = "planilla_por_confirmar"

# La extensión con que se guarda, que no es la que traía: lo que se sirve de este
# directorio no lo sirve nadie, pero un `.html` subido y guardado con su nombre
# es la clase de cosa que un día se acaba sirviendo.
EXTENSION = ".csv"


@dataclass(frozen=True)
class Esperando:
    """La planilla que espera confirmación: qué decía traer, cómo llegó y qué trae.

    Los tres viajan juntos siempre —quien la lee necesita saber quién sabe
    leerla— y por eso son un tipo y no una tupla que cada vista desempaqueta a su
    manera.
    """

    que: str
    nombre: str
    contenido: bytes


def _directorio():
    directorio = Path(settings.DIRECTORIO_DE_IMPORTACIONES)
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def barrer_lo_que_ya_no_alcanza_nadie():
    """Borra las planillas que nadie ha tocado en lo que dura una sesión.

    Es el mismo plazo y la misma cuenta que la sesión de la que cuelgan —por
    inactividad, no desde que se subieron—, porque `recuperar` rejuvenece el
    archivo cada vez que se mira. Una planilla más vieja que eso es una cuya
    sesión caducó, y su nombre inventado se fue con ella.

    Devuelve cuántas borró, que es lo único que quien lo corre desde un cron
    necesita saber.
    """
    limite = timezone.now().timestamp() - settings.SESSION_COOKIE_AGE
    barridas = 0
    for archivo in _directorio().glob(f"*{EXTENSION}"):
        if archivo.stat().st_mtime < limite:
            archivo.unlink(missing_ok=True)
            barridas += 1
    return barridas


def guardar(request, subido, que):
    """Deja la planilla a la espera y la cuelga de la sesión de quien la subió.

    `que` es lo que decía traer —Tutores o Pacientes—, y se guarda con ella
    porque las tres páginas que vienen después son las mismas para las dos: sin
    esto, confirmar una planilla de animales la leería como si fuera de personas.
    """
    olvidar(request)
    barrer_lo_que_ya_no_alcanza_nadie()

    guardada = uuid4().hex + EXTENSION
    (_directorio() / guardada).write_bytes(subido.read())
    request.session[CLAVE_EN_LA_SESION] = {
        "guardada": guardada,
        "nombre": subido.name,
        "que": que,
    }


def recuperar(request):
    """La planilla que espera: `(qué traía, nombre con que llegó, bytes)`, o `None`.

    `None` también cuando el archivo ya no está —la sesión sobrevivió a un
    barrido, o al despliegue que se llevó el disco—, porque para quien está
    delante es lo mismo: hay que volver a subirla.
    """
    esperando = request.session.get(CLAVE_EN_LA_SESION)
    if not esperando:
        return None
    archivo = _directorio() / Path(esperando["guardada"]).name
    if not archivo.is_file():
        olvidar(request)
        return None
    # Mirarla cuenta como tocarla, igual que para la sesión: quien lleva media
    # hora leyendo su vista previa no puede perder la planilla por leerla.
    archivo.touch()
    return Esperando(esperando.get("que"), esperando["nombre"], archivo.read_bytes())


def que_espera(request):
    """Qué decía traer la planilla que espera, o `None` si no hay ninguna.

    Se responde desde la sesión y sin tocar el disco: quien solo necesita saber
    de qué era —para volver a su página después de descartarla— no tiene por qué
    leerse el archivo entero ni rejuvenecerlo.
    """
    esperando = request.session.get(CLAVE_EN_LA_SESION)
    return esperando.get("que") if esperando else None


def olvidar(request):
    """Borra la planilla que esperaba, si había alguna. Se puede llamar siempre."""
    esperando = request.session.pop(CLAVE_EN_LA_SESION, None)
    if esperando:
        (_directorio() / Path(esperando["guardada"]).name).unlink(missing_ok=True)
