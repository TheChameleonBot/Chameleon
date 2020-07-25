import logging
import random
import string

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import Unauthorized, BadRequest, RetryAfter
from telegram.ext import CallbackContext, Dispatcher, Job

from strings import get_string
from telegram.utils.helpers import mention_html

from utils import helpers
from utils.specific_helpers import group_helpers
from database import database
from constants import TIME, MAX_PLAYERS, START_TIME
from utils.specific_helpers.group_helpers import name_generator

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext, dp: Dispatcher):
    chat_id = update.effective_chat.id
    chat_data = context.chat_data
    if "lang" not in chat_data:
        lang = database.get_language_chat(chat_id)
    else:
        lang = chat_data["lang"]
    if database.shutdown:
        update.effective_message.reply_text(get_string(lang, "group_start_shutdown"))
        return
    elif "players" in chat_data:
        update.effective_message.reply_text(get_string(lang, "game_running"))
        return
    first_name = name_generator(update.effective_user.first_name)
    user_id = update.effective_user.id
    game_id = ''.join(random.choices(string.ascii_lowercase, k=10))
    button = [[InlineKeyboardButton(get_string(lang, "start_button"), callback_data="join_" + game_id)]]
    mention = mention_html(user_id, first_name)
    group_settings = database.get_all_settings(chat_id)
    settings = ["deck", "fewer", "more", "pin", "tournament", "restrict", "exclamation"]
    wanted_settings = []
    for setting in settings:
        if setting == "deck":
            wanted_settings.append(f"{group_settings[setting]}")
        elif group_settings[setting]:
            wanted_settings.append(get_string(lang, "activated"))
        else:
            wanted_settings.append(get_string(lang, "deactivated"))
    text = get_string(lang, "start_game").format(mention, mention, *wanted_settings)
    message = update.effective_message.reply_html(text, reply_markup=InlineKeyboardMarkup(button))
    payload = {"dp": dp, "players": [{"user_id": user_id, "first_name": first_name}], "message": message.message_id,
               "lang": lang, "chat_id": chat_id, "known_players": [], "tutorial": False,
               "starter": {"user_id": user_id, "first_name": first_name}, "group_settings": group_settings,
               "game_id": game_id}
    context.job_queue.run_repeating(timer, START_TIME, context=payload, name=chat_id)
    payload = {"starter": {"user_id": user_id, "first_name": first_name},
               "players": [{"user_id": user_id, "first_name": first_name}], "lang": lang, "message": message.message_id,
               "left_players": {}, "settings": wanted_settings, "game_id": game_id, "chat_id": chat_id}
    chat_data.update(payload)
    chat_link = helpers.chat_link(update.effective_chat.title, update.effective_chat.link)
    for player_id in database.get_nextgame_ids(chat_id):
        if player_id == user_id:
            continue
        try:
            context.bot.send_message(player_id, get_string(lang, "nextgame").format(chat_link),
                                     parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except Unauthorized as e:
            database.remove_group_nextgame(chat_id, [player_id])
            database.insert_player_pm(user_id, False)
            e.message += "handled in group no PM"
            logger.info(e.message)
        except BadRequest as e:
            if e.message == "Chat not found":
                database.remove_group_nextgame(chat_id, [player_id])
                database.insert_player_pm(user_id, False)
                e.message += "handled in group no PM"
                logger.info(e.message)


def player_join(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_data = context.chat_data
    first_name = name_generator(update.effective_user.first_name)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    # check if the chat data is from a different state
    if "message" not in chat_data:
        # this means there is no game starting/running
        if "game_id" not in chat_data:
            group_helpers.no_game(update, context, "join_no_game_running")
            return
        # this means there is a game starting, but the button wasn't removed yet
        if chat_data["game_id"] == query.data.split("_")[1]:
            query.answer(get_string(chat_data["lang"], "join_while_starting"))
            return
        # if we are here, there is a newer game running and someone hit the button of an old one
        group_helpers.no_game(update, context, "join_old_button")
        return
    starter = mention_html(chat_data["starter"]["user_id"], chat_data["starter"]["first_name"])
    remove = False
    for player in chat_data["players"]:
        player_id = player["user_id"]
        # player leaves
        if user_id == player_id:
            # we do this so player can change their name between joining and leaving
            chat_data["players"].remove({"user_id": user_id, "first_name": player["first_name"]})
            # we need them in here so we can mention them later. Looks stupid, I know
            chat_data["left_players"][user_id] = first_name
            if "flood" in chat_data:
                query.answer(get_string(chat_data["lang"], "player_leaves_query_flood"), show_alert=True)
            else:
                query.answer(get_string(chat_data["lang"], "player_leaves_query"))
            remove = True
            break
    if not remove:
        # if they left and rejoined before the timer run through, they are still in this dict. If not, nothing happens
        chat_data["left_players"].pop(user_id, None)
        chat_data["players"].append({"user_id": user_id, "first_name": first_name})
        if "flood" in chat_data:
            query.answer(get_string(chat_data["lang"], "player_joins_query_flood"), show_alert=True)
        else:
            query.answer(get_string(chat_data["lang"], "player_joins_query"))
    players = group_helpers.players_mentions(chat_data["players"])
    try:
        job = context.job_queue.get_jobs_by_name(chat_id)[0]
    except IndexError:
        # this means the game already started, we are going to return, but quickly notify teh player they didnt made it
        mention = mention_html(user_id, first_name)
        context.bot.send_message(chat_id, get_string(chat_data["lang"], "player_joins_query").format(mention),
                                 parse_mode="HTML")
        return
    job.context["players"] = chat_data["players"]
    job.context["left_players"] = chat_data["left_players"]
    text = get_string(chat_data["lang"], "start_game").format(starter, players, *chat_data["settings"])
    if len(chat_data["players"]) == MAX_PLAYERS:
        query.edit_message_text(text, parse_mode=ParseMode.HTML)
        payload = job.context
        job.schedule_removal()
        new_context = context
        setattr(new_context, "job", Job(timer, interval=42, name=chat_id, context=payload))
        timer(context)
        return
    if "flood" in chat_data:
        return
    button = [[InlineKeyboardButton(get_string(chat_data["lang"], "start_button"), callback_data="join_" +
                                                                                                 chat_data["game_id"])]]
    try:
        query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(button))
    except RetryAfter as e:
        context.job_queue.run_once(flood_error, e.retry_after + 2, context=chat_data, name="flood for " + str(chat_id))
        chat_data["flood"] = True


def flood_error(context):
    data = context.job.context
    # this means the join phase ended and a different call edited the function already
    if "message" not in data:
        return
    starter = mention_html(data["starter"]["user_id"], data["starter"]["first_name"])
    players = group_helpers.players_mentions(data["players"])
    text = get_string(data["lang"], "start_game").format(starter, players, *data["settings"])
    button = InlineKeyboardMarkup([[InlineKeyboardButton(get_string(data["lang"], "start_button"),
                                                         callback_data="join_" + data["game_id"])]])
    context.bot.edit_message_text(text, data["chat_id"], data["message"], parse_mode=ParseMode.HTML,
                                  reply_markup=button)
    del data["flood"]


def timer(context):
    data = context.job.context
    chat_id = context.job.name
    lang = data["lang"]
    dp = data["dp"]
    # repeated join/leave timer
    if not len(data["players"]) == MAX_PLAYERS:
        known_players = []
        joined_player = []
        for player in data["players"]:
            user_id = player["user_id"]
            known_players.append(user_id)
            if user_id in data["known_players"]:
                data["known_players"].remove(user_id)
            # player joined
            else:
                joined_player.append(player)
        # if players are left in known_players data, they left
        left_player = []
        if data["known_players"]:
            for user_id in data["known_players"]:
                left_player.append({"user_id": user_id, "first_name": data["left_players"][user_id]})
                data["left_players"].pop(user_id)
        # if both lists are empty, nothing happened, so the timer runs out
        if not joined_player and not left_player:
            pass
        # yes, this replace is stupid. stupider then copying the function though. Fuck you.
        else:
            if joined_player:
                text = get_string(lang, "player_joins_text")\
                    .format(group_helpers.players_mentions(joined_player).replace("\n", ", "))
                if left_player:
                    text += "\n\n" + get_string(lang, "player_leaves_text")\
                        .format(group_helpers.players_mentions(left_player).replace("\n", ", "))
            # we can do that, cause otherwise we wouldn't be here
            else:
                text = get_string(lang, "player_leaves_text")\
                    .format(group_helpers.players_mentions(left_player).replace("\n", ", "))
            if context.job.interval == START_TIME:
                long = True
            else:
                long = False
            if len(data["players"]) >= 3:
                text += get_string(lang, "player_action_text").format(get_string(lang, "start"))
                if long:
                    context.job.interval = TIME
            else:
                text += get_string(lang, "player_action_text").format(get_string(lang, "fail")).replace("30", "60")
                if not long:
                    context.job.interval = START_TIME
            try:
                context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            except Unauthorized:
                dp.chat_data[chat_id].clear()
                context.job.schedule_removal()
                return
            data["known_players"] = known_players
            return
    # game either ends/starts
    context.job.schedule_removal()
    if not len(data["players"]) == MAX_PLAYERS:
        context.bot.edit_message_reply_markup(chat_id, data["message"], reply_markup=None)
    if len(data["players"]) >= 3:
        player_ids = [all_player["user_id"] for all_player in data["players"]]
        if database.get_new_player(player_ids):
            text = get_string(lang, "rules_prepend") + get_string(lang, "rules")
            context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            dp.chat_data[chat_id]["players"] = True
            context.job_queue.run_once(delay, 31, [context, data, chat_id, dp])
        else:
            group_helpers.yes_game(context, data, chat_id, dp)
        database.remove_group_nextgame(chat_id, player_ids)
    else:
        dp.chat_data[chat_id].clear()
        text = get_string(lang, "game_failed")
        context.bot.send_message(chat_id, text, reply_to_message_id=data["message"])


def delay(context: CallbackContext):
    group_helpers.yes_game(*context.job.context)


def greeting(update: Update, context: CallbackContext):
    new_chat_members = update.effective_message.new_chat_members
    if new_chat_members:
        if context.bot.id not in [user.id for user in new_chat_members]:
            return
    lang = database.get_language_chat(update.effective_chat.id)
    context.chat_data["lang"] = lang
    update.effective_message.reply_text(get_string(lang, "greeting"))


def change_id(update: Update, _):
    message = update.effective_message
    old_id = message.migrate_from_chat_id
    new_id = update.effective_chat.id
    database.insert_group_new_id(old_id, new_id)


def help_message(update: Update, context: CallbackContext):
    if "lang" not in context.chat_data:
        context.chat_data["lang"] = database.get_language_chat(update.effective_chat.id)
    update.effective_message.reply_text(get_string(context.chat_data["lang"], "help_group"))


def nextgame_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    pm = database.get_pm_player(user_id)
    new = database.insert_group_nextgame(chat_id, user_id)
    if "lang" not in context.chat_data:
        context.chat_data["lang"] = database.get_language_chat(chat_id)
    lang = context.chat_data["lang"]
    chat_link = helpers.chat_link(update.effective_chat.title, update.effective_chat.link)
    database.insert_group_title(chat_id, update.effective_chat.title, update.effective_chat.link)
    if pm:
        try:
            if new:
                context.bot.send_message(user_id, get_string(lang, "nextgame_added").format(chat_link),
                                         parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            else:
                context.bot.send_message(user_id, get_string(lang, "nextgame_removed").format(chat_link),
                                         parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except Unauthorized:
            update.effective_message.reply_text(get_string(lang, "nextgame_block"))
            database.insert_player_pm(user_id, False)
    else:
        button = [[InlineKeyboardButton(get_string(lang, "no_pm_settings_button"),
                                        url=f"https://t.me/thechameleonbot?start=nextgame_{chat_id}")]]
        update.effective_message.reply_text(get_string(lang, "nextgame_pm"), reply_markup=InlineKeyboardMarkup(button))


def nextgame_start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    database.insert_player_pm(user_id, True)
    context.args = context.args[0].split("_") if context.args else None
    if not context.args or context.args[0] != "nextgame":
        return
    try:
        chat_id = int(context.args[1])
        new_id = database.get_new_id(chat_id)
        if new_id:
            chat_id = new_id
        lang = database.get_language_chat(chat_id)
    except ValueError:
        context.bot.send_message(user_id, get_string("en", "group_not_found"))
        return
    chat_details = database.get_group_title(chat_id)
    chat_link = helpers.chat_link(chat_details["title"], chat_details["link"])
    new = database.insert_group_nextgame(chat_id, user_id)
    if new:
        context.bot.send_message(user_id, get_string(lang, "nextgame_added").format(chat_link),
                                 parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    else:
        context.bot.send_message(user_id, get_string(lang, "nextgame_removed").format(chat_link),
                                 parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def change_title(update: Update, _):
    chat_id = update.effective_chat.id
    title = update.effective_message.new_chat_title
    link = update.effective_chat.link
    database.insert_group_title(chat_id, title, link)


def game_rules(update: Update, context: CallbackContext):
    if update.effective_chat.type == "private":
        if "lang" not in context.user_data:
            context.user_data["lang"] = database.get_language_player(update.effective_user.id)
        lang = context.user_data["lang"]
    else:
        if "lang" not in context.chat_data:
            context.chat_data["lang"] = database.get_language_chat(update.effective_chat.id)
        lang = context.chat_data["lang"]
    update.effective_message.reply_html(get_string(lang, "rules"))
