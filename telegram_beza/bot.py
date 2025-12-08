import asyncio
import sys
import subprocess
import os

# Check if we're in the virtual environment
venv_python = os.path.join(os.path.dirname(__file__), 'beza', 'bin', 'python3')
if sys.executable != venv_python and os.path.exists(venv_python):
    print("❌ Please run the bot with the virtual environment:")
    print(f"   {venv_python} bot.py")
    print("   Or activate it first: source beza/bin/activate")
    sys.exit(1)

try:
    from telegram import Update
except ImportError:
    print("❌ Telegram library not found. Please install requirements:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram import error as telegram_error
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from flask import Flask, request

BOT_TOKEN = '8579160095:AAH2e1Y0i3ZOUBfyY96jS2hcOUHn7Dtc_i8'
CHANNEL_ID = '-1003491562982'
ADMIN_ID = '6017750801'
BOT_USERNAME = 'Hopeconfession2_bot'  # Your bot's username without @
WEBHOOK_URL = None

app = Flask(__name__)
application = None

PENDING_FILE = 'pending_confessions.json'
APPROVED_FILE = 'approved_confessions.json'
COMMENTS_FILE = 'comments.json'
CONTACTS_FILE = 'contacts.json'

# Global state for admin editing
editing_confession_id = None

# Conversation states
ASK_CONFESSION = 1
ASK_COMMENT = 2
FEEDBACK_STATE = 3
CONTACT_STATE = 4
ADMIN_REPLY_STATE = 5
MAIN_MENU = 0

def load_pending():
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_pending(pending):
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending, f, indent=2)

