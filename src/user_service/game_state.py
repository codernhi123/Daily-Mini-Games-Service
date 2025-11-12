class GameState:
    def __init__(self, session):
        self.session = session

    async def get_state(self, id: int, game_type: str):
        return None
    
    async def update_state(self, id: int, game_type: str, played_date, next_play_time):
        print(f"Mock, should save game state for user")
        pass

def get_game_state(db = None):
    return GameState(db)
