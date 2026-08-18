# 03 — Maquinaria de aislamiento por Clínica

**What to build:** la garantía de que ningún Usuario puede ver datos de otra Clínica, demostrada con el primer modelo de dominio real (Tutor, en su forma mínima: nombre y teléfono). Es el ticket que implementa ADR-0003, y el que define el patrón que seguirán todos los modelos posteriores.

**Blocked by:** 02

**Status:** done

- [x] Clave ajena `clinic` en el modelo Tutor, y manager por defecto que filtra por la Clínica activa
- [x] Middleware que resuelve la Clínica activa a partir del Usuario autenticado
- [x] Usar el manager por defecto es seguro; el acceso sin filtrar existe pero es explícito y llamativo en el código
- [x] **Test estructural**: recorre los modelos de dominio y falla si alguno no tiene `clinic`. Debe fallar de verdad si se añade un modelo sin la clave
- [x] Un Usuario que pide por su identificador un Tutor de otra Clínica recibe 404, nunca 403 con contenido
- [x] Los listados y las búsquedas nunca devuelven objetos de otra Clínica
- [x] Documentado en el README el patrón que debe seguir cualquier modelo de dominio nuevo
