---
name: harness2-adaptive-engineering
description: Mejora agentes, skills y workflows mediante Propose–Probe–Compose de Harness², contraste con la versión estable y aprendizaje basado en evidencia. Úsala en fallas recurrentes, mejoras de procedimientos o decisiones técnicas complejas; no para cambios triviales.
---

# Harness² Adaptive Engineering — integración segura v1.1

Inspirada en https://github.com/google-research/harness2 (Apache-2.0). Es una adaptación metodológica, **no** el motor experimental upstream ni una autooptimización del modelo.

## Antes de empezar
1. Lee `AGENTS.md`, instrucciones vigentes y skills especializadas. **Nunca reemplaces skills existentes por versiones genéricas**.
2. Identifica baseline LKG mediante commit/artefacto verificable. Si falta, registra **LKG_DESCONOCIDA**, sin inventar aceptación.
3. Define caso, entorno, entradas, costos, requisitos críticos, métricas comparables y rollback.
4. Usa `protected-engineering-workflow` para cualquier cambio. Ante fallos utiliza `failure-reproducer-regression-builder` o la skill de diagnóstico más específica.
5. Clasifica intervención: bajo riesgo -> workflow regular; compleja o repetitiva -> contraste Harness² con `k=1`.

## Propose → Probe → Compose
1. **Propose:** mejora A transversal (proceso, pruebas, herramientas o instrucciones) y mejora B especializada (Roku, Android, Office.js, etc.). Mantén ambas aisladas; si son incompatibles, explica por qué.
2. **Probe:** misma tarea, datos, condiciones y pruebas en baseline, A y B. Guarda logs y hashes reales, tiempos/tokens si están disponibles, casos límite y resultados `PASS / FAIL / NOT_RUN`. Cambiar el prompt sin medir efecto no es prueba.
3. **Compose:** integra únicamente diferencias que mejoren resultados sin regresiones críticas. Si hay datos insuficientes o contradicción, conserva LKG.
4. **Reflection:** conserva experiencias con origen, contexto, mejora observada, contrapruebas, ámbito de aplicación y límites. No guardar secretos, información personal ni datos corporativos sensibles.
5. **Gate:** si existe `scripts/experiment_gate.py` dentro de esta skill, ejecútalo sobre un registro JSON local con referencias SHA256 de evidencia real. Su resultado `ELIGIBLE_FOR_REVIEW` **no certifica** la ejecución ni autoriza promover LKG. Si el script falta, registrar `GATE_NOT_RUN`, nunca PASS.
6. **Delivery:** reportar versión base, archivos cambiados, pruebas ejecutadas con comandos, beneficios demostrados, fallos, costos y rollback. Validación en Roku/Android físico es PENDIENTE hasta realizarla.

## Guardrails
No modificar código de liberaciones inmutables; no desactivar sandbox ni controles de red; no exponer credenciales ni consultar rúbricas externas de evaluación; no instalar el ejecutor upstream sin revisión de seguridad; no fusionar automáticamente PRs cuando el repositorio lo prohíbe. Limitar iteraciones para proteger tiempo y tokens.

Fuentes: https://github.com/google-research/harness2 y https://arxiv.org/abs/2610.14224
