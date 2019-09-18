from telegram import Update, ParseMode
from telegram.ext import CallbackContext, Updater
from telegram.utils.helpers import mention_html
from threading import Timer

from constants import TRANSLATION_CHANNEL_ID
from database import database
from strings import get_string, new_strings
from utils.helpers import is_admin


def shutdown(update: Update, context: CallbackContext, updater: Updater):
    database.init_shutdown()
    dp = updater.dispatcher
    for chat_id in dp.chat_data:
        if dp.chat_data[chat_id]:
            lang = database.get_language_chat(chat_id)
            context.bot.send_message(chat_id, get_string(lang, "init_shutdown"))
    update.message.reply_text("Shutdown initiated, see you in t-5 min")
    t = Timer(5*60, real_shutdown, [[updater, update.effective_user.id]])
    t.start()


def real_shutdown(args):
    updater = args[0]
    dp = updater.dispatcher
    bot = dp.bot
    for chat_id in dp.chat_data:
        if dp.chat_data[chat_id]:
            lang = database.get_language_chat(chat_id)
            bot.send_message(chat_id, get_string(lang, "run_shutdown"))
    bot.send_message(args[1], "Shutdown done")
    updater.stop()


def yaml_file(update: Update, context: CallbackContext):
    if not is_admin(context.bot, update.effective_user.id, update.effective_chat):
        update.effective_message.reply_text("Sorry, admins only ;P")
        return
    if not update.effective_message.reply_to_message:
        update.effective_message.reply_text("You need to reply to a file... idiot")
        return
    file = update.effective_message.reply_to_message.document
    file_name = file.file_name
    if not file_name.endswith(".yaml"):
        update.effective_message.reply_text("You need to reply to a .yaml file... idiot")
        return
    file.get_file().download("./strings/" + file_name)
    returned = new_strings(file_name)
    if "error" in returned:
        update.effective_message.reply_text(f"An error happened with this file: {returned['error']}")
    elif file_name[:-5] == "en":
        text = "Hello translators. The english file received an update."
        if returned["new_strings"]:
            new = "<code>{}</code>\n".format('\n'.join(returned['new_strings']))
            text += f"\nThose are the new strings:\n{new}"
        if returned["new_arguments"]:
            new = "<code>{}</code>\n".format('\n'.join(returned['new_arguments']))
            text += f"\nThose are the strings which got new arguments (those weird brackets with numbers in them):" \
                    f"\n{new}"
        if text != "Hello translators. The english file received an update.\n":
            text += "\nThe bot will fallback to the english original in those cases until you update your file"
        else:
            text += "Nothing special happened :)"
        context.bot.send_document(TRANSLATION_CHANNEL_ID, file.file_id, caption=text, parse_mode=ParseMode.HTML)
    else:
        text = "Hey there, thanks for submitting your file"
        if returned["missing_strings"]:
            missing = "<code>{}</code>".format('\n'.join(returned['missing_strings']))
            text += f"\nThose are the strings which are missing:\n{missing}"
        if returned["missing_arguments"]:
            missing = "<code>{}</code>".format('\n'.join(returned['missing_arguments']))
            text += f"\nThose are the strings which are missing arguments (those weird brackets):\n{missing}"
        if text == "Hey there, thanks for submitting your file\n":
            text += "No errors in your file, good job!"
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def json_file(update: Update, _):
    file = update.message.document
    file.get_file().download("./cards/" + file.file_name)
    database.reload_decks()
    update.effective_message.reply_text("Done")


def error_handler(update: Update, context: CallbackContext):
    chat = update.effective_chat
    if chat.type == "private":
        if "lang" not in context.user_data:
            lang = database.get_language_player(update.effective_user.id)
        else:
            lang = context.user_data["lang"]
    else:
        if "lang" not in context.chat_data:
            lang = database.get_language_chat(update.effective_chat.id)
        else:
            lang = context.user_data["lang"]
    if update.callback_query:
        update.callback_query.answer(get_string(lang, "error"), show_alert=True)
    else:
        update.effective_message.reply_text(get_string(lang, "error"))
    payload = ""
    # normally, we always have an user. If not, its either a channel or a poll update.
    if update.effective_user:
        payload += f' with the user {mention_html(update.effective_user.id, update.effective_user.first_name)}'
    # there are more situations when you don't get a chat
    if update.effective_chat:
        payload += f' within the chat <i>{update.effective_chat.title}</i>'
        if update.effective_chat.username:
            payload += f' (@{update.effective_chat.username})'
    # but only one where you have an empty payload by now: A poll (buuuh)
    if update.poll:
        payload += f' with the poll id {update.poll.id}.'
    text = f"Oh no. The error <code>{context.error}</code> happened{payload}. The type of the chat is " \
           f"<code>{chat.type}</code>. The current user data is <code>{context.user_data}<c/ode>, the chat data " \
           f"<code>{context.chat_data}</code>."
    context.bot.send_message(208589966, text, parse_mode=ParseMode.HTML)


def reply_id(update, _):
    update.effective_message.reply_text(f"{update.effective_chat.id}")
