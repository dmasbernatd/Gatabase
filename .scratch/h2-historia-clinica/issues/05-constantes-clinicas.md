# 05 — Constantes clínicas: peso, temperatura y frecuencias como números

**What to build:** en la Consulta, el veterinario registra peso, temperatura, frecuencia cardíaca y frecuencia respiratoria como números con su unidad y su fecha, no como texto. Mientras escribe, ve el peso de la Consulta anterior para notar una pérdida sin buscarla.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] Las constantes son campos numéricos tipados con unidad fija (kg, °C, lpm, rpm) y momento de la medición; todas opcionales
- [ ] Rangos de validación que rechacen lo que no puede ser (un peso negativo, una temperatura de 400) sin impedir lo raro pero posible; los rangos se deciden aquí y se escriben
- [ ] Se aceptan decimales con coma, que es como se escriben en Chile
- [ ] Siguen la regla de la Consulta: editables mientras está abierta, inmutables al cerrarla (en el modelo); corregir una constante de una Consulta cerrada es una Enmienda
- [ ] Al escribir la Consulta se muestra el último peso registrado del Paciente, con su fecha, y la diferencia con el que se está escribiendo
- [ ] La página de la Consulta muestra las constantes con su unidad
- [ ] Aislamiento por HTTP: el peso anterior nunca sale de una Consulta de otra Clínica
- [ ] Decidir aquí si las constantes son columnas de la Consulta o una tabla de mediciones, pensando en la curva del 06 y en que el H3 puede querer pesar sin Consulta; anotarlo
