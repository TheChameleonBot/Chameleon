from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, Filters, MessageHandler, InlineQueryHandler)
import functools
import logging

from config import BOT_TOKEN
from constants import TRANSLATION_CHAT_ID
from handlers import group, game, dev, group_settings, private, stats

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO, filename="log.log")


def main():
    # since we are facing timeout error, I will keep increasing those until they are done
    updater = Updater(token=BOT_TOKEN, use_context=True,
                      request_kwargs={'read_timeout': 10, 'connect_timeout': 10})
    dp = updater.dispatcher
    # bot gets added to group
    dp.add_handler(MessageHandler(Filters.group & (Filters.status_update.chat_created | Filters.status_update.
                                                   new_chat_members),
                                  group.greeting))
    # deeplinking handler, making sure it can catch updates before the other ones
    dp.add_handler(CommandHandler("start", stats.private_stats_command, filters=Filters.regex("stats")))
    # a group starts a game
    dp.add_handler(CommandHandler("start", functools.partial(group.start, dp=dp), filters=Filters.group))
    dp.add_handler(CallbackQueryHandler(group.player_join, pattern="join"))
    # game running
    dp.add_handler(CommandHandler("abort_game", game.abort_game, Filters.group))
    dp.add_handler(MessageHandler(Filters.group & Filters.text & Filters.update.message, game.message))
    dp.add_handler(CallbackQueryHandler(game.secret_word, pattern="word"))
    dp.add_handler(CallbackQueryHandler(game.vote, pattern="vote"))
    dp.add_handler(CallbackQueryHandler(game.draw, pattern="draw"))
    dp.add_handler(MessageHandler(Filters.group & Filters.text, game.guess), 1)
    # nextgame list
    dp.add_handler(CommandHandler("nextgame", group.nextgame_command, Filters.group))
    dp.add_handler(CommandHandler("start", group.nextgame_start, Filters.private), 2)
    # general group commands
    # this one is also for private, yes. Not gonna make two callback for that
    dp.add_handler(CommandHandler("game_rules", group.game_rules))
    # group menu
    dp.add_handler(CommandHandler("settings", group_settings.group_setting, Filters.group))
    dp.add_handler(CommandHandler("start", group_settings.start, Filters.private))
    dp.add_handler(CommandHandler("admins_reload", group_settings.admins_reload, Filters.group))
    dp.add_handler(CallbackQueryHandler(group_settings.refresh, pattern="(?=.*groupsetting)(?=.*refresh)"))
    # group language
    dp.add_handler(CallbackQueryHandler(group_settings.change_language, pattern=r"(?=.*groupsetting)(?=.*language)"))
    dp.add_handler(CallbackQueryHandler(group_settings.select_language, pattern=r"grouplanguage"))
    # group deck
    dp.add_handler(CallbackQueryHandler(group_settings.change_deck, pattern=r"(?=.*groupsetting)(?=.*deck)"))
    dp.add_handler(CallbackQueryHandler(group_settings.select_deck_language, pattern=r"0deck"))
    dp.add_handler(CallbackQueryHandler(group_settings.select_deck, pattern=r"1deck"))
    # group fewer
    dp.add_handler(CallbackQueryHandler(group_settings.fewer, pattern=r"(?=.*groupsetting)(?=.*fewer)"))
    # group more
    dp.add_handler(CallbackQueryHandler(group_settings.more, pattern=r"(?=.*groupsetting)(?=.*more)"))
    # group tournament
    dp.add_handler(CallbackQueryHandler(group_settings.tournament, pattern=r"(?=.*groupsetting)(?=.*tournament)"))
    # group pin
    dp.add_handler(CallbackQueryHandler(group_settings.pin, pattern=r"(?=.*groupsetting)(?=.*pin)"))
    # group restrict
    dp.add_handler(CallbackQueryHandler(group_settings.restrict, pattern=r"(?=.*groupsetting)(?=.*restrict)"))
    # group exclamation
    dp.add_handler(CallbackQueryHandler(group_settings.exclamation, pattern=r"(?=.*groupsetting)(?=.*exclamation)"))
    # group changes
    dp.add_handler(MessageHandler(Filters.status_update.migrate, group.change_id))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_title, group.change_title))
    # change private language of a user
    dp.add_handler(CommandHandler("language", private.change_language, Filters.private))
    dp.add_handler(CallbackQueryHandler(private.selected_language, pattern="privatelanguage"))
    # more private commands
    dp.add_handler(CommandHandler("translation", private.translation, Filters.private))
    dp.add_handler(CommandHandler("deck", private.deck, Filters.private))
    dp.add_handler(CommandHandler("start", private.start, Filters.private), 1)
    dp.add_handler(CommandHandler("settings_help", private.settings_help, Filters.private))
    dp.add_handler(CallbackQueryHandler(private.settings_help_edit, pattern="settingshelp"))
    # stats
    dp.add_handler(InlineQueryHandler(stats.private_stats))
    dp.add_handler(CommandHandler("stats", stats.private_stats_command, filters=Filters.private))
    dp.add_handler(CommandHandler("stats", stats.group_stats, filters=Filters.group))
    # dev tools
    dp.add_handler(CommandHandler("id", dev.reply_id))
    dp.add_handler(CommandHandler("shutdown", functools.partial(dev.shutdown, updater=updater),
                                  Filters.user(208589966)))
    dp.add_handler(CommandHandler("upload", dev.upload, Filters.chat(TRANSLATION_CHAT_ID)))
    # help commands
    dp.add_handler(CommandHandler("help", group.help_message, Filters.group))
    dp.add_handler(CommandHandler("help", private.help_message, Filters.private))
    # take care of errors
    dp.add_error_handler(dev.error_handler)
    # start bot
    updater.start_polling(clean=True)
    updater.job_queue.run_repeating(stats.reload_sorted_players, 60*60*24, name="reload_sorted", first=0)
    updater.idle()


if __name__ == "__main__":
    main()
