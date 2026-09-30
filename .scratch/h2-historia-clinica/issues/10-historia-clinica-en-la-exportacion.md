# 10 — La Historia clínica en la exportación de la Clínica

**What to build:** la exportación del ticket 19 de H1 se lleva también la Historia clínica. Si la clínica pone su archivador clínico en el sistema, tiene que poder sacarlo igual que saca sus Tutores.

**Blocked by:** 03, 05, 08

**Status:** ready-for-agent

- [ ] Hojas nuevas en el zip: `consultas.csv`, `enmiendas.csv`, `constantes.csv` (o lo que salga del 05) y `adjuntos.csv`, con los mismos criterios que `apps/exports/hojas.py`: códigos tal cual, iteradores, la Clínica cruzada a mano
- [ ] Los archivos de los Adjuntos no retirados van dentro del zip, en carpetas que se entiendan sin manual, y se leen del almacenamiento por trozos: la promesa de memoria de `paquete.py` sigue en pie
- [ ] Test con dos Clínicas pobladas: solo sale la Historia de la propia
- [ ] Medido a mano con el volumen del 11 y anotado en Comments, como se hizo en el 19 de H1
- [ ] Revisar con el ticket 20 de H1 (derechos del titular): la anonimización de un Tutor no toca la Historia clínica, que es del Paciente (ADR-0004); dejar escrito qué pasa con el motivo «en palabras del Tutor», que puede contener datos suyos
