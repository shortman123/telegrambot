import asyncio

# Auto-install requirements if missing
try:
    from telegram import Update
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "-r", "requirements.txt"])
    print("Packages installed. Please run the script again.")
    sys.exit(0)

import os
import json
from telegram import error as telegram_error
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from flask import Flask, request

BOT_TOKEN = '8579160095:AAH2e1Y0i3ZOUBfyY96jS2hcOUHn7Dtc_i8'
CHANNEL_ID = '-1003491562982'
ADMIN_ID = '6017750801'
BOT_USERNAME = 'HopeConfessions_bot'  # Your bot's username without @
WEBHOOK_URL = None

app = Flask(__name__)
application = None

PENDING_FILE = 'pending_confessions.json'
APPROVED_FILE = 'approved_confessions.json'
COMMENTS_FILE = 'comments.json'

# Global state for admin editing
editing_confession_id = None

# Conversation states
ASK_CONFESSION = 1
ASK_COMMENT = 2
MAIN_MENU = 0

def load_pending():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, 'r') as f:
            return json.load(f)
    return []

def save_pending(pending):
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending, f, indent=2)

def load_approved():
    if os.path.exists(APPROVED_FILE):
        with open(APPROVED_FILE, 'r') as f:
            return json.load(f)
    return []

def save_approved(approved):
    with open(APPROVED_FILE, 'w') as f:
        json.dump(approved, f, indent=2)

