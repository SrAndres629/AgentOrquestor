"""
AgentOrquestor — Swarm Launcher (Córtex de Lanzamiento) v5.0
=============================================================
Orquesta el ciclo de vida de agentes IA como procesos aislados
de terminal Linux mediante tmux. Cada agente se ejecuta en su
propia sesión con un archivo de contexto ("cerebro") inyectado.

Protocolo IPC: Archivos físicos en .cortex/ con bloqueo atómico.
Race-condition safe: write-then-rename + fcntl.LOCK_EX.

Hardware target: i9 / 16GB RAM / RTX 3060 6GB VRAM.
"""

import os
import sys
import json
import time
import uuid
import fcntl
import shutil
import signal
import asyncio
import tempfile
import subprocess
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.telemetry import telemetry
from core.hardware_monitor import HardwareMonitor
from core.shredder import LogShredder


# ---------------------------------------------------------------------------
# 0. UTILIDADES IPC ATÓMICAS
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
CORTEX_DIR = BASE_DIR / ".cortex"
MISSIONS_DIR = CORTEX_DIR / "missions"


def atomic_write(path: str | Path, content: str) -> None:
    """
    Escritura atómica: write → fsync → rename.
    Segura para lecturas concurrentes desde otros procesos.
    En Linux, rename() en el mismo filesystem es atómico (POSIX).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp", prefix=".atomic_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fcntl.lockf(f, fcntl.LOCK_EX)
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_append(path: str | Path, line: str) -> None:
    """
    Append atómico con bloqueo exclusivo.
    Evita intercalación de bytes en JSONL cuando múltiples procesos
    escriben al mismo archivo.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        fcntl.lockf(f, fcntl.LOCK_EX)
        f.write(line if line.endswith("\n") else line + "\n")
        f.flush()
        os.fsync(f.fileno())
        fcntl.lockf(f, fcntl.LOCK_UN)


