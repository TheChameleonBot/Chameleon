class Player:
    def __init__(self, user_id, games_played=0, pm=False):
        self.id = user_id
        self.lang = "en"
        self.games_won = 0
        self.games_played = games_played
        self.been_chameleon = 0
        self.chameleon_won = 0
        self.games_started = 0
        self.starter = 0
        self.pm = pm
        self.tournaments_played = 0
        self.tournaments_won = 0
