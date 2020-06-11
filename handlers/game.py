import random
import string
from html import escape
import logging

from telegram import (Update, InlineKeyboardMarkup, ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove,
                      ChatPermissions, InlineKeyboardButton)
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html
from spellchecker import SpellChecker

from database import database
from objects import Deck
from strings import get_string
from utils.helpers import is_admin
from utils.specific_helpers.game_helpers import wordlist, vote_buttons, draw_buttons, word_buttons
from utils.specific_helpers.group_helpers import no_game
from utils.helpers import player_mention_string


logger = logging.getLogger(__name__)
spell = SpellChecker()


def message(update: Update, context: CallbackContext):
    chat_data = context.chat_data
    # check if a game is running, could also be game_id or smth else
    if "chameleon" not in chat_data or "voted" in chat_data:
        return
    # this means every message counts anyway
    if not chat_data["restrict"]:
        if update.effective_message.text.startswith("!"):
            # if the exclamation setting is deactivated, every message starting with an ! is ignored
            if not chat_data["exclamation"]:
                return
            else:
                # if the exclamation setting is activated, only messages starting with an ! are valid
                # lets remove the !
                update.effective_message.text = update.effective_message.text[1:]
        else:
            # if the exclamation setting is activated, only messages starting with an ! are valid
            if chat_data["exclamation"]:
                return
    user_id = update.effective_user.id
    if user_id not in [user["user_id"] for user in chat_data["players"]]:
        return
    chat_id = update.effective_chat.id
    lang = chat_data["lang"]
    players = chat_data["players"]
    done = False
    for index, player in enumerate(players):
        if "word" not in player:
            if user_id == player["user_id"]:
                word = update.effective_message.text
                if len(word) > 103:
                    if update.effective_message.link:
                        word = f"<a href=\"{update.effective_message.link}\">{word[:100]}...</a>"
                    else:
                        word = f"{escape(word[:100])}..."
                else:
                    word = escape(word)
                players[index]["word"] = word
                try:
                    next_player = players[index + 1]
                    if chat_data["restrict"]:
                        try:
                            if not chat_data["restrict"]["skip"]:
                                context.bot.promote_chat_member(chat_id, player["user_id"], can_invite_users=False)
                            if not is_admin(context.bot, next_player["user_id"], update.effective_chat):
                                context.bot.promote_chat_member(chat_id, next_player["user_id"], can_invite_users=True)
                                chat_data["restrict"]["skip"] = False
                            else:
                                chat_data["restrict"]["skip"] = True
                        except BadRequest as e:
                            chat_data["restrict"] = False
                            database.insert_group_restrict(chat_id)
                            e.message += "handled in game, L50"
                            logger.info(e.message)
                except IndexError:
                    done = True
                    if chat_data["restrict"]:
                        try:
                            if not chat_data["restrict"]["skip"]:
                                context.bot.promote_chat_member(chat_id, player["user_id"], can_invite_users=False)
                            context.bot.set_chat_permissions(chat_id, chat_data["restrict"]["initial_permissions"])
                        except BadRequest as e:
                            chat_data["restrict"] = False
                            database.insert_group_restrict(chat_id)
                            e.message += "handled in game, L62"
                            logger.info(e.message)
                    break
                words = wordlist(players)
                restricted = ""
                if not chat_data["restrict"]:
                    if chat_data["exclamation"]:
                        restricted += "\n\n" + get_string(lang, "exclamation_activated")
                    else:
                        restricted += "\n\n" + get_string(lang, "exclamation_deactivated")
                text = get_string(lang, "more_players_say_word")\
                    .format(mention_html(next_player["user_id"], next_player["first_name"]), words, restricted)
                update.effective_message.reply_html(text)
                return
            else:
                break
    if done:
        chat_data["voted"] = []
        words = wordlist(players)
        text = get_string(lang, "final_word_list").format(words) + "\n" + get_string(lang, "vote_list").format(
            player_mention_string(chat_data["players"]))
        buttons = vote_buttons(chat_data["players"], chat_data["game_id"])
        v_message = update.effective_message.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons),
                                                        reply_to_message_id=chat_data["word_list"])
        if chat_data["pin"]:
            try:
                context.bot.pin_chat_message(chat_id, v_message.message_id, True)
            except BadRequest as e:
                chat_data["pin"] = False
                e.message += "handled in game L88"
                logger.info(e.message)


