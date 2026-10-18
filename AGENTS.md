# Reglas de Codex — nvidia-online-gateway

Estas reglas son complementarias al README, las instrucciones del código y demás skills, que tienen prioridad si son más específicas.

## Skills de ingeniería disponibles
- `protected-engineering-workflow`: preservar baseline y contrato funcional.
- `failure-reproducer-regression-builder`: crear pruebas de reproducción y regresión.
- `harness2-adaptive-engineering`: contrastar mejoras de agentes con Propose–Probe–Compose solo para tareas complejas o recurrentes.

## Reglas de protección
1. Antes de cambiar código ubicar la última versión funcional real (LKG) desde commits/pruebas; si se desconoce reportarlo.
2. Gateway de infraestructura: protege autenticación, permisos, endpoints, configuración y despliegues. Nunca copiar credenciales ni usar datos corporativos sensibles en probes.
3. Editar el mínimo alcance en rama o copia aislada, jamás modificar release inmutable.
4. Guardar resultados reales de pruebas, hashes y rollback; no declarar éxito de runtime ni instalación física sin ejecutarlos.
5. Para Harness² comparar baseline y candidato bajo iguales condiciones. No aprobar LKG por resultados de tests de skills ni instalar el upstream con sandbox deshabilitado.
6. No divulgar secretos, tokens o datos sensibles. Si el repositorio tiene una política más restrictiva, respetarla.

Origen metodológico: https://github.com/google-research/harness2. Las skills locales son adaptación propia.
