import yaml
import os


class String:
    def __init__(self):
        self.languages = {}
        self.reload_strings()

    def get_string(self, lang, string):
        try:
            return self.languages[lang][string]
        except KeyError:
            pass
        # a keyerror happened, the english file must have it
        return self.languages["en"][string]

    def reload_strings(self):
        for filename in os.listdir(r"./strings"):
            if filename.endswith(".yaml"):
                language_name = filename[:-5]
                self.languages[language_name] = yaml.safe_load(open(r"./strings/" + filename))

    def get_languages(self):
        to_return = {}
        for language in self.languages:
            to_return[language] = self.languages[language]["language"]
        return to_return

    def get_language(self, language):
        return self.languages[language]["language"]


strings = String()
