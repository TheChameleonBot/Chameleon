from html import escape
from telegram import InlineKeyboardButton, KeyboardButton
from utils.helpers import build_menu


def wordlist(players):
    words = ""
    for player in players:
        if "word" in player:
            words += f"<b>{escape(player['first_name'])}</b>: {player['word']}\n"
        else:
            break
    return words


def vote_buttons(players, game_id):
    buttons = []
    for player in players:
        buttons.append(InlineKeyboardButton(player["first_name"],
                                            callback_data="vote" + game_id + str(player["user_id"])))
    return build_menu(buttons, 3)


def draw_buttons(same_voters, game_id):
    buttons = []
    for same_voter in same_voters:
        buttons.append(InlineKeyboardButton(same_voter["first_name"],
                                            callback_data="draw" + game_id + str(same_voter["user_id"])))
    return build_menu(buttons, 3)


def word_buttons(words, exclamation_mark=False):
    buttons = []
    for word in words:
        buttons.append(KeyboardButton(f"{'!' if exclamation_mark else ''}{word}"))
    return build_menu(buttons, 4)
