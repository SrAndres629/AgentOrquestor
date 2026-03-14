"""
AgentOrquestor — Handoff Router (Nodo Condicional de Transferencia) v5.0
========================================================================
Evalúa el estado del debate inter-proceso, decide si avanzar
(consensus.lock) o retroceder (handoff_state.md), y gestiona
la transición entre iteraciones del enjambre.

Integra: Arbitrator (convergencia), Shredder (destilación),
         TerminalMultiplexer (kill de sesiones).

Race-condition safe: Todas las escrituras usan atomic_write().
"""

import os
import json
import time
import glob
from typing import Dict, Any, Optional, Literal, List
from dataclasses import dataclass, field
from pathlib import Path

from core.telemetry import telemetry
from core.shredder import LogShredder
from core.hardware_monitor import HardwareMonitor
from core.swarm_launcher import (
    atomic_write,
    safe_read,
    CORTEX_DIR,
    MISSIONS_DIR,
    TerminalMultiplexer,
)


# ---------------------------------------------------------------------------
# 0. TIPOS DE RESULTADO
# ---------------------------------------------------------------------------

@dataclass
class EvaluationResult:
    """Resultado de la evaluación de un ciclo de debate."""
    status: Literal["CONVERGED", "DIVERGED", "INCOMPLETE", "ERROR"]
    convergence_score: float
    is_stable: bool
    reports_found: Dict[str, str]  # agent_name → report_content
    analysis: str                  # Explicación legible
    hardware_status: str = "UNKNOWN"
    iteration: int = 0


# ---------------------------------------------------------------------------
# 1. EVALUADOR DE DEBATE
# ---------------------------------------------------------------------------

