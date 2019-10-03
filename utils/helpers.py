from utils.mwt import MWT
from telegram.utils.helpers import mention_html


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def is_admin(bot, user_id, chat, reload=False):
    if chat.type == "group":
        return True
    if user_id not in get_admin_ids(bot, chat.id, reload):
        return False
    return True


@MWT(timeout=60 * 60)
def get_admin_ids(bot, chat_id, reload):
    """Return a list of admin IDs for a given chat. Results are cached for 1 hour."""
    return [admin.user.id for admin in bot.get_chat_administrators(chat_id)]


def player_mention_string(players):
    text = ""
    for player in players:
        text += f"{mention_html(player['user_id'], player['first_name'])}" + "\n"
    return text


def chat_link(title, link):
    return f"<a href=\"{link}\">{title}</a>" if link else f"<b>{title}</b>"
