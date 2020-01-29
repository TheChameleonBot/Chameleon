import yaml
import os
from string import Formatter


class String:
    def __init__(self):
        self.languages = {}
        self.reload_strings()

    def get_string(self, lang, string):
        try:
            return self.languages[lang][string]
        except KeyError:
            # a keyerror happened, the english file must have it
            return self.languages["en"][string]

    def reload_strings(self):
        for filename in os.listdir(r"./strings"):
            if filename.endswith(".yaml"):
                language_name = filename[:-5]
                self.languages[language_name] = yaml.safe_load(open(r"./strings/" + filename, encoding="utf8"))

    def new_strings(self, filename):
        try:
            new_language = yaml.safe_load(open(r"./strings/" + filename))
        except yaml.YAMLError as exc:
            return {"error": exc}
        if filename[:-5] == "en":
            new_strings = []
            new_arguments = []
            changed_strings = []
            for string in new_language:
                try:
                    old_string = self.languages["en"][string]
                    new_string = new_language[string]
                    pop_string = False
                    if isinstance(new_string, str):
                        old_argument = [tup[1] for tup in Formatter().parse(old_string) if tup[1] is not None]
                        new_argument = [tup[1] for tup in Formatter().parse(new_string) if tup[1] is not None]
                        if new_argument != old_argument:
                            new_arguments.append(string)
                            pop_string = True
                    if old_string != new_string and not pop_string:
                        changed_strings.append(string)
                        pop_string = True
                    if pop_string:
                        for language in self.languages:
                            if not language == "en":
                                self.languages[language].pop(string, None)
                                with open(r"./strings/" + language + ".yaml", 'w') as outfile:
                                    yaml.dump(self.languages[language], outfile, default_flow_style=False,
                                              sort_keys=False)
                except KeyError:
                    new_strings.append(string)
            self.reload_strings()
            return {"new_strings": new_strings, "new_arguments": new_arguments, "changed_strings": changed_strings}
        missing_strings = []
        missing_arguments = []
        for string in self.languages["en"]:
            try:
                translated_string = new_language[string]
            except KeyError:
                missing_strings.append(string)
                continue
            original_string = self.languages["en"][string]
            if isinstance(original_string, dict):
                if set(original_string) != set(translated_string):
                    missing_strings.append(string)
                    new_language.pop(string, None)
            elif isinstance(original_string, str):
                translated_argument = [tup[1] for tup in Formatter().parse(translated_string) if tup[1] is not None]
                original_argument = [tup[1] for tup in Formatter().parse(original_string) if tup[1] is not None]
                if translated_argument != original_argument:
                    missing_arguments.append(string)
                    new_language.pop(string, None)
        if missing_arguments:
            with open(r"./strings/" + filename, 'w') as outfile:
                yaml.dump(new_language, outfile, default_flow_style=False, sort_keys=False)
        self.reload_strings()
        return {"missing_arguments": missing_arguments, "missing_strings": missing_strings}

    def get_languages(self):
        to_return = {}
        for language in self.languages:
            to_return[language] = self.languages[language]["language"]
        return to_return

    def get_language(self, language):
        return self.languages[language]["language"]


strings = String()