class DebateEvaluator:
    """
    Lee los reportes de cada agente desde el filesystem y evalúa
    la convergencia del debate usando el motor Arbitrator existente.
    
    Detecta:
      - Reportes faltantes (agente que no respondió)
      - Convergencia insuficiente (score < threshold)
      - Estancamiento (plateau sin mejora)
      - Fricciones insuficientes (cortesía algorítmica)
    """

    def __init__(
        self,
        convergence_threshold: float = 0.80,
        min_report_length: int = 50,
    ):
        self.threshold = convergence_threshold
        self.min_report_length = min_report_length
        self.hw_monitor = HardwareMonitor()
        self.history: List[float] = []

    def calculate_convergence(self, pro: str, adv: str) -> float:
        """
        Calcula un score de convergencia [0-1] basado en señales lingüísticas.
        OSAA v5.0: Favorece la 'Aprobación Explícita' y la brevedad técnica.
        """
        pro_up = pro.upper()
        adv_up = adv.upper()
        
        score = 0.0
        # 1. Señales de Aprobación (50%)
        if "APPROVED" in adv_up: score += 0.5
        elif "FIXED" in adv_up or "RESOLVED" in adv_up: score += 0.3
        
        if "APPROVED" in pro_up: score += 0.2
        
        # 2. Señales de Rechazo (-50%)
        if "REJECTED" in adv_up or "VETO" in adv_up: score -= 0.5
        if "REJECTED" in pro_up: score -= 0.2

        # 3. Emparejamiento de longitud (20%) - Debate sano suele tener longitudes similares
        ratio = min(len(pro), len(adv)) / max(len(pro), len(adv))
        score += ratio * 0.3
        
        final_score = max(0.0, min(1.0, score))
        self.history.append(final_score)
        return final_score

    def is_stable(self) -> bool:
        """Detecta si el score ha convergido a un valor estable."""
        if len(self.history) < 2: return False
        # Si hay un veto activo, nunca es estable para cerrar
        return abs(self.history[-1] - self.history[-2]) < 0.05
    def _collect_reports(self, reports_dir: Path) -> Dict[str, str]:
        """
        Recoge todos los reportes *_report.md del directorio de la misión.
        Tolerante a archivos corruptos o parciales.
        """
        reports: Dict[str, str] = {}
        if not reports_dir.exists():
            return reports

        for report_file in sorted(reports_dir.glob("*_report.md")):
            agent_name = report_file.stem.replace("_report", "")
            content = safe_read(report_file)
            if content and len(content.strip()) >= self.min_report_length:
                reports[agent_name] = content
            else:
                telemetry.warning(
                    f"⚠️ Reporte de {agent_name} vacío o insuficiente "
                    f"({len(content.strip())} chars < {self.min_report_length})"
                )

        return reports

    def _classify_roles(
        self, reports: Dict[str, str]
    ) -> tuple[str, str]:
        """
        Identifica proponente y adversario por marcadores en el contenido.
        Heurística: busca TESIS/APPROVED → proponent, CRÍTICA/REJECTED → adversary.
        """
        proponent_content = ""
        adversary_content = ""

        pro_markers = ("TESIS", "PROPUESTA", "APPROVED", "IMPLEMENTACIÓN")
        adv_markers = ("CRÍTICA", "RIESGO", "REJECTED", "VETO", "VULNERABILIDAD")

        for agent_name, content in reports.items():
            upper = content.upper()
            pro_score = sum(1 for m in pro_markers if m in upper)
            adv_score = sum(1 for m in adv_markers if m in upper)

            if pro_score >= adv_score:
                proponent_content = content
            else:
                adversary_content = content

        return proponent_content, adversary_content

    def evaluate(
        self,
        mission_id: str,
        expected_agents: Optional[List[str]] = None,
        iteration: int = 0,
    ) -> EvaluationResult:
        """
        Evaluación completa del estado del debate.
        
        Proceso:
          1. Recoger reportes del filesystem
          2. Verificar completitud (todos los agentes reportaron)
          3. Clasificar roles (proponent / adversary)
          4. Calcular convergencia (Arbitrator)
          5. Evaluar estabilidad (plateau detection)
          6. Snapshot de hardware
        """
        mission_dir = MISSIONS_DIR / mission_id
        reports_dir = mission_dir / "reports"

        telemetry.info(f"🔍 Evaluador: Analizando reportes en {reports_dir}")

        # 1. Recoger reportes
        reports = self._collect_reports(reports_dir)

        if not reports:
            return EvaluationResult(
                status="INCOMPLETE",
                convergence_score=0.0,
                is_stable=False,
                reports_found={},
                analysis="No se encontraron reportes válidos.",
                iteration=iteration,
            )

        # 2. Verificar completitud
        missing_agents = []
        if expected_agents:
            for agent in expected_agents:
                if agent not in reports:
                    missing_agents.append(agent)

        if missing_agents:
            telemetry.warning(f"⚠️ Agentes sin reporte: {missing_agents}")

        # 3. Clasificar roles
        pro_text, adv_text = self._classify_roles(reports)

        if not pro_text or not adv_text:
            return EvaluationResult(
                status="INCOMPLETE",
                convergence_score=0.0,
                is_stable=False,
                reports_found=reports,
                analysis=(
                    f"Debate incompleto: {'sin proponente' if not pro_text else 'sin adversario'}. "
                    f"Agentes faltantes: {missing_agents or 'ninguno'}."
                ),
                iteration=iteration,
            )

        # 4. Calcular convergencia (Heurísticas Guía 02)
        score = self.calculate_convergence(pro_text, adv_text)
        
        # 5. Aplicar Regla de Veto Absoluto (Guía 02)
        active_veto = False
        veto_reason = None
        adv_upper = adv_text.upper()
        if any(m in adv_upper for m in ("REJECTED", "VETO", "RIESGO CRÍTICO", "VULNERABILIDAD")):
            active_veto = True
            veto_reason = "Veto detectado en el reporte del Auditor/QA."
            if score > 0.85:
                score = 0.85 # Cap de seguridad Guía 02

        # 6. Estabilidad
        is_stable = self.is_stable() if not active_veto else False

        # 7. Hardware
        hw = self.hw_monitor.check_stability()

        # Síntesis
        if score >= self.threshold and is_stable and not active_veto:
            status = "CONVERGED"
            analysis = (
                f"Convergencia alcanzada (score={score:.4f} ≥ {self.threshold}). "
                f"Debate estable tras {len(self.history)} rondas."
            )
        else:
            status = "DIVERGED"
            reasons = []
            if score < self.threshold:
                reasons.append(f"score={score:.4f} < {self.threshold}")
            if active_veto:
                reasons.append(f"VETO ACTIVO: {veto_reason}")
            elif not is_stable:
                reasons.append("plateau no detectado")
            
            if missing_agents:
                reasons.append(f"agentes faltantes: {missing_agents}")
            analysis = f"Debate no converge: {'; '.join(reasons)}."

        telemetry.info(f"📊 Evaluación: {status} — {analysis}")

        return EvaluationResult(
            status=status,
            convergence_score=score,
            is_stable=is_stable,
            reports_found=reports,
            analysis=analysis,
            hardware_status=hw["status"],
            iteration=iteration,
        )


