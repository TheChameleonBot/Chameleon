import html

from telegram import Update, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext

from database import database
from strings import get_languages, get_string
from utils.specific_helpers import private_helpers
from constants import DECKS_LINK, TRANSLATION_CHAT_LINK, TRANSLATIONS_LINK, HTML_STYLE_LINK


def change_language(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_id = update.effective_user.id
    if "lang" not in user_data:
        lang = database.get_language_player(user_id)
        user_data["lang"] = lang
    else:
        lang = user_data["lang"]
    current_lang = database.get_language_player(user_id)
    languages = get_languages()
    current_language = languages[current_lang]
    buttons = private_helpers.language_buttons(languages)
    update.effective_message.reply_text(get_string(lang, "private_language").format(current_language),
                                        reply_markup=InlineKeyboardMarkup(buttons))


def selected_language(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    selected_lang = data[1]
    context.user_data["lang"] = selected_lang
    database.insert_player_lang(update.effective_user.id, selected_lang)
    languages = get_languages()
    new_language = languages[selected_lang]
    query.edit_message_text(get_string(selected_lang, "private_language_selected").format(new_language))


def deck(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    lang = user_data["lang"]
    here = get_string(lang, "here")
    decks_link = f"<a href=\"{DECKS_LINK}\">{here}</a>"
    group_link = f"<a href=\"{TRANSLATION_CHAT_LINK}\">{here}</a>"
    update.effective_message.reply_html(get_string(lang, "deck").format(decks_link, group_link))


def translation(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    lang = user_data["lang"]
    here = get_string(lang, "here")
    translations_link = f"<a href=\"{TRANSLATIONS_LINK}\">{here}</a>"
    html_style_link = f"<a href=\"{HTML_STYLE_LINK}\">{here}</a>"
    group_link = f"<a href=\"{TRANSLATION_CHAT_LINK}\">{here}</a>"
    update.effective_message.reply_html(get_string(lang, "translation").format(translations_link, html_style_link,
                                                                               group_link))


def start(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    if context.args:
        return
    update.effective_message.reply_text(get_string(user_data["lang"], "greeting_private"))


def help_message(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    update.effective_message.reply_text(get_string(user_data["lang"], "help_private"))


def settings_help(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    lang = user_data["lang"]
    buttons = private_helpers.help_buttons(get_string(lang, "group_setting_buttons"), None)
    update.effective_message.reply_text(get_string(lang, "settings_help"),
                                        reply_markup=InlineKeyboardMarkup(buttons))


def settings_help_edit(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    lang = user_data["lang"]
    query = update.callback_query
    data = query.data.split("_")
    chosen = data[1]
    help_text = get_string(lang, f"{chosen}_help")
    if html.unescape(query.message.text_html) == help_text:
        query.answer()
        return
    buttons = private_helpers.help_buttons(get_string(lang, "group_setting_buttons"), chosen)
    query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(buttons),
                            parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    query.answer()
