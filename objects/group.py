class Group:
    def __init__(self, group_id):
        self.id = group_id
        self.lang = "en"
        self.deck = "Standard"
        self.fewer = True
        self.more = True
        self.pin = False
        self.tournament = False
        self.hardcore_game = False
        self.games_played = 0
        self.tournaments_played = 0
