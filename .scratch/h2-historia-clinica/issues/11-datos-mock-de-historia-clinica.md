# 11 — Historia clínica en los datos mock

**What to build:** `manage.py datos_mock` puebla también Consultas, Enmiendas, constantes y Adjuntos falsos, para que la Historia, la curva y la exportación se puedan ver y medir con volumen realista.

**Blocked by:** 06, 08

**Status:** ready-for-agent

- [ ] Cada Paciente de la Clínica mock tiene una Historia creíble: la mayoría pocas Consultas, algunos crónicos con muchas y una curva de peso que se mueve
- [ ] La mayoría cerradas, unas pocas abiertas, algunas con Enmiendas y Adjuntos (retirados incluidos)
- [ ] Los Adjuntos mock van al almacenamiento configurado, y en desarrollo sin S3 a uno local; nunca a un bucket de producción
- [ ] Medir con este volumen la Historia clínica de un crónico y la página del Registro, y anotar las cifras en la deuda técnica de H2
