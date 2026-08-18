"""El Registro de acceso no admite `UPDATE` ni `DELETE`, y lo impide Postgres.

Que la aplicación no ofrezca cómo editar una anotación no es garantía de nada:
la garantía tiene que sobrevivir a un `shell`, a un `psql` y a cualquier código
que se escriba después (ADR-0004). Por eso van dos cierres:

- **Permisos**: se le retiran `UPDATE` y `DELETE` sobre la tabla al rol con el
  que se conecta la aplicación. Es la defensa que pide el ADR, y la que vale en
  un despliegue donde ese rol no es el dueño de la base.
- **Disparador**: además, cualquier `UPDATE` o `DELETE` sobre una fila revienta.
  Un rol superusuario — el de una máquina de desarrollo, sin ir más lejos — se
  salta los permisos, pero no se salta un disparador.

`TRUNCATE` entra también en el `REVOKE`, porque vaciar la tabla de un golpe
borra tanto como un `DELETE` y el disparador no lo alcanza. No lo bloquea un
disparador propio a propósito: un rol superusuario se lo salta igualmente — con
lo que las herramientas de test siguen pudiendo vaciar la tabla entre pruebas —,
y en un despliegue de verdad, donde el rol de la aplicación no es superusuario,
el permiso retirado sí manda.

De ahí la condición de despliegue, que está en el README: la aplicación se
conecta con un rol que **no** es superusuario. Además, `CURRENT_USER` es el rol
que ejecuta esta migración; si un despliegue migra con un rol distinto del de la
aplicación, hay que retirarle a ese otro rol los mismos tres permisos.

Consecuencia buscada: borrar una Clínica deja de ser posible mientras tenga
accesos anotados, porque el borrado en cascada tropieza con el disparador. Una
Clínica que se va se exporta y se cierra (ticket 19); no se borra por debajo. Lo
mismo vale para los datos de desarrollo (ticket 16): se rehace la base, no se
borra la Clínica por debajo.
"""

from django.db import migrations

INALTERABLE = """
CREATE FUNCTION audit_registro_de_acceso_inalterable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'El Registro de acceso es inalterable: no admite UPDATE ni DELETE (ADR-0004).'
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

CREATE TRIGGER registro_de_acceso_inalterable
    BEFORE UPDATE OR DELETE ON audit_registrodeacceso
    FOR EACH ROW EXECUTE FUNCTION audit_registro_de_acceso_inalterable();

REVOKE UPDATE, DELETE, TRUNCATE ON audit_registrodeacceso FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_registrodeacceso FROM CURRENT_USER;
"""

ALTERABLE = """
DROP TRIGGER registro_de_acceso_inalterable ON audit_registrodeacceso;
DROP FUNCTION audit_registro_de_acceso_inalterable();
GRANT UPDATE, DELETE, TRUNCATE ON audit_registrodeacceso TO CURRENT_USER;
"""


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunSQL(INALTERABLE, reverse_sql=ALTERABLE)]
