import random
import database


def word_list(words):
    string = ""
    x = 0
    for word in words:
        if x == 3:
            string += word + "\n"
            x = -1
        else:
            string += word + ", "
        x += 1
    return string.strip()


class Deck:
    def __init__(self, deck_language, deck_name):
        deck = database.database.get_deck(deck_language, deck_name)
        choosen_deck = random.choice(list(deck))
        # get the content of the dict since it is packed in an additional id key
        # it only contains one key value pair
        self.topic = choosen_deck[choosen_deck.keys()[0]]
        self.words = deck[self.topic]
        self.word_list = word_list(self.words)
        self.secret = random.choice(deck[self.topic])
