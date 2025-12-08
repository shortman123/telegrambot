# Telegram Confession Bot

This is a Telegram bot that collects anonymous confessions with admin moderation. Users send confessions, admin reviews them, and can approve/reject for posting to a channel. Features include commenting system, safety guidelines, feedback, and reporting tools for a safe community experience.

## Channel Setup

To integrate with your Telegram channel:

1. **Create a channel** or use existing one
2. **Add your bot as admin**:
   - Go to channel settings
   - Add member: Search for your bot username
   - Give admin rights with "Post messages" permission
3. **Set CHANNEL_ID** in `.env`:
   - For public channels: `@channelname`
   - For private channels: The numeric ID (get from @userinfobot by forwarding a message)

The bot will post approved confessions to your channel anonymously!

## Running the Bot

**Linux/Mac:**
```bash
python3 bot.py
```

**Windows:**
```cmd
python bot.py
```
or
```cmd
py bot.py
```

The bot will automatically:
- Install required packages
- Prompt for missing credentials (BOT_TOKEN, CHANNEL_ID, ADMIN_ID)
- Start running and listening for messages

## 24/7 Operation

**Linux/Mac:**
```bash
screen -S confession_bot -d -m python3 bot.py
```

**Windows:**
For persistent running on Windows, you have several options:

1. **Using NSSM (Non-Sucking Service Manager) - Recommended:**
   - Download NSSM from https://nssm.cc/
   - Install as service: `nssm install ConfessionBot "python" "bot.py"`
   - Start service: `nssm start ConfessionBot`

2. **Using Windows Task Scheduler:**
   - Create a task that runs on startup
   - Action: Start a program -> `python.exe` with argument `bot.py`

3. **Using PowerShell (background job):**
   ```powershell
   Start-Job -ScriptBlock { python bot.py } -Name ConfessionBot
   ```

4. **Cloud Hosting (Recommended for always-online):**
   Use Railway, Render, or Heroku as described below.

## User Interface

Users interact with **inline buttons** for a smooth experience:

- 📝 **Send Confession** - Start the confession process
- 💬 **Comment** - Learn how to comment on confessions
- ℹ️ **About Bot** - Learn about the bot
- 🛡️ **Safety** - Safety and privacy guidelines
- ❓ **Help** - Usage instructions
- 📞 **Feedback** - Send feedback or suggestions
- ⬅️ **Back to Menu** - Return to main menu anytime

**User Commands:**
- `/start` - Main menu
- `/menu` - Quick access menu
- `/comment <id> <text>` - Comment on confessions anonymously
- `/feedback <message>` - Send feedback
- `/report <id> <reason>` - Report inappropriate content
- `/safety` - Safety and privacy info

**Navigation**: You can use `/start` or `/menu` at any time to return to the main menu!

## Admin Commands

As the bot admin, you can manage confessions:

- `/pending` - 📋 View all pending confessions
- `/approve <id>` - ✅ Approve and post confession to channel
- `/reject <id>` - ❌ Reject confession
- `/help` - ❓ Show admin help

**Inline Buttons**: When a new confession arrives, you'll get notification with ✅ Approve, ❌ Reject, and ✏️ Edit buttons for quick action!

## Keeping Your Bot Running 24/7

**Linux/Mac:**
```bash
# Start in background with screen
screen -S confession_bot -d -m python3 bot.py

# Check if running
screen -ls

# Reattach to manage
screen -r confession_bot

# Detach: Ctrl+A, D
```

**Windows:**
```cmd
# Using NSSM service
nssm install ConfessionBot "python" "bot.py"
nssm start ConfessionBot

# Check status
nssm status ConfessionBot

# Stop service
nssm stop ConfessionBot
```

Your bot will now run 24/7 with emojis and a friendly UI! 🎉

## Manual Setup (Alternative)

## Hosting Your Bot (So You Don't Have to Run It Locally)

Since you want the bot "hosted" like other bots, here are free/cheap options to deploy it online:

### Option 1: Railway (Recommended - Free Tier)

⚠ Railway will NOT run your bot unless:

✔ You have a requirements.txt
✔ You have a Procfile or start.sh

1. Go to [railway.app](https://railway.app) and sign up.
2. Connect your GitHub repo or upload the code.
3. Set environment variables in Railway dashboard.
4. Deploy - it gives you a URL.
5. Set `WEBHOOK_URL` to `https://your-railway-url.up.railway.app/webhook`

### Option 2: Render
1. Go to [render.com](https://render.com) and create account.
2. Create a new Web Service from your Git repo.
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python bot.py`
5. Add environment variables.
6. Deploy.

### Option 3: Heroku
1. Sign up at [heroku.com](https://heroku.com).
2. Create a new app.
3. Connect GitHub repo.
4. Set config vars (environment variables).
5. Deploy.

### For All Options:
- Use webhook mode by setting `WEBHOOK_URL` in your `.env`.
- Your bot will run 24/7 on their servers.
- Free tiers have limits, but enough for a small bot.

This way, your bot is "hosted" by these services, not running on your local machine forever.

## How it works

- Users start the bot with /start
- Send text messages, which are forwarded anonymously to the channel.# telegrambot
# telegrambot
# telegrambot
