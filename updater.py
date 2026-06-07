"""
updater.py — Verificador de atualizações automáticas
Roda toda vez que o Jarvis abre. Se tiver versão nova no GitHub, baixa e aplica.
"""

import subprocess
import sys
import json
import urllib.request
from pathlib import Path

REPO_URL    = "https://github.com/tvrubira-cloud/JARVIS-2.0.git"
API_URL     = "https://api.github.com/repos/tvrubira-cloud/JARVIS-2.0/commits/master"
VERSION_FILE = Path(__file__).parent / ".version"


def get_local_version() -> str:
    """Retorna o hash do último commit local."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent)
        )
        return r.stdout.strip()
    except Exception:
        return ""


def get_remote_version() -> str:
    """Retorna o hash do último commit no GitHub."""
    try:
        req = urllib.request.Request(
            API_URL,
            headers={"User-Agent": "JARVIS-Updater"}
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            data = json.loads(res.read())
            return data["sha"]
    except Exception:
        return ""


def apply_update() -> bool:
    """Puxa as atualizações do GitHub."""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "master"],
            capture_output=True, text=True,
            cwd=str(Path(__file__).parent)
        )
        print(f"[Updater] {result.stdout.strip()}")
        return "Already up to date" not in result.stdout
    except Exception as e:
        print(f"[Updater] Erro ao atualizar: {e}")
        return False


def install_new_dependencies():
    """Instala dependências novas se requirements.txt mudou."""
    try:
        req_file = Path(__file__).parent / "requirements.txt"
        if req_file.exists():
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                capture_output=True
            )
    except Exception:
        pass


def check_and_update(silent: bool = True) -> bool:
    """
    Verifica e aplica atualização se disponível.
    Retorna True se atualizou, False se já estava atualizado.
    """
    if not silent:
        print("[Updater] Verificando atualizações...")

    local  = get_local_version()
    remote = get_remote_version()

    if not remote:
        if not silent:
            print("[Updater] Sem conexão ou repositório inacessível.")
        return False

    if local == remote:
        if not silent:
            print("[Updater] ✅ Já está na versão mais recente.")
        return False

    print("[Updater] 🔄 Nova versão disponível! Atualizando...")
    updated = apply_update()

    if updated:
        install_new_dependencies()
        print("[Updater] ✅ Atualização concluída! Reiniciando...")
        # Reinicia o Jarvis com a versão nova
        python = Path(sys.executable)
        main   = Path(__file__).parent / "main.py"
        subprocess.Popen([str(python), str(main)], cwd=str(Path(__file__).parent))
        sys.exit(0)

    return updated


if __name__ == "__main__":
    check_and_update(silent=False)
