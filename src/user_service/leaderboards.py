class Leaderboards:
    def __init__(self, session):
        self.session = session

    async def update_score(self, id: int, game_type: str, played_date, next_play_time):
        print("Mock, should save to score to leaderboard for user")
        pass

def get_leaderboards(db = None):
    return Leaderboards(db)
