---
name: failure-reproducer-regression-builder
description: Reproduce y aisla errores, crea fixtures, pruebas rojas antes de corregir y pruebas de regresión permanentes después; usar para crash, instalación APK, foco Roku, Excel/Power Pivot, Office.js, HTML o diferencias de cálculos.
---
# Failure Reproducer & Regression Builder — v1.1
1. Preservar archivo/commit/artefacto exacto que falla; no tocar release estable.
2. Documentar ID, entorno, versiones, precondiciones, pasos, entrada, esperado/real y evidencia.
3. Intentar reproducir ANTES del parche. Si no reproduce, informar NO_REPRODUCIDO y mantener hipótesis separadas de hechos.
4. Reducir a caso mínimo y crear prueba que falle (RED). Si hace falta equipo físico, crear procedimiento determinista y marcar NOT_RUN hasta ejecutarlo.
5. Instrumentar sin secretos, localizar la causa, corregir en rama/copia aislada con cambio mínimo.
6. Verificar el caso exacto, vecinos y límites (GREEN), conservar una regresión permanente.
7. Entregar comandos realmente ejecutados, evidencia, limitaciones y rollback.
8. En caso de mejorar el propio workflow usar harness2-adaptive-engineering para comparar enfoques; un log inventado no es evidencia.