def safe_read(path: str | Path, default: str = "") -> str:
    """Lectura tolerante a archivos inexistentes o parciales."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, OSError):
        return default


# ---------------------------------------------------------------------------
# 1. TOPOLOGÍA DEL ENJAMBRE
# ---------------------------------------------------------------------------

@dataclass
class AgentSlot:
    """Define un slot de ejecución para un agente del enjambre."""
    name: str
    role: Literal["proponent", "adversary", "architect", "optimizer"]
    model: str
    provider: str
    system_message: str
    tools: List[str] = field(default_factory=list)
    vram_budget_mb: int = 2000


@dataclass
class SwarmTopology:
    """Mapa de despliegue completo del enjambre."""
    mission_id: str
    mission_goal: str
    agents: List[AgentSlot]
    mode: Literal["DIALECTIC", "EFFICIENCY", "FULL_SWARM"]
    max_iterations: int = 3
    convergence_threshold: float = 0.90


def build_topology_from_registry(
    goal: str,
    mode: str = "DIALECTIC",
    registry_path: Optional[str] = None,
) -> SwarmTopology:
    """
    Lee agents/registry.yaml y construye la topología según el modo.
    
    DIALECTIC → LeadDev (proponent) + SecurityQA (adversary)
    EFFICIENCY → System_Architect solo  
    FULL_SWARM → Todos los agentes disponibles
    """
    if registry_path is None:
        registry_path = str(BASE_DIR / "agents" / "registry.yaml")

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f)

    agent_defs = registry.get("agents", {})
    mission_id = f"m_{uuid.uuid4().hex[:12]}"

    role_map = {
        "Lead_Developer": "proponent",
        "Security_QA": "adversary",
        "System_Architect": "architect",
        "Silicon_Optimizer": "optimizer",
        "Quantum_Architect": "architect",
        "Meta_Engineer": "proponent",
        "Multimodal_Auditor": "adversary",
        "Token_Analyst": "optimizer",
    }

    # Filtrar agentes según modo
    if mode == "DIALECTIC":
        selected_keys = ["Lead_Developer", "Security_QA"]
    elif mode == "EFFICIENCY":
        selected_keys = ["System_Architect"]
    else:  # FULL_SWARM
        selected_keys = list(agent_defs.keys())

    slots: List[AgentSlot] = []
    for key in selected_keys:
        defn = agent_defs.get(key)
        if not defn:
            continue
        slots.append(AgentSlot(
            name=defn["name"],
            role=role_map.get(key, "proponent"),
            model=defn.get("model", "llama-3.3-70b-versatile"),
            provider=defn.get("provider", "groq"),
            system_message=defn.get("system_message", ""),
            tools=defn.get("tools", []),
        ))

    return SwarmTopology(
        mission_id=mission_id,
        mission_goal=goal,
        agents=slots,
        mode=mode,
    )


# ---------------------------------------------------------------------------
# 2. FORJA DE CEREBROS (Brain Forge)
# ---------------------------------------------------------------------------

class BrainForge:
    """
    Genera archivos de contexto dinámico (.md) para cada agente.
    Cada "cerebro" contiene:
      - System prompt del rol
      - Estado actual del debate (destilado)
      - Herramientas MCP habilitadas
      - Restricciones de hardware
      - Historial destilado de iteraciones previas (si existe)
    """

    def __init__(self, mission_dir: Path):
        self.mission_dir = mission_dir
        self.brains_dir = mission_dir / "brains"
        self.brains_dir.mkdir(parents=True, exist_ok=True)
        self.shredder = LogShredder()

    def forge(
        self,
        agent: AgentSlot,
        topology: SwarmTopology,
        iteration: int = 0,
        distilled_history: str = "",
        hardware_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Escribe el archivo de cerebro y retorna su ruta.
        El archivo es leído por el script runner de cada terminal.
        """
        hw_section = ""
        if hardware_snapshot:
            vram = hardware_snapshot.get("vram", {})
            hw_section = (
                f"## Restricciones de Hardware (Tiempo Real)\n"
                f"- VRAM Disponible: {vram.get('vram_total', 0) - vram.get('vram_used', 0):.0f} MB\n"
                f"- GPU Temp: {vram.get('gpu_temp', 0):.0f}°C\n"
                f"- Presupuesto VRAM por agente: {agent.vram_budget_mb} MB\n"
                f"- Acción recomendada: {hardware_snapshot.get('action', 'PROCEED')}\n\n"
            )

        history_section = ""
        if distilled_history:
            history_section = (
                f"## Historial Destilado (Iteraciones Previas)\n"
                f"```\n{distilled_history}\n```\n\n"
            )

        tools_section = ""
        if agent.tools:
            tools_section = (
                f"## Herramientas MCP Habilitadas\n"
                + "\n".join(f"- `{t}`" for t in agent.tools)
                + "\n\n"
            )

        peers = [a.name for a in topology.agents if a.name != agent.name]
        peers_str = ", ".join(peers) if peers else "(Solo)"

        # 0. Ingesta de Handoff (Continuidad Autónoma)
        handoff_section = ""
        prev_handoff = self.mission_dir / "handoff_state.md"
        if prev_handoff.exists():
            handoff_data = safe_read(prev_handoff)
            if handoff_data:
                handoff_section = (
                    f"## <previous_iteration_lessons>\n"
                    f"Aprende de los errores de la iteración previa antes de actuar:\n"
                    f"```markdown\n{handoff_data[:2000]}\n```\n"
                    f"</previous_iteration_lessons>\n\n"
                )

        content = (
            f"# Cerebro del Agente: {agent.name}\n"
            f"## Misión: {topology.mission_goal}\n"
            f"## Rol: {agent.role.upper()} | Modelo: {agent.provider}/{agent.model}\n"
            f"## Iteración: {iteration + 1}/{topology.max_iterations}\n"
            f"## Pares en Enjambre: {peers_str}\n\n"
            f"---\n\n"
            f"## Directiva de Sistema\n"
            f"{agent.system_message}\n\n"
            f"{handoff_section}"
            f"## Protocolo de Comunicación IPC\n"
            f"- Escribe tu reporte en: `.cortex/missions/{topology.mission_id}/reports/{agent.name}_report.md`\n"
            f"- Lee reportes de pares en: `.cortex/missions/{topology.mission_id}/reports/`\n"
            f"- Señala convergencia escribiendo APPROVED o REJECTED al inicio de tu reporte.\n"
            f"- NO compartas memoria RAM con otros agentes. Solo archivos.\n\n"
            f"{hw_section}"
            f"{history_section}"
            f"{tools_section}"
            f"## Reglas Absolutas\n"
            f"1. Cero alucinaciones. Código verificable o nada.\n"
            f"2. Respeta el límite de VRAM: {agent.vram_budget_mb} MB.\n"
            f"3. Tu output completo debe caber en una respuesta.\n"
            f"4. Si eres ADVERSARY: ataca con evidencia, no con cortesía.\n"
            f"5. Si eres PROPONENT: defiende con código, no con promesas.\n"
        )

        brain_path = self.brains_dir / f"contexto_{agent.name}.md"
        atomic_write(brain_path, content)
        telemetry.info(f"🧠 BrainForge: Cerebro de {agent.name} forjado ({len(content)} chars)")
        return brain_path