def secret_word(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    chat_data = context.chat_data
    game_id = query.data[4:]
    # somehow this button is there, but no game is running
    if "game_id" not in chat_data:
        no_game(update, context, "join_no_game_running")
        return
    # somehow this button is there, but another game is running
    elif chat_data["game_id"] != game_id:
        no_game(update, context, "wrong_game")
        return
    lang = chat_data["lang"]
    if user_id not in [user["user_id"] for user in chat_data["players"]]:
        query.answer(get_string(lang, "user_not_in_game"), show_alert=True)
        return
    if chat_data["chameleon"]["user_id"] == user_id:
        query.answer(get_string(lang, "player_is_chameleon"), show_alert=True)
    else:
        query.answer(get_string(lang, "secret_word").format(chat_data["secret"]), show_alert=True)


def vote(update: Update, context: CallbackContext):
    query = update.callback_query
    chat_data = context.chat_data
    user_id = update.effective_user.id
    game_id = query.data[4:14]
    # somehow this button is there, but no game is running
    if "game_id" not in chat_data:
        no_game(update, context, "join_no_game_running")
        return
    # somehow this button is there, but another game is running
    elif chat_data["game_id"] != game_id:
        no_game(update, context, "wrong_game")
        return
    vote_id = int(query.data[14:])
    lang = chat_data["lang"]
    if user_id not in [user["user_id"] for user in chat_data["players"]]:
        query.answer(get_string(lang, "user_not_in_game"), show_alert=True)
        return
    players = chat_data["players"]
    if user_id in chat_data["voted"]:
        query.answer(get_string(lang, "already_voted"), show_alert=True)
        return
    elif user_id == vote_id:
        query.answer(get_string(lang, "vote_yourself"), show_alert=True)
        return
    else:
        pass
    for player in players:
        if vote_id == player["user_id"]:
            if "votes" in player:
                player["votes"] += 1
            else:
                player["votes"] = 1
            break
    chat_data["voted"].append(user_id)
    query.answer(get_string(lang, "voted"))
    voters = players.copy()
    for voter_id in chat_data["voted"]:
        for index, voter in enumerate(voters):
            if voter["user_id"] == voter_id:
                del voters[index]
    if len(players) is not len(chat_data["voted"]):
        buttons = vote_buttons(players, chat_data["game_id"])
        words = wordlist(players)
        text = get_string(lang, "final_word_list").format(words) + "\n" + get_string(lang, "vote_list").\
            format(player_mention_string(voters))
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML)
    else:
        words = wordlist(players)
        text = get_string(lang, "final_word_list").format(words) + "\n" + get_string(lang, "vote_list").\
            format(player_mention_string(voters))
        query.edit_message_text(text, parse_mode=ParseMode.HTML)
        votes = []
        for player in players:
            if "votes" in player:
                votes.append((player["votes"], player["user_id"]))
            else:
                votes.append((0, player["user_id"]))
        # this works cause https://docs.python.org/3/howto/sorting.html#key-functions. Do I have any idea why? no
        votes = sorted(votes, key=lambda votes: votes[0], reverse=True)
        # this means, we have a draw, so the first person who had to say a word (cause disadvantage) can decide
        if votes[0][0] == votes[1][0]:
            same_votes = []
            for vote_number in votes:
                if vote_number[0] is not votes[0][0]:
                    break
                else:
                    voter_id = vote_number[1]
                    for player in players:
                        if player["user_id"] == voter_id:
                            same_votes.append({"user_id": voter_id, "first_name": player["first_name"]})
                            break
            text = get_string(lang, "draw").format(mention_html(players[0]["user_id"], players[0]["first_name"]))
            buttons = draw_buttons(same_votes, chat_data["game_id"])
            query.message.reply_html(text, reply_markup=InlineKeyboardMarkup(buttons), quote=False)
        else:
            chat_id = update.effective_message.chat.id
            unmasked_id = votes[0][1]
            who_wins(context, chat_id, unmasked_id)


