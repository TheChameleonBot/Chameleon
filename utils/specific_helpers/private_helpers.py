from telegram import InlineKeyboardButton

from utils.helpers import build_menu

from random import randint


def language_buttons(languages):
    buttons = []
    for language in languages:
        buttons.append(InlineKeyboardButton(languages[language], callback_data=f"privatelanguage_{language}"))
    return build_menu(buttons, 3)


def help_buttons(settings, chosen):
    # getting angry at the ios client because it allows users to spam the server so fast that its impossible to avoid
    # re-editing the message with the same (though code wise different) content, thus resulting in a BadRequest
    refresh_id = randint(0, 100000000000)
    buttons = []
    for setting in settings:
        if setting == "refresh":
            continue
        data = f"settingshelp_{setting}_{refresh_id}"
        if setting == chosen:
            buttons.append(InlineKeyboardButton(f"[{settings[setting]}]", callback_data=data))
        else:
            buttons.append(InlineKeyboardButton(settings[setting], callback_data=data))
    return build_menu(buttons, 4)
