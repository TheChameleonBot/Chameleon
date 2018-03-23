import json
import random

def get():
    class Result:
        def __init__(self, topic, words, secret_word):
            self.topic = topic
            self.words = words
            self.secret_word = secret_word
    data_file = open('./list.json')
    data = json.load(data_file)
    random_topic = random.choice(data["standard"])
    word_list = data[random_topic]
    word_secret = random.choice(data[random_topic])
    result = Result(random_topic, word_list, word_secret)
    return result