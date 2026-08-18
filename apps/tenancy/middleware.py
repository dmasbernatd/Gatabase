"""Resuelve la Clínica activa de cada petición a partir del Usuario autenticado.

Va después de `AuthenticationMiddleware`, porque necesita `request.user`. Deja la
Clínica en el contexto durante la petición y la retira al terminar: un hilo
reutilizado no puede heredar la Clínica de quien lo usó antes.
"""

from apps.tenancy.aislamiento import activar_clinica


def clinica_del_usuario(get_response):
    def middleware(request):
        usuario = getattr(request, "user", None)
        clinica = usuario.clinic if usuario is not None and usuario.is_authenticated else None
        with activar_clinica(clinica):
            request.clinica = clinica
            return get_response(request)

    return middleware