# ---------------------------------------------------------------------------
# 2. GENERADOR DE HANDOFF
# ---------------------------------------------------------------------------

class HandoffGenerator:
    """
    Cuando el debate diverge, genera un archivo handoff_state.md con:
      - Errores y riesgos identificados
      - Historial destilado (via Shredder)
      - Directivas para la siguiente iteración
      - Métricas de hardware al momento del handoff
    
    También señaliza al TerminalMultiplexer que debe matar 
    las sesiones tmux activas.
    """

    def __init__(self):
        self.shredder = LogShredder()
        self.hw_monitor = HardwareMonitor()

    def _distill_reports(self, reports: Dict[str, str]) -> str:
        """Destila los reportes usando el Shredder para context compression."""
        if not reports:
            return "Sin historial para destilar."

        # Convertir reportes a formato digerible por el shredder
        history_dicts = []
        agents = list(reports.keys())
        
        # Emparejar reportes como proponent/adversary
        pro_content = ""
        adv_content = ""
        for name, content in reports.items():
            upper = content.upper()
            if any(m in upper for m in ("TESIS", "PROPUESTA", "APPROVED")):
                pro_content = content
            else:
                adv_content = content

        if pro_content or adv_content:
            history_dicts.append({
                "proponent": pro_content,
                "adversary": adv_content,
            })

        return self.shredder.distill(history_dicts)

    def generate(
        self,
        evaluation: EvaluationResult,
        mission_id: str,
    ) -> Path:
        """
        Genera handoff_state.md y lo escribe atómicamente al filesystem.
        
        Returns: Path al archivo generado.
        """
        mission_dir = MISSIONS_DIR / mission_id
        hw = self.hw_monitor.check_stability()

        distilled = self._distill_reports(evaluation.reports_found)

        content = (
            f"# Handoff State — Iteración {evaluation.iteration + 1}\n"
            f"## Misión: {mission_id}\n"
            f"## Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"---\n\n"
            f"## Resultado de Evaluación\n"
            f"- **Status:** {evaluation.status}\n"
            f"- **Score de Convergencia:** {evaluation.convergence_score:.4f}\n"
            f"- **Estable:** {'Sí' if evaluation.is_stable else 'No'}\n"
            f"- **Hardware:** {evaluation.hardware_status}\n\n"
            f"## Análisis\n"
            f"{evaluation.analysis}\n\n"
            f"## Directivas para Siguiente Iteración\n"
        )

        # Generar directivas específicas según tipo de fallo
        directives = []

        if evaluation.convergence_score < 0.50:
            directives.append(
                "- ⚠️ **DIVERGENCIA SEVERA**: Los agentes tienen posiciones irreconciliables. "
                "Considerar replanteamiento del objetivo o cambio de modo."
            )
        elif evaluation.convergence_score < 0.90:
            directives.append(
                "- 🔄 **AJUSTE FINO**: Los agentes están cerca del consenso. "
                "Focalizar en los puntos de fricción restantes."
            )

        if not evaluation.is_stable:
            directives.append(
                "- 📈 **SIN PLATEAU**: El score no se ha estabilizado. "
                "Incrementar las rondas de debate internas."
            )

        missing = [a for a in (evaluation.reports_found or {}) 
                   if not evaluation.reports_found.get(a)]
        if len(evaluation.reports_found) < 2:
            directives.append(
                "- 🚫 **DEBATE INCOMPLETO**: Faltan reportes de agentes. "
                "Verificar que las terminales no hayan crasheado (OOM/Timeout)."
            )

        if hw["status"] == "CRITICAL":
            vram = hw.get("vram", {})
            directives.append(
                f"- 🔥 **ALERTA TÉRMICA**: GPU a {vram.get('gpu_temp', '?')}°C. "
                f"VRAM: {vram.get('vram_used', '?')}/{vram.get('vram_total', '?')} MB. "
                "Reducir carga o cambiar a modo EFFICIENCY."
            )

        if not directives:
            directives.append(
                "- ℹ️ **REINTENTAR**: Sin errores específicos detectados. "
                "Reiniciar debate con contexto destilado."
            )

        content += "\n".join(directives)

        content += (
            f"\n\n## Historial Destilado (Context Shredder)\n"
            f"```\n{distilled}\n```\n\n"
            f"## Reportes Recibidos ({len(evaluation.reports_found)} agentes)\n"
        )

        for agent_name, report in evaluation.reports_found.items():
            # Incluir solo las primeras 500 chars de cada reporte
            preview = report[:500].replace("\n", " ")
            content += f"- **{agent_name}**: {preview}...\n"

        # Escribir atómicamente
        handoff_path = mission_dir / "handoff_state.md"
        atomic_write(handoff_path, content)

        telemetry.info(
            f"📝 Handoff generado: {handoff_path} "
            f"({len(content)} chars, score={evaluation.convergence_score:.4f})"
        )

        return handoff_path


