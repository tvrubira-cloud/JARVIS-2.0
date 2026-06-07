"""
pc_control_advanced.py  — Controle avançado do PC para Windows
Integração: adicione ao seu actions/ e registre em TOOL_DECLARATIONS no main.py
"""

import subprocess
import psutil
import os
import json
import ctypes
import winreg
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


# ─── helpers ────────────────────────────────────────────────────────────────

def _run(cmd: list, capture=True) -> str:
    try:
        r = subprocess.run(cmd, capture_output=capture, text=True, timeout=15)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)


def _powershell(script: str) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=20
        )
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)


# ─── ações ──────────────────────────────────────────────────────────────────

def list_processes(filter_name: Optional[str] = None) -> str:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]):
        try:
            name = p.info["name"] or ""
            if filter_name and filter_name.lower() not in name.lower():
                continue
            mem_mb = round(p.info["memory_info"].rss / 1024 / 1024, 1)
            procs.append(f"{p.info['pid']:6}  {name[:30]:30}  {mem_mb:7.1f} MB  {p.info['status']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if not procs:
        return "Nenhum processo encontrado."
    header = f"{'PID':>6}  {'Nome':<30}  {'Memória':>9}  Status\n" + "-" * 65
    return header + "\n" + "\n".join(procs[:50])


def kill_process(name_or_pid: str) -> str:
    killed = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            match = (name_or_pid.isdigit() and p.pid == int(name_or_pid)) or \
                    (not name_or_pid.isdigit() and name_or_pid.lower() in (p.info["name"] or "").lower())
            if match:
                p.terminate()
                killed.append(p.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return f"Encerrado: {', '.join(killed)}" if killed else f"Processo '{name_or_pid}' não encontrado."


def system_info() -> str:
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    boot = datetime.fromtimestamp(psutil.boot_time()).strftime("%d/%m/%Y %H:%M")
    battery = psutil.sensors_battery()
    bat_str = f"{battery.percent:.0f}% {'(carregando)' if battery.power_plugged else '(bateria)'}" if battery else "N/A"

    return (
        f"CPU: {cpu}%  |  Núcleos: {psutil.cpu_count()}\n"
        f"RAM: {ram.used/1e9:.1f}/{ram.total/1e9:.1f} GB  ({ram.percent}% usado)\n"
        f"Disco C: {disk.used/1e9:.1f}/{disk.total/1e9:.1f} GB  ({disk.percent}% usado)\n"
        f"Bateria: {bat_str}\n"
        f"Ligado desde: {boot}"
    )


def list_startup_programs() -> str:
    result = _powershell(
        "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | "
        "Format-Table -AutoSize | Out-String"
    )
    return result or "Sem programas de inicialização encontrados."


def manage_startup(action: str, name: str) -> str:
    """enable/disable programa na inicialização via registro."""
    key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    if action == "disable":
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as k:
                winreg.DeleteValue(k, name)
            return f"'{name}' removido da inicialização."
        except FileNotFoundError:
            return f"'{name}' não encontrado na inicialização."
        except Exception as e:
            return str(e)
    return "Ação não suportada. Use 'disable'."


def scheduled_tasks(action: str = "list", task_name: str = "", command: str = "",
                    trigger_time: str = "") -> str:
    if action == "list":
        return _powershell(
            "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | "
            "Select-Object TaskName, State | Format-Table -AutoSize | Out-String"
        )
    elif action == "run" and task_name:
        return _powershell(f'Start-ScheduledTask -TaskName "{task_name}"') or f"Tarefa '{task_name}' iniciada."
    elif action == "stop" and task_name:
        return _powershell(f'Stop-ScheduledTask -TaskName "{task_name}"') or f"Tarefa '{task_name}' parada."
    elif action == "create" and task_name and command and trigger_time:
        # trigger_time no formato HH:MM diário
        script = (
            f'$action = New-ScheduledTaskAction -Execute "{command}"; '
            f'$trigger = New-ScheduledTaskTrigger -Daily -At "{trigger_time}"; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $action -Trigger $trigger -Force'
        )
        return _powershell(script)
    elif action == "delete" and task_name:
        return _powershell(f'Unregister-ScheduledTask -TaskName "{task_name}" -Confirm:$false')
    return "Parâmetros inválidos."


def network_info() -> str:
    connections = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.status == "ESTABLISHED" and conn.raddr:
            try:
                p = psutil.Process(conn.pid)
                connections.append(f"{p.name():<25} {conn.laddr.ip}:{conn.laddr.port} → {conn.raddr.ip}:{conn.raddr.port}")
            except Exception:
                pass
    io = psutil.net_io_counters()
    stats = (
        f"Enviado: {io.bytes_sent/1e6:.1f} MB  |  Recebido: {io.bytes_recv/1e6:.1f} MB\n"
        f"Conexões ativas ({len(connections)}):\n"
    )
    return stats + "\n".join(connections[:20]) if connections else stats + "Nenhuma."


def clipboard_action(action: str, text: str = "") -> str:
    if action == "read":
        return _powershell("Get-Clipboard")
    elif action == "write" and text:
        _powershell(f'Set-Clipboard -Value "{text}"')
        return "Área de transferência atualizada."
    elif action == "clear":
        _powershell("Set-Clipboard -Value $null")
        return "Área de transferência limpa."
    return "Ação inválida."


def window_manager(action: str, title: str = "") -> str:
    """Gerencia janelas abertas via PowerShell."""
    if action == "list":
        return _powershell(
            "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
            "Select-Object Id, ProcessName, MainWindowTitle | Format-Table -AutoSize | Out-String"
        )
    elif action == "minimize" and title:
        script = (
            f'$hwnd = (Get-Process | Where-Object {{$_.MainWindowTitle -like "*{title}*"}}).MainWindowHandle; '
            f'[void][System.Runtime.InteropServices.Marshal]::GetLastWin32Error(); '
            f'Add-Type -TypeDefinition "using System;using System.Runtime.InteropServices;'
            f'public class W{{[DllImport(\\"user32.dll\\")]public static extern bool ShowWindow(IntPtr h,int n);}}" -PassThru | Out-Null; '
            f'[W]::ShowWindow($hwnd, 6)'
        )
        _powershell(script)
        return f"Janela '{title}' minimizada."
    elif action == "maximize" and title:
        script = (
            f'$p = Get-Process | Where-Object {{$_.MainWindowTitle -like "*{title}*"}} | Select-Object -First 1; '
            f'if($p){{$p.MainWindowHandle | ForEach-Object{{ '
            f'Add-Type -A System.Windows.Forms; [System.Windows.Forms.Application]::DoEvents() }}}}'
        )
        # Alternativa simples via appactivate
        _powershell(f'(New-Object -ComObject WScript.Shell).AppActivate("{title}")')
        return f"Janela '{title}' ativada."
    elif action == "close" and title:
        _powershell(f'Get-Process | Where-Object {{$_.MainWindowTitle -like "*{title}*"}} | Stop-Process')
        return f"Janela '{title}' fechada."
    return "Ação/parâmetros inválidos."


def run_as_admin(command: str) -> str:
    """Executa comando como administrador (abre UAC prompt)."""
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f'/c "{command}"', None, 1)
        return f"Comando enviado como administrador: {command}"
    except Exception as e:
        return str(e)


def environment_variable(action: str, name: str = "", value: str = "") -> str:
    if action == "get" and name:
        return os.environ.get(name, f"Variável '{name}' não encontrada.")
    elif action == "set" and name and value:
        _powershell(f'[System.Environment]::SetEnvironmentVariable("{name}", "{value}", "User")')
        return f"Variável '{name}' definida como '{value}'."
    elif action == "list":
        lines = [f"{k}={v}" for k, v in os.environ.items()]
        return "\n".join(lines[:40])
    return "Parâmetros inválidos."


def disk_cleanup(drive: str = "C") -> str:
    _powershell(f"cleanmgr /d {drive}: /sagerun:1")
    return f"Limpeza de disco iniciada em {drive}:."


def get_installed_apps() -> str:
    script = (
        "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
        "| Select-Object DisplayName, DisplayVersion, Publisher "
        "| Where-Object {$_.DisplayName -ne $null} "
        "| Sort-Object DisplayName "
        "| Format-Table -AutoSize | Out-String"
    )
    return _powershell(script)


# ─── dispatcher principal ────────────────────────────────────────────────────

def pc_control_advanced(parameters: dict, player=None) -> str:
    action = parameters.get("action", "")

    dispatch = {
        "list_processes":      lambda: list_processes(parameters.get("filter")),
        "kill_process":        lambda: kill_process(parameters.get("target", "")),
        "system_info":         system_info,
        "list_startup":        list_startup_programs,
        "manage_startup":      lambda: manage_startup(parameters.get("startup_action", "disable"), parameters.get("name", "")),
        "scheduled_tasks":     lambda: scheduled_tasks(
                                    parameters.get("task_action", "list"),
                                    parameters.get("task_name", ""),
                                    parameters.get("command", ""),
                                    parameters.get("trigger_time", "")),
        "network_info":        network_info,
        "clipboard":           lambda: clipboard_action(parameters.get("clipboard_action", "read"), parameters.get("text", "")),
        "window_manager":      lambda: window_manager(parameters.get("window_action", "list"), parameters.get("title", "")),
        "run_as_admin":        lambda: run_as_admin(parameters.get("command", "")),
        "env_variable":        lambda: environment_variable(parameters.get("env_action", "list"), parameters.get("name", ""), parameters.get("value", "")),
        "disk_cleanup":        lambda: disk_cleanup(parameters.get("drive", "C")),
        "installed_apps":      get_installed_apps,
    }

    fn = dispatch.get(action)
    if fn:
        result = fn()
        if player:
            player.write_log(f"PC: {result[:200]}")
        return result
    return f"Ação desconhecida: '{action}'. Opções: {', '.join(dispatch.keys())}"