def load_comments():
    if os.path.exists(COMMENTS_FILE):
        with open(COMMENTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_comments(comments):
    with open(COMMENTS_FILE, 'w') as f:
        json.dump(comments, f, indent=2)

def get_next_confession_id():
    """Get the next sequential confession ID (no gaps)."""
    pending = load_pending()
    approved = load_approved()
    
    # Find the highest ID used so far
    max_pending_id = max([conf.get('id', 0) for conf in pending], default=0)
    max_approved_id = max([conf.get('id', 0) for conf in approved], default=0)
    
    # Return the next sequential ID
    return max(max_pending_id, max_approved_id) + 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle deep link for commenting
    if context.args and len(context.args) > 0 and context.args[0].startswith('comment_'):
        try:
            conf_id = int(context.args[0].split('_')[1])
            # Check if confession exists
            approved = load_approved()
            if any(conf['id'] == conf_id for conf in approved):
                await update.message.reply_text(
                    f'💬 **Comment on Confession #{conf_id:03d}** 💬\n\n'
                    'Please reply to this message with your anonymous comment.\n\n'
                    'Example: This really helped me too!\n\n'
                    'Your comment will be reviewed before posting.',
                    reply_markup=ReplyKeyboardRemove()
                )
                # Set user state for comment
                context.user_data['comment_conf_id'] = conf_id
                return ASK_COMMENT  # Need to define this state
            else:
                await update.message.reply_text('❓ Confession not found.')
                return
        except:
            await update.message.reply_text('❓ Invalid comment link.')
            return
    
    keyboard = [
        [InlineKeyboardButton("📝 Send Confession", callback_data='send_confession'),
         InlineKeyboardButton("💬 Comment", callback_data='comment_help')],
        [InlineKeyboardButton("ℹ️ About Bot", callback_data='about'),
         InlineKeyboardButton("🛡️ Safety", callback_data='safety')],
        [InlineKeyboardButton("❓ Help", callback_data='help_user'),
         InlineKeyboardButton("📞 Feedback", callback_data='feedback')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    intro_text = """
🤖 **Welcome to the Anonymous Confession Bot!** 🙏

📝 Share your thoughts anonymously - they're reviewed before posting.
💬 Comment on confessions to support others.
🛡️ Your safety and privacy are our top priority.

**Choose what to do:**
"""
    await update.message.reply_text(intro_text, reply_markup=reply_markup)
    return MAIN_MENU

async def receive_confession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    confession = {
        'id': get_next_confession_id(),
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code,
        'text': update.message.text,
        'timestamp': str(update.message.date)
    }
    pending = load_pending()
    pending.append(confession)
    save_pending(pending)
    
    await update.message.reply_text('✅ **Thank you for sharing!** 🙏\n\nYour confession has been received safely. It will be reviewed by the admin before being shared anonymously.\n\nYou can send another confession anytime or use /start for more options. 💌')
    
    # Notify admin with more user intel and buttons
    if ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f'approve_{confession["id"]}'),
             InlineKeyboardButton("❌ Reject", callback_data=f'reject_{confession["id"]}')],
            [InlineKeyboardButton("✏️ Edit", callback_data=f'edit_{confession["id"]}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        user_info = f'👤 {user.first_name or "Unknown"}'
        if user.last_name:
            user_info += f' {user.last_name}'
        if user.username:
            user_info += f' (@{user.username})'
        user_info += f'\n🆔 {user.id}'
        if user.language_code:
            user_info += f'\n🌐 {user.language_code.upper()}'
        
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text=f'📝 **New Confession #{confession["id"]:03d}** 📝\n\n{user_info}\n\n💌 **Confession:**\n{update.message.text}',
            reply_markup=reply_markup
        )
    return ConversationHandler.END

async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conf_id = context.user_data.get('comment_conf_id')
    if not conf_id:
        await update.message.reply_text('❓ No active comment session. Use /start to begin.')
        return ConversationHandler.END
    
    comment_text = update.message.text.strip()
    if not comment_text:
        await update.message.reply_text('📝 Please provide a comment. Try again or use /start to cancel.')
        return ASK_COMMENT
    
    # Check if confession exists
    approved = load_approved()
    if not any(conf['id'] == conf_id for conf in approved):
        await update.message.reply_text('❓ Confession not found.')
        return ConversationHandler.END
    
    # Save comment
    comments = load_comments()
    comment_id = len(comments) + 1
    comments.append({
        'id': comment_id,
        'conf_id': conf_id,
        'user_id': update.message.from_user.id,
        'text': comment_text,
        'approved': False,
        'timestamp': update.message.date.isoformat()
    })
    save_comments(comments)
    
    await update.message.reply_text('✅ Your comment has been submitted anonymously and is pending approval. 🙏')
    
    # Notify admin
    await context.bot.send_message(chat_id=ADMIN_ID, text=f'💬 **New Comment on Confession #{conf_id:03d}** 💬\n\n💭 **Comment:** {comment_text[:100]}...\n\n✅ Approve with `/approve_comment {comment_id}`\n❌ Reject with `/reject_comment {comment_id}`')
    
    # Notify the confession sender
    conf = next((c for c in approved if c['id'] == conf_id), None)
    if conf and 'user_id' in conf:
        try:
            await context.bot.send_message(
                chat_id=conf['user_id'],
                text=f'💬 **Someone commented on your confession!** 💬\n\nYour anonymous confession #{conf_id:03d} received a new comment:\n\n💭 "{comment_text}"\n\n*Comment is pending admin approval and will appear in the channel once approved.*'
            )
        except:
            pass
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ Unauthorized access!')
        return
    
    pending = load_pending()
    if not pending:
        await update.message.reply_text('📭 No pending confessions. 🎉')
        return
    
    text = "📋 **Pending Confessions** 📋\n\n"
    for conf in pending[:10]:  # Show first 10
        text += f"🌟 **Confession #{conf['id']:03d}** 🌟\n📝 {conf['text'][:50]}...\n\n"
    text += "✅ /approve <id>  ❌ /reject <id>"
    await update.message.reply_text(text)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ Unauthorized!')
        return
    
    try:
        conf_id = int(context.args[0])
    except:
        await update.message.reply_text('📝 Usage: /approve <id>')
        return
    
    pending = load_pending()
    for i, conf in enumerate(pending):
        if conf['id'] == conf_id:
            # Post to channel
            if CHANNEL_ID:
                message = await context.bot.send_message(chat_id=CHANNEL_ID, text=f'🎭 **Anonymous Confession #{conf_id:03d}** 🎭\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📖 **Story:**\n{conf["text"]}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n💭 **Share Your Thoughts:**\n💬 [Comment](https://t.me/{BOT_USERNAME}?start=comment_{conf_id})\n\n🌟 **Help others feel less alone!**\n\n#Confession #{conf_id} #Anonymous #Support #Community')
                message_id = message.message_id
                # Save to approved
                approved = load_approved()
                approved.append({
                    'id': conf_id,
                    'text': conf['text'],
                    'user_id': conf['user_id'],
                    'message_id': message_id,
                    'timestamp': conf.get('timestamp', None)
                })
                save_approved(approved)
            # Remove from pending
            pending.pop(i)
            save_pending(pending)
            await update.message.reply_text(f'✅ Confession #{conf_id} approved and posted! 📢')
            return
    
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ Unauthorized!')
        return
    
    try:
        conf_id = int(context.args[0])
    except:
        await update.message.reply_text('📝 Usage: /reject <id>')
        return
    
    pending = load_pending()
    for i, conf in enumerate(pending):
        if conf['id'] == conf_id:
            pending.pop(i)
            save_pending(pending)
            await update.message.reply_text(f'❌ Confession #{conf_id} rejected and removed. 🗑️')
            return
    
    await update.message.reply_text('❓ Confession not found.')

async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conf_id = int(context.args[0])
        comment_text = ' '.join(context.args[1:])
        if not comment_text:
            await update.message.reply_text('📝 Usage: /comment <confession_id> <your_comment>')
            return
    except:
        await update.message.reply_text('📝 Usage: /comment <confession_id> <your_comment>')
        return
    
    # Check if confession exists
    approved = load_approved()
    if not any(conf['id'] == conf_id for conf in approved):
        await update.message.reply_text('❓ Confession not found.')
        return
    
    # Save comment
    comments = load_comments()
    comment_id = len(comments) + 1
    comments.append({
        'id': comment_id,
        'conf_id': conf_id,
        'user_id': update.message.from_user.id,
        'text': comment_text,
        'approved': False,
        'timestamp': update.message.date.isoformat()
    })
    save_comments(comments)
    
    await update.message.reply_text('✅ Your comment has been submitted anonymously and is pending approval. 🙏')
    
    # Notify admin
    await context.bot.send_message(chat_id=ADMIN_ID, text=f'💬 **New Comment on Confession #{conf_id:03d}** 💬\n\n💭 **Comment:** {comment_text[:100]}...\n\n✅ Approve with `/approve_comment {comment_id}`\n❌ Reject with `/reject_comment {comment_id}`')
    
    # Notify the confession sender
    approved = load_approved()
    conf = next((c for c in approved if c['id'] == conf_id), None)
    if conf and 'user_id' in conf:
        try:
            await context.bot.send_message(
                chat_id=conf['user_id'],
                text=f'💬 **Someone commented on your confession!** 💬\n\nYour anonymous confession #{conf_id:03d} received a new comment:\n\n💭 "{comment_text}"\n\n*Comment is pending admin approval and will appear in the channel once approved.*'
            )
        except:
            # User might have blocked the bot or something
            pass

async def view_comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ Unauthorized!')
        return
    
    try:
        conf_id = int(context.args[0])
    except:
        await update.message.reply_text('📝 Usage: /view_comments <confession_id>')
        return
    
    comments = load_comments()
    pending_comments = [c for c in comments if c['conf_id'] == conf_id and not c['approved']]
    
    if not pending_comments:
        await update.message.reply_text(f'📭 No pending comments for confession #{conf_id}.')
        return
    
    text = f"💬 **Pending Comments for Confession #{conf_id:03d}** 💬\n\n"
    for c in pending_comments[:10]:
        text += f"💭 **Comment #{c['id']}** 💭\n📝 {c['text']}\n\n"
    text += "✅ /approve_comment <id>  ❌ /reject_comment <id>"
    await update.message.reply_text(text)

async def approve_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ Unauthorized!')
        return
    
    try:
        comment_id = int(context.args[0])
    except:
        await update.message.reply_text('📝 Usage: /approve_comment <comment_id>')
        return
    
    comments = load_comments()
    approved = load_approved()
    
    for i, c in enumerate(comments):
        if c['id'] == comment_id and not c['approved']:
            # Find the confession message_id
            conf = next((conf for conf in approved if conf['id'] == c['conf_id']), None)
            if conf:
                # Post as reply to the channel message
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=f'💭 **Anonymous Comment** 💭\n\n📝 {c["text"]}\n\n#Comment #{comment_id}',
                    reply_to_message_id=conf['message_id']
                )
                c['approved'] = True
                save_comments(comments)
                
                # Notify the commenter
                try:
                    await context.bot.send_message(
                        chat_id=c['user_id'],
                        text=f'🎉 **Your comment has been approved!** 🎉\n\nYour anonymous comment on confession #{c["conf_id"]:03d} is now live in the channel:\n\n💭 "{c["text"]}"\n\nThank you for contributing to the community! 🙏'
                    )
                except:
                    pass
                
                await update.message.reply_text(f'✅ Comment #{comment_id} approved and posted as reply! 📢')
                return
    
    await update.message.reply_text('❓ Comment not found or already approved.')

async def reject_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ Unauthorized!')
        return
    
    try:
        comment_id = int(context.args[0])
    except:
        await update.message.reply_text('📝 Usage: /reject_comment <comment_id>')
        return
    
    comments = load_comments()
    for i, c in enumerate(comments):
        if c['id'] == comment_id and not c['approved']:
            comments.pop(i)
            save_comments(comments)
            await update.message.reply_text(f'❌ Comment #{comment_id} rejected and removed. 🗑️')
            return
    
    await update.message.reply_text('❓ Comment not found.')

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Send Confession", callback_data='send_confession'),
         InlineKeyboardButton("💬 Comment", callback_data='comment_help')],
        [InlineKeyboardButton("ℹ️ About Bot", callback_data='about'),
         InlineKeyboardButton("🛡️ Safety", callback_data='safety')],
        [InlineKeyboardButton("❓ Help", callback_data='help_user'),
         InlineKeyboardButton("📞 Feedback", callback_data='feedback')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    menu_text = """
🤖 **Main Menu** 🤖

**Choose what to do:**
"""
    await update.message.reply_text(menu_text, reply_markup=reply_markup)

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feedback_text = ' '.join(context.args)
    if not feedback_text:
        await update.message.reply_text('📝 Usage: /feedback <your_message>')
        return
    
    # Save feedback
    feedback_data = {
        'user_id': update.message.from_user.id,
        'username': update.message.from_user.username,
        'text': feedback_text,
        'timestamp': update.message.date.isoformat()
    }
    
    # For now, just notify admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f'📞 **New Feedback** 📞\n\n👤 {update.message.from_user.first_name}\n💬 {feedback_text}'
    )
    
    await update.message.reply_text('🎉 **Thank you for your feedback!** 🙏\n\n💌 We\'ve received your message and will review it carefully.\n\n🌟 Your input helps us improve the bot for everyone!\n\n📞 For urgent matters, contact the admin directly.')

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conf_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
        if not reason:
            await update.message.reply_text('📝 Usage: /report <confession_id> <reason>')
            return
    except:
        await update.message.reply_text('📝 Usage: /report <confession_id> <reason>')
        return
    
    # Check if confession exists
    approved = load_approved()
    if not any(conf['id'] == conf_id for conf in approved):
        await update.message.reply_text('❓ Confession not found.')
        return
    
    # Notify admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f'🚨 **Report Received** 🚨\n\nConfession #{conf_id:03d}\n👤 Reporter: {update.message.from_user.first_name}\n📝 Reason: {reason}'
    )
    
    await update.message.reply_text('✅ Report submitted. Thank you for helping keep the community safe! 🛡️')

