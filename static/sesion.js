// Aviso de que la sesión está por caducar.
//
// La caducidad la aplica el servidor: aquí no se decide nada, solo se cuenta.
// Los plazos vienen en los `data-` del aviso y los textos ya están escritos en
// la página —traducidos, como todo lo demás—, así que este archivo no contiene
// ni una cadena visible.
//
// El reloj se reinicia con cada petición que sale de la página, porque cada
// petición renueva también el plazo del servidor. Lo que este guion **no** hace
// es sacar a nadie de la página: su reloj es el de esta pestaña, y cualquier
// otra pestaña de la misma sesión renueva el plazo sin que aquí se note.
// Navegar al login al llegar a cero se llevaría por delante justo la ficha a
// medio escribir que el aviso viene a salvar. Si la sesión murió de verdad, lo
// dirá el servidor en la siguiente petición.
(function () {
  "use strict";

  var aviso = document.getElementById("aviso-de-sesion");
  if (!aviso) {
    return;
  }

  var formulario = document.getElementById("seguir-conectado");
  var sesion = Number(aviso.dataset.segundosDeSesion) * 1000;
  var antelacion = Number(aviso.dataset.segundosDeAviso) * 1000;
  var reloj = null;

  function reiniciar() {
    clearTimeout(reloj);
    aviso.hidden = true;
    reloj = setTimeout(function () {
      aviso.hidden = false;
    }, sesion - antelacion);
  }

  if (formulario) {
    formulario.addEventListener("submit", function (evento) {
      // Sin recargar: quien dice que sigue ahí está a media ficha.
      evento.preventDefault();
      fetch(formulario.action, {
        method: "POST",
        body: new FormData(formulario),
        credentials: "same-origin",
      })
        .then(function (respuesta) {
          // 204 exacto, y no `ok`: sin sesión el servidor redirige al login y
          // `fetch` sigue la redirección, así que la página de entrada llegaría
          // aquí como un 200 y el aviso se escondería mintiendo.
          if (respuesta.status === 204) {
            reiniciar();
          }
        })
        .catch(function () {
          // Se queda el aviso puesto. No hay nada honesto que decir desde aquí:
          // el guion no sabe si la sesión sigue viva, y esconderlo o navegar
          // serían las dos maneras de perder la ficha.
        });
    });
  }

  // htmx recarga trozos de la página sin pasar por aquí: cada uno de esos
  // trozos es una petición, y cada petición alarga la sesión.
  document.body.addEventListener("htmx:afterRequest", reiniciar);

  reiniciar();
})();
