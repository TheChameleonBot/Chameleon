"""
This file contains collection of topics
Don't look for something important, just topics ;)
"""

import random
# Here we have a dict holding a whole collection of topics, we'll expand it

topics = {
    'cities': ['New York', 'Berlin', 'Tashkent', 'Mexiko', 'Pekin', 'Tunis'],
    'fruits': ['Apple', 'Banana', 'Orange', 'Mango'],
    'colors': ['White', 'Black', 'Blue', 'Red', 'Green', 'Yellow', 'Pink']
}

# This function chooses random topic and returns object of Result class. Class has 2 attributes: topic and words


def get():

    global topics

    class Result:
        def __init__(self, topic, words):
            self.topic = topic
            self.words = words

    random_topic = random.choice(list(topics.keys()))
    word_list = topics[random_topic]

    result = Result(random_topic, word_list)
    return result
