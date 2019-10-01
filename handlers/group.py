from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import CallbackContext, Dispatcher, Job

from strings import get_string
from telegram.utils.helpers import mention_html

from utils.specific_helpers import group_helpers
from database import database
from constants import TIME, MAX_PLAYERS


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
    first_name = update.effective_user.first_name
    user_id = update.effective_user.id
    button = [[InlineKeyboardButton(get_string(lang, "start_button"), callback_data="join")]]
    mention = mention_html(user_id, first_name)
    group_settings = database.get_all_settings(chat_id)
    wanted_settings = []
    for setting in group_settings:
        if setting == "lang":
            continue
        if setting == "deck":
            wanted_settings.append(group_settings[setting])
        elif group_settings[setting]:
            wanted_settings.append(get_string(lang, "activated"))
        else:
            wanted_settings.append(get_string(lang, "deactivated"))
    text = get_string(lang, "start_game").format(mention, mention, *wanted_settings)
    message = update.message.reply_html(text,
                                        reply_markup=InlineKeyboardMarkup(button))
    payload = {"dp": dp, "players": [{"user_id": user_id, "first_name": first_name}], "message": message.message_id,
               "lang": lang, "chat_id": chat_id, "known_players": [], "tutorial": False,
               "starter": {"user_id": user_id, "first_name": first_name}, "group_settings": group_settings}
    context.job_queue.run_repeating(timer, TIME, context=payload, name=chat_id)
    payload = {"starter": {"user_id": user_id, "first_name": first_name},
               "players": [{"user_id": user_id, "first_name": first_name}], "lang": lang, "message": message.message_id,
               "left_players": {}, "settings": wanted_settings}
    chat_data.update(payload)


def player_join(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_data = context.chat_data
    first_name = update.effective_user.first_name
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    # somehow, this callback button is there, but we aren't in join mode, so we handle this now :D
    if "message" not in chat_data:
        group_helpers.no_game(update, context, "join_no_game_running")
        return
    starter = mention_html(chat_data["starter"]["user_id"], chat_data["starter"]["first_name"])
    remove = False
    for player in chat_data["players"]:
        player_id = player["user_id"]
        # player leaves
        if user_id == player_id:
            chat_data["players"].remove({"user_id": user_id, "first_name": first_name})
            # we need them in here so we can mention them later. Looks stupid, I know
            chat_data["left_players"][user_id] = first_name
            query.answer(get_string(chat_data["lang"], "player_leaves_query"))
            remove = True
            break
    if not remove:
        # if they left and rejoined before the timer run through, they are still in this dict. If not, nothing happens
        chat_data["left_players"].pop(user_id, None)
        chat_data["players"].append({"user_id": user_id, "first_name": first_name})
        query.answer(get_string(chat_data["lang"], "player_joins_query"))
    players = group_helpers.players_mentions(chat_data["players"])
    job = context.job_queue.get_jobs_by_name(chat_id)[0]
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
    button = [[InlineKeyboardButton(get_string(chat_data["lang"], "start_button"), callback_data="join")]]
    query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(button))


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
            if len(data["players"]) >= 3:
                text += get_string(lang, "player_action_text").format(get_string(lang, "start"))
            else:
                text += get_string(lang, "player_action_text").format(get_string(lang, "fail"))
            context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            data["known_players"] = known_players
            return
    # game either ends/starts
    dp.chat_data[chat_id].clear()
    context.job.schedule_removal()
    if not len(data["players"]) == MAX_PLAYERS:
        context.bot.edit_message_reply_markup(chat_id, data["message"], reply_markup=None)
    if len(data["players"]) >= 3:
        if database.get_new_player([all_player["user_id"] for all_player in data["players"]]):
            context.bot.send_message(chat_id, get_string(lang, "rules"), parse_mode=ParseMode.HTML)
            context.job_queue.run_once(delay, 15, [context, data, chat_id, dp])
        else:
            group_helpers.yes_game(context, data, chat_id, dp)
    else:
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
    database.change_id(old_id, new_id)


def help_message(update: Update, context: CallbackContext):
    if "lang" not in context.chat_data:
        context.chat_data["lang"] = database.get_language_chat(update.effective_chat.id)
    update.effective_message.reply_text(get_string(context.chat_data["lang"], "help_group"))
