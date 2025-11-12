class GameHistory:
    def __init__(self, session):
        self.session = session
    
    async def add_entry(self, id: int, game_type: str, score: int, daily_date):
        print(f"Mock, should save game history for user")
        pass

def get_game_history(db = None):
    return GameHistory(db)
