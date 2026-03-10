import os
import subprocess
import sys

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

def get_git_diff():
    stdout, _ = run_command("git diff --cached")
    return stdout

def load_env_token():
    """Busca la variable github_token en el archivo .env."""
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith("github_token="):
                    # Extraer el valor ignorando posibles comillas
                    token = line.split("=")[1].strip().strip("\"").strip("'")
                    return token
    return None

def main():
    print("🚀 [SMART_COMMIT] Iniciando ciclo de sincronización inteligente con Token...")
    
    # 1. Comprobar cambios
    diff = get_git_diff()
    if not diff:
        print("⚠️  No hay cambios en el stage. Usa 'git add' primero.")
        sys.exit(0)

    # 2. Generación de Mensaje
    commit_msg = "feat: evolution of AgentOrquestor (v2.3) - Reactive EDA & Self-Healing"
    if "event_bus" in diff: commit_msg = "feat(core): enhance reactive event bus"
    elif "registry" in diff: commit_msg = "refactor(agents): update dynamic registry"
    elif "telemetry" in diff: commit_msg = "feat(telemetry): implement real-time log sentinel"

    # 3. Commit Local
    stdout, stderr = run_command(f"git commit -m '{commit_msg}'")
    if stderr and "error" in stderr.lower() and "nothing to commit" not in stderr.lower():
        print(f"❌ Error en commit: {stderr}")
    else:
        print(f"✅ Commit local exitoso: '{commit_msg}'")

    # 4. Push con Token
    token = load_env_token()
    repo_url = "https://github.com/SrAndres629/AgentOrquestor.git"
    
    if token:
        print("🔑 [AUTH] Token detectado. Configurando empuje autenticado...")
        # Construimos la URL con el token para bypass de login interactivo
        auth_url = f"https://SrAndres629:{token}@github.com/SrAndres629/AgentOrquestor.git"
        stdout, stderr = run_command(f"git push {auth_url} main")
    else:
        print("⚠️  No se encontró 'github_token' en .env. Usando push estándar...")
        stdout, stderr = run_command("git push origin main")

    if "Everything up-to-date" in stdout or "Everything up-to-date" in stderr:
        print("✅ Todo está actualizado.")
    elif stderr and "error" in stderr.lower():
        print(f"❌ Error en Push: {stderr}")
    else:
        print("🎊 [SUCCESS] Proyecto sincronizado correctamente en GitHub.")

if __name__ == "__main__":
    main()
