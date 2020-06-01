from uuid import uuid4

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from database import database
from handlers.dev import backup
from strings import get_string

players_games = []
players_tournaments = []
group_games = []
group_tournaments = []


def reload_sorted_players(context):
    for name in [players_games, players_tournaments, group_games, group_tournaments]:
        name.clear()
    players = database.get_player_games()
    for player in players:
        players_games.append(player["id"])
    players = database.get_player_tournaments()
    for player in players:
        players_tournaments.append(player["id"])
    groups = database.get_groups_games()
    for group in groups:
        group_games.append(group["id"])
    groups = database.get_groups_tournaments()
    for group in groups:
        group_tournaments.append(group["id"])
    # since this job runs once per day, we call the backup function from here
    backup(context.bot)


def percentage(part, whole):
    try:
        return round(100 * float(part)/float(whole), 2)
    except ZeroDivisionError:
        return 00.0


def stats_arguments(player, update):
    player_mention = mention_html(player["id"], update.effective_user.first_name)
    won_per = percentage(player["games_won"], player["games_played"])
    games_lost = player["games_played"] - player["games_won"]
    first_per = percentage(player["starter"], player["games_played"])
    cham_per = percentage(player["been_chameleon"], player["games_played"])
    won_cham_per = percentage(player["chameleon_won"], player["been_chameleon"])
    won_tour_per = percentage(player["tournaments_won"], player["tournaments_played"])
    tour_lost = player["tournaments_played"] - player["tournaments_won"]
    won_cham_towon_per = percentage(player["chameleon_won"], player["games_won"])
    # we need the plus one cause indexes start at one, :)
    try:
        position = players_games.index(player["id"]) + 1
    except ValueError:
        players_games.append(player["id"])
        position = players_games.index(player["id"]) + 1
        players_tournaments.append(player["id"])
    amount = len(players_games)
    second_position = players_tournaments.index(player["id"]) + 1
    arguments = [player["games_played"], player["games_won"], won_per, games_lost, player["starter"], first_per,
                 player["been_chameleon"], cham_per, player["chameleon_won"], won_cham_per, position,
                 player["tournaments_played"], player["tournaments_won"], won_tour_per, tour_lost, won_cham_towon_per,
                 amount, second_position]
    all_arguments = [player_mention] + arguments
    return all_arguments


def private_stats(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    player = database.get_player(update.effective_user.id)
    all_arguments = stats_arguments(player, update)
    text = get_string(user_data["lang"], "private_stats_text").format(*all_arguments)
    result_article = InlineQueryResultArticle(
            id=uuid4(),
            title=get_string(user_data["lang"], "private_stats_title"),
            description=get_string(user_data["lang"], "private_stats_description"),
            input_message_content=InputTextMessageContent(message_text=text, parse_mode="HTML"))
    if "old_games_played" in player.keys():
        text += get_string(user_data["lang"], "private_old_stats")
        result_article.input_message_content.message_text = text
        result_article.reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(
            get_string(user_data["lang"], "private_old_button"), "https://t.me/TheChameleonBot?start=stats")]])
    results = [result_article]
    update.inline_query.answer(results)


def private_stats_command(update: Update, context: CallbackContext):
    user_data = context.user_data
    if "lang" not in user_data:
        user_data["lang"] = database.get_language_player(update.effective_user.id)
    player = database.get_player(update.effective_user.id)
    all_arguments = stats_arguments(player, update)
    text = get_string(user_data["lang"], "private_stats_text").format(*all_arguments)
    if "old_games_played" not in player.keys():
        update.effective_message.reply_html(text)
        return
    all_games = player["old_games_played"] + player["games_played"]
    won_per = percentage(player["old_games_won"], player["old_games_played"])
    all_won = player["old_games_won"] + player["games_won"]
    all_won_per = percentage(all_won, all_games)
    lost = player["old_games_played"] - player["old_games_won"]
    all_lost = all_games - all_won
    start_per = percentage(player["old_starter"], player["old_games_played"])
    all_start = player["starter"] + player["old_starter"]
    all_start_per = percentage(all_start, all_games)
    cham_per = percentage(player["old_been_chameleon"], player["old_games_played"])
    all_cham = player["old_been_chameleon"] + player["been_chameleon"]
    all_cham_per = percentage(all_cham, all_games)
    all_arguments = [player["old_games_played"], all_games, player["old_games_won"], won_per, all_won, all_won_per,
                     lost, all_lost, player["old_starter"], start_per, all_start, all_start_per,
                     player["old_been_chameleon"], cham_per, all_cham, all_cham_per]
    text += get_string(user_data["lang"], "private_old_stats_command").format(*all_arguments)
    update.effective_message.reply_html(text)


def group_stats(update: Update, context: CallbackContext):
    chat_data = context.chat_data
    if "lang" not in chat_data:
        chat_data["lang"] = database.get_language_chat(update.effective_chat.id)
    stats = database.get_group_stats(update.effective_chat.id)
    try:
        position = group_games.index(update.effective_chat.id) + 1
    except ValueError:
        group_games.append(update.effective_chat.id)
        position = group_games.index(update.effective_chat.id) + 1
        group_tournaments.append(update.effective_chat.id)
    amount = len(group_games)
    second_position = group_tournaments.index(update.effective_chat.id) + 1
    text = get_string(chat_data["lang"], "group_stats").format(stats["games"], stats["tournaments"], position, amount,
                                                               second_position)
    update.effective_message.reply_text(text)
