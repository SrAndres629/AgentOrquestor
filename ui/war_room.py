import os
import time
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text
from core.hardware_monitor import HardwareMonitor

# Instancia global para telemetría
hardware_monitor = HardwareMonitor()
console = Console()

class WarRoom:
    """
    Interfaz Táctica OSAA v4.0.
    Visualización en tiempo real del metabolismo y debate del enjambre.
    """
    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.start_time = time.time()

    def generate_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="side", size=40),
            Layout(name="body", ratio=1)
        )
        return layout

    def get_telemetry_panel(self) -> Panel:
        stats = hardware_monitor.check_stability()
        vram = stats["vram"]
        sys = stats["system"]
        
        table = Table.grid(expand=True)
        table.add_row("GPU Temp:", f"[bold red]{vram['gpu_temp']}°C[/]")
        table.add_row("VRAM Used:", f"[bold yellow]{vram['vram_used']} MB[/]")
        table.add_row("CPU Load:", f"[bold blue]{sys['cpu_percent']}%[/]")
        table.add_row("RAM Used:", f"{sys['ram_used_gb']} GB")
        
        status_color = "green" if stats["status"] == "STABLE" else "red"
        return Panel(table, title=f"[{status_color}]SENTINEL STATUS[/]", border_style=status_color)

    def get_debate_panel(self, pro_text: str = "Esperando tesis...", adv_text: str = "Esperando auditoría...") -> Panel:
        content = Text()
        content.append("📜 PROPONENTE (LEAD DEV):\n", style="bold green")
        content.append(f"{pro_text[:300]}...\n\n")
        content.append("🛡️ ADVERSARIO (SECURITY QA):\n", style="bold red")
        content.append(f"{adv_text[:300]}...")
        
        return Panel(content, title="DIALECTIC FLOW")

    def run(self, state_callback):
        """Loop de renderizado en vivo."""
        layout = self.generate_layout()
        
        with Live(layout, refresh_per_second=4, screen=True):
            while True:
                # Aquí recuperaríamos el estado real del AgentState
                state = state_callback()
                
                # Actualizar Header
                layout["header"].update(Panel(f"🚀 OSAA v4.0 - MISSION ID: {self.mission_id} | Uptime: {int(time.time() - self.start_time)}s", style="bold magenta"))
                
                # Actualizar Paneles
                layout["side"].update(self.get_telemetry_panel())
                layout["body"].update(self.get_debate_panel(
                    state.get("proponent_report", "Iniciando..."),
                    state.get("adversary_audit", "Iniciando...")
                ))
                
                # Actualizar Footer con el Score del Árbitro
                score = state.get("consensus_score", 0.0)
                layout["footer"].update(Panel(f"⚖️ CONVERGENCE SCORE: [bold cyan]{score:.4f}[/] | ROUND: {state.get('debate_rounds', 0)}", border_style="cyan"))
                
                time.sleep(0.5)