# ---------------------------------------------------------------------------
# 3. SELLADOR DE CONSENSO
# ---------------------------------------------------------------------------

class ConsensusSealer:
    """
    Cuando el debate converge, escribe consensus.lock con el 
    reporte final consolidado. Esto desbloquea al ConsensusWatchdog
    del SwarmLauncher.
    """

    def seal(
        self,
        evaluation: EvaluationResult,
        mission_id: str,
    ) -> Path:
        """
        Escribe el archivo consensus.lock con la decisión final.
        
        El archivo contiene un JSON con:
          - Score final
          - Reportes consolidados
          - Timestamp de consenso
          - Análisis del árbitro
        """
        mission_dir = MISSIONS_DIR / mission_id

        consensus_data = {
            "sealed_at": time.time(),
            "sealed_at_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mission_id": mission_id,
            "convergence_score": evaluation.convergence_score,
            "is_stable": evaluation.is_stable,
            "analysis": evaluation.analysis,
            "iteration": evaluation.iteration,
            "agents": list(evaluation.reports_found.keys()),
            "hardware_status": evaluation.hardware_status,
        }

        consensus_path = mission_dir / "consensus.lock"
        atomic_write(
            consensus_path,
            json.dumps(consensus_data, indent=2, ensure_ascii=False),
        )

        # También persistir los reportes individuales como archivo consolidado
        consolidated_path = mission_dir / "final_consolidated_report.md"
        consolidated = (
            f"# Reporte Final Consolidado\n"
            f"## Misión: {mission_id}\n"
            f"## Score: {evaluation.convergence_score:.4f}\n"
            f"## Sellado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
        )
        for agent, report in evaluation.reports_found.items():
            consolidated += f"## Reporte de {agent}\n{report}\n\n---\n\n"

        atomic_write(consolidated_path, consolidated)

        telemetry.info(
            f"🔒 Consenso sellado: {consensus_path} "
            f"(score={evaluation.convergence_score:.4f})"
        )

        return consensus_path


# ---------------------------------------------------------------------------
# 4. ROUTER PRINCIPAL
# ---------------------------------------------------------------------------

