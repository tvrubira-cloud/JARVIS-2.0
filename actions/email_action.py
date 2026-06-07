"""
email_action.py — Envio e leitura de emails (Gmail / Outlook / qualquer SMTP+IMAP)
Configuração: preencha config/email_config.json  (veja EMAIL_CONFIG_EXAMPLE abaixo)

EMAIL_CONFIG_EXAMPLE  (salve em  config/email_config.json):
{
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "imap_host": "imap.gmail.com",
    "imap_port": 993,
    "username": "seuemail@gmail.com",
    "password": "sua_senha_de_app",  ← Gmail: crie em myaccount.google.com/apppasswords
    "display_name": "Seu Nome"
}

Para Outlook use:
    smtp_host: smtp.office365.com / smtp_port: 587
    imap_host: outlook.office365.com / imap_port: 993
"""

import smtplib
import imaplib
import email as email_lib
import json
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from pathlib import Path
from typing import Optional
from datetime import datetime


CONFIG_PATH = Path(__file__).parent.parent / "config" / "email_config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {CONFIG_PATH}\n"
            "Crie o arquivo com suas credenciais de email."
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def send_email(to: str, subject: str, body: str,
               cc: str = "", attachment_path: str = "") -> str:
    cfg = _load_config()
    msg = MIMEMultipart()
    msg["From"] = f"{cfg.get('display_name', cfg['username'])} <{cfg['username']}>"
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={Path(attachment_path).name}")
        msg.attach(part)

    recipients = [to] + ([cc] if cc else [])

    with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
        server.starttls()
        server.login(cfg["username"], cfg["password"])
        server.sendmail(cfg["username"], recipients, msg.as_string())

    return f"Email enviado para {to} com assunto '{subject}'."


def read_emails(folder: str = "INBOX", count: int = 10,
                unread_only: bool = False, search_query: str = "") -> str:
    cfg = _load_config()

    with imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"]) as imap:
        imap.login(cfg["username"], cfg["password"])
        imap.select(folder)

        if search_query:
            criteria = f'SUBJECT "{search_query}"'
        elif unread_only:
            criteria = "UNSEEN"
        else:
            criteria = "ALL"

        _, msg_nums = imap.search(None, criteria)
        ids = msg_nums[0].split()
        ids = ids[-count:]  # últimos N

        if not ids:
            return "Nenhum email encontrado."

        results = []
        for num in reversed(ids):
            _, data = imap.fetch(num, "(RFC822)")
            raw = data[0][1]
            msg = email_lib.message_from_bytes(raw)

            subject = _decode_header_value(msg.get("Subject", "(sem assunto)"))
            sender = _decode_header_value(msg.get("From", ""))
            date = msg.get("Date", "")

            # Extrai texto
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

            body_preview = body[:300].replace("\n", " ").strip()
            results.append(f"De: {sender}\nAssunto: {subject}\nData: {date}\n{body_preview}\n{'─'*60}")

        return "\n".join(results)


def reply_email(original_message_id: str, reply_body: str) -> str:
    """Responde ao email mais recente que corresponde ao subject/sender fornecido."""
    # Simplificado: busca e responde ao último email de um remetente
    cfg = _load_config()
    with imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"]) as imap:
        imap.login(cfg["username"], cfg["password"])
        imap.select("INBOX")
        _, data = imap.fetch(original_message_id, "(RFC822)")
        raw = data[0][1]
        orig = email_lib.message_from_bytes(raw)

    sender = orig.get("Reply-To") or orig.get("From")
    subject = "Re: " + _decode_header_value(orig.get("Subject", ""))
    return send_email(to=sender, subject=subject, body=reply_body)


def get_email_stats() -> str:
    cfg = _load_config()
    with imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"]) as imap:
        imap.login(cfg["username"], cfg["password"])
        imap.select("INBOX")
        _, unread = imap.search(None, "UNSEEN")
        _, total = imap.search(None, "ALL")
        unread_count = len(unread[0].split()) if unread[0] else 0
        total_count = len(total[0].split()) if total[0] else 0
    return f"Caixa de entrada: {total_count} emails | Não lidos: {unread_count}"


# ─── dispatcher ──────────────────────────────────────────────────────────────

def email_action(parameters: dict, player=None) -> str:
    action = parameters.get("action", "read")

    try:
        if action == "send":
            return send_email(
                to=parameters.get("to", ""),
                subject=parameters.get("subject", "(sem assunto)"),
                body=parameters.get("body", ""),
                cc=parameters.get("cc", ""),
                attachment_path=parameters.get("attachment", "")
            )
        elif action == "read":
            return read_emails(
                folder=parameters.get("folder", "INBOX"),
                count=int(parameters.get("count", 10)),
                unread_only=parameters.get("unread_only", False),
                search_query=parameters.get("search", "")
            )
        elif action == "stats":
            return get_email_stats()
        else:
            return f"Ação desconhecida: '{action}'. Use: send | read | stats"
    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        return f"Erro no email: {e}"
