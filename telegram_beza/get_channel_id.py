#!/usr/bin/env python3
"""
Script to help get the correct Telegram channel ID.
Run this script and follow the instructions.
"""

import asyncio
import sys
import os

# Check if we're in the virtual environment
venv_python = os.path.join(os.path.dirname(__file__), 'beza', 'bin', 'python3')
if sys.executable != venv_python and os.path.exists(venv_python):
    print("❌ Please run with virtual environment:")
    print(f"   {venv_python} get_channel_id.py")
    sys.exit(1)

try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError:
    print("❌ Telegram library not found. Please install requirements:")
    print("   pip install -r requirements.txt")
    sys.exit(1)

# Your bot token - update this!
BOT_TOKEN = '8579160095:AAH2e1Y0i3ZOUBfyY96jS2hcOUHn7Dtc_i8'

async def get_channel_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded messages to extract channel info"""
    if update.message.forward_from_chat:
        chat = update.message.forward_from_chat
        await update.message.reply_text(
            f"📺 **Channel Information:**\n\n"
            f"**Name:** {chat.title or 'Unknown'}\n"
            f"**Username:** @{chat.username or 'No username'}\n"
            f"**ID:** `{chat.id}`\n\n"
            f"Use this ID in your bot code:\n"
            f"`CHANNEL_ID = '{chat.id}'`"
        )
    else:
        await update.message.reply_text(
            "❌ Please forward a message from your channel.\n\n"
            "**Steps:**\n"
            "1. Go to your Telegram channel\n"
            "2. Copy any message\n"
            "3. Come back here and paste it\n"
            "4. I'll extract the channel ID for you!"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Channel ID Helper Bot**\n\n"
        "Forward any message from your channel to get its ID.\n\n"
        "**Instructions:**\n"
        "1. Go to your channel\n"
        "2. Copy a message\n"
        "3. Forward it to me\n"
        "4. I'll give you the channel ID to use in your bot!"
    )

async def main():
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN':
        print("❌ Please update BOT_TOKEN in this script first!")
        return
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        await application.initialize()
        print("✅ Bot initialized! Send /start to your bot to begin.")
        
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(None, get_channel_info))
        
        await application.start()
        await application.updater.start_polling()
        print("✅ Helper bot is running! Forward a message from your channel to get its ID.")
        print("Press Ctrl+C to stop.")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping helper bot...")
            await application.updater.stop()
            await application.stop()
            print("✅ Helper bot stopped.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    try:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.run(main())
    except ImportError:
        print("❌ nest_asyncio not found. Install it: pip install nest_asyncio")
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
