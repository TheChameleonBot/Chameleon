class Group:
    def __init__(self, group_id):
        self.id = group_id
        self.old_id = None
        self.title = ""
        self.link = None
        self.lang = "en"
        self.deck = "English_Standard"
        self.fewer = True
        self.more = True
        self.pin = False
        self.tournament = False
        self.restrict = False
        self.exclamation = False
        self.games_played = 0
        self.tournaments_played = 0
        self.nextgame = []
