import random
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional, Dict, List, Any

class MemoryGameService:

    weekly_images = {
        0: ["apples", "oranges", "banana", "mango", "watermelon", "strawberry"],
        1: ["garlic", "lettuce", "broccoli", "carrot", "pepper", "tomato"],
        5: ["coffee", "eggs", "bread", "bacon", "salt", "waffle"],
        4: ["chicken", "cow", "horse", "sheep", "goat", "pig"],
        3: ["volleyball", "basketball", "soccerball", "badminton", "bowling", "football"],
        2: ["rainy", "sunny", "haily", "snowy", "stormy", "cloudy"],
        6: ["fish", "child", "dog", "door", "tipi"]
    }

    level_configuration = {
        1: {
            "count": 12,
            "score": 10,
            "recolor": False,
            "mirror": False,
            "minify": False,
            "description": "Regular Images"
        },
        2: {
            "count": 12,
            "score": 20,
            "recolor": True,
            "mirror": False,
            "minify": False,
            "description": "Recolored Images"
        },
        3: {
            "count": 12,
            "score": 30,
            "recolor": True,
            "mirror": True,
            "minify": False,
            "description": "Recolored and Mirrored Images"
        },
        4: {
            "count": 12,
            "score": 40,
            "recolor": True,
            "mirror": True,
            "minify": True,
            "description": "Recolored, Mirrored, and Minified Images"
        },
    }

    def __init__(self, game_state, game_history, leaderboard):
        self.game_state = game_state
        self.game_history = game_history
        self.leaderboard = leaderboard
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def get_todays_images() -> List[str]:
        day_of_the_week = date.today().weekday()
        return MemoryGameService.weekly_images[day_of_the_week]
    
    def _generate_level_data(self, level: int) -> Dict[str, Any]:
        configuration = self.level_configuration[level]
        todays_images = self.get_todays_images()
        images: List[Dict[str, Any]] = []

        target_image = random.choice(todays_images)
        correct_image_count = 0

        canvas_width = 800
        canvas_height = 800
        image_size = 120


        for _ in range(configuration["count"]):
            if random.random() < 0.40:
                filename = target_image
                correct_image_count += 1
            else:
                filename = random.choice(todays_images)
                if filename == target_image:
                    correct_image_count += 1

            x = random.randint(0, canvas_width - image_size)
            y = random.randint(0, canvas_height - image_size)

            image_data: Dict[str, Any] = {
                "filename": f"{filename}.png",
                "x": x,
                "y": y,
                "size": image_size,
            }

            if configuration["recolor"]:
                image_data["color"] = f"rgb({random.randint(50, 255)}, {random.randint(50, 255)}, {random.randint(50, 255)})"
        
            if configuration["mirror"] and random.random() < 0.50:
                image_data["mirror"] = True

            if configuration["minify"] and random.random() < 0.50:
                image_data["size"] = int(image_size * random.uniform(0.5, 0.7))

            images.append(image_data)

        return {
            "images": images,
            "target": target_image,
            "correct_answer": correct_image_count,
            "canvas_width": canvas_width,
            "canvas_height": canvas_height
        }
    
    async def can_play_today(self, id: int) -> Dict[str, Any]:
        # Use the new dict-based API from GameState
        state = await self.game_state.get_state(id, 'Memory')

        if state["can_play"]:
            return {"can_play": True}
             
        # if not state:
        #     return {"can_play": True}
        
        # today = date.today()
        # if state.last_played_date < today:
        #     return {"can_play": True}

        # user is locked
        next_play_time = state["next_play_time"]

        # if for some reason next_play_time is None, treat as can_play
        if next_play_time is None:
            return {"can_play": True}
        
        return {
            "can_play": False,
            "next_play_time": next_play_time.isoformat(),
            "message": "You have already played the memory game today"
        }
    
    async def start_game(self, id: Optional[int] = None) -> Dict[str, Any]:
        if id is not None:
            can_play = await self.can_play_today(id)
            if not can_play["can_play"]:
                return can_play
            
        level_data = self._generate_level_data(1)

        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = {
            "id": id,
            "level": 1,
            "score": 0,
            "current_level_data": level_data,
            "started_at": datetime.now(timezone.utc)
        }

        return {
            "can_play": True,
            "session_id": session_id,
            "level": 1,
            "level_description": self.level_configuration[1]["description"],
            "is_guest": id is None,
            "total_levels": 4
        }
    
    async def display_and_get_question(self, session_id: str) -> Dict[str, Any]:
        print(f"🔍 Looking for session_id: {session_id}")
        print(f"🔍 Active sessions: {list(self.active_sessions.keys())}")
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")
        
        session = self.active_sessions[session_id]
        level_data = session["current_level_data"]
        level = session["level"]

        return {
            "images": level_data["images"],
            "canvas_width": level_data["canvas_width"],
            "canvas_height": level_data["canvas_height"],
            "question": f"How many {level_data['target']} did you see?",
            "target": level_data["target"],
            "level": level,
            "level_description": self.level_configuration[level]["description"],
            "display_duration": 5
        }
    
    async def submit_answer(self, session_id: str, answer: int) -> Dict[str, Any]:
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")
        
        session = self.active_sessions[session_id]
        level = session["level"] 
        correct_answer = session["current_level_data"]["correct_answer"]

        is_correct = (answer == correct_answer)

        if is_correct:
            session["score"] += self.level_configuration[level]["score"]
        
        if level < 4:
            session["level"] += 1
            next_level = session["level"]
            session["current_level_data"] = self._generate_level_data(next_level)

            return {
                "is_correct": is_correct,
                "correct_answer": correct_answer,
                "score": session["score"],
                "game_over": False,
                "current_level": next_level,
                "level_description": self.level_configuration[next_level]["description"],
                "message": (
                    "Correct! Moving to the next level"
                    if is_correct
                    else f"Wrong! It was {correct_answer}, moving to the next level"
                ),
            }
        else: 
            return await self._complete_game(session_id, is_correct, correct_answer)
        
    async def _complete_game(self, session_id: str, last_answer: bool, correct_answer: int) -> Dict[str, Any]:
        session = self.active_sessions[session_id]
        id = session["id"]
        final_score = session["score"]

        now = datetime.now(timezone.utc)

        if id is not None:
            # today = date.today()
            # tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())
            # tomorrow = tomorrow.replace(tzinfo = timezone.utc)

            # await self.game_state.update_state(id, "memory", today, tomorrow)
            # await self.game_history.add_entry(id, "memory", final_score, today)
            # await self.leaderboard.update_score(id, "memory", final_score, today)

            # Next play time: next midnight UTC
            next_midnight = (
                (now + timedelta(days=1))
                .replace(hour=0, minute=0, second=0, microsecond=0)
            )

            # Persist state + history
            await self.game_state.update_state(id, "Memory", now, next_midnight)
            await self.game_history.add_entry(id, "Memory", final_score, now)

            # Leaderboard wants the current time in UTC
            await self.leaderboard.update_scores(id, "NULL", final_score, "Memory", now, now)

        del self.active_sessions[session_id]

        message_suffix = (
            "All levels complete!"
            if last_answer
            else f"Wrong! Last answer was {correct_answer}"
        )

        return {
                "is_correct": last_answer,
                "correct_answer": correct_answer,
                "game_over": True,
                "final_score": final_score,
                "max_score": 100,
                "score_saved": id is not None,
                "message": "Game complete! " + message_suffix,
            }
    
    def cleanup_inactive_sessions(self):
        now = datetime.now(timezone.utc)
        expired: List[str] = []

        for session_id, session in self.active_sessions.items():
            age = (now - session["started_at"]).total_seconds()
            if age > 3600:
                expired.append(session_id)

        for session_id in expired:
            del self.active_sessions[session_id]

def get_memory_game_service(game_state = None, game_history = None, leaderboard = None) -> MemoryGameService:
    return MemoryGameService(game_state, game_history, leaderboard)