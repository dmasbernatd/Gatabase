---
status: accepted
---

# La Historia clínica no se comparte entre Clínicas

El sistema es multi-tenant y el microchip identifica de forma única a un animal en todo Chile, así que técnicamente podríamos reconocer que el Paciente que llega a la Clínica B es el mismo que atiende la Clínica A y unificar su Historia clínica. Decidimos **no hacerlo**: cada Clínica tiene su propio Paciente, con su propia Historia clínica, aunque el animal y el número de chip sean los mismos.

El motivo no es técnico. La Historia clínica contiene datos de salud y datos personales del Tutor cuyo responsable de tratamiento es la Clínica que los registró; cruzarlos entre tenants sin base legal ni consentimiento es exactamente lo que la Ley 21.719 sanciona. Además destruiría el aislamiento entre tenants, que es la única garantía de privacidad que podemos ofrecer al vender el sistema a clínicas que compiten entre sí.

## Consecuencias

- El número de chip es único **dentro** de una Clínica, nunca global.
- Habrá fichas duplicadas del mismo animal en distintas Clínicas. **Esto es correcto, no es un bug.** Si en el futuro alguien propone deduplicar Pacientes por microchip a nivel de instancia, la respuesta está aquí.
- Un traspaso de Historia clínica entre Clínicas, si algún día se pide, tendrá que diseñarse como una exportación que autoriza el Tutor, no como una consulta entre tenants.