# ---------------------------------------------------------------------------
# 3. MULTIPLEXOR DE TERMINALES (tmux)
# ---------------------------------------------------------------------------

class TerminalMultiplexer:
    """
    Gestiona sesiones tmux nombradas para cada agente.
    Cada sesión ejecuta un script Python runner que:
      1. Lee el archivo de contexto (.md)
      2. Invoca la API de LLM correspondiente
      3. Escribe el reporte en .cortex/missions/{id}/reports/
    """

    SESSION_PREFIX = "osaa"

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._sessions: List[str] = []

    def _session_name(self, agent_name: str) -> str:
        return f"{self.SESSION_PREFIX}_{self.mission_id[:8]}_{agent_name}"

    def _tmux_exists(self) -> bool:
        """Verifica que tmux está instalado."""
        return shutil.which("tmux") is not None

    def _session_alive(self, session: str) -> bool:
        """Comprueba si una sesión tmux específica existe."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True,
        )
        return result.returncode == 0

    def spawn(
        self,
        agent: AgentSlot,
        brain_path: Path,
        runner_script: str,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Crea una sesión tmux y ejecuta el runner script dentro.
        
        El runner_script es la ruta al script Python que cada agente ejecuta.
        El brain_path se pasa como argumento al runner.
        
        Returns: nombre de la sesión creada.
        """
        if not self._tmux_exists():
            raise RuntimeError(
                "tmux no está instalado. Ejecuta: sudo apt install tmux"
            )

        session = self._session_name(agent.name)

        # Kill previa si existe (limpieza de runs abortados)
        if self._session_alive(session):
            subprocess.run(
                ["tmux", "kill-session", "-t", session],
                capture_output=True,
            )

        # Crear sesión detached
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", session, "-x", "200", "-y", "50"],
            check=True,
            capture_output=True,
        )

        # Construir comando de ejecución (con quoting para rutas con espacios)
        import shlex
        venv_python = str(BASE_DIR / ".venv" / "bin" / "python")
        cmd_parts = [
            shlex.quote(venv_python), 
            shlex.quote(runner_script),
            "--brain", shlex.quote(str(brain_path)),
            "--mission-id", shlex.quote(self.mission_id),
            "--agent-name", shlex.quote(agent.name),
        ]
        cmd = " ".join(cmd_parts)

        # Inyectar variables de entorno si las hay
        if env_vars:
            for k, v in env_vars.items():
                subprocess.run(
                    ["tmux", "send-keys", "-t", session, f"export {k}='{v}'", "Enter"],
                    capture_output=True,
                )
                time.sleep(0.05)

        # Enviar el comando de ejecución
        subprocess.run(
            ["tmux", "send-keys", "-t", session, cmd, "Enter"],
            check=True,
            capture_output=True,
        )

        self._sessions.append(session)
        telemetry.info(f"🖥️  Terminal [{session}] desplegada para {agent.name}")
        return session

    def kill_session(self, session: str) -> bool:
        """Termina una sesión tmux de forma limpia."""
        if self._session_alive(session):
            subprocess.run(
                ["tmux", "kill-session", "-t", session],
                capture_output=True,
            )
            telemetry.info(f"💀 Terminal [{session}] terminada.")
            return True
        return False

    def kill_all(self) -> int:
        """Termina todas las sesiones del enjambre actual."""
        killed = 0
        for session in self._sessions:
            if self.kill_session(session):
                killed += 1
        self._sessions.clear()
        return killed

    def list_active(self) -> List[str]:
        """Retorna sesiones activas de esta misión."""
        return [s for s in self._sessions if self._session_alive(s)]

    def capture_output(self, session: str, lines: int = 50) -> str:
        """Captura las últimas N líneas de output de una sesión tmux."""
        if not self._session_alive(session):
            return ""
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", session, "-p", "-S", f"-{lines}"],
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else ""


