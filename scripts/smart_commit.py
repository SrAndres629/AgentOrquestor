import os
import subprocess
import sys

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def main():
    sys.stderr.write("🚀 [SYNC] Sincronización Directa v3.5\n")
    # 1. Staging
    run_command("git add .")
    
    # 2. Commit
    commit_msg = "refactor: structural unif. and smart_commit 3.5"
    run_command(f"git commit -m \"{commit_msg}\"")
    
    # 3. Token & Push
    token = ""
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "github_token=" in line:
                    token = line.split("=")[1].strip().strip("\"").strip("'")
    
    if token:
        sys.stderr.write("🔑 [AUTH] Empujando con Token...\n")
        auth_url = f"https://SrAndres629:{token}@github.com/SrAndres629/AgentOrquestor.git"
        _, stderr, code = run_command(f"git push {auth_url} main")
        if code == 0:
            sys.stderr.write("✅ [SUCCESS] Proyecto sincronizado correctamente en GitHub.\n")
        else:
            sys.stderr.write(f"❌ [ERROR] Falló el Push: {stderr}\n")
    else:
        run_command("git push origin main")

if __name__ == "__main__":
    main()
