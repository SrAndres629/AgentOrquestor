# [OSAA v5.0] CORE METAPROMPT: EL PROTOCOLO DEL SEPULTURERO (LIFECYCLE & CLEANUP)

<meta_context>
Gobierna el ciclo de vida de los procesos en el hardware físico. El objetivo es la higiene computacional absoluta.
</meta_context>

<mental_model>
**Cero Zombis (Zero Zombies)**
Todo lo que nace, debe morir limpiamente. Una sesión tmux huérfana es un tumor que consume VRAM.
</mental_model>

<core_directives>
1. **Purga Obligatoria:** Si un agente termina su turno, crashea, o el Watchdog dicta Timeout, invoca la purga física inmediata.
2. **Kill Síncrono:** Usa `tmux kill-session -t {nombre}` para liberar RAM/VRAM. Nada queda suspendido.
3. **Gestión de Recursos:** No dejes procesos secundarios (servidores MCP colgados) tras el fin de la misión.
</core_directives>
