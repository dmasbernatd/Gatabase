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

**Se barre lo viejo al subir algo nuevo.** Un archivo cuya sesión ya caducó no lo
puede recuperar nadie —el nombre inventado vivía ahí dentro— y quedaría en el
disco para siempre. Barrerlo al subir cuesta un listado de un directorio con muy
pocas entradas y evita el proceso periódico que nadie va a montar.

Lo viejo se mide como lo mide la sesión, y por eso **recuperar la planilla la
rejuvenece**: la sesión de Gatabase caduca por inactividad y se renueva en cada
petición (`SESSION_SAVE_EVERY_REQUEST`), así que quien está mirando su vista
previa desde hace una hora sigue teniendo sesión. Sin rejuvenecer el archivo, el
barrido se llevaría por delante justo la planilla que esa persona está a punto de
confirmar.
"""

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


def _directorio():
    directorio = Path(settings.DIRECTORIO_DE_IMPORTACIONES)
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def _barrer_lo_que_ya_no_alcanza_nadie(directorio):
    """Borra las planillas que nadie ha tocado en lo que dura una sesión.

    Es el mismo plazo y la misma cuenta que la sesión de la que cuelgan —por
    inactividad, no desde que se subieron—, porque `recuperar` rejuvenece el
    archivo cada vez que se mira. Una planilla más vieja que eso es una cuya
    sesión caducó, y su nombre inventado se fue con ella.
    """
    limite = timezone.now().timestamp() - settings.SESSION_COOKIE_AGE
    for archivo in directorio.glob(f"*{EXTENSION}"):
        if archivo.stat().st_mtime < limite:
            archivo.unlink(missing_ok=True)


def guardar(request, subido):
    """Deja la planilla a la espera y la cuelga de la sesión de quien la subió."""
    olvidar(request)
    directorio = _directorio()
    _barrer_lo_que_ya_no_alcanza_nadie(directorio)

    guardada = uuid4().hex + EXTENSION
    (directorio / guardada).write_bytes(subido.read())
    request.session[CLAVE_EN_LA_SESION] = {"guardada": guardada, "nombre": subido.name}


def recuperar(request):
    """La planilla que espera confirmación: `(nombre con que llegó, bytes)`, o `None`.

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
    return esperando["nombre"], archivo.read_bytes()


def olvidar(request):
    """Borra la planilla que esperaba, si había alguna. Se puede llamar siempre."""
    esperando = request.session.pop(CLAVE_EN_LA_SESION, None)
    if esperando:
        (_directorio() / Path(esperando["guardada"]).name).unlink(missing_ok=True)
