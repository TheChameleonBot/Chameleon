from telegram.utils.helpers import mention_html

from database import database
from strings import get_string


def players_mentions(players):
    mentions = []
    for player in players:
        mentions.append(mention_html(player["user_id"], player["first_name"]))
    return "\n".join(mentions)


def no_game(update, context, text):
    query = update.callback_query
    chat_data = context.chat_data
    chat_id = update.effective_chat.id
    if "lang" in chat_data:
        lang = chat_data["lang"]
    else:
        lang = database.get_language_chat(chat_id)
    query.answer(get_string(lang, text), show_alert=True)
    query.edit_message_reply_markup(None)