# ---------------------------------------------------------------------------
# 4. WATCHDOG DE CONSENSO
# ---------------------------------------------------------------------------

class ConsensusWatchdog:
    """
    Monitor asíncrono que espera señales de consenso o handoff.
    Hace polling ligero del filesystem + bus IPC cada N segundos.
    
    Señales de archivo:
      - consensus.lock  → misión completada con éxito
      - handoff_state.md → debate divergió, se requiere re-iteración
      - abort.signal     → cancelación manual / OOM
    
    Prevención de Deadlock:
      Monitorea el bus IPC para contar las rondas completadas por
      cada agente. Si TODOS los agentes agotan sus rondas máximas
      sin que aparezca consensus.lock, el Watchdog auto-invoca al
      HandoffRouter para forzar una decisión (SEAL o HANDOFF).
    """

    def __init__(
        self,
        mission_dir: Path,
        mission_id: str = "",
        agents_expected: Optional[List[str]] = None,
        max_rounds_per_agent: int = 3,
        poll_interval: float = 2.0,
        terminals: Optional[TerminalMultiplexer] = None,
    ):
        self.mission_dir = mission_dir
        self.mission_id = mission_id or mission_dir.name
        self.agents_expected = agents_expected or []
        self.max_rounds = max_rounds_per_agent
        self.poll_interval = poll_interval
        self.terminals = terminals
        self.consensus_path = mission_dir / "consensus.lock"
        self.handoff_path = mission_dir / "handoff_state.md"
        self.abort_path = mission_dir / "abort.signal"
        self.bus_path = CORTEX_DIR / "bus_buffer.jsonl"
        self._cancelled = False

    def _count_agent_rounds(self) -> Dict[str, int]:
        """
        Lee el bus IPC y cuenta cuántos AGENT_REPORT ha emitido
        cada agente para esta misión. Tolerante a líneas corruptas.
        """
        counts: Dict[str, int] = {name: 0 for name in self.agents_expected}
        content = safe_read(self.bus_path)
        if not content:
            return counts

        for line in content.strip().splitlines():
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if event.get("type") != "AGENT_REPORT":
                continue
            payload = event.get("payload", {})
            if payload.get("mission_id") != self.mission_id:
                continue
            sender = event.get("sender", "")
            if sender in counts:
                counts[sender] += 1
        return counts

    def _all_agents_exhausted(self) -> bool:
        """True si todos los agentes esperados han emitido >= max_rounds reportes."""
        if not self.agents_expected:
            return False
        counts = self._count_agent_rounds()
        return all(c >= self.max_rounds for c in counts.values())

    async def _auto_invoke_handoff_router(self, iteration: int = 0) -> str:
        """
        Invoca al HandoffRouter para forzar una decisión cuando los
        agentes agotan sus rondas sin consenso. Previene deadlock.
        
        Returns: "consensus" o "handoff" según el resultado del router.
        """
        telemetry.warning(
            f"⚡ Watchdog: Todos los agentes agotaron {self.max_rounds} rondas. "
            "Auto-invocando HandoffRouter para forzar decisión."
        )
        
        # --- PARCHE 2: Limpieza de Zombies ---
        if self.terminals:
            telemetry.info("🧹 Watchdog: Purgando terminales antes del handoff para evitar zombies.")
            self.terminals.kill_all()
            
        try:
            from core.handoff_router import HandoffRouter
            router = HandoffRouter()
            result = router.evaluate_and_route(self.mission_id, iteration=iteration)
            outcome = result.get("action", "HANDOFF")

            if outcome == "SEALED":
                telemetry.info("✅ Watchdog: HandoffRouter selló consenso automáticamente.")
                return "consensus"
            else:
                telemetry.info("🔄 Watchdog: HandoffRouter generó handoff automático.")
                return "handoff"
        except Exception as e:
            telemetry.error(f"❌ Watchdog: Error al invocar HandoffRouter: {e}")
            # Fallback: generar handoff manual para evitar deadlock
            handoff_content = (
                f"# Handoff Automático (Generado por Watchdog)\n\n"
                f"Motivo: Todos los agentes agotaron {self.max_rounds} rondas "
                f"sin consenso y el HandoffRouter falló: {str(e)[:200]}\n\n"
                f"Acción requerida: Re-evaluación manual.\n"
            )
            atomic_write(self.handoff_path, handoff_content)
            return "handoff"

    async def watch(
        self,
        timeout: float = 300.0,
        iteration: int = 0,
    ) -> Literal["consensus", "handoff", "timeout", "abort"]:
        """
        Espera hasta que se detecte una señal o expire el timeout.
        Monitorea el bus para prevenir deadlock por agotamiento de rondas.
        
        Returns:
            "consensus" → debate convergió
            "handoff"   → debate divergió o rondas agotadas
            "timeout"   → se excedió el timeout sin señal
            "abort"     → cancelación manual
        """
        start = time.monotonic()
        telemetry.info(
            f"👁️  Watchdog: Monitoreando {self.mission_dir.name} "
            f"(timeout={timeout}s, agentes={self.agents_expected}, max_rounds={self.max_rounds})"
        )

        while not self._cancelled:
            elapsed = time.monotonic() - start

            # 1. Señales de archivo (prioridad máxima)
            if self.consensus_path.exists():
                telemetry.info("✅ Watchdog: consensus.lock detectado → Misión completada.")
                return "consensus"

            if self.handoff_path.exists():
                telemetry.info("🔄 Watchdog: handoff_state.md detectado → Re-iteración requerida.")
                return "handoff"

            if self.abort_path.exists():
                telemetry.info("🛑 Watchdog: abort.signal detectado → Cancelación.")
                return "abort"

            # 2. Prevención de deadlock: ¿agotaron todos sus rondas?
            if self.agents_expected and self._all_agents_exhausted():
                return await self._auto_invoke_handoff_router(iteration)

            # 3. Timeout global
            if elapsed >= timeout:
                # Antes de dar timeout, intentar forzar decisión si hay reportes
                if self.agents_expected:
                    counts = self._count_agent_rounds()
                    has_reports = any(c > 0 for c in counts.values())
                    if has_reports:
                        telemetry.warning(
                            f"⏰ Watchdog: Timeout con reportes parciales. "
                            f"Forzando evaluación: {counts}"
                        )
                        return await self._auto_invoke_handoff_router(iteration)

                telemetry.warning(f"⏰ Watchdog: Timeout de {timeout}s excedido.")
                return "timeout"

            await asyncio.sleep(self.poll_interval)

        return "abort"

    def cancel(self):
        """Señaliza cancelación del watchdog."""
        self._cancelled = True


