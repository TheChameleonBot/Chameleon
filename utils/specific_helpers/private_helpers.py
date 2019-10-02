from telegram import InlineKeyboardButton

from utils.helpers import build_menu


def language_buttons(languages):
    buttons = []
    for language in languages:
        buttons.append(InlineKeyboardButton(languages[language], callback_data=f"privatelanguage_{language}"))
    return build_menu(buttons, 3)


def help_buttons(settings, chosen):
    buttons = []
    for setting in settings:
        if setting == "refresh":
            continue
        data = f"settingshelp_{setting}"
        if setting == chosen:
            buttons.append(InlineKeyboardButton(f"[{settings[setting]}]", callback_data=data))
        else:
            buttons.append(InlineKeyboardButton(settings[setting], callback_data=data))
    return build_menu(buttons, 4)
