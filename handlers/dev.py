from telegram import Update, ParseMode
from telegram.ext import CallbackContext, Updater
from telegram.utils.helpers import mention_html
from threading import Timer
from database import database
from strings import get_string, reload_strings


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


def yaml_file(update: Update, _):
    file = update.message.document
    file.get_file().download("./strings/" + file.file_name)
    reload_strings()
    update.effective_message.reply_text("Done")


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
    context.bot.send_message(-1001179994444, text, parse_mode=ParseMode.HTML)