# ---------------------------------------------------------------------------
# 5. LAUNCHER PRINCIPAL
# ---------------------------------------------------------------------------

class SwarmLauncher:
    """
    Punto de entrada del enjambre distribuido.
    
    Flujo completo:
      1. Analizar hardware y construir topología
      2. Forjar cerebros para cada agente
      3. Desplegar terminales tmux paralelas
      4. Monitorizar consenso (watchdog)
      5. Si handoff → destilar contexto y re-lanzar
      6. Si consenso → recopilar resultado final
    """

    def __init__(
        self,
        runner_script: Optional[str] = None,
        max_iterations: int = 3,
        watchdog_timeout: float = 300.0,
    ):
        self.hw_monitor = HardwareMonitor()
        self.max_iterations = max_iterations
        self.watchdog_timeout = watchdog_timeout
        # Runner por defecto: scripts/agent_runner.py
        self.runner_script = runner_script or str(BASE_DIR / "scripts" / "agent_runner.py")

    def _load_env_vars(self) -> Dict[str, str]:
        """Carga variables de entorno del .env para inyectarlas en terminales."""
        env_path = BASE_DIR / ".env"
        env_vars: Dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip().strip('"').strip("'")
        return env_vars

    async def launch(
        self,
        goal: str,
        mode: str = "DIALECTIC",
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de vida completo del enjambre.
        
        Args:
            goal: Objetivo de la misión en lenguaje natural.
            mode: DIALECTIC | EFFICIENCY | FULL_SWARM
            
        Returns:
            Diccionario con el resultado de la misión.
        """
        telemetry.info(f"🚀 SwarmLauncher: Iniciando misión — {goal}")

        # --- Pre-Ignición: Telemetría de hardware ---
        hw_snapshot = self.hw_monitor.check_stability()
        if hw_snapshot["status"] == "CRITICAL":
            telemetry.warning("⚠️ Hardware en estado CRÍTICO. Forzando modo EFFICIENCY.")
            mode = "EFFICIENCY"

        # --- Construir topología ---
        topology = build_topology_from_registry(goal, mode)
        topology.max_iterations = self.max_iterations
        mission_dir = MISSIONS_DIR / topology.mission_id

        # Crear estructura de directorios de la misión
        (mission_dir / "reports").mkdir(parents=True, exist_ok=True)
        (mission_dir / "brains").mkdir(parents=True, exist_ok=True)
        (mission_dir / "logs").mkdir(parents=True, exist_ok=True)

        # Persistir manifiesto
        manifest = {
            "mission_id": topology.mission_id,
            "goal": goal,
            "mode": mode,
            "agents": [a.name for a in topology.agents],
            "created_at": time.time(),
            "hardware": hw_snapshot,
        }
        atomic_write(
            mission_dir / "manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )

        env_vars = self._load_env_vars()
        result: Dict[str, Any] = {"mission_id": topology.mission_id, "iterations": []}

        # --- Ciclo iterativo ---
        for iteration in range(self.max_iterations):
            telemetry.info(f"📡 === ITERACIÓN {iteration + 1}/{self.max_iterations} ===")

            # --- Hot Reload: Construir/Refrescar topología en cada iteración ---
            topology = build_topology_from_registry(goal, mode)
            topology.max_iterations = self.max_iterations
            mission_dir = MISSIONS_DIR / topology.mission_id

            # Asegurar estructura de directorios
            (mission_dir / "reports").mkdir(parents=True, exist_ok=True)
            (mission_dir / "brains").mkdir(parents=True, exist_ok=True)
            (mission_dir / "logs").mkdir(parents=True, exist_ok=True)

            # Limpiar señales previas
            for signal_file in [
                mission_dir / "consensus.lock",
                mission_dir / "handoff_state.md",
                mission_dir / "abort.signal",
            ]:
                if signal_file.exists():
                    signal_file.unlink()

            # Leer historial destilado de iteración previa
            distilled_history = ""
            prev_handoff = mission_dir / f"handoff_iter_{iteration}.md"
            if prev_handoff.exists():
                distilled_history = prev_handoff.read_text(encoding="utf-8")

            # Forjar cerebros (actualizado por iteración)
            forge = BrainForge(mission_dir)
            hw_now = self.hw_monitor.check_stability()
            brain_paths: Dict[str, Path] = {}
            for agent in topology.agents:
                brain_paths[agent.name] = forge.forge(
                    agent=agent,
                    topology=topology,
                    iteration=iteration,
                    distilled_history=distilled_history,
                    hardware_snapshot=hw_now,
                )

            # Desplegar terminales paralelas
            mux = TerminalMultiplexer(topology.mission_id)
            for agent in topology.agents:
                mux.spawn(
                    agent=agent,
                    brain_path=brain_paths[agent.name],
                    runner_script=self.runner_script,
                    env_vars=env_vars,
                )

            # Watchdog de consenso (con prevención de deadlock y limpieza de zombies)
            agent_names = [a.name for a in topology.agents]
            watchdog = ConsensusWatchdog(
                mission_dir=mission_dir,
                mission_id=topology.mission_id,
                agents_expected=agent_names,
                max_rounds_per_agent=topology.max_iterations,
                terminals=mux,
            )
            signal_result = await watchdog.watch(
                timeout=self.watchdog_timeout,
                iteration=iteration,
            )

            # Recopilar estado de iteración
            iter_data = {
                "iteration": iteration + 1,
                "signal": signal_result,
                "agents_active": mux.list_active(),
                "hw_status": hw_now["status"],
            }

            # Capturar output de cada terminal antes de cerrar
            for session in mux._sessions:
                output = mux.capture_output(session, lines=30)
                if output:
                    log_path = mission_dir / "logs" / f"{session}_iter{iteration}.log"
                    atomic_write(log_path, output)

            # Limpiar terminales
            killed = mux.kill_all()
            iter_data["terminals_killed"] = killed
            result["iterations"].append(iter_data)

            # Evaluar resultado
            if signal_result == "consensus":
                telemetry.info("🏆 Consenso alcanzado. Misión completada.")
                result["status"] = "COMPLETED"
                result["final_consensus"] = safe_read(mission_dir / "consensus.lock")
                break

            elif signal_result == "handoff":
                telemetry.info("🔄 Handoff detectado. Preparando re-iteración...")
                # Preservar handoff para la próxima iteración
                handoff_content = safe_read(mission_dir / "handoff_state.md")
                atomic_write(
                    mission_dir / f"handoff_iter_{iteration + 1}.md",
                    handoff_content,
                )
                continue

            elif signal_result in ("timeout", "abort"):
                telemetry.warning(f"⚠️ Misión terminada por {signal_result}.")
                result["status"] = signal_result.upper()
                break
        else:
            # Se agotaron las iteraciones sin consenso
            result["status"] = "MAX_ITERATIONS_REACHED"
            telemetry.warning("⚠️ Máximo de iteraciones alcanzado sin consenso.")

        # Persistir resultado final
        atomic_write(
            mission_dir / "result.json",
            json.dumps(result, indent=2, ensure_ascii=False, default=str),
        )

        telemetry.info(f"✨ Misión {topology.mission_id} finalizada: {result.get('status')}")
        return result


# ---------------------------------------------------------------------------
# 6. CLI (Ejecución directa)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Optimización Core OSAA v5.0"
    launcher = SwarmLauncher()
    final = asyncio.run(launcher.launch(goal))
    print(json.dumps(final, indent=2, ensure_ascii=False, default=str))
