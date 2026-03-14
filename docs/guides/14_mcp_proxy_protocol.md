# [OSAA v5.0] CORE METAPROMPT: TOPOLOGÍA DE RED MCP (PROXY ROUTING)

<meta_context>
Gobierna la interacción con herramientas externas. Centralización y control.
</meta_context>

<mental_model>
**El Operador de Centralita (The Switchboard Operator)**
No hay conexiones directas. Todo pasa por el router central (`mcp_proxy.py`).
</mental_model>

<core_directives>
1. **Mediación Obligatoria:** Los agentes no inician servidores. Llaman a la función y el Proxy intercepta.
2. **Truncamiento en el Borde:** El resultado debe ser limpiado y truncado antes de llegar al agente para proteger su contexto.
3. **Mapeo Interno:** Traducción de llamadas JSON a puertos locales (`localhost:8001+, etc.`).
</core_directives>
