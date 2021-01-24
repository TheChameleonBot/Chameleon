import io
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime
from json import JSONDecodeError
import logging

from telegram import Update, ParseMode
from telegram.ext import CallbackContext, Updater, CommandHandler, Filters
from telegram.utils.helpers import mention_html
from threading import Timer

from constants import TRANSLATION_CHANNEL_ID, TRANSLATION_CHAT_ID, BACKUP_CHANNEL
from database import database
from strings import get_string, new_strings
from utils.helpers import is_admin


logger = logging.getLogger(__name__)


def shutdown(update: Update, context: CallbackContext, updater: Updater):
    database.init_shutdown()
    dp = updater.dispatcher
    skip = True
    for chat_id in dp.chat_data:
        if dp.chat_data[chat_id] and "players" in dp.chat_data[chat_id]:
            skip = False
            lang = dp.chat_data[chat_id]["lang"]
            try:
                context.bot.send_message(chat_id, get_string(lang, "init_shutdown"))
            except Exception as e:
                update.message.reply_text(f"Chat {chat_id} didn't get the shutdown message because "
                                          f"{e.__dict__}")
    if not skip:
        t = Timer(5 * 60, real_shutdown, [[dp, update.effective_user.id]])
        t.start()
    else:
        change_handlers(dp)
    update.message.reply_text(f"Shutdown initiated, {'see you in t-5 min' if not skip else 'upload activated'}")


def real_shutdown(args):
    dp = args[0]
    bot = dp.bot
    for chat_id in dp.chat_data:
        if dp.chat_data[chat_id] and "players" in dp.chat_data[chat_id]:
            lang = database.get_language_chat(chat_id)
            try:
                bot.send_message(chat_id, get_string(lang, "run_shutdown"))
            except Exception as e:
                bot.send_message(args[1], f"{chat_id} still skipped because {e.__dict__}")
    change_handlers(dp)
    bot.send_message(args[1], "Shutdown done, upload activated")


def change_handlers(dp):
    dp.handlers.clear()
    dp.handlers = {0: [CommandHandler("upload", upload, Filters.chat(TRANSLATION_CHAT_ID))], 1: [], 2: []}


def upload(update: Update, context: CallbackContext):
    if not is_admin(context.bot, update.effective_user.id, update.effective_chat):
        update.effective_message.reply_text("Sorry, admins only ;P")
        return
    if not update.effective_message.reply_to_message:
        update.effective_message.reply_text("You need to reply to a file... idiot")
        return
    file = update.effective_message.reply_to_message.document
    file_name = file.file_name
    if file_name.endswith(".yaml"):
        yaml_file(file, update, context.bot)
    elif file_name.endswith(".json"):
        json_file(file, update)
    else:
        update.effective_message.reply_text("You need to reply to a .yaml file... idiot")
        return


def yaml_file(file, update: Update, bot):
    file_name = file.file_name
    temp_name = "./strings/" + "temp_" + file_name
    file.get_file().download(temp_name)
    returned = new_strings(file_name)
    if "error" in returned:
        update.effective_message.reply_text(f"An error happened with this file: {returned['error']}")
        os.remove(temp_name)
    elif file_name[:-5] == "en":
        text = "Hello translators. The english file received an update."
        if returned["new_strings"]:
            new = "<code>{}</code>\n".format('\n'.join(returned['new_strings']))
            text += f"\nThose are the new strings:\n{new}"
        if returned["new_arguments"]:
            new = "<code>{}</code>\n".format('\n'.join(returned['new_arguments']))
            text += f"\nThose are the strings which got new arguments (those weird brackets with numbers in them):" \
                    f"\n{new}"
        if returned["changed_strings"]:
            new = "<code>{}</code>\n".format('\n'.join(returned['changed_strings']))
            text += f"\nThose are strings which changed significantly from the old ones:\n{new}"
        if text != "Hello translators. The english file received an update.":
            text += "\nThe bot will fallback to the english original in those cases until you update your file"
        else:
            text += "\nNothing special happened :)"
        bot.send_document(TRANSLATION_CHANNEL_ID, file.file_id, caption=text, parse_mode=ParseMode.HTML)
    else:
        text = "Hey there, thanks for submitting your file"
        if returned["missing_strings"]:
            missing = "<code>{}</code>".format('\n'.join(returned['missing_strings']))
            text += f"\nThose are the strings which are missing:\n{missing}"
        if returned["missing_arguments"]:
            missing = "<code>{}</code>".format('\n'.join(returned['missing_arguments']))
            text += f"\nThose are the strings which are missing arguments (those weird brackets):\n{missing}"
        if text == "Hey there, thanks for submitting your file":
            text += "\nNo errors in your file, good job!"
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    os.rename(temp_name, "./strings/" + file.file_name)
    github("./strings/" + file.file_name)


