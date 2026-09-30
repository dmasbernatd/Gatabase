# 06 — Curva de peso del Paciente

**What to build:** el veterinario ve la evolución del peso de un Paciente a lo largo del tiempo, que es el dato que más orienta en un crónico.

**Blocked by:** 04, 05

**Status:** ready-for-agent

- [ ] La Historia clínica del Paciente muestra la curva de peso: un punto por medición, en orden cronológico, con fecha y valor
- [ ] Una Consulta sin peso no rompe la curva ni aparece como cero
- [ ] Con una sola medición se ve el punto; sin ninguna, un texto que lo dice
- [ ] El cálculo de la serie vive en un módulo de servicio de `records` con tests propios, no en la vista ni en la plantilla
- [ ] Tests: la curva devuelve los valores en orden, y una Consulta sin peso no la rompe
- [ ] Legible sin JavaScript: además del gráfico, la tabla de valores
- [ ] Solo pesos de Consultas de la Clínica activa
- [ ] Ver la curva queda en el Registro de acceso como lectura de la Historia del Paciente
