# 13 — Sesiones de mostrador y segundo factor del admin

**What to build:** el sistema se usa en un computador de mostrador a la vista de los Tutores y en una tablet de box que comparten tres veterinarios. Este ticket hace que eso sea seguro sin volverlo incómodo.

El riesgo real no es un atacante remoto: es que una Consulta quede firmada con el nombre del veterinario equivocado, y esa firma tiene valor legal.

**Blocked by:** 02

**Status:** done

- [x] Caducidad de sesión por inactividad, con el plazo configurable y 30 minutos por defecto
- [x] Aviso al Usuario antes de que caduque, para no perder lo que está escribiendo
- [x] Cambio rápido de Usuario en pocos clics, pensado para la tablet compartida
- [x] La página muestra siempre y de forma visible qué Usuario está activo
- [x] Segundo factor **obligatorio** para el rol admin, que es quien puede exportar toda la base
- [x] Segundo factor **no exigido** a veterinario ni a recepción, por fricción en mostrador
- [x] Tests de caducidad por inactividad y de que el admin sin segundo factor configurado no completa el login

## Comments

Implementado en `apps/tenancy`. No hay modelos nuevos de Gatabase: la caducidad
es configuración de Django y el segundo factor lo guarda `allauth.mfa`.

- **La caducidad por inactividad es `SESSION_COOKIE_AGE` + `SESSION_SAVE_EVERY_REQUEST`**,
  no un reloj propio. Esa segunda opción es la que la vuelve *por inactividad* y
  no *desde que se entró*: cada petición renueva el plazo, así que a nadie lo
  echan a media ficha. Son 30 minutos, y `GATABASE_MINUTOS_DE_SESION` los cambia.
  Lo único que Django no sabe —cuánto antes hay que avisar— vive en
  `apps/tenancy/sesion.py`, que recorta el aviso a la mitad de la sesión: con la
  caducidad bajada a un minuto, un aviso de dos no aparecería nunca.
- **El aviso es `static/sesion.js`**, no una plantilla con un `<script>` dentro:
  todo lo que se escribe dentro de una plantilla se queda fuera de `gettext`, y
  `tests/test_plantillas_en_gettext.py` lo haría fallar con razón. El guion no
  lleva ni un texto visible — los plazos le llegan en `data-` y los textos ya
  están escritos y traducidos en el `<aside>`, que nace oculto.
- **`seguir_conectado` devuelve 204 y ninguna página**: quien pulsa «Sigo aquí»
  está a media ficha y no quiere perderla. La vista marca la sesión como
  modificada aunque `SESSION_SAVE_EVERY_REQUEST` ya lo haría, para que siga
  cumpliendo su promesa si esa opción cambia.
- **El cambio de Usuario conserva la Sede.** `logout()` vacía la sesión, así que
  la Sede se vuelve a fijar después, sobre la sesión anónima nueva; el `login`
  de Django preserva los datos cuando no había otro Usuario dentro. La tablet no
  se ha movido de box: quien entra detrás no tiene que volver a elegir dónde
  está trabajando. Lo demás sí se va — cambiar de Usuario es cambiar de Usuario.
- **El segundo factor obligatorio es una etapa de login propia**
  (`apps/tenancy/segundo_factor.py`), enganchada por `ACCOUNT_ADAPTER`
  (`apps/tenancy/adaptador.py`). `allauth` sabe pedir el código a quien ya tiene
  segundo factor, pero no sabe exigir tenerlo. Va **detrás** de la etapa de
  `allauth`: al admin que ya lo tiene se lo piden, y al que no, se le lleva a
  darlo de alta. Mientras tanto el login está a medias — hay contraseña
  correcta y no hay sesión —, así que la página del alta no exige estar dentro:
  la protege `login_stage_required`, que sin login pendiente redirige al login.
- **De `allauth.mfa` se enruta solo `mfa_authenticate`**, como se hizo con
  `allauth.account` en el 02. Retirar el segundo factor no tiene URL a propósito:
  para el admin es obligatorio. Quien pierde el teléfono se rescata con
  `manage.py restablecer_segundo_factor <correo>`, que solo lo retira — darlo de
  alta otra vez lo hace el propio Usuario al entrar.
- `MFA_SUPPORTED_TYPES = ["totp"]`: sin códigos de recuperación (habría que
  entregarlos por correo, y no hay correo saliente) y sin WebAuthn (en un
  mostrador compartido sería una llave física más que perder). Aun así hay que
  instalar `fido2` — `django-allauth[mfa]` —, porque `allauth.mfa` lo importa al
  envolver cualquier autenticador. Anotado en la deuda técnica.
- **`test_el_admin_dado_de_alta_entra_con_su_contrasena` cambió de significado**:
  el primer admin de una Clínica ya no obtiene sesión con la contraseña. Su
  contraseña vale, y lo que consigue es llegar al alta de su segundo factor.
- Tests en `tests/test_sesiones_de_mostrador.py` y `tests/test_segundo_factor.py`,
  por HTTP. Se comprobó en rojo, invirtiendo tres piezas: `le_exige_segundo_factor`
  devolviendo `False` (caen seis del segundo factor), `SESSION_SAVE_EVERY_REQUEST`
  apagado y la conservación de la Sede quitada (caen cuatro de las sesiones). Los
  códigos TOTP de los tests se calculan con las mismas funciones que los valida
  `allauth`, sin reloj falso.

Deuda consciente, anotada en `deuda-tecnica.md`: el secreto TOTP se guarda en
claro, el alta se hace con la contraseña recién tecleada, no hay códigos de
recuperación, y sin JavaScript la sesión caduca sin avisar.
