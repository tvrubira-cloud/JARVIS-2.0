"""
memory_manager_v2.py — Sistema de memória persistente avançado
Substitui memory/memory_manager.py do projeto original.

Melhorias:
- Memória por categorias com timestamps
- Busca semântica simples por palavras-chave
- Histórico de conversas resumido
- Contexto de sessão (preferências temporárias)
- Exportação/importação de memória
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from copy import deepcopy


MEMORY_DIR = Path(__file__).parent
MEMORY_FILE = MEMORY_DIR / "memory.json"
HISTORY_FILE = MEMORY_DIR / "conversation_history.json"

# Schema padrão de memória
DEFAULT_MEMORY = {
    "identity": {},       # nome, idade, cidade, idioma, profissão
    "preferences": {},    # comida, cor, música, jogos, hobbies
    "projects": {},       # projetos ativos, metas
    "relationships": {},  # amigos, família, parceiro
    "wishes": {},         # planos futuros, compras desejadas
    "notes": {},          # hábitos, horários, qualquer outra coisa
    "routines": {},       # rotinas diárias, horários fixos
    "devices": {},        # dispositivos, configurações do PC
    "_meta": {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "version": "2.0"
    }
}


# ─── I/O básico ──────────────────────────────────────────────────────────────

def load_memory() -> dict:
    if not MEMORY_FILE.exists():
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        save_memory(DEFAULT_MEMORY)
        return deepcopy(DEFAULT_MEMORY)
    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        # Garante que todas as categorias existam
        for cat in DEFAULT_MEMORY:
            if cat not in data:
                data[cat] = {}
        return data
    except Exception:
        return deepcopy(DEFAULT_MEMORY)


def save_memory(memory: dict) -> None:
    memory.setdefault("_meta", {})
    memory["_meta"]["last_updated"] = datetime.now().isoformat()
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")


def update_memory(updates: dict) -> None:
    """
    Atualiza campos específicos. updates pode ser:
    {"identity": {"name": {"value": "João", "updated_at": "..."}}}
    ou o formato legado: {"identity": {"name": "João"}}
    """
    mem = load_memory()
    now = datetime.now().isoformat()

    for category, fields in updates.items():
        if category.startswith("_"):
            continue
        if category not in mem:
            mem[category] = {}
        if isinstance(fields, dict):
            for key, val in fields.items():
                if isinstance(val, dict) and "value" in val:
                    mem[category][key] = val
                else:
                    # Formato legado: converte para novo formato
                    mem[category][key] = {"value": val, "updated_at": now}

    save_memory(mem)


# ─── formatação para prompt ──────────────────────────────────────────────────

def format_memory_for_prompt(memory: dict) -> str:
    """Gera bloco de contexto para o system prompt."""
    sections = []
    label_map = {
        "identity":      "IDENTIDADE DO USUÁRIO",
        "preferences":   "PREFERÊNCIAS",
        "projects":      "PROJETOS & METAS",
        "relationships": "PESSOAS IMPORTANTES",
        "wishes":        "DESEJOS & PLANOS",
        "routines":      "ROTINAS",
        "devices":       "DISPOSITIVOS & CONFIGS",
        "notes":         "ANOTAÇÕES DIVERSAS",
    }

    for cat, label in label_map.items():
        fields = memory.get(cat, {})
        if not fields:
            continue
        lines = []
        for key, val in fields.items():
            if isinstance(val, dict):
                v = val.get("value", "")
                ts = val.get("updated_at", "")
                ts_str = f" (atualizado: {ts[:10]})" if ts else ""
                lines.append(f"  • {key}: {v}{ts_str}")
            else:
                lines.append(f"  • {key}: {val}")
        if lines:
            sections.append(f"[{label}]\n" + "\n".join(lines))

    if not sections:
        return ""

    return (
        "[MEMÓRIA PERSISTENTE DO USUÁRIO — use estas informações naturalmente]\n"
        + "\n\n".join(sections)
        + "\n"
    )


# ─── busca na memória ────────────────────────────────────────────────────────

def search_memory(query: str) -> str:
    """Busca na memória por palavras-chave."""
    mem = load_memory()
    query_lower = query.lower()
    results = []

    for cat, fields in mem.items():
        if cat.startswith("_") or not isinstance(fields, dict):
            continue
        for key, val in fields.items():
            v = val.get("value", str(val)) if isinstance(val, dict) else str(val)
            if query_lower in key.lower() or query_lower in v.lower():
                results.append(f"{cat}/{key}: {v}")

    if not results:
        return f"Nada encontrado na memória para '{query}'."
    return "Encontrado:\n" + "\n".join(results)


def delete_memory_entry(category: str, key: str) -> str:
    mem = load_memory()
    if category in mem and key in mem[category]:
        del mem[category][key]
        save_memory(mem)
        return f"Entrada '{category}/{key}' removida da memória."
    return f"Entrada '{category}/{key}' não encontrada."


def clear_category(category: str) -> str:
    mem = load_memory()
    if category in mem:
        mem[category] = {}
        save_memory(mem)
        return f"Categoria '{category}' apagada."
    return f"Categoria '{category}' não existe."


def get_memory_summary() -> str:
    mem = load_memory()
    total = sum(len(v) for k, v in mem.items() if not k.startswith("_") and isinstance(v, dict))
    last = mem.get("_meta", {}).get("last_updated", "desconhecido")
    cats = {k: len(v) for k, v in mem.items() if not k.startswith("_") and isinstance(v, dict) and v}
    cat_str = ", ".join(f"{k}({n})" for k, n in cats.items())
    return f"Memória: {total} entradas | Última atualização: {last[:16]} | Categorias: {cat_str}"


def export_memory(path: str = "") -> str:
    mem = load_memory()
    out = Path(path) if path else Path.home() / "Desktop" / "antigravity_memory_backup.json"
    out.write_text(json.dumps(mem, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"Memória exportada para: {out}"


def import_memory(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return f"Arquivo não encontrado: {path}"
    data = json.loads(p.read_text(encoding="utf-8"))
    save_memory(data)
    return f"Memória importada de: {path}"


# ─── histórico de conversa resumido ──────────────────────────────────────────

def save_conversation_turn(user: str, assistant: str) -> None:
    """Salva um turno de conversa no histórico (limita a 100 últimos)."""
    if not HISTORY_FILE.exists():
        history = []
    else:
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append({
        "timestamp": datetime.now().isoformat(),
        "user": user[:500],
        "assistant": assistant[:500]
    })
    history = history[-100:]  # mantém os 100 últimos
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def get_recent_history(n: int = 10) -> str:
    if not HISTORY_FILE.exists():
        return "Sem histórico."
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return "Erro ao ler histórico."
    recent = history[-n:]
    lines = []
    for turn in recent:
        ts = turn.get("timestamp", "")[:16]
        lines.append(f"[{ts}] Você: {turn.get('user','')}\n       Assistente: {turn.get('assistant','')}")
    return "\n\n".join(lines) if lines else "Sem histórico."


# ─── dispatcher para ferramenta ──────────────────────────────────────────────

def memory_manager_action(parameters: dict, player=None) -> str:
    action = parameters.get("action", "summary")

    if action == "search":
        return search_memory(parameters.get("query", ""))
    elif action == "delete":
        return delete_memory_entry(parameters.get("category", ""), parameters.get("key", ""))
    elif action == "clear_category":
        return clear_category(parameters.get("category", ""))
    elif action == "summary":
        return get_memory_summary()
    elif action == "export":
        return export_memory(parameters.get("path", ""))
    elif action == "import":
        return import_memory(parameters.get("path", ""))
    elif action == "history":
        return get_recent_history(int(parameters.get("count", 10)))
    elif action == "save":
        update_memory({
            parameters.get("category", "notes"): {
                parameters.get("key", ""): parameters.get("value", "")
            }
        })
        return f"Memória salva: {parameters.get('category')}/{parameters.get('key')}"
    else:
        return f"Ação desconhecida: '{action}'. Use: search | delete | summary | export | import | history | save"