def load_approved():
    if os.path.exists(APPROVED_FILE):
        try:
            with open(APPROVED_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # File exists but is empty or corrupted, return empty list
            return []
    return []

def save_approved(approved):
    with open(APPROVED_FILE, 'w') as f:
        json.dump(approved, f, indent=2)

def load_comments():
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_comments(comments):
    with open(COMMENTS_FILE, 'w') as f:
        json.dump(comments, f, indent=2)

def load_contacts():
    if os.path.exists(CONTACTS_FILE):
        try:
            with open(CONTACTS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_contacts(contacts):
    with open(CONTACTS_FILE, 'w') as f:
        json.dump(contacts, f, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"User ID: {update.message.from_user.id}")
    # Handle deep link for commenting
    if context.args and len(context.args) > 0 and context.args[0].startswith('comment_'):
        try:
            conf_id = int(context.args[0].split('_')[1])
            # Check if confession exists
            approved = load_approved()
            if any(conf['id'] == conf_id for conf in approved):
                await update.message.reply_text(
                    f'💬 Comment on Confession #{conf_id:03d} 💬\n\n'
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
        [InlineKeyboardButton("📝 Share My Story", callback_data='send_confession'),
         InlineKeyboardButton("💬 Support Others", callback_data='comment_help')],
        [InlineKeyboardButton("🌟 About Our Community", callback_data='about'),
         InlineKeyboardButton("🛡️ Safety First", callback_data='safety')],
        [InlineKeyboardButton("❓ How It Works", callback_data='help_user')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    intro_text = """
🎭 Welcome to Hope Confessions 🎭

✨ A Safe Space for Your Heart ✨

💝 Share anonymously, heal together, grow stronger

🌈 Why people choose us:
• 🙈 100% Anonymous - Your identity stays private
• 👥 Supportive Community - Connect with understanding hearts  
• 🛡️ Safe Environment - All content is carefully reviewed
• 💪 Empowerment - Your story can inspire others

📊 Join 1000+ people who've found courage here

🎯 Ready to begin your journey?
"""
    await update.message.reply_text(intro_text, reply_markup=reply_markup)
    return MAIN_MENU

async def receive_confession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    confession = {
        'id': len(load_pending()) + 1,
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
    
    keyboard = [[InlineKeyboardButton("🏠 Return to Menu", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Thank You for Trusting Us 🙏✨\n\n'
        'Your courage is beautiful 💝\n\n'
        'Your story is now in safe hands\n'
        '👀 Our compassionate admin will read it with care\n'
        '📢 When approved, it will touch hearts anonymously\n\n'
        'You\'ve taken a powerful step - healing begins here 🌱\n\n'
        'Want to share another chapter? Send another message anytime\n'
        'Need to return? Click the button below\n\n'
        'Remember: You\'re stronger than you know 💪❤️\n\n'
        'Your vulnerability inspires hope in others 🌈',
        reply_markup=reply_markup
    )
    
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
            text=f'📝 New Confession #{confession["id"]:03d} 📝\n\n{user_info}\n\n💌 Confession:\n{update.message.text}',
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
    
    await update.message.reply_text(
        '💬 **Thank You for Your Kindness!** 💬\n\n'
        '🙏 **Your supportive comment has been received**\n\n'
        '👀 Our admin will review it carefully\n'
        '📢 Once approved, it will appear as a reply to help others\n\n'
        '🌟 **Your empathy makes our community stronger**\n\n'
        '💝 **Want to support more stories?** Visit our channel anytime\n\n'
        '**Thank you for being part of the healing** ✨',
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Notify admin
    keyboard = [
        [InlineKeyboardButton("✅ Approve Comment", callback_data=f'approve_comment_{comment_id}'),
         InlineKeyboardButton("❌ Reject Comment", callback_data=f'reject_comment_{comment_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=ADMIN_ID, 
        text=f'💬 **New Comment on Confession #{conf_id:03d}** 💬\n\n💭 **Comment:**\n{comment_text}\n\n👤 **Comment ID:** {comment_id}',
        reply_markup=reply_markup
    )
    
    # Notify the confession sender
    conf = next((c for c in approved if c['id'] == conf_id), None)
    if conf and 'user_id' in conf:
        try:
            await context.bot.send_message(
                chat_id=conf['user_id'],
                text=f'💬 Someone commented on your confession! 💬\n\nYour anonymous confession #{conf_id:03d} received a new comment:\n\n💭 "{comment_text}"\n\nComment is pending admin approval and will appear in the channel once approved.'
            )
        except:
            pass
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def receive_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_feedback'):
        await update.message.reply_text('❓ No active feedback session. Use the menu to send feedback.')
        return ConversationHandler.END
    
    feedback_text = update.message.text.strip()
    if not feedback_text:
        await update.message.reply_text('📝 Please provide feedback. Try again or use /start to cancel.')
        return FEEDBACK_STATE
    
    # Save feedback to contacts file
    user = update.message.from_user
    contact = {
        'id': len(load_contacts()) + 1,
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code,
        'text': feedback_text,
        'timestamp': str(update.message.date),
        'type': 'feedback'
    }
    contacts = load_contacts()
    contacts.append(contact)
    save_contacts(contacts)
    
    # Send feedback to admin with reply button
    user_info = f'👤 {user.first_name or "Unknown"}'
    if user.last_name:
        user_info += f' {user.last_name}'
    if user.username:
        user_info += f' (@{user.username})'
    user_info += f'\n🆔 {user.id}'
    
    keyboard = [[InlineKeyboardButton("💬 Reply", callback_data=f'reply_contact_{contact["id"]}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f'💬 **New Feedback** 💬\n\n{user_info}\n\n💭 **Feedback:**\n{feedback_text}\n\n📅 **Status:** Awaiting review',
        reply_markup=reply_markup
    )
    
    await update.message.reply_text(
        '✅ **Feedback Sent Successfully!** ✅\n\n'
        '📨 Your feedback has been delivered to our admin team\n'
        '👀 **Status: Being Reviewed** - Our team will read it carefully\n'
        '💬 You will receive a direct reply from admin if needed\n\n'
        '💝 Your input helps us improve and serve our community better\n\n'
        '🌟 Thank you for helping us grow!',
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def receive_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Received contact message")
    if not context.user_data.get('awaiting_contact'):
        await update.message.reply_text('❓ No active contact session. Use the menu to contact admin.')
        return ConversationHandler.END
    
    contact_text = update.message.text.strip()
    if not contact_text:
        await update.message.reply_text('📝 Please provide a message. Try again or use /start to cancel.')
        return CONTACT_STATE
    
    # Save contact to file
    user = update.message.from_user
    contact = {
        'id': len(load_contacts()) + 1,
        'user_id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code,
        'text': contact_text,
        'timestamp': str(update.message.date),
        'type': 'contact'
    }
    contacts = load_contacts()
    contacts.append(contact)
    save_contacts(contacts)
    
    # Send contact to admin with reply buttons
    user_info = f'👤 {user.first_name or "Unknown"}'
    if user.last_name:
        user_info += f' {user.last_name}'
    if user.username:
        user_info += f' (@{user.username})'
    user_info += f'\n🆔 {user.id}'
    
    keyboard = [[InlineKeyboardButton("💬 Reply", callback_data=f'reply_contact_{contact["id"]}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f'📞 New Contact Message 📞\n\n{user_info}\n\n💭 Message:\n{contact_text}\n\n📅 Status: Awaiting review',
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Failed to send contact to admin: {e}")
        # Still proceed, maybe admin hasn't started bot
    
    await update.message.reply_text(
        '✅ Message Sent Successfully! ✅\n\n'
        '📨 Your message has been delivered to our admin team\n'
        '👀 Status: Being Reviewed - Our team will read it carefully\n'
        '💬 You will receive a direct reply from admin soon\n\n'
        '⏰ Response Time: Usually within 24 hours\n\n'
        '🙏 Thank you for your patience and for reaching out!',
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def receive_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Admin sending reply")
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ This function is for admins only!')
        return ConversationHandler.END
    
    if not context.user_data.get('replying_to_contact'):
        await update.message.reply_text('❓ No active reply session. Use /view_contacts to start replying.')
        return ConversationHandler.END
    
    contact_id = context.user_data['replying_to_contact']
    reply_text = update.message.text.strip()
    
    if not reply_text:
        await update.message.reply_text('📝 Please provide a reply message. Try again or use /start to cancel.')
        return ADMIN_REPLY_STATE
    
    contacts = load_contacts()
    contact = next((c for c in contacts if c['id'] == contact_id), None)
    
    if not contact:
        await update.message.reply_text('❌ Contact not found.')
        context.user_data.clear()
        return ConversationHandler.END
    
    # Send reply to user
    try:
        user_info = f"👤 {contact.get('first_name', 'Unknown')}"
        if contact.get('username'):
            user_info += f" (@{contact['username']})"
        
        original_type = "contact message" if contact.get('type') == 'contact' else "feedback"
        
        await context.bot.send_message(
            chat_id=contact['user_id'],
            text=f'💬 Admin Reply 💬\n\n'
                 f'📋 Regarding your {original_type}:\n'
                 f'"{contact["text"][:100]}{"..." if len(contact["text"]) > 100 else ""}"\n\n'
                 f'👨‍💼 Admin Response:\n{reply_text}\n\n'
                 f'✅ Message Status: Read and replied to\n'
                 f'🙏 Thank you for your patience!'
        )
        
        print("Reply sent to user")
        await update.message.reply_text(f'✅ Reply sent to user #{contact_id}!')
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error sending reply: {e}')
    
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
            try:
                if CHANNEL_ID:
                    keyboard = [[InlineKeyboardButton("💭 Comment", url=f"https://t.me/{BOT_USERNAME}?start=comment_{conf_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    message = await context.bot.send_message(
                        chat_id=CHANNEL_ID, 
                        text=f'💫 Anonymous Confession #{conf_id:03d} 💫\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"{conf["text"]}"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
                        reply_markup=reply_markup
                    )
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
                    
                    # Notify the user that their confession was approved
                    try:
                        await context.bot.send_message(
                            chat_id=conf['user_id'],
                            text=f'🌟 **Your Confession Was Approved!** 🌟\n\nYour anonymous confession #{conf_id:03d} has been reviewed and approved!\n\nIt\'s now live in the channel and ready to help others. Thank you for sharing your story! 💝\n\n💭 Others can now comment and support you through the bot.'
                        )
                    except Exception as e:
                        # User might have blocked the bot or deleted their account
                        pass
                    
                # Remove from pending
                pending.pop(i)
                save_pending(pending)
                await update.message.reply_text(f'✅ Confession #{conf_id} approved and posted! 📢')
            except telegram_error.BadRequest as e:
                if "Chat not found" in str(e):
                    await update.message.reply_text(f'❌ **Channel not found!**\n\nThe configured channel ID `{CHANNEL_ID}` is invalid or the bot lacks permission.\n\n**To fix this:**\n1. Add your bot as an administrator to your channel\n2. Get the correct channel ID\n3. Update CHANNEL_ID in the code\n\n**How to get channel ID:**\n- Forward a message from your channel to @userinfobot\n- Or use @getidsbot\n\nConfession #{conf_id} remains in pending.')
                else:
                    await update.message.reply_text(f'❌ Error posting to channel: {e}\n\nConfession #{conf_id} remains in pending.')
            except Exception as e:
                await update.message.reply_text(f'❌ Unexpected error: {e}\n\nConfession #{conf_id} remains in pending.')
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
    
    await update.message.reply_text(
        '💬 **Thank You for Your Kindness!** 💬\n\n'
        '🙏 **Your supportive comment has been received**\n\n'
        '👀 Our admin will review it carefully\n'
        '📢 Once approved, it will appear as a reply to help others\n\n'
        '🌟 **Your empathy makes our community stronger**\n\n'
        '💝 **Want to support more stories?** Visit our channel anytime\n\n'
        '**Thank you for being part of the healing** ✨',
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Notify admin
    keyboard = [
        [InlineKeyboardButton("✅ Approve Comment", callback_data=f'approve_comment_{comment_id}'),
         InlineKeyboardButton("❌ Reject Comment", callback_data=f'reject_comment_{comment_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=ADMIN_ID, 
        text=f'💬 **New Comment on Confession #{conf_id:03d}** 💬\n\n💭 **Comment:**\n{comment_text}\n\n👤 **Comment ID:** {comment_id}',
        reply_markup=reply_markup
    )
    
    # Notify the confession sender
    approved = load_approved()
    conf = next((c for c in approved if c['id'] == conf_id), None)
    if conf and 'user_id' in conf:
        try:
            await context.bot.send_message(
                chat_id=conf['user_id'],
                text=f'💬 Someone commented on your confession! 💬\n\nYour anonymous confession #{conf_id:03d} received a new comment:\n\n💭 "{comment_text}"\n\nComment is pending admin approval and will appear in the channel once approved.'
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
            # Find the confession message_id,,
            conf = next((conf for conf in approved if conf['id'] == c['conf_id']), None)
            if conf:
                try:
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
                except telegram_error.BadRequest as e:
                    if "Chat not found" in str(e):
                        await update.message.reply_text(f'❌ **Channel not found!**\n\nCannot post comment. The channel ID `{CHANNEL_ID}` is invalid.\n\nPlease fix the CHANNEL_ID in the code first.')
                    else:
                        await update.message.reply_text(f'❌ Error posting comment to channel: {e}')
                except Exception as e:
                    await update.message.reply_text(f'❌ Unexpected error posting comment: {e}')
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
async def handle_main_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '👋 Please use the buttons above to navigate!\n\n'
        '🎯 Click "Share My Story" to share your confession\n'
        '💬 Click "Support Others" to comment on stories\n'
        '🌟 Click "About Our Community" to learn more\n'
        '🛡️ Click "Safety First" for guidelines\n\n'
        'All interactions are through buttons - no typing needed! ✨'
    )
async def handle_main_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🚫 **Please don\'t type here!**\n\n'
        '❌ This section is for reading only\n'
        '👆 Use the buttons above to navigate\n\n'
        '🎯 **What you can do:**\n'
        '• 📝 Click "Share My Story" to share your confession\n'
        '• 💬 Click "Support Others" to comment on stories\n'
        '• 🌟 Click "About Our Community" to learn more\n'
        '• 🛡️ Click "Safety First" for guidelines\n'
        '• ❓ Click "How It Works" for help\n'
        '• 📞 Click "Contact Us" for support\n\n'
        '✨ **No typing needed** - everything is button-driven!'
    )
    return MAIN_MENU

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
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
📞 /view_contacts - View contact messages and feedback
💬 Click "Reply" buttons in /view_contacts to reply to messages
✏️ Edit button - Edit confession text
❓ /help - Show this help

Example: /approve 1
Example: Use /view_contacts and click Reply buttons to respond
"""
    await update.message.reply_text(help_text)

async def view_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ This command is for admins only!')
        return
    
    contacts = load_contacts()
    if not contacts:
        await update.message.reply_text('📭 No contact messages or feedback to review.')
        return
    
    text = '📞 Contact Messages & Feedback:\n\n'
    keyboard = []
    
    for contact in contacts[-10:]:  # Show last 10
        contact_type = "📞 Contact" if contact.get('type') == 'contact' else "💬 Feedback"
        user_info = f"{contact.get('first_name', 'Unknown')}"
        if contact.get('username'):
            user_info += f" (@{contact['username']})"
        
        text += f"#{contact['id']} {contact_type} - {user_info}\n"
        text += f"💭 {contact['text'][:50]}{'...' if len(contact['text']) > 50 else ''}\n\n"
        
        keyboard.append([InlineKeyboardButton(f"💬 Reply #{contact['id']}", callback_data=f'reply_contact_{contact["id"]}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def reply_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.from_user.id) != ADMIN_ID:
        await update.message.reply_text('❌ This command is for admins only!')
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text('Usage: /reply_contact <id> <message>')
        return
    
    try:
        contact_id = int(context.args[0])
        reply_text = ' '.join(context.args[1:])
    except ValueError:
        await update.message.reply_text('❌ Invalid contact ID.')
        return
    
    contacts = load_contacts()
    contact = next((c for c in contacts if c['id'] == contact_id), None)
    
    if not contact:
        await update.message.reply_text('❌ Contact not found.')
        return
    
    # Send reply to user
    try:
        user_info = f"👤 {contact.get('first_name', 'Unknown')}"
        if contact.get('username'):
            user_info += f" (@{contact['username']})"
        
        original_type = "contact message" if contact.get('type') == 'contact' else "feedback"
        
        await context.bot.send_message(
            chat_id=contact['user_id'],
            text=f'💬 **Admin Reply** 💬\n\n'
                 f'📋 **Regarding your {original_type}:**\n'
                 f'"{contact["text"][:100]}{"..." if len(contact["text"]) > 100 else ""}"\n\n'
                 f'👨‍💼 **Admin Response:**\n{reply_text}\n\n'
                 f'✅ **Message Status:** Read and replied to\n'
                 f'🙏 Thank you for your patience!'
        )
        
        await update.message.reply_text(f'✅ Reply sent to user #{contact_id}!')
        
    except Exception as e:
        await update.message.reply_text(f'❌ Error sending reply: {e}')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == 'send_confession':
        keyboard = [[InlineKeyboardButton("⬅️ Take Me Back", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            'Your Story Matters - Let\'s Begin ✨\n\n'
            'Take a deep breath... 🌬️\n\n'
            'This is your safe space - no judgment, only understanding hearts\n\n'
            'What\'s weighing on your soul today?\n'
            '• 💭 "I\'ve been carrying this secret for years..."\n'
            '• ❤️ "I\'m learning to love myself again after everything"\n'
            '• 🌟 "Today I conquered a fear I thought would break me"\n'
            '• 🤝 "I need someone to understand what I\'m going through"\n\n'
            'Your words have power - they can heal you and help others\n\n'
            'Ready to share? Just type your message below and send it to me\n'
            'We\'re here with open hearts 💕',
            reply_markup=reply_markup
        )
        return ASK_CONFESSION
    elif query.data == 'about':
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        about_text = """
🌟 About Hope Confessions 🌟

💝 Our Mission: Creating a safe haven for hearts to heal

🤝 What We Believe:
• 🙈 Anonymity is sacred - Your story, your privacy, your choice
• 👥 Community heals - Together we find strength in vulnerability  
• 🛡️ Safety first - Every message is reviewed with compassion
• 💪 Empowerment through sharing - Your courage inspires others

📊 Our Impact:
• ❤️ 1000+ stories shared - Each one matters
• 🤗 Countless lives touched - Through empathy and understanding
• 🌱 Growth fostered - Personal journeys celebrated

🎯 Our Promise:
• 🔒 Zero data collection - What you share stays between you and us
• 👨‍⚕️ Caring moderation - Human review with heart
• 🌈 Positive focus - Building bridges, not walls

Built with love for the human experience 💙
"""
        await query.edit_message_text(about_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'help_user':
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        help_text = """
❓ How to Use

1. 📝 Click "Share My Story" to share your confession
2. ✍️ Type your message and send it
3. ✅ Your confession is reviewed by our admin
4. 📢 If approved, it appears anonymously in the channel

💭 You can also support others by commenting on their stories!

All interactions are through buttons - no commands needed! 🎯
"""
        await query.edit_message_text(help_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'comment_help':
        # Load recent approved confessions to show for commenting
        approved = load_approved()
        if not approved:
            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                '💬 Support Others 💬\n\n'
                'No confessions available to comment on yet.\n'
                'Check back later when more stories are shared!\n\n'
                '🌟 You can also share your own story to start the conversation.',
                reply_markup=reply_markup
            )
            return MAIN_MENU
        
        # Show last 5 confessions with comment buttons
        keyboard = []
        message_text = '💬 Support Others - Choose a Story to Comment On 💬\n\n'
        message_text += 'Here are recent confessions that could use your support:\n\n'
        
        # Show up to 5 most recent confessions
        recent_confessions = approved[-5:] if len(approved) > 5 else approved
        recent_confessions.reverse()  # Show newest first
        
        for i, conf in enumerate(recent_confessions):
            # Truncate long confessions for preview
            preview = conf['text'][:100] + '...' if len(conf['text']) > 100 else conf['text']
            message_text += f'#{conf["id"]:03d}: {preview}\n\n'
            keyboard.append([InlineKeyboardButton(f'💭 Comment on #{conf["id"]:03d}', callback_data=f'comment_on_{conf["id"]}')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text += 'Click a button above to share your thoughts and support!'
        
        await query.edit_message_text(message_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data.startswith('comment_on_'):
        # Extract confession ID from callback data
        try:
            conf_id = int(query.data.split('_')[2])
        except (IndexError, ValueError):
            await query.answer("Invalid confession ID")
            return MAIN_MENU
        
        # Check if confession exists
        approved = load_approved()
        conf = next((c for c in approved if c['id'] == conf_id), None)
        if not conf:
            await query.answer("Confession not found")
            return MAIN_MENU
        
        # Set up comment session
        context.user_data['comment_conf_id'] = conf_id
        
        # Show confirmation and prompt for comment
        keyboard = [[InlineKeyboardButton("⬅️ Cancel", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        preview = conf['text'][:150] + '...' if len(conf['text']) > 150 else conf['text']
        
        await query.edit_message_text(
            f'💬 Comment on Confession #{conf_id:03d} 💬\n\n'
            f'📝 Confession: {preview}\n\n'
            'Please reply to this message with your anonymous comment.\n\n'
            'Example: This really helped me too!\n\n'
            'Your comment will be reviewed before posting.',
            reply_markup=reply_markup
        )
        return ASK_COMMENT
    elif query.data == 'safety':
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
            [InlineKeyboardButton("💬 Send Feedback", callback_data='send_feedback')],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        safety_text = """
🛡️ Safety & Privacy Guidelines 🛡️

Your safety is our 🌟 top priority! We protect your anonymity and well-being.

🔒 Privacy Protection:
• 🙈 All confessions are completely anonymous
• 🚫 No personal information is ever shared
• 👀 Admin reviews all content before posting

🚫 What We Don't Allow:
• 😡 Harmful, abusive, or threatening content
• 👊 Personal attacks or harassment
• ⚖️ Illegal activities or promotion of harm
• 📢 Spam, scams, or inappropriate content

📞 If You Need Help:
• 🚨 Report inappropriate content using the buttons below
• 👨‍💼 Contact admin for urgent safety concerns
• 💬 Send feedback to help us improve

💙 Remember: This is a safe space for positive, supportive sharing. 🌈

Stay safe and be kind! 🙏
"""
        await query.edit_message_text(safety_text, reply_markup=reply_markup)
        return MAIN_MENU
    elif query.data == 'back_to_menu':
        keyboard = [
            [InlineKeyboardButton("📝 Share My Story", callback_data='send_confession'),
             InlineKeyboardButton("💬 Support Others", callback_data='comment_help')],
            [InlineKeyboardButton("🌟 About Our Community", callback_data='about'),
             InlineKeyboardButton("🛡️ Safety First", callback_data='safety')],
            [InlineKeyboardButton("❓ How It Works", callback_data='help_user')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        intro_text = """
🎭 Welcome to Hope Confessions 🎭

✨ A Safe Space for Your Heart ✨

💝 Share anonymously, heal together, grow stronger

🌈 Why people choose us:
• 🙈 100% Anonymous - Your identity stays private
• 👥 Supportive Community - Connect with understanding hearts  
• 🛡️ Safe Environment - All content is carefully reviewed
• 💪 Empowerment - Your story can inspire others

📊 Join 1000+ people who've found courage here

🎯 Ready to begin your journey?
"""
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=intro_text,
            reply_markup=reply_markup
        )
        return MAIN_MENU
    elif query.data.startswith('approve_') or query.data.startswith('reject_') or query.data.startswith('edit_'):
        # Admin actions
        if str(query.from_user.id) != ADMIN_ID:
            await query.edit_message_text('❌ Unauthorized!')
            return
        
        parts = query.data.split('_')
        action = parts[0]
        
        # Check if this is a comment action (approve_comment_123) or confession action (approve_123)
        if len(parts) >= 3 and parts[1] == 'comment':
            # Comment action: approve_comment_123
            action = f"{parts[0]}_{parts[1]}"  # "approve_comment" or "reject_comment"
            item_id = int(parts[2])
            is_comment_action = True
        else:
            # Confession action: approve_123
            item_id = int(parts[1])
            is_comment_action = False
        
        if is_comment_action:
            # Handle comment actions
            comments = load_comments()
            comment = next((c for c in comments if c['id'] == item_id), None)
            
            if not comment:
                await query.edit_message_text('❓ Comment not found.')
                return
            
            if action == 'approve_comment':
                # Mark comment as approved
                comment['approved'] = True
                save_comments(comments)
                
                # Notify the confessor that their confession received a comment
                user_notified = False
                
                try:
                    approved = load_approved()
                    conf = next((c for c in approved if c['id'] == comment['conf_id']), None)
                    if conf and 'user_id' in conf:
                        await context.bot.send_message(
                            chat_id=conf['user_id'],
                            text=f'💬 Someone commented on your confession! 💬\n\nYour anonymous confession #{comment["conf_id"]:03d} received a new supportive comment:\n\n💭 "{comment["text"]}"\n\nThank you for sharing - your story is helping others heal! 🌟'
                        )
                        user_notified = True
                except Exception as e:
                    user_notified = False
                
                # Provide feedback to admin
                if user_notified:
                    await query.edit_message_text(f'✅ Comment #{item_id} approved and user notified! 📢')
                else:
                    await query.edit_message_text(f'✅ Comment #{item_id} approved but user notification failed. 📢')
            elif action == 'reject_comment':
                # Remove comment from pending
                comments = [c for c in comments if c['id'] != item_id]
                save_comments(comments)
                await query.edit_message_text(f'❌ Comment #{item_id} rejected and removed. 🗑️')
            return
        
        # Handle confession actions (existing logic)
        conf_id = item_id
        pending = load_pending()
        for i, conf in enumerate(pending):
            if conf['id'] == conf_id:
                if action == 'approve':
                    try:
                        if CHANNEL_ID:
                            keyboard = [[InlineKeyboardButton("💭 Comment", url=f"https://t.me/{BOT_USERNAME}?start=comment_{conf_id}")]]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            message = await context.bot.send_message(
                                chat_id=CHANNEL_ID, 
                                text=f'💫 Anonymous Confession #{conf_id:03d} 💫\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"{conf["text"]}"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
                                reply_markup=reply_markup
                            )
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
                            
                            # Notify the user that their confession was approved
                            try:
                                await context.bot.send_message(
                                    chat_id=conf['user_id'],
                                    text=f'🌟 **Your Confession Was Approved!** 🌟\n\nYour anonymous confession #{conf_id:03d} has been reviewed and approved!\n\nIt\'s now live in the channel and ready to help others. Thank you for sharing your story! 💝\n\n💭 Others can now comment and support you through the bot.'
                                )
                            except Exception as e:
                                # User might have blocked the bot or deleted their account
                                pass
                                
                        pending.pop(i)
                        save_pending(pending)
                        await query.edit_message_text(f'✅ Confession #{conf_id} approved and posted! 📢')
                    except telegram_error.BadRequest as e:
                        if "Chat not found" in str(e):
                            await query.edit_message_text(f'❌ **Channel not found!**\n\nThe configured channel ID `{CHANNEL_ID}` is invalid or the bot lacks permission.\n\n**To fix this:**\n1. Add your bot as an administrator to your channel\n2. Get the correct channel ID\n3. Update CHANNEL_ID in the code\n\n**How to get channel ID:**\n- Forward a message from your channel to @userinfobot\n- Or use @getidsbot\n\nConfession #{conf_id} remains in pending.')
                        else:
                            await query.edit_message_text(f'❌ Error posting to channel: {e}\n\nConfession #{conf_id} remains in pending.')
                    except Exception as e:
                        await query.edit_message_text(f'❌ Unexpected error: {e}\n\nConfession #{conf_id} remains in pending.')
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
    elif query.data.startswith('approve_comment_') or query.data.startswith('reject_comment_'):
        # Admin comment actions
        if str(query.from_user.id) != ADMIN_ID:
            await query.edit_message_text('❌ Unauthorized!')
            return
        
        parts = query.data.split('_')
        action = parts[0] + '_' + parts[1]  # approve_comment or reject_comment
        comment_id = int(parts[2])
        
        comments = load_comments()
        comment = next((c for c in comments if c['id'] == comment_id), None)
        
        if not comment:
            await query.edit_message_text('❓ Comment not found.')
            return
        
        if action == 'approve_comment':
            # Mark comment as approved
            comment['approved'] = True
            save_comments(comments)
            
            # Post comment as reply to the confession in channel
            try:
                approved = load_approved()
                conf = next((c for c in approved if c['id'] == comment['conf_id']), None)
                if conf and conf.get('message_id'):
                    await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        reply_to_message_id=conf['message_id'],
                        text=f'💬 {comment["text"]}'
                    )
                await query.edit_message_text(f'✅ Comment #{comment_id} approved and posted as reply! 📢')
            except Exception as e:
                await query.edit_message_text(f'❌ Error posting comment: {e}')
        elif action == 'reject_comment':
            # Remove comment from pending
            comments = [c for c in comments if c['id'] != comment_id]
            save_comments(comments)
            await query.edit_message_text(f'❌ Comment #{comment_id} rejected and removed. 🗑️')
        return
    elif query.data == 'contact_admin':
        await query.answer()
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            '📞 Contact Admin 📞\n\n'
            'Need to reach out directly? We\'re here to help! 💬\n\n'
            '📝 What would you like to discuss?\n'
            '• 💡 Share an idea for the bot\n'
            '• 🆘 Report an issue or concern\n'
            '• 💭 Ask a question\n'
            '• 🤝 Suggest a collaboration\n\n'
            'Just type your message and send it to us!\n'
            '👀 Your message will be reviewed by our admin team.',
            reply_markup=reply_markup
        )
        # Set user state for contact
        context.user_data['awaiting_contact'] = True
        return CONTACT_STATE
    elif query.data == 'send_feedback':
        await query.answer()
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            '💬 Send Feedback 💬\n\n'
            'Help us improve! Your feedback is valuable:\n\n'
            '📝 What do you think of our bot?\n'
            '💡 Any features you\'d like to see?\n'
            '🐛 Found any issues?\n\n'
            'Just type your message and send it to us! ✨',
            reply_markup=reply_markup
        )
        # Set user state for feedback
        context.user_data['awaiting_feedback'] = True
        return FEEDBACK_STATE
    elif query.data.startswith('reply_contact_'):
        # Admin reply to contact/feedback
        await query.answer()
        if str(query.from_user.id) != ADMIN_ID:
            return
        
        contact_id = int(query.data.split('_')[2])
        print(f"Admin clicked reply for contact {contact_id}")
        contacts = load_contacts()
        contact = next((c for c in contacts if c['id'] == contact_id), None)
        
        if not contact:
            await query.answer("❌ Contact not found!")
            return
        
        # Set context for admin reply
        context.user_data['replying_to_contact'] = contact_id
        
        contact_type = "contact message" if contact.get('type') == 'contact' else "feedback"
        user_info = f"{contact.get('first_name', 'Unknown')}"
        if contact.get('username'):
            user_info += f" (@{contact['username']})"
        
        await query.edit_message_text(
            f'💬 Reply to {contact_type} #{contact_id}\n\n'
            f'👤 From: {user_info}\n'
            f'💭 Original: {contact["text"]}\n\n'
            f'📝 Type your reply message and send it:'
        )
        
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f'💬 Reply to {contact_type} #{contact_id}\n\n'
            f'👤 From: {user_info}\n'
            f'💭 Original: {contact["text"]}\n\n'
            f'📝 Type your reply message and send it:',
            reply_markup=reply_markup
        )
        
        # Set state for receiving admin reply
        print("State set to ADMIN_REPLY_STATE")
        return ADMIN_REPLY_STATE

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
        print("✅ Bot application created successfully!")
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu_message),
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
            FEEDBACK_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_feedback),
                CommandHandler('start', start)  # Allow restart
            ],
            CONTACT_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_contact),
                CommandHandler('start', start)  # Allow restart
            ],
            ADMIN_REPLY_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_admin_reply),
                CommandHandler('start', start)  # Allow restart
            ],
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('pending', pending))
    application.add_handler(CommandHandler('approve', approve))
    application.add_handler(CommandHandler('reject', reject))
    application.add_handler(CommandHandler('comment', comment))
    application.add_handler(CommandHandler('view_comments', view_comments))
    application.add_handler(CommandHandler('approve_comment', approve_comment))
    application.add_handler(CommandHandler('reject_comment', reject_comment))
    application.add_handler(CommandHandler('view_contacts', view_contacts))
    application.add_handler(CommandHandler('reply_contact', reply_contact))
    application.add_handler(CommandHandler('help', help_admin))
    application.add_handler(CommandHandler('intro', intro))
    application.add_handler(CommandHandler('menu', menu))
    application.add_handler(CommandHandler('report', report))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    
    if WEBHOOK_URL:
        # Webhook mode - use manual event loop management
        print("🚀 Starting bot webhook...")
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get('PORT', 5000)),
            url_path="webhook",
            webhook_url=WEBHOOK_URL
        )
        print("✅ Bot webhook is now running! Press Ctrl+C to stop.")
        try:
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping bot...")
            await application.updater.stop()
            await application.stop()
            print("✅ Bot stopped successfully!")
    else:
        # Polling mode - use manual event loop management
        print("🚀 Starting bot polling...")
        await application.start()
        await application.updater.start_polling()
        print("✅ Bot is now running! Press Ctrl+C to stop.")
        try:
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping bot...")
            await application.updater.stop()
            await application.stop()
            print("✅ Bot stopped successfully!")

if __name__ == '__main__':
    # Handle event loop issues - try nest_asyncio if available
    try:
        import nest_asyncio
        nest_asyncio.apply()
        print("🔧 Applied nest_asyncio to handle event loop conflicts")
        asyncio.run(main())
    except ImportError:
        print("⚠️  nest_asyncio not available, trying alternative approach...")
        try:
            asyncio.run(main())
        except RuntimeError as e:
            if "event loop" in str(e).lower():
                print("❌ Event loop conflict detected. Please run in a fresh environment:")
                print("   ./beza/bin/python3 -c 'import bot; import asyncio; asyncio.run(bot.main())'")
                print("   Or: source beza/bin/activate && python -c 'import bot; import asyncio; asyncio.run(bot.main())'")
            else:
                raise