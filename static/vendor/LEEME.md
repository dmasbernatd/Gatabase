# Dependencias del navegador, versionadas aquí

`htmx.min.js` es htmx **2.0.4**, tal cual se descarga de
`https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js`.

Se versiona en el repositorio en vez de enlazarse desde un CDN por tres motivos:
la clínica trabaja con datos personales y no tiene por qué pedirle un archivo a
un tercero en cada página; un despliegue con la red capada tiene que seguir
funcionando; y así la versión que se sirve es la misma que se probó.

Para subir de versión: descargar el archivo nuevo, sustituirlo, actualizar el
número de arriba y pasar los tests.
