"""Qué animales atiende la clínica: el catálogo de especies y el de razas.

Son dos catálogos con reglas distintas a propósito.

**La especie es cerrada.** De ella dependen protocolos, dosis y formularios, así
que no admite texto libre: un «perrito» y un «canino» escritos a mano serían dos
especies para las estadísticas y ninguna para los protocolos. Que sea código y no
una tabla es la consecuencia buscada — atender una especie nueva obliga a pasar
por aquí, que es donde después habrá que decidir qué protocolo le toca — y no un
descuido.

**La raza no lo es.** El catálogo por especie existe para que las estadísticas
sirvan, pero un catálogo de razas nunca está completo: el mestizo con algo raro
llega igual, y bloquear el mostrador por una raza que falta sería pedirle a
recepción que mienta. Así que lo escrito se compara con el catálogo y, si se
parece a una entrada, se guarda con la ortografía del catálogo; si no, se guarda
tal cual. Esa es la opción «otra», y no hace falta que sea un valor mágico: el
Paciente sabe después si su raza salió del catálogo (`raza_del_catalogo`).

`mestizo` es una entrada normal y la primera de las especies donde significa
algo, porque en Chile es el caso más frecuente, no la excepción.
"""

import unicodedata

from django.db import models
from django.utils.translation import gettext_lazy as _


class Especie(models.TextChoices):
    """Las especies que la clínica atiende. Cerrado: ver el módulo."""

    PERRO = "perro", _("perro")
    GATO = "gato", _("gato")
    CONEJO = "conejo", _("conejo")
    ROEDOR = "roedor", _("roedor")
    AVE = "ave", _("ave")
    REPTIL = "reptil", _("reptil")
    HURON = "huron", _("hurón")


MESTIZO = "Mestizo"

# Las razas que recepción va a encontrar escritas ya, por especie. No pretende
# ser exhaustivo — para eso está el texto libre —, sino ahorrar el tecleo y la
# ortografía de las que se ven todos los días.
#
# Los roedores, las aves y los reptiles no tienen raza en el sentido en que la
# tienen un perro o un gato: lo que recepción escribe ahí es de qué animal se
# trata. Se listan igual, porque es lo que hace falta escribir en esa casilla.
RAZAS = {
    Especie.PERRO: (
        MESTIZO,
        "Labrador Retriever",
        "Golden Retriever",
        "Poodle",
        "Bulldog Francés",
        "Chihuahua",
        "Cocker Spaniel",
        "Pastor Alemán",
        "Beagle",
        "Yorkshire Terrier",
        "Schnauzer",
        "Shih Tzu",
        "Border Collie",
        "Rottweiler",
        "Husky Siberiano",
        "Dachshund",
        "Maltés",
        "Pug",
        "Boxer",
    ),
    Especie.GATO: (
        MESTIZO,
        "Siamés",
        "Persa",
        "Angora",
        "Maine Coon",
        "Ragdoll",
        "Bengalí",
        "Británico de pelo corto",
        "Esfinge",
        "Azul Ruso",
    ),
    Especie.CONEJO: (
        MESTIZO,
        "Belier",
        "Cabeza de León",
        "Angora",
        "Holandés Enano",
        "Rex",
    ),
    Especie.ROEDOR: (
        "Cobayo",
        "Hámster sirio",
        "Hámster ruso",
        "Chinchilla",
        "Jerbo",
        "Degú",
        "Rata",
        "Ratón",
    ),
    Especie.AVE: (
        "Canario",
        "Periquito",
        "Agapornis",
        "Ninfa",
        "Cacatúa",
        "Loro",
        "Diamante mandarín",
        "Gallina",
    ),
    Especie.REPTIL: (
        "Tortuga de tierra",
        "Tortuga de agua",
        "Iguana",
        "Gecko leopardo",
        "Dragón barbudo",
        "Serpiente del maíz",
    ),
    Especie.HURON: (),
}


def razas_de(especie):
    """Las razas que se le ofrecen a esa especie. Ninguna si la especie no existe.

    Una especie desconocida no es un error que merezca reventar: es un
    formulario a medio rellenar o una URL escrita a mano, y lo que corresponde es
    no ofrecer nada.
    """
    return RAZAS.get(especie, ())


def _como_se_compara(raza):
    """La raza reducida a lo que no depende de cómo se teclee: sin tildes, sin
    mayúsculas y sin espacios de sobra.

    Nadie escribe «Bulldog Francés» con el acento a las siete de la tarde, y
    guardar «bulldog frances» como una raza distinta es justo lo que rompería las
    estadísticas que el catálogo viene a salvar.
    """
    sin_tildes = unicodedata.normalize("NFKD", raza)
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).casefold().strip()


def canonica(especie, escrita):
    """Cómo se guarda lo que recepción escribió en la casilla de la raza.

    Con la ortografía del catálogo si se le parece; tal cual —quitando los
    espacios de los extremos— si no: esa es la raza «otra».
    """
    escrita = escrita.strip()
    if not escrita:
        return ""
    comparable = _como_se_compara(escrita)
    for raza in razas_de(especie):
        if _como_se_compara(raza) == comparable:
            return raza
    return escrita


def es_del_catalogo(especie, raza):
    """Si esa raza es una entrada del catálogo de esa especie.

    Se pregunta, no se guarda: guardarlo sería un segundo sitio donde vive la
    misma verdad, y el día que una raza entre en el catálogo las fichas viejas
    seguirían diciendo que no.
    """
    return bool(raza) and raza in razas_de(especie)


# A qué especies les exige la Ley 21.020 estar identificadas e inscritas en el
# Registro Nacional de Mascotas. Son los perros y los gatos, no todo lo que la
# clínica atiende, y la diferencia importa en el mostrador: decirle a quien trae
# una iguana que la inscriba es darle un consejo falso desde detrás del
# mostrador. Está aquí, junto al catálogo cerrado, porque es lo mismo que la
# especie ya decide —qué protocolo y qué papeleo le toca a cada animal— y porque
# así una especie nueva obliga a pasar por el sitio donde hay que decidirlo.
ESPECIES_QUE_LA_LEY_OBLIGA_A_IDENTIFICAR = frozenset({Especie.PERRO, Especie.GATO})


def la_ley_exige_identificar(especie):
    """Si la Ley 21.020 obliga a chipear e inscribir a un animal de esa especie."""
    return especie in ESPECIES_QUE_LA_LEY_OBLIGA_A_IDENTIFICAR