def json_file(file, update):
    temp_name = "./decks/" + "temp_" + file.file_name
    file.get_file().download(temp_name)
    try:
        new_deck = json.load(open(temp_name))
    except JSONDecodeError as e:
        text = f"This json file is no valid json, I got the following error: <code>{str(e)}</code>"
        update.effective_message.reply_html(text)
        os.remove(temp_name)
        return
    if not isinstance(new_deck, dict):
        update.effective_message.reply_text("This json file is not a dictionary!")
        os.remove(temp_name)
        return
    try:
        if not isinstance(new_deck["language"], str) or not isinstance(new_deck["name"], str):
            update.effective_message.reply_text("language and name needs to be strings!")
            os.remove(temp_name)
            return
    except KeyError as e:
        update.effective_message.reply_text(f"Hey, you need to include {e} in your file in order to submit a deck")
        os.remove(temp_name)
        return
    stripped_keys = []
    stripped_items = []
    for key in new_deck:
        if key == "language" or key == "name":
            continue
        if not isinstance(new_deck[key], list):
            stripped_keys.append(key)
            new_deck.pop(key, None)
            continue
        temp_list = new_deck[key]
        for item in new_deck[key]:
            if not isinstance(item, str):
                stripped_items.append(str(item))
                temp_list.remove(item)
        if stripped_items:
            new_deck[key] = temp_list
    text = "Hey there, thanks for submitting your file"
    if stripped_keys:
        stripped = "<code>{}</code>".format('\n'.join(stripped_keys))
        text += f"\nUnfortunately, I had to remove those keys from your dictionary, since their values " \
                f"aren't lists:\n{stripped}"
    if stripped_items:
        stripped = "<code>{}</code>".format('\n'.join(stripped_items))
        text += f"\nUnfortunately, I had to remove those items from your lists, since they aren't strings:\n{stripped}"
    if text == "Hey there, thanks for submitting your file":
        text += "\nNo error happend, good for you!"
    update.effective_message.reply_html(text)
    os.rename(temp_name, "./decks/" + file.file_name)
    database.reload_decks()
    github("./decks/" + file.file_name)


def github(file):
    subprocess.call(["git", "add", file])
    subprocess.call(["git", "commit", "-m", "updating file via /upload command"])
    subprocess.call(["git", "push"])


def error_handler(update: Update, context: CallbackContext):
    if not update:
        text = "Hey jo, error outside of update, The full traceback:\n\n < code > {trace} < / code > "
        context.bot.send_message(208589966, text, parse_mode=ParseMode.HTML)
        return
    chat = update.effective_chat
    if chat.type == "private":
        if "lang" not in context.user_data:
            context.user_data["lang"] = database.get_language_player(update.effective_user.id)
        lang = context.user_data["lang"]
    else:
        if "lang" not in context.chat_data:
            context.chat_data["lang"] = database.get_language_chat(update.effective_chat.id)
        lang = context.chat_data["lang"]
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
    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    text = f"Oh no. The error <code>{context.error}</code> happened{payload}. The type of the chat is " \
           f"<code>{chat.type}</code>. The current user data is <code>{context.user_data}</code>, the chat data " \
           f"<code>{context.chat_data}</code>.\nThe full traceback:\n\n<code>{trace}</code>"
    context.bot.send_message(208589966, text, parse_mode=ParseMode.HTML)
    raise


def reply_id(update, _):
    update.effective_message.reply_text(f"{update.effective_chat.id}")


def backup(bot):
    run = subprocess.run(["mongodump", "-dchameleonbot", "--gzip", "--archive"], capture_output=True)
    output = io.BytesIO(run.stdout)
    time = datetime.now().strftime("%d-%m-%Y")
    bot.send_document(BACKUP_CHANNEL, output, filename=f"{time}.archive.gz")
