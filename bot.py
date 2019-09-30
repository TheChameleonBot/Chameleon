from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, Filters, MessageHandler)
import functools
import logging

from config import BOT_TOKEN, ADMINS
from constants import TRANSLATION_CHAT_ID
from handlers import group, game, dev, group_settings, private

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
    # a group starts a game
    dp.add_handler(CommandHandler("start", functools.partial(group.start, dp=dp), filters=Filters.group))
    dp.add_handler(CallbackQueryHandler(group.player_join, pattern="join"))
    # game running
    dp.add_handler(CommandHandler("abort_game", game.abort_game, Filters.group))
    dp.add_handler(MessageHandler(Filters.group & Filters.text, game.message))
    dp.add_handler(CallbackQueryHandler(game.secret_word, pattern="word"))
    dp.add_handler(CallbackQueryHandler(game.vote, pattern="vote"))
    dp.add_handler(CallbackQueryHandler(game.draw, pattern="draw"))
    dp.add_handler(MessageHandler(Filters.group & Filters.text, game.guess), 1)
    # group menu
    dp.add_handler(CommandHandler("settings", group_settings.group_setting, Filters.group))
    dp.add_handler(CommandHandler("start", group_settings.start, Filters.private))
    dp.add_handler(CommandHandler("admins_reload", group_settings.reload_admins))
    dp.add_handler(CallbackQueryHandler(group_settings.back, pattern="groupback"))
    dp.add_handler(CallbackQueryHandler(group_settings.refresh, pattern="(?=.*groupsetting)(?=.*refresh)"))
    # group language
    dp.add_handler(CallbackQueryHandler(group_settings.change_language, pattern=r"(?=.*groupsetting)(?=.*language)"))
    dp.add_handler(CallbackQueryHandler(group_settings.select_language, pattern=r"grouplanguage"))
    # group deck
    dp.add_handler(CallbackQueryHandler(group_settings.change_deck, pattern=r"(?=.*groupsetting)(?=.*deck)"))
    dp.add_handler(CallbackQueryHandler(group_settings.select_deck, pattern=r"deck"))
    # group fewer
    dp.add_handler(CallbackQueryHandler(group_settings.fewer, pattern=r"(?=.*groupsetting)(?=.*fewer)"))
    # group more
    dp.add_handler(CallbackQueryHandler(group_settings.more, pattern=r"(?=.*groupsetting)(?=.*more)"))
    # group tournament
    dp.add_handler(CallbackQueryHandler(group_settings.tournament, pattern=r"(?=.*groupsetting)(?=.*tournament)"))
    # group pin
    dp.add_handler(CallbackQueryHandler(group_settings.pin, pattern=r"(?=.*groupsetting)(?=.*pin)"))
    # group hardcore
    dp.add_handler(CallbackQueryHandler(group_settings.hardcore_game, pattern=r"(?=.*groupsetting)(?=.*hardcore)"))
    # group changes id
    dp.add_handler(MessageHandler(Filters.status_update.migrate, group.change_id))
    # change private language of a user
    dp.add_handler(CommandHandler("language", private.change_language, Filters.private))
    dp.add_handler(CallbackQueryHandler(private.selected_language, pattern="privatelanguage"))
    # more private commands
    dp.add_handler(CommandHandler("translation", private.translation, Filters.private))
    dp.add_handler(CommandHandler("deck", private.deck, Filters.private))
    # dev tools
    dp.add_handler(CommandHandler("id", dev.reply_id))
    dp.add_handler(CommandHandler("shutdown", functools.partial(dev.shutdown, updater=updater),
                                  Filters.user(208589966)))
    dp.add_handler(CommandHandler("translation", dev.yaml_file, Filters.chat(TRANSLATION_CHAT_ID)))
    dp.add_handler(MessageHandler(Filters.document.mime_type("text/plain") & Filters.user(ADMINS), dev.json_file))
    # take care of errors
    dp.add_error_handler(dev.error_handler)
    # start bot
    updater.start_polling(clean=True)
    updater.idle()


if __name__ == "__main__":
    main()
