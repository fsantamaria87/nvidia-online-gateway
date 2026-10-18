---
name: protected-engineering-workflow
description: Protege la última versión funcional y las restricciones del proyecto durante cambios de código, seguridad, Excel, Android, Roku o HTML; requiere alcance, pruebas, revisión, rollback y aprobación explícita para cambiar LKG.
---
# Protected Engineering Workflow — v1.1
1. Leer AGENTS.md y las skills especializadas; no reemplazar instrucciones más específicas.
2. Localizar versión estable real: commit, hash, registro de pruebas y contrato funcional. Si falta, declarar LKG_DESCONOCIDA.
3. Planear solo modificaciones necesarias, en rama o copia aislada. Respetar la política de PR y releases del repositorio.
4. Spec -> Build -> Verify -> Review -> Ship, ajustando profundidad al riesgo. No cambiar otras funciones por estética.
5. Mantener pruebas de reproducción, seguridad, privacidad, compatibilidad y resultados numéricos cuando aplique.
6. Contrastar baseline y candidato; preservar original y preparar reversión verificable.
7. No declarar pruebas físicas de Roku, teléfono Android, Excel o producción como PASS sin haberlas ejecutado.
8. No promover LKG ni fusionar PR automáticamente si las normas del repositorio requieren aprobación.
9. Para mejoras complejas o recurrentes activar harness2-adaptive-engineering; solo adoptar cambios respaldados por evidencias.
