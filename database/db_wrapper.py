from pymongo import MongoClient
import objects
import logging
import os
import json


class Database:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Database init")
        self.db = MongoClient()
        self.db = self.db["chameleonbot"]
        self.cards = {}
        self.reload_decks()
        self.shutdown = False

    # get part group

    def get_language_chat(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group:
            return group["lang"]
        else:
            self.db["groups"].insert_one(vars(objects.Group(chat_id)))
            return "en"

    def get_deck_chat(self, chat_id):
        return self.db["groups"].find_one({"id": chat_id})["deck"]

    def get_deck(self, deck_language, deck_name):
        if deck_name == "all":
            # put all decks for a language in one object for special key
            return_deck = {}
            for deck in get_decks(deck_language):
                return_deck.update(deck)
            return return_deck
        else:
            return self.cards[deck_language][deck_name]

    def get_deck_languages(self):
        return self.cards.keys()

    def get_decks(self, deck_language):
        return self.cards[deck_language].keys()

    def get_fewer_setting(self, chat_id):
        return self.db["groups"].find_one({"id": chat_id})["fewer"]

    def get_more_setting(self, chat_id):
        return self.db["groups"].find_one({"id": chat_id})["more"]

    def get_all_settings(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if not group:
            self.db["groups"].insert_one(vars(objects.Group(chat_id)))
            group = vars(objects.Group(chat_id))
        entries_to_remove = {"id", "games_played", "_id"}
        for k in entries_to_remove:
            group.pop(k, None)
        return group

    def get_pin_setting(self, chat_id):
        return self.db["groups"].find_one({"id": chat_id})["pin"]

    def get_restrict_setting(self, chat_id):
        return self.db["groups"].find_one({"id": chat_id})["restrict"]

    def get_new_id(self, chat_id):
        existing = self.db["groups"].find_one({"old_id": chat_id})
        if existing:
            return existing["id"]

    def get_nextgame_ids(self, chat_id):
        return self.db["groups"].find_one({"id": chat_id})["nextgame"]

    def get_group_title(self, chat_id):
        to_return = {"title": "", "link": ""}
        group = self.db["groups"].find_one({"id": chat_id})
        to_return.update({"title": group["title"], "link": group["link"]})
        return to_return

    def get_group_stats(self, chat_id):
        to_return = {"games": 0, "tournaments": 0}
        group = self.db["groups"].find_one({"id": chat_id})
        to_return.update({"games": group["games_played"], "tournaments": group["tournaments_played"]})
        return to_return

    # get part player
    def get_new_player(self, player_ids):
        for player_id in player_ids:
            player = self.db["players"].find_one({"id": player_id})
            if player:
                if player["games_played"] == 0:
                    return True
            else:
                return True
        return False

    def get_language_player(self, user_id):
        player = self.db["players"].find_one({"id": user_id})
        if player:
            return player["lang"]
        else:
            self.db["players"].insert_one(vars(objects.Player(user_id)))
            return "en"

    def get_pm_player(self, user_id):
        # possible start point
        player = self.db["players"].find_one({"id": user_id})
        if not player:
            self.db["players"].insert_one(vars(objects.Player(user_id)))
            player = {"pm": False}
        return player["pm"]

    def get_player(self, user_id):
        player = self.db["players"].find_one({"id": user_id})
        # this should never happen, but just in case
        if not player:
            return False
        return player

    def get_player_games(self):
        return self.db["players"].find().sort("games_played", -1)

    def get_player_tournaments(self):
        return self.db["players"].find().sort("tournaments_played", -1)

    def get_groups_games(self):
        return self.db["groups"].find().sort("games_played", -1)

    def get_groups_tournaments(self):
        return self.db["groups"].find().sort("tournaments_played", -1)
    # insert part groups

    def end_game(self, chat_id, players, chameleon, winners, starter=False):
        self.db["groups"].update_one({"id": chat_id}, {"$inc": {"games_played": 1}})
        for player in players:
            updated = self.db["players"].find_one_and_update({"id": player}, {"$inc": {"games_played": 1}})
            if not updated:
                self.db["players"].insert_one(vars(objects.Player(player, 1)))
        if len(winners) == 1:
            # means chameleon won
            self.db["players"].update_one({"id": chameleon}, {"$inc": {"been_chameleon": 1, "chameleon_won": 1}})
        else:
            self.db["players"].update_one({"id": chameleon}, {"$inc": {"been_chameleon": 1}})
        self.db["players"].update_many({"id": {"$in": winners}}, {"$inc": {"games_won": 1}})
        if starter:
            self.db["players"].update_one({"id": starter}, {"$inc": {"games_started": 1}})
        self.db["players"].update_one({"id": players[0]}, {"$inc": {"starter": 1}})

    def end_tournament(self, chat_id, players, winners):
        self.db["groups"].update_one({"id": chat_id}, {"$inc": {"tournaments_played": 1}})
        self.db["players"].update_many({"id": {"$in": players}}, {"$inc": {"tournaments_played": 1}})
        self.db["players"].update_many({"id": {"$in": winners}}, {"$inc": {"tournaments_won": 1}})

    def insert_group_lang(self, chat_id, lang):
        self.db["groups"].update_one({"id": chat_id}, {"$set": {"lang": lang}})

    def insert_group_deck(self, chat_id, deck):
        self.db["groups"].update_one({"id": chat_id}, {"$set": {"deck": deck}})

    def insert_group_fewer(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group["fewer"]:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"fewer": False}})
            return False
        else:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"fewer": True}})
            return True

    def insert_group_more(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group["more"]:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"more": False}})
            return False
        else:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"more": True}})
            return True

    def insert_group_tournament(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group["tournament"]:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"tournament": False}})
            return False
        else:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"tournament": True}})
            return True

    def insert_group_pin(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group["pin"]:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"pin": False}})
            return False
        else:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"pin": True}})
            return True

    def insert_group_restrict(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group["restrict"]:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"restrict": False}})
            return False
        else:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"restrict": True}})
            return True

    def insert_group_exclamation(self, chat_id):
        group = self.db["groups"].find_one({"id": chat_id})
        if group["exclamation"]:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"exclamation": False}})
            return False
        else:
            self.db["groups"].update_one({"id": chat_id}, {"$set": {"exclamation": True}})
            return True

    def insert_group_new_id(self, old_id, new_id):
        self.db["groups"].update_one({"id": old_id}, {"$set": {"id": new_id, "old_id": old_id}})

    def insert_group_nextgame(self, chat_id, player_id):
        result = self.db["groups"].update_one({"id": chat_id}, {"$addToSet": {"nextgame": player_id}})
        if result.modified_count == 0:
            self.db["groups"].update_one({"id": chat_id}, {"$pull": {"nextgame": player_id}})
            return False
        return True

    def remove_group_nextgame(self, chat_id, player_ids):
        self.db["groups"].update_one({"id": chat_id}, {"$pull": {"nextgame": {"$in": player_ids}}})

    def insert_group_title(self, chat_id, title, link):
        self.db["groups"].update_one({"id": chat_id}, {"$set": {"title": title, "link": link}})

    # insert part player

    def insert_player_pm(self, user_id, boolean):
        self.db["players"].update_one({"id": user_id}, {"$set": {"pm": boolean}})

    def insert_player_lang(self, user_id, lang):
        self.db["players"].update_one({"id": user_id}, {"$set": {"lang": lang}})

    def init_shutdown(self):
        self.shutdown = True

    # reload part

    def reload_decks(self):
        deck_num = 0
        for filename in os.listdir('./decks'):
            if filename.endswith(".json"):
                temp = json.load(open('./decks/' + filename, encoding="UTF-8"))
                language = temp["language"]
                name = temp["name"]
                [temp.pop(key) for key in ["name", "language"]]
                temp_deck = {}
                # pack cards in an additional id key
                for card in temp:
                    temp_deck[deck_num] = temp
                    deck_num += 1
                if language in self.cards:
                    self.cards[language][name] = temp_deck
                else:
                    self.cards[language] = {name: temp_deck}


database = Database()
