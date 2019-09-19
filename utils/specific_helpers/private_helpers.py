from telegram import InlineKeyboardButton

from utils.helpers import build_menu


def language_buttons(languages):
    buttons = []
    for language in languages:
        buttons.append(InlineKeyboardButton(languages[language], callback_data=f"privatelanguage_{language}"))
    return build_menu(buttons, 3)
