from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update, ChatPermissions
from telegram.ext import CallbackContext, Dispatcher, Job
import random
import string

from objects import Deck
from strings import get_string
from telegram.utils.helpers import mention_html

from utils.helpers import is_admin
from utils.specific_helpers.group_helpers import players_mentions, no_game
from database import database
from constants import TIME, MAX_PLAYERS


def start(update: Update, context: CallbackContext, dp: Dispatcher):
    chat_id = update.effective_chat.id
    lang = database.get_language_chat(chat_id)
    chat_data = context.chat_data
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
    message = update.message.reply_html(get_string(lang, "start_game").format(mention, mention),
                                        reply_markup=InlineKeyboardMarkup(button))
    payload = {"bot": context.bot, "dp": dp, "players": [{"user_id": user_id, "first_name": first_name}],
               "message": message.message_id, "lang": lang, "chat_id": chat_id, "known_players": [],
               "starter": {"user_id": user_id, "first_name": first_name}}
    context.job_queue.run_repeating(timer, TIME, context=payload, name=chat_id)
    payload = {"starter": {"user_id": user_id, "first_name": first_name},
               "players": [{"user_id": user_id, "first_name": first_name}], "lang": lang, "message": message.message_id,
               "left_players": {}}
    chat_data.update(payload)


def player_join(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_data = context.chat_data
    first_name = update.effective_user.first_name
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    # somehow, this callback button is there, but we aren't in join mode, so we handle this now :D
    if "message" not in chat_data:
        no_game(update, context, "join_no_game_running")
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
    players = players_mentions(chat_data["players"])
    job = context.job_queue.get_jobs_by_name(chat_id)[0]
    job.context["players"] = chat_data["players"]
    job.context["left_players"] = chat_data["left_players"]
    if len(chat_data["players"]) == MAX_PLAYERS:
        query.edit_message_text(get_string(chat_data["lang"], "start_game").format(starter, players),
                                parse_mode=ParseMode.HTML)
        payload = job.context
        job.schedule_removal()
        new_context = context
        setattr(new_context, "job", Job(timer, interval=42, name=chat_id, context=payload))
        timer(context)
        return
    button = [[InlineKeyboardButton(get_string(chat_data["lang"], "start_button"), callback_data="join")]]
    query.edit_message_text(get_string(chat_data["lang"], "start_game").format(starter, players),
                            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(button))


def timer(context):
    data = context.job.context
    chat_id = context.job.name
    bot = data["bot"]
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
                text = get_string(lang, "player_joins_text").format(players_mentions(joined_player).replace("\n", ", "))
                if left_player:
                    text += "\n\n" + get_string(lang, "player_leaves_text").format(players_mentions(left_player)
                                                                                   .replace("\n", ", "))
            # we can do that, cause otherwise we wouldn't be here
            else:
                text = get_string(lang, "player_leaves_text").format(players_mentions(left_player).replace("\n", ", "))
            text += get_string(lang, "player_action_text")
            bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            data["known_players"] = known_players
            return
    # game either ends/starts
    dp.chat_data[chat_id].clear()
    context.job.schedule_removal()
    if not len(data["players"]) == MAX_PLAYERS:
        bot.edit_message_reply_markup(chat_id, data["message"], reply_markup=None)
    if len(data["players"]) >= 3:
        group_settings = database.get_all_settings(chat_id)
        deck = Deck(group_settings["deck"])
        chameleon = random.choice(list(data["players"]))
        random.shuffle(data["players"])
        game_id = ''.join(random.choices(string.ascii_lowercase, k=10))
        dp.chat_data[chat_id].update({"chameleon": chameleon, "secret": deck.secret, "players": data["players"],
                                      "lang": lang, "starter": data["starter"], "words": deck.words,
                                      "game_id": game_id, "fewer": group_settings["fewer"],
                                      "tournament": group_settings["tournament"],
                                      "more": group_settings["more"], "pin": group_settings["pin"],
                                      "hardcore_game": {}, "deck": group_settings["deck"]})
        text = get_string(lang, "game_succeed").format(deck.topic, deck.word_list)
        button = InlineKeyboardMarkup([[InlineKeyboardButton(get_string(lang, "play_button"),
                                                             callback_data="word" + game_id)]])
        message = bot.send_message(chat_id, text, reply_to_message_id=data["message"], reply_markup=button,
                                   parse_mode=ParseMode.HTML)
        if group_settings["pin"]:
            pinned_message = context.bot.get_chat(chat_id).pinned_message
            if pinned_message:
                dp.chat_data[chat_id]["pin"] = pinned_message.message_id
            context.bot.pin_chat_message(chat_id, message.message_id, True)
        user = data["players"][0]
        text = get_string(lang, "first_player_say_word").format(mention_html(user["user_id"], user["first_name"]))
        bot.send_message(chat_id, text, reply_to_message_id=message.message_id, parse_mode=ParseMode.HTML)
        if group_settings["hardcore_game"]:
            chat = context.bot.get_chat(chat_id)
            dp.chat_data[chat_id]["hardcore_game"]["initial_permissions"] = chat.permissions
            context.bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
            if not is_admin(bot, user["user_id"], chat):
                context.bot.promote_chat_member(chat_id, user["user_id"], can_invite_users=True)
                dp.chat_data[chat_id]["hardcore_game"]["skip"] = False
            else:
                dp.chat_data[chat_id]["hardcore_game"]["skip"] = True
        dp.chat_data[chat_id]["word_list"] = message.message_id

    else:
        text = get_string(lang, "game_failed")
        bot.send_message(chat_id, text, reply_to_message_id=data["message"])
