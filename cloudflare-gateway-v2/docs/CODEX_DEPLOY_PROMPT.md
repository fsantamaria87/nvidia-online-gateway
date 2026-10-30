# Prompt para Codex — NVIDIA Gateway v2, una entrega

Trabaja sobre la carpeta `nvidia_orchestrator_v2` incluida en el ZIP. Esta es una candidatura con 26 pruebas offline aprobadas; falta build con dependencias reales, deploy y prueba extremo a extremo.

Objetivo: sustituir el MCP NVIDIA de Railway por un Worker seguro Cloudflare y lograr que `nvidia_infer`, `nvidia_review`, `nvidia_generate_evalset` funcionen realmente desde el MCP nuevo.

1. Ejecuta `npm install`, `npm run check`, `npm test`, compila con `npx wrangler deploy --dry-run` (si disponible), corrige compatibilidad SDK v2/Agents/Worker y añade test de MCP `initialize` + `tools/list` + `tools/call` con token válido y token inválido. Conserva todas las funciones actuales y corrige cualquier regresión.
2. Mantén `/mcp` protegido con autenticación. Si ChatGPT requiere OAuth o la autenticación estática no es compatible, implementa autorización OAuth con Cloudflare OAuth Provider y documenta el flujo de inicio de sesión. **Nunca abras un MCP público sin autenticar**, ya que usaría la clave NVIDIA de otro usuario.
3. Comprueba la disponibilidad de los ID `fast`, `balanced` y `deep` contra la API oficial de NVIDIA, con modelos configurables. La verificación con datos sintéticos no implica disponibilidad gratuita ilimitada. Mantén control de gastos y fallo cerrado. No envíes datos de planta confidenciales.
4. Despliega solo cuando la cuenta Cloudflare y secretos `NVIDIA_API_KEY`, `MCP_CLIENT_TOKEN` estén autorizados y cargados por el usuario/gestor seguro. Si faltan, detente en el gate de deploy; nunca simules un resultado en producción. No copies la clave desde registros de Railway.
5. Prueba 401 no autenticado, 403 origen prohibido, tres herramientas disponibles, una inferencia de prueba y comprobación de uso/fallback, con prueba real de Codex y, si la conexión lo permite, ChatGPT.
6. Crea PR y conserva la LKG main y los tres servicios antiguos de Railway sin borrado. Entrega URL del Worker solo tras verificar, SHA GitHub, ZIP y reporte de gates. No toques LibroVerse ni NotebookLM.

Instrucción: minimiza las entregas, privilegia una corrección integral, pero no ocultes fallos. No uses servicios de pago sin autorización.