async def safety(update: Update, context: ContextTypes.DEFAULT_TYPE):
    safety_text = """
🛡️ **Safety & Privacy Guidelines** 🛡️

Your safety is our 🌟 top priority! We protect your anonymity and well-being.

🔒 **Privacy Protection:**
• 🙈 All confessions are completely anonymous
• 🚫 No personal information is ever shared
• 👀 Admin reviews all content before posting

🚫 **What We Don't Allow:**
• 😡 Harmful, abusive, or threatening content
• 👊 Personal attacks or harassment
• ⚖️ Illegal activities or promotion of harm
• 📢 Spam, scams, or inappropriate content

📞 **If You Need Help:**
• 🚨 Use `/report <id> <reason>` to report inappropriate content
• 👨‍💼 Contact admin for urgent safety concerns
• 💬 Use `/feedback` to suggest improvements

💙 **Remember:** This is a safe space for positive, supportive sharing. 🌈

Stay safe and be kind! 🙏
"""
    await update.message.reply_text(safety_text)

async def intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ This command is for admins only!')
        return
    
    help_text = """
🤖 Confession Bot Admin Commands:

📋 /pending - View all pending confessions
✅ /approve <id> - Approve and post confession
❌ /reject <id> - Reject confession
❓ /help - Show this help

Example: /approve 1
"""
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        return  # Not admin, ignore
    
    global editing_confession_id
    if editing_confession_id:
        # This is the edited confession
        pending = load_pending()
        for conf in pending:
            if conf['id'] == editing_confession_id:
                old_text = conf['text']
                conf['text'] = update.message.text
                
                # Get user info
                user_info = f'👤 {conf.get("first_name", "Unknown")}'
                if conf.get('last_name'):
                    user_info += f' {conf["last_name"]}'
                if conf.get('username'):
                    user_info += f' (@{conf["username"]})'
                user_info += f'\n🆔 {conf["user_id"]}'
                if conf.get('language_code'):
                    user_info += f'\n🌐 {conf["language_code"].upper()}'
                
                save_pending(pending)
                
                # Show updated confession with buttons
                keyboard = [
                    [InlineKeyboardButton("✅ Approve", callback_data=f'approve_{conf["id"]}'),
                     InlineKeyboardButton("❌ Reject", callback_data=f'reject_{conf["id"]}')],
                    [InlineKeyboardButton("✏️ Edit Again", callback_data=f'edit_{conf["id"]}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f'✅ Confession #{editing_confession_id} updated!\n\n'
                    f'📝 **Old:** "{old_text}"\n'
                    f'📝 **New:** "{update.message.text}"\n\n'
                    f'👤 **From:** {user_info}\n\n'
                    f'💌 **Final confession:**\n"{update.message.text}"',
                    reply_markup=reply_markup
                )
                editing_confession_id = None
                return
        await update.message.reply_text('❓ Confession not found for editing.')
        editing_confession_id = None

async def help_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ This command is for admins only!')
        return
    
    help_text = """
🤖 Confession Bot Admin Commands:

📋 /pending - View all pending confessions
✅ /approve <id> - Approve and post confession
❌ /reject <id> - Reject confession
💬 /view_comments <id> - View pending comments for a confession
✅ /approve_comment <id> - Approve and post comment as reply
❌ /reject_comment <id> - Reject comment
✏️ Edit button - Edit confession text
❓ /help - Show this help

Example: /approve 1
"""
    await update.message.reply_text(help_text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'send_confession':
        keyboard = [[InlineKeyboardButton("⬅️ Go Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            '🙏 **Write your confession below** 📝\n\n'
            'Type your anonymous message and send it to me.\n'
            'I\'ll keep it completely private and show it to the admin for review.\n\n'
            '💡 **Examples:**\n'
            '• "I\'ve been keeping a secret from my friends"\n'
            '• "I regret not saying sorry when I had the chance"\n'
            '• "I\'m proud of overcoming my fear"\n\n'
            '✨ Your confession will help others feel less alone.\n\n'
            'Or go back to menu:',
            reply_markup=reply_markup
        )
        return ASK_CONFESSION
    elif query.data == 'about':
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        about_text = """
🤖 **About This Bot**

This is an anonymous confession sharing platform where:
• 📝 You can share thoughts without revealing identity
• 🔒 Privacy is protected - admin reviews before posting
• ✅ Only approved confessions appear publicly
• 💌 Safe space for honest expression

Made with ❤️ for positive anonymous sharing.
"""
        await query.edit_message_text(about_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'help_user':
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        help_text = """
❓ **How to Use**

1. 📝 Click "Send Confession" to share
2. ✍️ Type your message
3. ✅ Your confession is reviewed
4. 📢 If approved, it appears anonymously

**Available Commands:**
/start - Main menu
/menu - Quick access menu
/comment <id> <text> - Comment on confessions
/feedback <message> - Send feedback
/report <id> <reason> - Report inappropriate content
/safety - Safety and privacy info
"""
        await query.edit_message_text(help_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'comment_help':
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        comment_help_text = """
💬 **How to Comment on Confessions** 💬

Want to share your 💭 thoughts and support others? Here's how!

1. 📢 **Find a Confession:** Look for confessions posted in the channel
2. 🔢 **Note the Number:** Each confession has a number like #001
3. 💬 **Send Your Comment:** Use `/comment 001 Your supportive comment here`

✨ **What happens next:**
• 🙈 Your comment stays anonymous
• 👀 Admin reviews it for safety
• ✅ If approved, it appears as a reply below the confession

🌟 **Comments help build a supportive community!**

Remember: Be kind, respectful, and supportive! 🙏
"""
        await query.edit_message_text(comment_help_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'safety':
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        safety_text = """
🛡️ **Safety & Privacy Guidelines** 🛡️

Your safety is our 🌟 top priority! We protect your anonymity and well-being.

🔒 **Privacy Protection:**
• 🙈 All confessions are completely anonymous
• 🚫 No personal information is ever shared
• 👀 Admin reviews all content before posting

🚫 **What We Don't Allow:**
• 😡 Harmful, abusive, or threatening content
• 👊 Personal attacks or harassment
• ⚖️ Illegal activities or promotion of harm
• 📢 Spam, scams, or inappropriate content

📞 **If You Need Help:**
• 🚨 Use `/report <id> <reason>` to report inappropriate content
• 👨‍💼 Contact admin for urgent safety concerns
• 💬 Use `/feedback` to suggest improvements

💙 **Remember:** This is a safe space for positive, supportive sharing. 🌈

Stay safe and be kind! 🙏
"""
        await query.edit_message_text(safety_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'feedback':
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        feedback_text = """
📞 **Feedback & Support** 📞

We 💖 your input! Your feedback helps us grow! 🌱

**💬 Send us feedback:**
`/feedback <your_message>`

**🚨 Report issues:**
`/report <confession_id> <reason>`

**📧 Contact Admin:**
For urgent matters, message the bot admin directly.

**🙏 Thank you for helping us improve!**
"""
        await query.edit_message_text(feedback_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("📝 Send Confession", callback_data='send_confession'),
             InlineKeyboardButton("💬 Comment", callback_data='comment_help')],
            [InlineKeyboardButton("ℹ️ About Bot", callback_data='about'),
             InlineKeyboardButton("🛡️ Safety", callback_data='safety')],
            [InlineKeyboardButton("❓ Help", callback_data='help_user'),
             InlineKeyboardButton("📞 Feedback", callback_data='feedback')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        menu_text = """
🤖 **Welcome back!** 🙏

**Choose what to do:**
"""
        await query.edit_message_text(menu_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data.startswith('approve_') or query.data.startswith('reject_') or query.data.startswith('edit_'):
        # Admin actions
        if str(query.from_user.id) != ADMIN_ID:
            await query.edit_message_text('❌ Unauthorized!')
            return
        
        parts = query.data.split('_')
        action = parts[0]
        conf_id = int(parts[1])
        
        pending = load_pending()
        for i, conf in enumerate(pending):
            if conf['id'] == conf_id:
                if action == 'approve':
                    if CHANNEL_ID:
                        message = await context.bot.send_message(chat_id=CHANNEL_ID, text=f'🎭 **Anonymous Confession #{conf_id:03d}** 🎭\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📖 **Story:**\n{conf["text"]}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n💭 **Share Your Thoughts:**\n💬 [Comment](https://t.me/{BOT_USERNAME}?start=comment_{conf_id})\n\n🌟 **Help others feel less alone!**\n\n#Confession #{conf_id} #Anonymous #Support #Community')
                        message_id = message.message_id
                        # Save to approved
                        approved = load_approved()
                        approved.append({
                            'id': conf_id,
                            'text': conf['text'],
                            'user_id': conf['user_id'],
                            'message_id': message_id,
                            'timestamp': conf.get('timestamp', None)
                        })
                        save_approved(approved)
                    pending.pop(i)
                    save_pending(pending)
                    await query.edit_message_text(f'✅ Confession #{conf_id} approved and posted! 📢')
                elif action == 'reject':
                    pending.pop(i)
                    save_pending(pending)
                    await query.edit_message_text(f'❌ Confession #{conf_id} rejected and removed. 🗑️')
                elif action == 'edit':
                    global editing_confession_id
                    editing_confession_id = conf_id
                    await query.edit_message_text(f'✏️ Editing confession #{conf_id}.\n\nCurrent text: "{conf["text"]}"\n\nReply with the corrected confession:')
                return
        
        await query.edit_message_text('❓ Confession not found.')

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return 'OK'

def setup_credentials():
    """Check if credentials are set (hardcoded)."""
    if BOT_TOKEN and CHANNEL_ID and ADMIN_ID:
        return True
    else:
        print("Credentials not properly set. Please check the hardcoded values.")
        return False

async def main():
    global application
    if not setup_credentials():
        return
    
    try:
        # Create application with custom request settings for better connectivity
        from telegram.request import HTTPXRequest
        
        # Check for proxy settings
        proxy_url = os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
        if proxy_url:
            print(f"🔗 Using proxy: {proxy_url}")
            request = HTTPXRequest(
                connection_pool_size=20,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=10,
                pool_timeout=10,
                proxy_url=proxy_url
            )
        else:
            request = HTTPXRequest(
                connection_pool_size=20,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=10,
                pool_timeout=10
            )
        
        application = Application.builder().token(BOT_TOKEN).request(request).build()
        await application.initialize()
        print("✅ Bot initialized successfully!")
    except telegram_error.TimedOut:
        print("❌ Connection timeout! Please check your internet connection and try again.")
        print("💡 If you're behind a firewall, you may need to configure proxy settings.")
        return
    except telegram_error.InvalidToken:
        print("❌ Invalid bot token! Please check your BOT_TOKEN in the code.")
        return
    except Exception as e:
        print(f"❌ Failed to initialize bot: {e}")
        return
    # Conversation handler for confessions
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(button_callback),
                CommandHandler('start', start)  # Allow restart
            ],
            ASK_CONFESSION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_confession),
                CommandHandler('start', start)  # Allow restart
            ],
            ASK_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_comment),
                CommandHandler('start', start)  # Allow restart
            ],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('pending', pending))
    application.add_handler(CommandHandler('approve', approve))
    application.add_handler(CommandHandler('reject', reject))
    application.add_handler(CommandHandler('comment', comment))
    application.add_handler(CommandHandler('view_comments', view_comments))
    application.add_handler(CommandHandler('approve_comment', approve_comment))
    application.add_handler(CommandHandler('reject_comment', reject_comment))
    application.add_handler(CommandHandler('help', help_admin))
    application.add_handler(CommandHandler('intro', intro))
    application.add_handler(CommandHandler('menu', menu))
    application.add_handler(CommandHandler('feedback', feedback))
    application.add_handler(CommandHandler('report', report))
    application.add_handler(CommandHandler('safety', safety))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    
    if WEBHOOK_URL:
        # Webhook mode
        await application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get('PORT', 5000)),
            url_path="webhook",
            webhook_url=WEBHOOK_URL
        )
    else:
        # Polling mode
        await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())