class HandoffRouter:
    """
    Nodo condicional central: Máquina de estados del debate.
    
    Flujo:
      EVALUATING → CONVERGED → SEALED (consensus.lock) → FIN
      EVALUATING → DIVERGED  → HANDOFF (handoff_state.md) → Re-lanzamiento
    
    Se invoca desde el SwarmLauncher o como herramienta MCP independiente.
    """

    def __init__(self, convergence_threshold: float = 0.90):
        self.evaluator = DebateEvaluator(convergence_threshold=convergence_threshold)
        self.handoff_gen = HandoffGenerator()
        self.sealer = ConsensusSealer()

    def evaluate_and_route(
        self,
        mission_id: str,
        expected_agents: Optional[List[str]] = None,
        iteration: int = 0,
        kill_terminals: bool = True,
    ) -> Dict[str, Any]:
        """
        Punto de entrada del enrutamiento.
        
        1. Evalúa el debate
        2. Si CONVERGED → sella consenso
        3. Si DIVERGED/INCOMPLETE → genera handoff y (opcionalmente) mata terminales
        
        Args:
            mission_id: ID de la misión activa.
            expected_agents: Lista de nombres de agentes esperados.
            iteration: Número de iteración actual.
            kill_terminals: Si True, mata las sesiones tmux al generar handoff.
            
        Returns:
            Diccionario con la decisión de enrutamiento.
        """
        telemetry.info(f"🔀 HandoffRouter: Evaluando misión {mission_id}, iteración {iteration + 1}")

        # 1. Evaluar
        evaluation = self.evaluator.evaluate(
            mission_id=mission_id,
            expected_agents=expected_agents,
            iteration=iteration,
        )

        result: Dict[str, Any] = {
            "mission_id": mission_id,
            "iteration": iteration + 1,
            "status": evaluation.status,
            "convergence_score": evaluation.convergence_score,
            "analysis": evaluation.analysis,
        }

        # 2. Enrutar
        if evaluation.status == "CONVERGED":
            # → SEAL
            consensus_path = self.sealer.seal(evaluation, mission_id)
            result["action"] = "SEALED"
            result["consensus_path"] = str(consensus_path)
            telemetry.info("🏆 Ruta: CONVERGED → SEALED")

        elif evaluation.status in ("DIVERGED", "INCOMPLETE"):
            # → HANDOFF
            handoff_path = self.handoff_gen.generate(evaluation, mission_id)
            result["action"] = "HANDOFF"
            result["handoff_path"] = str(handoff_path)

            # Matar terminales si se solicita
            if kill_terminals:
                mux = TerminalMultiplexer(mission_id)
                # Reconstruir las sesiones activas de esta misión
                import subprocess as sp
                tmux_ls = sp.run(["tmux", "ls"], capture_output=True, text=True)
                if tmux_ls.returncode == 0:
                    for line in tmux_ls.stdout.splitlines():
                        session_name = line.split(":")[0]
                        if mission_id[:8] in session_name:
                            mux._sessions.append(session_name)
                    killed = mux.kill_all()
                    result["terminals_killed"] = killed
                    telemetry.info(f"💀 {killed} terminales eliminadas.")

            telemetry.info(f"🔄 Ruta: {evaluation.status} → HANDOFF")

        else:
            result["action"] = "ERROR"
            result["error"] = evaluation.analysis
            telemetry.error(f"❌ Ruta: ERROR — {evaluation.analysis}")

        # Persistir decisión
        mission_dir = MISSIONS_DIR / mission_id
        decision_log = mission_dir / "logs" / f"routing_decision_iter{iteration}.json"
        atomic_write(
            decision_log,
            json.dumps(result, indent=2, ensure_ascii=False, default=str),
        )

        return result


# ---------------------------------------------------------------------------
# 5. INSTANCIA GLOBAL + CLI
# ---------------------------------------------------------------------------

handoff_router = HandoffRouter()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python handoff_router.py <mission_id> [iteration]")
        sys.exit(1)

    mid = sys.argv[1]
    it = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    decision = handoff_router.evaluate_and_route(mid, iteration=it)
    print(json.dumps(decision, indent=2, ensure_ascii=False, default=str))
