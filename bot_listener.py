#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bot_listener.py — Telegram command listener for manual job hunt triggers.
Polls the bot for incoming DMs and triggers job_alert.py based on message content.

How to use:
  DM your Telegram bot with profile names (case-insensitive):
    "JIGAR"          → run JIGAR only
    "NEELAM JIGAR"   → run NEELAM and JIGAR
    "ALL"            → run all 4 profiles
    "XYZ ABC"        → run XYZ and ABC

Run via OpenClaw cron every 2 minutes so it stays responsive.
"""

import os, sys, json, subprocess, urllib.request
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE      = Path(__file__).parent
OFFSET_FILE    = WORKSPACE / ".bot_listener_offset"
BOT_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "")
VALID_PROFILES = {"JIGAR", "NEELAM", "XYZ", "ABC"}
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
        # Try reading from job_alert.py env fallback path isn't needed —
        # just require the env var to be set.
        print("[ERROR] TELEGRAM_BOT_TOKEN env var not set. "
              "Set it in your shell or OpenClaw environment.")
        sys.exit(1)

    offset = load_offset()
    data = tg_get_updates(offset)
    if not data or not data.get("ok"):
        print("[WARN] Could not reach Telegram getUpdates")
        return

    updates = data.get("result", [])
    if not updates:
        return  # Nothing new

    new_offset = offset
    for update in updates:
        update_id = update["update_id"]
        new_offset = update_id + 1  # Advance past this update

        # Support both direct messages and group messages
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue

        text    = (msg.get("text") or "").strip()
        chat_id = msg["chat"]["id"]

        if not text:
            continue

        profiles = parse_profiles(text)
        if not profiles:
            # Unrecognised message — send help hint
            tg_send(chat_id,
                    "Send profile names to trigger a manual run:\n"
                    "  ALL  |  JIGAR  |  NEELAM  |  XYZ  |  ABC\n"
                    "Example: JIGAR NEELAM")
            save_offset(new_offset)
            continue

        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
        print(f"[{ts}] Manual trigger received: {profiles}")
        tg_send(chat_id,
                f"🔄 Manual run started — {', '.join(profiles)}\n"
                f"⏳ This takes up to 10 minutes, you'll get the results shortly.")

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
