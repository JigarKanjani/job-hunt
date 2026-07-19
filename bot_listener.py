#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot_listener.py — Telegram command listener for manual job hunt triggers.
Polls the bot for incoming DMs and triggers job_alert.py based on message content.

How to use:
  DM your Telegram bot with profile names (case-insensitive):
    "J"        → run J only
    "N J"      → run N and J
    "ALL"      → run all 4 profiles
    "R G"      → run R and G

Profiles: J (Supply Chain/Data), N (Admin/Social), R (IT Analyst), G (General Admin)
Run via GitHub Actions every 5 minutes so it stays responsive.
"""

import os, sys, json, subprocess, urllib.request
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE      = Path(__file__).parent
OFFSET_FILE    = WORKSPACE / ".bot_listener_offset"
BOT_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "")
VALID_PROFILES = {"J", "N", "R", "G"}
SCRIPT         = WORKSPACE / "job_alert.py"


def tg_get_updates(offset=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=5"
    if offset is not None:
        url += f"&offset={offset}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[getUpdates error] {e}")
        return None


def tg_send(chat_id, text):
    payload = json.dumps({"chat_id": str(chat_id), "text": text,
                          "disable_web_page_preview": True}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        print(f"[send error] {e}")


def parse_profiles(text):
    """Return list of valid profiles from message text. 'ALL' → all 4."""
    words = text.upper().split()
    if "ALL" in words:
        return sorted(VALID_PROFILES)
    found = [w for w in words if w in VALID_PROFILES]
    return found


def load_offset():
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text().strip())
        except Exception:
            pass
    return None


def save_offset(offset):
    OFFSET_FILE.write_text(str(offset))


def main():
    if not BOT_TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN env var not set.")
        sys.exit(1)

    offset = load_offset()
    data = tg_get_updates(offset)
    if not data or not data.get("ok"):
        print("[WARN] Could not reach Telegram getUpdates")
        return

    updates = data.get("result", [])
    if not updates:
        return

    new_offset = offset
    for update in updates:
        update_id = update["update_id"]
        new_offset = update_id + 1

        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue

        text    = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]

        if not text:
            continue

        profiles = parse_profiles(text)
        if not profiles:
            tg_send(chat_id,
                    "Send profile names to trigger a manual run:\n"
                    "  ALL  |  J  |  N  |  R  |  G\n"
                    "Example: J N\n\n"
                    "J = Supply Chain/Data\n"
                    "N = Admin/Social\n"
                    "R = IT Analyst\n"
                    "G = General Admin")
            save_offset(new_offset)
            continue

        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
        print(f"[{ts}] Manual trigger received: {profiles}")
        tg_send(chat_id,
                f"👍 On it! Working on {', '.join(profiles)} now.\n"
                f"⏳ Give me ~30 minutes — I'll drop the job postings here as soon as they're ready.")

        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--hours", "24", "--profiles"] + profiles,
            cwd=str(WORKSPACE)
        )

        if result.returncode != 0:
            tg_send(chat_id,
                    f"⚠️ Run finished with errors for: {', '.join(profiles)}\n"
                    "Check the console output for details.")

    save_offset(new_offset)


if __name__ == "__main__":
    main()
