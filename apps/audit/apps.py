from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Registro de acceso."""

    name = "apps.audit"
    label = "audit"

    def ready(self):
        # Importar el módulo registra el `check` de la condición de despliegue
        # de la que depende la inalterabilidad del Registro (ADR-0004).
        from apps.audit import comprobaciones  # noqa: F401
