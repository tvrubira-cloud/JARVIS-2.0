"""
install.py — Instalador do JARVIS 2.0
Rode UMA VEZ para instalar tudo automaticamente.

Como usar:
1. Instale Python 3.12 em python.org
2. Baixe este arquivo
3. Dê duplo clique ou rode: python install.py
"""

import subprocess
import sys
import os
import winreg
import urllib.request
import zipfile
from pathlib import Path


REPO_URL   = "https://github.com/tvrubira-cloud/JARVIS-2.0.git"
INSTALL_DIR = Path.home() / "Desktop" / "JARVIS 2.0"
PYTHON_EXE  = sys.executable
STARTUP_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"


def print_step(msg: str):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print('='*50)


def run(cmd: list, cwd=None) -> bool:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        if r.returncode != 0:
            print(f"  ⚠️  {r.stderr.strip()}")
        return r.returncode == 0
    except Exception as e:
        print(f"  ❌ Erro: {e}")
        return False


def check_python_version():
    print_step("Verificando Python...")
    major, minor = sys.version_info.major, sys.version_info.minor
    print(f"  Python {major}.{minor} detectado.")
    if major < 3 or minor < 10:
        print("  ❌ Python 3.10 ou superior necessário!")
        print("  Baixe em: https://python.org/downloads")
        input("\nPressione Enter para fechar...")
        sys.exit(1)
    print("  ✅ Python OK!")


def check_git():
    print_step("Verificando Git...")
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, text=True)
        print(f"  {r.stdout.strip()}")
        print("  ✅ Git OK!")
        return True
    except FileNotFoundError:
        print("  ❌ Git não encontrado!")
        print("  Instalando Git...")
        run(["winget", "install", "Git.Git", "-e", "--silent"])
        print("  ✅ Git instalado! Feche e abra este instalador novamente.")
        input("\nPressione Enter para fechar...")
        sys.exit(0)


def clone_repo():
    print_step("Baixando JARVIS 2.0...")
    if INSTALL_DIR.exists():
        print(f"  Pasta já existe: {INSTALL_DIR}")
        print("  Atualizando...")
        run(["git", "pull", "origin", "master"], cwd=str(INSTALL_DIR))
    else:
        print(f"  Clonando para: {INSTALL_DIR}")
        ok = run(["git", "clone", REPO_URL, str(INSTALL_DIR)])
        if not ok:
            print("  ❌ Erro ao baixar o projeto!")
            input("\nPressione Enter para fechar...")
            sys.exit(1)
    print("  ✅ Projeto baixado!")


def install_dependencies():
    print_step("Instalando dependências...")
    req_file = INSTALL_DIR / "requirements.txt"
    if req_file.exists():
        run([PYTHON_EXE, "-m", "pip", "install", "-r", str(req_file)])
    run([PYTHON_EXE, "-m", "pip", "install", "vosk", "sounddevice", "SpeechRecognition", "psutil"])
    print("  ✅ Dependências instaladas!")


def install_playwright():
    print_step("Instalando navegador (Playwright)...")
    run([PYTHON_EXE, "-m", "playwright", "install"])
    print("  ✅ Playwright instalado!")


def setup_api_key():
    print_step("Configurando API Key do Gemini...")
    print("  Acesse: https://aistudio.google.com/apikey")
    print("  Crie uma chave e cole abaixo.")
    key = input("\n  Cole sua chave Gemini (AIza...): ").strip()
    if key:
        config_dir = INSTALL_DIR / "config"
        config_dir.mkdir(exist_ok=True)
        api_file = config_dir / "api_keys.json"
        import json
        api_file.write_text(json.dumps({
            "gemini_api_key": key,
            "os_system": "windows"
        }, indent=4), encoding="utf-8")
        print("  ✅ Chave salva!")
    else:
        print("  ⚠️  Chave não configurada. Configure depois pela interface do Jarvis.")


def setup_startup():
    print_step("Configurando inicialização automática...")
    wakeword = INSTALL_DIR / "wakeword.py"
    pythonw  = Path(PYTHON_EXE).parent / "pythonw.exe"
    exe = str(pythonw) if pythonw.exists() else PYTHON_EXE

    # Cria vbs invisível
    vbs = INSTALL_DIR / "wakeword_start.vbs"
    vbs.write_text(
        f'CreateObject("WScript.Shell").Run """{exe}"" ""{wakeword}""", 0, False\n',
        encoding="utf-8"
    )

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "JarvisWakeWord", 0, winreg.REG_SZ, f'wscript.exe "{vbs}"')
        print("  ✅ Jarvis vai iniciar com o Windows!")
    except Exception as e:
        print(f"  ⚠️  Erro ao configurar inicialização: {e}")


def create_shortcut():
    print_step("Criando atalho na área de trabalho...")
    shortcut = Path.home() / "Desktop" / "Jarvis.bat"
    shortcut.write_text(
        f'@echo off\ncd /d "{INSTALL_DIR}"\n"{PYTHON_EXE}" main.py\n',
        encoding="utf-8"
    )
    print(f"  ✅ Atalho criado: {shortcut}")


def main():
    print("\n" + "="*50)
    print("   JARVIS 2.0 — Instalador")
    print("="*50)

    check_python_version()
    check_git()
    clone_repo()
    install_dependencies()
    install_playwright()
    setup_api_key()
    setup_startup()
    create_shortcut()

    print("\n" + "="*50)
    print("  ✅ JARVIS 2.0 instalado com sucesso!")
    print("  Diga 'Jarvis' para ativar após reiniciar.")
    print("  Ou clique em 'Jarvis.bat' na área de trabalho.")
    print("="*50)
    input("\nPressione Enter para fechar...")


if __name__ == "__main__":
    main()
