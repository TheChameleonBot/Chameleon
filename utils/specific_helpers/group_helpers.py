import random
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, ChatPermissions
from telegram.error import BadRequest
from telegram.utils.helpers import mention_html

from database import database
from objects import Deck
from strings import get_string
from utils.helpers import is_admin

logger = logging.getLogger(__name__)


def players_mentions(players):
    mentions = []
    for player in players:
        mentions.append(mention_html(player["user_id"], player["first_name"]))
    return "\n".join(mentions)


def yes_game(context, data, chat_id, dp):
    chat_data = dp.chat_data[chat_id]
    chat_data.clear()
    lang = data["lang"]
    group_settings = data["group_settings"]
    deck = Deck(*group_settings["deck"].split("_"))
    chameleon = random.choice(list(data["players"]))
    random.shuffle(data["players"])
    chat_data.update({"chameleon": chameleon, "secret": deck.secret, "players": data["players"], "lang": lang,
                      "starter": data["starter"], "words": deck.words, "game_id": data["game_id"],
                      "fewer": group_settings["fewer"], "tournament": group_settings["tournament"],
                      "more": group_settings["more"], "pin": group_settings["pin"], "restrict": {},
                      "deck": group_settings["deck"], "tutorial": data["tutorial"],
                      "exclamation": group_settings["exclamation"]})
    text = get_string(lang, "game_succeed").format(deck.topic, deck.word_list)
    button = InlineKeyboardMarkup([[InlineKeyboardButton(get_string(lang, "play_button"),
                                                         callback_data="word" + data["game_id"])]])
    message = context.bot.send_message(chat_id, text, reply_to_message_id=data["message"], reply_markup=button,
                                       parse_mode=ParseMode.HTML)
    chat = None
    if group_settings["pin"] or group_settings["restrict"]:
        chat = context.bot.get_chat(chat_id)
    if group_settings["pin"]:
        pinned_message = chat.pinned_message
        if pinned_message:
            chat_data["pin"] = pinned_message.message_id
        try:
            context.bot.pin_chat_message(chat_id, message.message_id, True)
        except BadRequest as e:
            if e.message == "Not enough rights to pin a message":
                chat_data["pin"] = False
                database.insert_group_pin(chat_id)
                e.message += "handled in ghelper L48"
                logger.info(e.message)
    user = data["players"][0]
    text = get_string(lang, "first_player_say_word").format(mention_html(user["user_id"], user["first_name"]))
    if not group_settings["restrict"]:
        if group_settings["exclamation"]:
            text += "\n\n" + get_string(lang, "exclamation_activated")
        else:
            text += "\n\n" + get_string(lang, "exclamation_deactivated")
    context.bot.send_message(chat_id, text, reply_to_message_id=message.message_id, parse_mode=ParseMode.HTML)
    if group_settings["restrict"]:
        chat_data["restrict"]["initial_permissions"] = chat.permissions
        try:
            context.bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
            if not is_admin(context.bot, user["user_id"], chat):
                context.bot.promote_chat_member(chat_id, user["user_id"], can_invite_users=True)
                chat_data["restrict"]["skip"] = False
            else:
                chat_data["restrict"]["skip"] = True
        except BadRequest as e:
            chat_data["restrict"] = False
            database.insert_group_restrict(chat_id)
            e.message += "handled in ghelper L68"
            logger.info(e.message)
    chat_data["word_list"] = message.message_id


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


def name_generator(first_name):
    if len(first_name) > 30:
        first_name = first_name[:27] + "..."
    return first_name
