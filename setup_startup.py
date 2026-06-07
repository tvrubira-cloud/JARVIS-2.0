"""
setup_startup.py — Registra o Jarvis para iniciar com o Windows
Execute UMA VEZ como administrador.

O que faz:
  1. Registra wakeword.py na inicialização do Windows (via registro)
  2. Cria atalho na área de trabalho para abrir o Jarvis manualmente
  3. Opcional: cria atalho na barra de tarefas

Uso:
  python setup_startup.py          ← instala
  python setup_startup.py remove   ← remove da inicialização
"""

import sys
import os
import winreg
import subprocess
from pathlib import Path


BASE_DIR    = Path(__file__).parent
PYTHON_EXE  = sys.executable
WAKEWORD    = BASE_DIR / "wakeword.py"
MAIN_SCRIPT = BASE_DIR / "main.py"
STARTUP_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
APP_NAME    = "JarvisWakeWord"


# ─── Registro do Windows ──────────────────────────────────────────────────────

def install_startup():
    """Adiciona wakeword.py à inicialização do Windows via wscript (sem janela)."""
    pythonw = Path(PYTHON_EXE).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = PYTHON_EXE

    # Cria um .vbs invisível que roda o wakeword sem nenhuma janela
    vbs_path = BASE_DIR / "wakeword_start.vbs"
    vbs_content = f'CreateObject("WScript.Shell").Run "{pythonw} {WAKEWORD}", 0, False\n'
    vbs_path.write_text(vbs_content, encoding="utf-8")

    # Registra o .vbs no startup (wscript não abre janela nenhuma)
    cmd = f'wscript.exe "{vbs_path}"'

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY,
                             0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        print(f"✅ Jarvis adicionado à inicialização do Windows!")
        print(f"   Comando: {cmd}")
    except Exception as e:
        print(f"❌ Erro ao registrar: {e}")


def remove_startup():
    """Remove wakeword.py da inicialização do Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY,
                             0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        print(f"✅ Jarvis removido da inicialização.")
    except FileNotFoundError:
        print("ℹ️  Jarvis não estava na inicialização.")
    except Exception as e:
        print(f"❌ Erro: {e}")


def check_startup():
    """Verifica se está registrado."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            print(f"✅ Jarvis está na inicialização: {val}")
            return True
    except FileNotFoundError:
        print("ℹ️  Jarvis NÃO está na inicialização.")
        return False


# ─── Atalho na área de trabalho ───────────────────────────────────────────────

def create_desktop_shortcut():
    """Cria atalho .vbs na área de trabalho para abrir o Jarvis."""
    desktop = Path.home() / "Desktop"
    shortcut = desktop / "Jarvis.vbs"

    pythonw = Path(PYTHON_EXE).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = PYTHON_EXE

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{BASE_DIR}"
WshShell.Run "{pythonw} {MAIN_SCRIPT}", 0, False
'''
    shortcut.write_text(vbs_content, encoding="utf-8")
    print(f"✅ Atalho criado na área de trabalho: {shortcut}")


# ─── Instalar dependências ────────────────────────────────────────────────────

def install_dependencies():
    print("📦 Instalando dependências (vosk, sounddevice)...")
    subprocess.run([PYTHON_EXE, "-m", "pip", "install", "vosk", "sounddevice"], check=False)
    print("✅ Dependências instaladas!")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "remove":
        remove_startup()
    else:
        print("=" * 50)
        print("  JARVIS — Configuração de Inicialização")
        print("=" * 50)
        install_dependencies()
        install_startup()
        create_desktop_shortcut()
        check_startup()
        print("\n✅ Pronto! Na próxima vez que o Windows iniciar,")
        print("   o Jarvis já estará ouvindo em segundo plano.")
        print("   Diga 'Jarvis' para ativá-lo!")
        print("\n   Para remover: python setup_startup.py remove")
        input("\nPressione Enter para fechar...")
