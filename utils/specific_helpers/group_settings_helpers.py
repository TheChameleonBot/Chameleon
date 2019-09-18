from telegram import InlineKeyboardButton

from database import database
from utils.helpers import build_menu
from strings import get_language


def group_settings_buttons(settings, chat_id, refresh_id=0):
    buttons = []
    refresh_button = []
    group_settings = database.get_all_settings(chat_id)
    for setting in settings:
        if setting == "language":
            buttons.append(InlineKeyboardButton(f"{settings[setting]}: {get_language(group_settings['lang'])}",
                                                callback_data=f"groupsettings_{str(chat_id)}_{setting}"))
        elif setting == "deck":
            buttons.append(InlineKeyboardButton(f"{settings[setting]}: {group_settings['deck']}",
                                                callback_data=f"groupsettings_{str(chat_id)}_{setting}"))
        elif setting == "refresh":
            refresh_button.append(InlineKeyboardButton(f"{settings[setting]} 🔄",
                                                       callback_data=f"groupsettings_{str(chat_id)}_{setting}_"
                                                                     f"{refresh_id}"))
        elif group_settings[setting]:
            buttons.append(InlineKeyboardButton(f"{settings[setting]} ✅",
                                                callback_data=f"groupsettings_{str(chat_id)}_{setting}"))
        else:
            buttons.append(InlineKeyboardButton(f"{settings[setting]} ❌",
                                                callback_data=f"groupsettings_{str(chat_id)}_{setting}"))
    return build_menu(buttons, 2, header_buttons=refresh_button)


def language_buttons(languages, chat_id, back):
    buttons = []
    for language in languages:
        buttons.append(InlineKeyboardButton(languages[language],
                                            callback_data=f"grouplanguage_{str(chat_id)}_{language}"))
    return build_menu(buttons, 3, footer_buttons=[group_back(chat_id, back)])


def group_back(chat_id, back):
    return InlineKeyboardButton(back, callback_data=f"groupback_{str(chat_id)}")


def deck_buttons(deck, chat_id, back):
    buttons = []
    for deck_name in deck:
        buttons.append(InlineKeyboardButton(deck_name, callback_data=f"deck_{str(chat_id)}_{deck_name}"))
    return build_menu(buttons, 3, footer_buttons=[group_back(chat_id, back)])
