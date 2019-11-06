from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.error import Unauthorized, BadRequest
from telegram.ext import CallbackContext

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
        chat_id = int(query.data.split("_")[1])
        try:
            chat = context.bot.get_chat(chat_id)
        except BadRequest:
            new_chat_id = database.get_new_id(chat_id)
            if new_chat_id:
                chat = context.bot.get_chat(chat_id)
            else:
                query.edit_message_text(get_string(lang, "group_not_found"))
                return
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
    database.insert_group_title(chat_id, update.effective_chat.title, update.effective_chat.link)
    if pm:
        try:
            # yes, its not a string, I don't change the functions name for this you fucker
            chat_link = helpers.chat_link(update.effective_chat.title, update.effective_chat.link)
            buttons = group_settings_helpers.group_settings_buttons(get_string(user_lang, "group_setting_buttons"),
                                                                    chat_id)
            context.bot.send_message(user_id, get_string(user_lang, "group_setting_text").format(chat_link),
                                     reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML,
                                     disable_web_page_preview=True)
        # this means the bot was blocked wtf
        except Unauthorized:
            update.effective_message.reply_text(get_string(lang, "admin_blocked_bot"))
            database.insert_player_pm(user_id, False)
    else:
        button = [[InlineKeyboardButton(get_string(lang, "no_pm_settings_button"),
                                        url=f"https://t.me/thechameleonbot?start=settings_{chat_id}")]]
        update.effective_message.reply_text(get_string(lang, "no_pm_settings"),
                                            reply_markup=InlineKeyboardMarkup(button))


def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    database.insert_player_pm(user_id, True)
    user_data = context.user_data
    if "lang" not in user_data:
        lang = database.get_language_player(user_id)
        user_data["lang"] = lang
    else:
        lang = user_data["lang"]
    context.args = context.args[0].split("_") if context.args else None
    if not context.args or context.args[0] != "settings":
        return
    # not necessary, but pycharm won't believe me that...
    chat_id = 0
    try:
        chat_id = int(context.args[1])
        chat = context.bot.get_chat(chat_id)
    except ValueError:
        context.bot.send_message(user_id, get_string(lang, "group_not_found"))
        return
    except BadRequest:
        try:
            new_id = database.get_new_id(chat_id)
            if new_id:
                chat = context.bot.get_chat(int(new_id))
            else:
                raise BadRequest
        except BadRequest:
            context.bot.send_message(user_id, get_string(lang, "group_not_found"))
            return
    database.insert_group_title(chat_id, chat.title, chat.link)
    if not helpers.is_admin(context.bot, update.effective_user.id, chat):
        update.effective_message.reply_text(get_string(lang, "no_admin_settings"))
        return
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id)
    chat_link = helpers.chat_link(chat.title, chat.link)
    context.bot.send_message(user_id, get_string(lang, "group_setting_text").format(chat_link),
                             reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML,
                             disable_web_page_preview=True)


def admins_reload(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    helpers.get_admin_ids(context.bot, chat_id, True)
    lang = database.get_language_chat(chat_id)
    update.effective_message.reply_html(get_string(lang, "admins_reload"))


@admins_only
def change_language(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    current_lang = database.get_language_chat(chat_id)
    languages = get_languages()
    current_language = languages[current_lang]
    lang = context.user_data["lang"]
    buttons = group_settings_helpers.language_buttons(languages, chat_id)
    query.edit_message_text(get_string(lang, "group_setting_languages").format(current_language),
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
    edit(query, chat_id, lang)


@admins_only
def change_deck(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_id = int(query.data.split("_")[1])
    lang = context.user_data["lang"]
    context.user_data["deck"] = database.get_deck_chat(chat_id)
    deck = context.user_data["deck"]
    deck_languages = database.get_deck_languages()
    buttons = group_settings_helpers.deck_languages_buttons(deck_languages, chat_id)
    text = get_string(lang, "group_setting_deck_language").format(deck.split("_")[0])
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def select_deck_language(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    selected_language = data[2]
    lang = context.user_data["lang"]
    deck = context.user_data["deck"]
    context.user_data["selected_lang"] = selected_language
    decks = database.get_decks(selected_language)
    buttons = group_settings_helpers.deck_buttons(decks, chat_id)
    text = get_string(lang, "group_setting_decks").format(deck.split("_")[1])
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)


@admins_only
def select_deck(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    selected_deck = f"{context.user_data['selected_lang']}_{data[2]}"
    lang = context.user_data["lang"]
    database.insert_group_deck(chat_id, selected_deck)
    edit(query, chat_id, lang)


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
    edit(query, chat_id, lang)


@admins_only
def more(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    refresh_id = 1
    if int(data[3]) != 0:
        refresh_id = 0
    lang = context.user_data["lang"]
    more_setting = database.insert_group_more(chat_id)
    if more_setting:
        query.answer(get_string(lang, "group_setting_more_activate"))
    else:
        query.answer(get_string(lang, "group_setting_more_deactivate"))
    edit(query, chat_id, lang, refresh_id)


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
    edit(query, chat_id, lang)


@admins_only
def pin(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    refresh_id = 1
    if int(data[3]) != 0:
        refresh_id = 0
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
    edit(query, chat_id, lang, refresh_id)


@admins_only
def restrict(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    refresh_id = 1
    if int(data[3]) != 0:
        refresh_id = 0
    lang = context.user_data["lang"]
    if not database.get_restrict_setting(chat_id):
        chat_member = context.bot.get_chat_member(chat_id, context.bot.id)
        if chat_member.can_invite_users and chat_member.can_promote_members and chat_member.can_restrict_members:
            database.insert_group_restrict(chat_id)
            query.answer(get_string(lang, "group_setting_restrict_activate"))
        else:
            query.answer(get_string(lang, "group_setting_restrict_required"), show_alert=True)
            return
    else:
        database.insert_group_restrict(chat_id)
        query.answer(get_string(lang, "group_setting_restrict_deactivate"))
    edit(query, chat_id, lang, refresh_id)


@admins_only
def exclamation(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    refresh_id = 1
    if int(data[3]) != 0:
        refresh_id = 0
    lang = context.user_data["lang"]
    exclamation_setting = database.insert_group_exclamation(chat_id)
    if exclamation_setting:
        query.answer(get_string(lang, "group_setting_exclamation_activate"))
    else:
        query.answer(get_string(lang, "group_setting_exclamation_deactivate"))
    edit(query, chat_id, lang, refresh_id)


@admins_only
def refresh(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data.split("_")
    chat_id = int(data[1])
    refresh_id = 1
    if int(data[3]) != 0:
        refresh_id = 0
    lang = context.user_data["lang"]
    query.answer(get_string(lang, "group_setting_refresh"))
    edit(query, chat_id, lang, refresh_id)


def edit(query, chat_id, lang, refresh_id=0):
    buttons = group_settings_helpers.group_settings_buttons(get_string(lang, "group_setting_buttons"), chat_id,
                                                            refresh_id)
    chat_details = database.get_group_title(chat_id)
    chat_link = helpers.chat_link(chat_details["title"], chat_details["link"])
    text = get_string(lang, "group_setting_text").format(chat_link)
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True)
