from django.apps import AppConfig


class TenancyConfig(AppConfig):
    """Clínica, Sede, pertenencia de Usuario, Horario de atención y Clínica de derivación."""

    name = "apps.tenancy"
    label = "tenancy"

    def ready(self):
        # Importar el módulo registra el `check` de aislamiento (ADR-0003).
        from apps.tenancy import comprobaciones  # noqa: F401
