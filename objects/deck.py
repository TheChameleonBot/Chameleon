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
        self.topic = random.choice(list(deck))
        self.words = deck[self.topic]
        self.word_list = word_list(self.words)
        self.secret = random.choice(deck[self.topic])