def draw(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    chat_data = context.chat_data
    game_id = query.data[4:14]
    # somehow this button is there, but no game is running
    if "game_id" not in chat_data:
        no_game(update, context, "join_no_game_running")
        return
    # somehow this button is there, but another game is running
    elif chat_data["game_id"] != game_id:
        no_game(update, context, "wrong_game")
        return
    starter_id = chat_data["players"][0]["user_id"]
    lang = chat_data["lang"]
    if not user_id == starter_id:
        query.answer(get_string(lang, "not_starter"), show_alert=True)
        return
    unmasked_id = int(query.data[14:])
    if unmasked_id == user_id:
        query.answer(get_string(lang, "vote_yourself"), show_alert=True)
        return
    query.edit_message_reply_markup(None)
    chat_id = update.effective_message.chat.id
    who_wins(context, chat_id, unmasked_id)


def who_wins(context, chat_id, unmasked_id):
    chat_data = context.chat_data
    players = chat_data["players"]
    lang = chat_data["lang"]
    buttons = word_buttons(chat_data["words"], chat_data["exclamation"])
    if unmasked_id == chat_data["chameleon"]["user_id"]:
        chameleon_found = True
        text = None
        chat_data["guesses"] = 1
        if len(players) == 3:
            if chat_data["fewer"]:
                text = get_string(lang, "chameleon_found_fewer")
                chat_data["guesses"] = 2
        elif len(players) > 5:
            if chat_data["more"]:
                text = get_string(lang, "chameleon_found_more")
                button = InlineKeyboardMarkup([[InlineKeyboardButton(get_string(lang, "play_button"),
                                                                     callback_data="word" + chat_data["game_id"])]])
                hidden = get_string(lang, "hidden")
                context.bot.edit_message_text(get_string(lang, "game_succeed").format(hidden, hidden),
                                              chat_id, chat_data["word_list"], reply_markup=button, parse_mode="HTML")
                buttons = None
        if not text:
            text = get_string(lang, "chameleon_found")
        if chat_data["exclamation"]:
            text += "\n\n" + get_string(lang, "exclamation_activated")
        else:
            text += "\n\n" + get_string(lang, "exclamation_deactivated")
    else:
        text = get_string(lang, "chameleon_not_found")
        chameleon_found = False
    chameleon_id = chat_data["chameleon"]["user_id"]
    chameleon_mention = mention_html(chameleon_id, chat_data["chameleon"]["first_name"])
    if chameleon_found:
        if buttons:
            context.bot.send_message(chat_id, text.format(chameleon_mention),
                                     reply_markup=ReplyKeyboardMarkup(buttons, selective=True, resize_keyboard=True),
                                     parse_mode=ParseMode.HTML)
        else:
            context.bot.send_message(chat_id, text.format(chameleon_mention), parse_mode=ParseMode.HTML)
    else:
        vote_mention = None
        for player in players:
            if player["user_id"] == unmasked_id:
                vote_mention = mention_html(unmasked_id, player["first_name"])
                break
        text = text.format(vote_mention, chameleon_mention, chat_data["secret"])
        game_end(context, text, chat_id, chameleon_id, [chameleon_id], lang)


def guess(update: Update, context: CallbackContext):
    chat_data = context.chat_data
    if "guesses" not in chat_data:
        return
    user_id = update.effective_user.id
    chameleon_id = chat_data["chameleon"]["user_id"]
    if not user_id == chameleon_id:
        return
    lang = chat_data["lang"]
    word = update.effective_message.text
    if word.startswith("!"):
        # if the exclamation setting is deactivated, every message starting with an ! is ignored
        if not chat_data["exclamation"]:
            return
        else:
            # if the exclamation setting is activated, only messages starting with an ! are valid
            # lets remove the !
            word = word[1:]
    else:
        # if the exclamation setting is activated, only messages starting with an ! are valid
        if chat_data["exclamation"]:
            return
    chameleon_mention = mention_html(chameleon_id, chat_data["chameleon"]["first_name"])
    if word.lower() == chat_data["secret"].lower():
        text = get_string(lang, "chameleon_guess_right").format(chameleon_mention)
        game_end(context, text, update.effective_chat.id, chameleon_id, [chameleon_id], lang)
    else:
        # we try to guess a better spelled name
        spell_fix = spell.correction(word.lower())
        # this means there is a correction
        if spell_fix != word.lower():
            # we go through all possible candidates
            for fix in spell.candidates(word.lower()):
                if fix.lower() == chat_data["secret"].lower():
                    text = get_string(lang, "chameleon_guess_corrected").format(chameleon_mention)
                    game_end(context, text, update.effective_chat.id, chameleon_id, [chameleon_id], lang)
                    # the return is important
                    return
        if chat_data["guesses"] == 1:
            text = get_string(lang, "chameleon_guess_wrong").format(chameleon_mention, chat_data["secret"])
            players = []
            for player in chat_data["players"]:
                players.append(player["user_id"])
            game_end(context, text, update.effective_chat.id, chameleon_id, players, lang)
        else:
            chat_data["guesses"] = 1
            text = get_string(lang, "chameleon_guess_wrong_fewer").format(chameleon_mention)
            update.effective_message.reply_html(text)


def game_end(context, text, chat_id, chameleon_id, winner_ids, lang):
    chat_data = context.chat_data
    players = chat_data["players"]
    context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML, reply_markup=ReplyKeyboardRemove())
    context.bot.edit_message_reply_markup(chat_id, chat_data["word_list"], reply_markup=None)
    player_ids = []
    for player in players:
        player_ids.append(player["user_id"])
    if chat_data["tournament"]:
        tournament = chat_data["tournament"]
        # first game of tournament
        if not isinstance(tournament, dict):
            database.end_game(chat_id, player_ids, chameleon_id, winner_ids, chat_data["starter"]["user_id"])
            tournament = {}
            for player_id in player_ids:
                tournament[player_id] = 0
        else:
            database.end_game(chat_id, player_ids, chameleon_id, winner_ids)
        # that means the chameleon won
        if len(winner_ids) == 1:
            # that means the chameleon had to guess, but won, so gets a point, no one else does
            if "guesses" in chat_data:
                tournament[chameleon_id] += 1
            # that means the chameleon escaped undetected, so gets two points
            else:
                tournament[chameleon_id] += 2
        # that means everyone else won, they get two points
        else:
            for user_id in winner_ids:
                if user_id is not chameleon_id:
                    tournament[user_id] += 2
        tournament_winners = []
        for user_id in tournament:
            if tournament[user_id] >= 5:
                tournament_winners.append(user_id)
        # that means we have winner(s), the tournament is over
        if tournament_winners:
            database.end_tournament(chat_id, player_ids, tournament_winners)
            if len(tournament_winners) == 1:
                winner_mention = None
                contestant_mentions_points = []
                for player in players:
                    if player["user_id"] in tournament_winners:
                        winner_mention = mention_html(player["user_id"], player["first_name"])
                    else:
                        contestant_mentions_points.append(f"{mention_html(player['user_id'], player['first_name'])}: "
                                                          f"<b>{tournament[player['user_id']]}</b>")
                text = get_string(lang, "tournament_end_one").format(winner_mention, tournament[tournament_winners[0]],
                                                                     "\n".join(contestant_mentions_points))
            else:
                winner_mention_points = []
                contestant_mentions_points = []
                for player in players:
                    if player["user_id"] in tournament_winners:
                        winner_mention_points.append(f"{mention_html(player['user_id'], player['first_name'])}: "
                                                     f"<b>{tournament[player['user_id']]}</b>")
                    else:
                        contestant_mentions_points.append(f"{mention_html(player['user_id'], player['first_name'])}: "
                                                          f"<b>{tournament[player['user_id']]}</b>")
                text = get_string(lang, "tournament_end_several").format("\n".join(winner_mention_points),
                                                                         "\n".join(contestant_mentions_points))
            context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            if chat_data["pin"]:
                if not isinstance(chat_data["pin"], bool):
                    try:
                        context.bot.pin_chat_message(chat_id, chat_data["pin"], True)
                    except BadRequest as e:
                        if e.message != "Not enough rights to pin a message":
                            context.bot.unpin_chat_message(chat_id)
                            e.message += "handled in game L363"
                        else:
                            chat_data["pin"] = False
                            e.message += "handled in game L363, 2"
                        logger.info(e.message)
                else:
                    context.bot.unpin_chat_message(chat_id)
            chat_data.clear()
            chat_data["lang"] = lang
        # that means we dont, lets play another round
        else:
            chat_data["tournament"] = tournament
            for player in chat_data["players"]:
                player.pop("word", None)
                player.pop("votes", None)
            deck = Deck(*chat_data["deck"].split("_"))
            chameleon = random.choice(list(chat_data["players"]))
            chat_data["players"] = chat_data["players"][1:] + [chat_data["players"][0]]
            game_id = ''.join(random.choices(string.ascii_lowercase, k=10))
            chat_data.update({"chameleon": chameleon, "secret": deck.secret, "game_id": game_id, "words": deck.words})
            contestant_mentions_points = []
            for player in players:
                contestant_mentions_points.append(f"{mention_html(player['user_id'], player['first_name'])}: "
                                                  f"<b>{tournament[player['user_id']]}</b>")
            text = get_string(lang, "tournament_end").format("\n".join(contestant_mentions_points), deck.topic,
                                                             deck.word_list)
            button = InlineKeyboardMarkup([[InlineKeyboardButton(get_string(lang, "play_button"),
                                                                 callback_data="word" + game_id)]])
            send_message = context.bot.send_message(chat_id, text, reply_markup=button, parse_mode=ParseMode.HTML)
            if chat_data["pin"]:
                context.bot.pin_chat_message(chat_id, send_message.message_id, True)
            user = chat_data["players"][0]
            text = get_string(lang, "first_player_say_word").format(mention_html(user["user_id"], user["first_name"]))
            if not chat_data["restrict"]:
                if chat_data["exclamation"]:
                    text += "\n\n" + get_string(lang, "exclamation_activated")
                else:
                    text += "\n\n" + get_string(lang, "exclamation_deactivated")
            context.bot.send_message(chat_id, text, reply_to_message_id=send_message.message_id,
                                     parse_mode=ParseMode.HTML)
            if chat_data["restrict"]:
                context.bot.set_chat_permissions(chat_id, ChatPermissions(can_send_messages=False))
                if not is_admin(context.bot, user["user_id"], context.bot.get_chat(chat_id)):
                    context.bot.promote_chat_member(chat_id, user["user_id"], can_invite_users=True)
                    chat_data["restrict"]["skip"] = False
                else:
                    chat_data["restrict"]["skip"] = True
            chat_data["word_list"] = send_message.message_id
            # we dont care if other values exist or not, but this is needed in calculating of our points, so we pop it
            chat_data.pop("guesses", None)
            chat_data.pop("voted", None)
    else:
        database.end_game(chat_id, player_ids, chameleon_id, winner_ids, chat_data["starter"]["user_id"])
        if chat_data["pin"]:
            if not isinstance(chat_data["pin"], bool):
                try:
                    context.bot.pin_chat_message(chat_id, chat_data["pin"], True)
                except BadRequest as e:
                    if e.message != "Not enough rights to pin a message":
                        context.bot.unpin_chat_message(chat_id)
                        e.message += "handled in game L419"
                    else:
                        chat_data["pin"] = False
                        e.message += "handled in game L419, 2"
                    logger.info(e.message)
            else:
                context.bot.unpin_chat_message(chat_id)
        chat_data.clear()
        chat_data["lang"] = lang


def abort_game(update: Update, context: CallbackContext):
    chat_data = context.chat_data
    if "players" not in chat_data:
        chat_id = update.effective_chat.id
        lang = database.get_language_chat(chat_id)
        update.effective_message.reply_text(get_string(lang, "no_game_running"))
        return
    # sometimes a keyerror happens here. That can have different reasons, but this being an important command, I decided
    # to throw in an try expect
    try:
        lang = chat_data["lang"]
    except KeyError:
        lang = "en"
        chat_data["lang"] = "en"
    # little admin check
    if not is_admin(context.bot, update.effective_user.id, update.effective_chat):
        update.effective_message.reply_text(get_string(lang, "no_admin_abort"))
        return
    chat_id = update.effective_chat.id
    potential_job = context.job_queue.get_jobs_by_name(chat_id)
    if potential_job:
        potential_job[0].schedule_removal()
    chat_data.clear()
    update.effective_message.reply_text(get_string(lang, "abort_game"))
    chat_data["lang"] = lang
