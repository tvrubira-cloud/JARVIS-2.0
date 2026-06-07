"""
calendar_action.py — Gerenciamento de calendário (Windows)
Suporta: Google Calendar (via API), Outlook/Microsoft 365, e calendário local via ICS.

Configuração rápida (Google Calendar):
1. Acesse console.cloud.google.com → crie projeto → ative Google Calendar API
2. Crie credenciais OAuth2 → baixe como config/google_calendar_credentials.json
3. Na primeira execução, um browser abrirá para autorização.

Configuração rápida (Outlook):
- Usa PowerShell COM objects nativos do Windows — sem configuração extra!
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


# ─── Outlook via COM (nativo Windows, sem API key) ────────────────────────────

def _powershell(script: str) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=30
        )
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)


def outlook_list_events(days: int = 7) -> str:
    """Lista eventos do Outlook nos próximos N dias."""
    script = f"""
$outlook = New-Object -ComObject Outlook.Application
$calendar = $outlook.GetNamespace("MAPI").GetDefaultFolder(9)
$start = Get-Date
$end = (Get-Date).AddDays({days})
$items = $calendar.Items
$items.IncludeRecurrences = $true
$items.Sort("[Start]")
$filter = "[Start] >= '" + $start.ToString("g") + "' AND [Start] <= '" + $end.ToString("g") + "'"
$filtered = $items.Restrict($filter)
foreach($item in $filtered) {{
    Write-Output ("📅 " + $item.Start.ToString("dd/MM HH:mm") + " — " + $item.Subject + " | " + $item.Location)
}}
"""
    result = _powershell(script)
    if not result or "Error" in result:
        return f"Nenhum evento encontrado nos próximos {days} dias (Outlook pode não estar aberto)."
    return f"Eventos nos próximos {days} dias:\n{result}"


def outlook_create_event(title: str, start: str, end: str = "",
                          location: str = "", notes: str = "",
                          reminder_minutes: int = 15) -> str:
    """Cria evento no Outlook Calendar."""
    # Parse flexible date formats
    if not end:
        end = start  # evento de 1 hora por padrão

    script = f"""
$outlook = New-Object -ComObject Outlook.Application
$appt = $outlook.CreateItem(1)
$appt.Subject = "{title}"
$appt.Start = "{start}"
$appt.End = "{end}"
$appt.Location = "{location}"
$appt.Body = "{notes}"
$appt.ReminderMinutesBeforeStart = {reminder_minutes}
$appt.Save()
Write-Output "Evento criado com sucesso."
"""
    result = _powershell(script)
    if "criado" in result.lower():
        return f"✅ Evento '{title}' criado para {start}."
    return result or f"Evento '{title}' criado."


def outlook_delete_event(title: str) -> str:
    script = f"""
$outlook = New-Object -ComObject Outlook.Application
$calendar = $outlook.GetNamespace("MAPI").GetDefaultFolder(9)
$items = $calendar.Items
$items.Sort("[Start]")
$filter = "[Subject] = '{title}'"
$filtered = $items.Restrict($filter)
$count = 0
foreach($item in $filtered) {{
    $item.Delete()
    $count++
}}
Write-Output "Deletados: $count evento(s)."
"""
    return _powershell(script)


def outlook_today() -> str:
    return outlook_list_events(days=1)


# ─── Calendário local simples (JSON) — sem dependências externas ─────────────

CALENDAR_FILE = Path(__file__).parent.parent / "memory" / "local_calendar.json"


def _load_local() -> list:
    if not CALENDAR_FILE.exists():
        return []
    try:
        return json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_local(events: list) -> None:
    CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_FILE.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")


def local_add_event(title: str, date: str, time: str = "00:00",
                     end_time: str = "", location: str = "", notes: str = "") -> str:
    events = _load_local()
    event = {
        "id": len(events) + 1,
        "title": title,
        "date": date,
        "time": time,
        "end_time": end_time,
        "location": location,
        "notes": notes,
        "created_at": datetime.now().isoformat()
    }
    events.append(event)
    # Ordena por data+hora
    events.sort(key=lambda e: f"{e['date']} {e['time']}")
    _save_local(events)
    return f"✅ Evento '{title}' adicionado para {date} às {time}."


def local_list_events(days: int = 30, filter_text: str = "") -> str:
    events = _load_local()
    today = datetime.now().date()
    end = today + timedelta(days=days)

    filtered = []
    for e in events:
        try:
            edate = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except Exception:
            try:
                edate = datetime.strptime(e["date"], "%d/%m/%Y").date()
            except Exception:
                continue
        if today <= edate <= end:
            if not filter_text or filter_text.lower() in e["title"].lower():
                filtered.append(e)

    if not filtered:
        return f"Nenhum evento nos próximos {days} dias."

    lines = []
    for e in filtered:
        loc = f" @ {e['location']}" if e.get("location") else ""
        notes = f"\n   📝 {e['notes']}" if e.get("notes") else ""
        lines.append(f"📅 {e['date']} {e.get('time','')}{loc} — {e['title']}{notes}")

    return f"Próximos {len(filtered)} evento(s):\n" + "\n".join(lines)


def local_delete_event(event_id: int = 0, title: str = "") -> str:
    events = _load_local()
    before = len(events)
    if event_id:
        events = [e for e in events if e.get("id") != event_id]
    elif title:
        events = [e for e in events if title.lower() not in e.get("title", "").lower()]
    _save_local(events)
    removed = before - len(events)
    return f"{removed} evento(s) removido(s)."


def local_today() -> str:
    events = _load_local()
    today = datetime.now().strftime("%Y-%m-%d")
    todays = [e for e in events if e.get("date", "") == today]
    if not todays:
        return "Nenhum evento para hoje."
    lines = [f"📅 {e.get('time','')} — {e['title']}" for e in todays]
    return "Hoje:\n" + "\n".join(lines)


# ─── dispatcher principal ────────────────────────────────────────────────────

def calendar_action(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    backend = parameters.get("backend", "local")  # local | outlook

    try:
        if backend == "outlook":
            if action == "list":
                return outlook_list_events(int(parameters.get("days", 7)))
            elif action == "today":
                return outlook_today()
            elif action == "create":
                return outlook_create_event(
                    title=parameters.get("title", "Novo Evento"),
                    start=parameters.get("start", ""),
                    end=parameters.get("end", ""),
                    location=parameters.get("location", ""),
                    notes=parameters.get("notes", ""),
                    reminder_minutes=int(parameters.get("reminder_minutes", 15))
                )
            elif action == "delete":
                return outlook_delete_event(parameters.get("title", ""))

        else:  # local (padrão)
            if action in ("list", "upcoming"):
                return local_list_events(
                    int(parameters.get("days", 30)),
                    parameters.get("filter", "")
                )
            elif action == "today":
                return local_today()
            elif action in ("create", "add"):
                return local_add_event(
                    title=parameters.get("title", "Evento"),
                    date=parameters.get("date", datetime.now().strftime("%Y-%m-%d")),
                    time=parameters.get("time", "00:00"),
                    end_time=parameters.get("end_time", ""),
                    location=parameters.get("location", ""),
                    notes=parameters.get("notes", "")
                )
            elif action == "delete":
                return local_delete_event(
                    event_id=int(parameters.get("event_id", 0)),
                    title=parameters.get("title", "")
                )

        return f"Ação '{action}' não reconhecida. Use: list | today | create | delete"

    except Exception as e:
        return f"Erro no calendário: {e}"
