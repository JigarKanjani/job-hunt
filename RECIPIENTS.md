# Telegram Recipients — Setup Guide

This job hunt sends alerts to Telegram. Every recipient is identified by a
numeric **chat ID**. You can now add as many accounts as you like by
comma-separating their chat IDs in a single GitHub secret.

---

## 1. Create the bot (one-time, only if you don't have one yet)

You only need **one** bot for everything — all recipients receive messages
from the same bot.

1. In Telegram, open a chat with **@BotFather**.
2. Send `/newbot`.
3. Give it a display name (e.g. `Job Hunt Alerts`).
4. Give it a username ending in `bot` (e.g. `calgary_jobhunt_bot`).
5. BotFather replies with a **token** that looks like
   `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
6. Put that token in the repo secret **`TELEGRAM_BOT_TOKEN`**
   (Settings → Secrets and variables → Actions → New repository secret).

> Keep the token private — anyone with it can send messages as your bot.

---

## 2. Get a recipient's chat ID

⚠️ **Telegram rule:** a bot cannot message someone who has never messaged the
bot first. Each new recipient must start the conversation.

**For a person (1:1 DM):**

1. The new person opens Telegram, searches for **your bot's username**, opens
   it, and taps **Start** (or sends any message).
2. In a browser, open:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   (replace `<YOUR_BOT_TOKEN>` with the real token)
3. In the JSON, find:
   ```json
   "chat": { "id": 123456789, "first_name": "...", ... }
   ```
   The `"id"` number is their chat ID.

   *If the result is empty, have them send the message again and refresh —
   updates expire after ~24h and are also consumed by the `bot_listener` poller.*

**Even simpler:** have the person DM **@userinfobot** in Telegram. It instantly
replies with their numeric ID, which is the same as their 1:1 chat ID.

**For a group chat:**

1. Add your bot to the group and send any message in the group.
2. Open the `getUpdates` URL as above.
3. The group's `"chat":{"id": ...}` is a **negative** number (e.g. `-1001234567890`).
   Use it exactly as shown, minus sign included.

---

## 3. Add the recipient

All recipient secrets accept **comma-separated** chat IDs, so a single secret
can hold multiple accounts.

| Secret | Who receives what |
|---|---|
| `TELEGRAM_CHAT_ID` | default / fallback recipient |
| `TELEGRAM_CHAT_ID_J` | jobs for profile **J** (Supply Chain / Data) |
| `TELEGRAM_CHAT_ID_N` | jobs for profile **N** (Admin / Social) |
| `TELEGRAM_CHAT_ID_R` | jobs for profile **R** (IT Analyst) |
| `TELEGRAM_CHAT_ID_G` | jobs for profile **G** (General Admin) |
| `TELEGRAM_CHAT_ID_BROADCAST` | receives **all** jobs from **all** profiles + the run summary |

**To add another account that gets everything**, edit the
`TELEGRAM_CHAT_ID_BROADCAST` secret and comma-separate:

```
747174717,123456789,-1001234567890
```

**To add someone to just one profile**, do the same on that profile's secret,
e.g. `TELEGRAM_CHAT_ID_R`:

```
111111111,222222222
```

Steps to edit a secret:
Repo → **Settings → Secrets and variables → Actions** → click the secret →
**Update** → paste the comma-separated value → **Save**.

Changes take effect on the next scheduled run (every 2 hours) or when you
manually trigger the **Job Hunt** workflow from the Actions tab.

---

## Notes

- A recipient in the `BROADCAST` list who is *also* a profile recipient won't
  get duplicate copies of the same job.
- Whitespace around commas is ignored, so
  `111, 222 , 333` is fine.
- Removing a recipient is just editing the secret and deleting their ID.
