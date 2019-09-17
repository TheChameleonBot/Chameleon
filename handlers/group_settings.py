from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.error import Unauthorized
from telegram.ext import CallbackContext

from constants import TRANSLATION_CHAT_LINK
from database import database
from strings import get_string, get_languages
from utils import group_settings_helpers, helpers


def admins_only(func):
    def wrapper(*args, **kwargs):
        update = args[0]
        context = args[1]
        user_id = update.effective_user.id
        user_data = context.user_data
        if "lang" not in user_data:
            lang = database.get_language_player(user_id)
            user_data["lang"] = lang
        else:
            lang = user_data["lang"]
        query = update.callback_query
        chat_id = query.data.split("_")[1]
        chat = context.bot.get_chat(chat_id)
        if not helpers.is_admin(context.bot, update.effective_user.id, chat):
            query.edit_message_text(get_string(lang, "no_admin_settings"))
            return
        return func(*args, **kwargs)

    return wrapper


def group_setting(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    lang = database.get_language_chat(chat_id)
    if not helpers.is_admin(context.bot, update.effective_user.id, update.effective_chat):
        update.effective_message.reply_text(get_string(lang, "no_admin_settings"))
        return
    user_id = update.effective_user.id
    user_lang = database.get_language_player(user_id)
    pm = database.get_pm_player(user_id)
    context.user_data["lang"] = user_lang
    if pm:
        try:
            # yes, its not a string, I don't change the functions name for this you fucker
            buttons = group_settings_helpers.group_settings_buttons(get_string(user_lang, "group_setting_buttons"),
                                                                    chat_id)
            context.bot.send_message(user_id, get_string(user_lang, "group_setting_text"),
                                     reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
        # this means the bot was blocked wtf
        except Unauthorized:
            update.effective_message.reply_text(get_string(lang, "admin_blocked_bot"))
    else:
        button = [[InlineKeyboardButton(get_string(lang, "no_pm_settings_button"),
                                        url=f"https://t.me/thechameleonbot?start={chat_id}")]]
        update.effective_message.reply_text(get_string(lang, "no_pm_settings"),
                                            reply_markup=InlineKeyboardMarkup(button))


def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    database.insert_player_pm(user_id)
    user_data = context.user_data
    if "lang" not in user_data:
        lang = database.get_language_player(user_id)
        user_data["lang"] = lang
    else:
        lang = user_data["lang"]
    chat_id = int(context.args[0])
    chat = context.bot.get_chat(chat_id)
    if not helpers.is_admin(context.bot, update.effective_user.id, chat):
        update.effective_message.reply_text(get_string(lang, "no_admin_settings"))
        return
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    context.bot.send_message(user_id, get_string(lang, "group_setting_text"),
                             reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


def reload_admins(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    helpers.get_admin_ids(context.bot, chat_id, True)
    lang = database.get_language_chat(chat_id)
    update.effective_message.reply_html(get_string(lang, "reload_admins"))


@admins_only
def change_language(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    current_lang = database.get_language_chat(chat_id)
    languages = get_languages()
    current_language = languages[current_lang]
    lang = context.user_data["lang"]
    buttons = group_settings_helpers.language_buttons(languages, chat_id, get_string(lang, "settings_back_button"))
    query.edit_message_text(get_string(lang, "group_setting_languages").format(current_language, TRANSLATION_CHAT_LINK),
                            reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def select_language(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    selected_lang = data[2]
    lang = context.user_data["lang"]
    database.insert_group_lang(chat_id, selected_lang)
    # yes, its not a string, I don't change the functions name for this you fucker
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    text = get_string(lang, "group_setting_text")
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def change_deck(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    current_deck = database.get_deck_chat(chat_id)
    deck = list(database.cards.keys())
    buttons = group_settings_helpers.deck_buttons(deck, chat_id, get_string(lang, "settings_back_button"))
    text = get_string(lang, "group_setting_decks").format(current_deck, TRANSLATION_CHAT_LINK)
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def select_deck(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    selected_deck = data[2]
    lang = context.user_data["lang"]
    database.insert_group_deck(chat_id, selected_deck)
    # yes, its not a string, I don't change the functions name for this you fucker
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    text = get_string(lang, "group_setting_text")
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def fewer(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    fewer_setting = database.insert_group_fewer(chat_id)
    if fewer_setting:
        query.answer(get_string(lang, "group_setting_fewer_activate"))
    else:
        query.answer(get_string(lang, "group_setting_fewer_deactivate"))
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    text = get_string(lang, "group_setting_text")
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def more(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    more_setting = database.insert_group_more(chat_id)
    if more_setting:
        query.answer(get_string(lang, "group_setting_more_activate"))
    else:
        query.answer(get_string(lang, "group_setting_more_deactivate"))
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    text = get_string(lang, "group_setting_text")
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def tournament(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    tournament_setting = database.insert_group_tournament(chat_id)
    if tournament_setting:
        query.answer(get_string(lang, "group_setting_tournament_activate"))
    else:
        query.answer(get_string(lang, "group_setting_tournament_deactivate"))
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    text = get_string(lang, "group_setting_text")
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def pin(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    if not database.get_pin_setting(chat_id):
        can_pin = context.bot.get_chat_member(chat_id, context.bot.id).can_pin_messages
        if can_pin:
            database.insert_group_pin(chat_id)
            query.answer(get_string(lang, "group_setting_pin_activate"))
        else:
            query.answer(get_string(lang, "group_setting_pin_required"), show_alert=True)
            return
    else:
        database.insert_group_pin(chat_id)
        query.answer(get_string(lang, "group_setting_pin_deactivate"))
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    text = get_string(lang, "group_setting_text")
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def hardcore_game(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    if not database.get_hardcore_game_setting(chat_id):
        chat_member = context.bot.get_chat_member(chat_id, context.bot.id)
        if chat_member.can_invite_users and chat_member.can_promote_members:
            database.insert_group_hardcore_game(chat_id)
            query.answer(get_string(lang, "group_setting_hardcore_activate"))
        else:
            query.answer(get_string(lang, "group_setting_hardcore_required"), show_alert=True)
            return
    else:
        database.insert_group_hardcore_game(chat_id)
        query.answer(get_string(lang, "group_setting_hardcore_deactivate"))
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    text = get_string(lang, "group_setting_text")
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def back(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    query.edit_message_text(get_string(lang, "group_setting_text"), reply_markup=InlineKeyboardMarkup(buttons),
                            parse_mode=ParseMode.HTML)
