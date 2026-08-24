"""A quién se parece la ficha que se está escribiendo, antes de guardarla.

Recepción registra a alguien que ya está registrado más veces de lo que parece:
el mismo Tutor con el RUT tecleado de otra forma, el animal que trajo su hermana
el año pasado. Fusionar dos fichas es caro y se pospone a propósito, así que lo
que queda es la prevención barata — poner la ficha que ya existe delante de quien
está a punto de crear la segunda, y enlazarla.

Aquí vive solo la mecánica: qué es un parecido, cómo se busca y cómo se dice. A
quién se parece cada ficha lo declara su formulario (`PARECIDOS`), que es quien
sabe qué campos tiene delante y cuáles de ellos identifican a alguien.

Está fuera de las dos apps de dominio porque las dos lo necesitan y ninguna puede
importar de la otra (`CLAUDE.md`), igual que `apps/busqueda.py` y
`apps/campos.py`.

**Un parecido avisa; solo dos de ellos impiden guardar**, y esa asimetría es la
decisión de este módulo:

- El RUT y el microchip repetidos **no dejan guardar**, y no porque se parezcan:
  son únicos dentro de la Clínica en la base de datos (ADR-0001, ADR-0003), así
  que la segunda ficha no cabe por mucho que se insista. El aviso lleva a la que
  ya existe, que es a lo que recepción venía casi siempre.
- Lo demás **solo avisa**. Una familia comparte teléfono y dos animales de la
  misma casa pueden llamarse parecido; bloquear ahí obligaría a inventarse un
  dato falso, que es peor que un duplicado porque no se distingue de uno bueno.

Nombrar la ficha que ya existe es servir sus datos, así que las tres maneras de
decirlo —el hueco que se repinta mientras se escribe, el aviso que sobrevive a
guardar y el error al lado del campo— dejan constancia en el Registro de acceso
(ADR-0004). Las tres viven aquí, al lado de la mecánica y no en las vistas de
las dos apps: es el mismo gesto contado en tres momentos, y las dos apps lo
cuentan igual.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html

from apps.audit.models import Accion
from apps.audit.registro import anotar
from apps.tenancy.aislamiento import FormularioDeLaClinica

# Lo que se devuelve cuando se pregunta a quién se parece una ficha: solo el
# hueco de los avisos, que es lo que htmx sustituye sin recargar la página.
PLANTILLA = "coincidencias/_avisos.html"

# Cada cuánto se pregunta mientras se teclea. Es el mismo retardo que la caja del
# mostrador (`apps/tutors/mostrador.py`) y por lo mismo: es lo que separa
# «mientras se escribe» de «una petición por tecla».
RETARDO = "input changed delay:250ms"


class Parecido:
    """Un campo por el que la ficha que se escribe puede ser una que ya existe.

    Sabe tres cosas y ninguna más: qué campo mirar, qué se le dice a quien está
    escribiendo, y si además la base de datos va a rechazar la ficha.
    """

    def __init__(self, campo, aviso, codigo=None):
        self.campo = campo
        # El aviso lleva un hueco `{ficha}` donde va el enlace a la que existe.
        self.aviso = aviso
        # El código del error cuando el duplicado no se puede guardar, o `None`
        # cuando solo se avisa. Que sea el mismo dato el que decide las dos
        # cosas es a propósito: un parecido que impide guardar sin decir por qué
        # sería un error de servidor en la cara de recepción.
        self.codigo = codigo

    @property
    def impide_guardar(self):
        return self.codigo is not None

    def encuentra(self, entre, escrito):
        """Las fichas de esa Clínica que ya tienen ese dato.

        Igualdad y no parecido de verdad: lo escrito llega ya normalizado del
        campo del formulario (`apps/campos.py`), así que «12.345.678-5» y
        «123456785» son el mismo RUT antes de llegar aquí. Sin dato no hay nada
        que buscar — una comparación con la cadena vacía traería la Clínica
        entera.
        """
        if not escrito:
            return []
        return [Coincidencia(self, ficha) for ficha in entre.filter(**{self.campo: escrito})]


class Coincidencia:
    """Una ficha que ya existe y a la que se parece lo que se está escribiendo."""

    def __init__(self, parecido, ficha):
        self.parecido = parecido
        self.ficha = ficha

    @property
    def campo(self):
        return self.parecido.campo

    @property
    def impide_guardar(self):
        return self.parecido.impide_guardar

    @property
    def aviso(self):
        """Lo que se lee en pantalla: el aviso con el enlace a la ficha dentro.

        El enlace se compone aquí y no en cada formulario porque es siempre el
        mismo gesto —llevar a la ficha que ya existe— y porque la ficha sabe
        dónde vive (`get_absolute_url`).
        """
        return format_html(
            self.parecido.aviso,
            ficha=format_html(
                '<a href="{}">{}</a>', self.ficha.get_absolute_url(), str(self.ficha)
            ),
        )

    def como_error(self):
        """El aviso convertido en el error que impide guardar la ficha."""
        return ValidationError(self.aviso, code=self.parecido.codigo)


class FormularioQueSeParece(FormularioDeLaClinica):
    """Formulario de una ficha que puede resultar ser una que ya existe.

    Declara `PARECIDOS` —por qué campos se la puede confundir con otra— y
    `DETECCION` —la URL a la que preguntar mientras se escribe—, y con eso
    obtiene tres cosas que no hay que acordarse de pedir: los campos preguntan
    solos mientras se teclea, el duplicado que no cabe en la base no deja
    guardar, y el que sí cabe queda a mano de la vista para avisar de él.

    Los avisos se componen una sola vez y valen para las dos pantallas: la
    detección en vivo los pinta en su hueco y el formulario rechazado los pone
    al lado del campo. Sin esto habría dos redacciones del mismo aviso, y la de
    la pantalla que menos se prueba envejecería sola.
    """

    # Los `Parecido` por los que esta ficha puede resultar ser otra.
    PARECIDOS = ()
    # El nombre de la ruta que responde a la detección en vivo. Recibe el `pk`
    # de la ficha cuando se está corrigiendo una, para que no se avise de que se
    # parece a sí misma.
    DETECCION = None
    # El hueco de la página donde se pintan los avisos. Se escribe una vez: el
    # formulario lo pone en el `hx-target` de sus campos y la plantilla, que lo
    # lee de aquí, en el `id` del hueco. Si los dos no dijeran lo mismo, la
    # detección dejaría de pintar nada en silencio.
    CAJA = "coincidencias"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._coincidencias = None
        for parecido in self.PARECIDOS:
            # Preguntar mientras se escribe se monta aquí y no en la plantilla:
            # quién puede coincidir con quién ya está dicho en `PARECIDOS`, y
            # repetirlo campo a campo en el HTML dejaría un campo sin preguntar
            # el día que se añada el tercero.
            self.fields[parecido.campo].widget.attrs.update(
                {
                    "hx-get": self.deteccion,
                    "hx-target": f"#{self.CAJA}",
                    "hx-trigger": RETARDO,
                    # La ficha entera, no solo el campo que se acaba de tocar:
                    # el aviso habla de todos los parecidos a la vez.
                    "hx-include": "closest form",
                }
            )

    @property
    def deteccion(self):
        """A qué URL se le pregunta a quién se parece lo que se está escribiendo."""
        return reverse(self.DETECCION, args=[self.instance.pk] if self.instance.pk else [])

    def coincidencias(self):
        """Las fichas de la Clínica a las que se parece lo escrito hasta ahora.

        Se lee de lo tecleado y no de `cleaned_data` porque esto corre también
        sobre una ficha a medio escribir, que nunca va a ser válida: le falta el
        nombre, o el RUT todavía no cuadra. Cada campo se lee con el campo del
        formulario que lo guardaría, así que un RUT con puntos y otro sin ellos
        son el mismo antes de compararse con nada.

        Se resuelve una sola vez: la vista pregunta después de guardar para
        avisar de lo que no impidió nada, y volver a preguntar entonces
        respondería sobre la ficha recién creada.
        """
        if self._coincidencias is None:
            self._coincidencias = [
                coincidencia
                for parecido in self.PARECIDOS
                for coincidencia in parecido.encuentra(
                    self.los_demas(), self._tecleado(parecido.campo)
                )
            ]
        return self._coincidencias

    def _tecleado(self, campo):
        """Lo escrito en ese campo, ya normalizado, o `None` si no se deja leer.

        Un RUT al que le falta el último dígito no es un RUT: no se parece a
        nadie todavía, y buscarlo tal cual traería lo que no es.
        """
        entrada = self.fields[campo]
        escrito = entrada.widget.value_from_datadict(
            self.data, self.files, self.add_prefix(campo)
        )
        try:
            return entrada.clean(escrito)
        except ValidationError:
            return None

    def clean(self):
        """Rechaza la ficha que la base de datos no va a admitir, y solo esa.

        Las demás coincidencias no se tocan aquí: quedan a mano de la vista, que
        avisa de ellas cuando ya hay dos fichas y las dos existen.
        """
        datos = super().clean()
        for coincidencia in self.coincidencias():
            if coincidencia.impide_guardar:
                self.add_error(coincidencia.campo, coincidencia.como_error())
        return datos


# --- Cómo llega la coincidencia a quien está delante ----------------------
#
# Por tres caminos, y los tres viven aquí y no en las vistas de las dos apps:
# son el mismo gesto —nombrar la ficha que ya existe— contado en tres momentos,
# y escribirlo dos veces dejaría que la app que menos se toca se quedara atrás.
# Los tres dejan constancia de lo que nombran, que es la parte que no puede
# depender de acordarse (ADR-0004).


def responde_a_quien_se_parece(request, formulario):
    """El hueco de los avisos, para la detección mientras se escribe.

    No guarda nada y no impide nada: enseña las fichas que ya existen y enlaza a
    ellas, y quien está delante decide si venía a esa o no.

    Cada aviso nombra una ficha, así que cada aviso es una lectura y consta como
    tal. Aquí no vale la regla de la caja del mostrador —anotar el conjunto y no
    cada resultado—: esto no lista a nadie de paso, nombra exactamente la ficha
    que recepción está a punto de duplicar, y solo cuando el dato tecleado está
    entero.
    """
    encontradas = formulario.coincidencias()
    respuesta = render(request, PLANTILLA, {"coincidencias": encontradas})
    _constancia_de(request.user, encontradas)
    return respuesta


def avisar_de_lo_que_no_impidio_guardar(request, formulario):
    """Los avisos que sobreviven a la redirección, para la ficha ya guardada.

    Se avisa después de guardar y no al validar: el parecido que no impide nada
    solo tiene sentido cuando hay dos fichas y existen las dos, y entonces quien
    lee el aviso puede ir a comparar.
    """
    avisadas = [
        coincidencia
        for coincidencia in formulario.coincidencias()
        if not coincidencia.impide_guardar
    ]
    for coincidencia in avisadas:
        messages.warning(request, coincidencia.aviso)
    _constancia_de(request.user, avisadas)


def constancia_de_lo_que_impidio_guardar(request, formulario):
    """Anota las fichas que nombra el formulario que acaba de ser rechazado.

    Solo esas: son las que la página trae escritas al lado de su campo. Las que
    no impidieron nada no se anotan aquí, porque en esta página no se enseñan —
    el hueco de los avisos vuelve vacío, y lo que no se llegó a servir no se
    anota (ADR-0004).
    """
    _constancia_de(
        request.user,
        [
            coincidencia
            for coincidencia in formulario.coincidencias()
            if coincidencia.impide_guardar
        ],
    )


def _constancia_de(usuario, coincidencias):
    """Anota la lectura de cada ficha que el aviso nombra (ADR-0004).

    El aviso dice cómo se llama la otra ficha y enlaza a ella: quien lo lee ha
    visto un dato suyo sin haber abierto nada, y eso es una lectura igual que si
    la hubiera abierto.
    """
    for coincidencia in coincidencias:
        anotar(usuario, Accion.LECTURA, coincidencia.ficha)
