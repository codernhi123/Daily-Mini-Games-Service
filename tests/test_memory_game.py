import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from user_service.memory_game_service import MemoryGameService

class TestGetTodaysImages:
    def test_return_list_of_images(self):
        result = MemoryGameService.get_todays_images()
        assert isinstance(result, list)
        assert all(isinstance(img, str) for img in result)

class TestLevelConfiguration:
    def test_all_levels(self):
        configuration = MemoryGameService.level_configuration
        assert 1 in configuration
        assert 2 in configuration
        assert 3 in configuration
        assert 4 in configuration

    def test_scores_per_level(self):
        configuration = MemoryGameService.level_configuration
        assert configuration[1]["score"] < configuration[2]["score"] < configuration[3]["score"] < configuration[4]["score"]

class TestWeeklyImages:
    def test_all_days_have_images(self):
        images = MemoryGameService.weekly_images
        for day in range(7):
            assert day in images
            assert len(images[day]) >= 5

class TestMemoryGameService:
    def test_can_play_today_guest(self):
        async def run_test():
            mock_game_state = AsyncMock()
            mock_game_state.get_state.return_value = {"can_play": True}
            service = MemoryGameService(mock_game_state, None, None)
            result = await service.can_play_today(None)
            assert result["can_play"] is True
        asyncio.run(run_test())

    def test_start_game(self):
        async def run_test():
            mock_game_state = AsyncMock()
            mock_game_state.get_state.return_value = {"can_play": True}
            service = MemoryGameService(mock_game_state, None, None)
            result = await service.start_game(id=1, name="TestUser")
            assert result["can_play"] is True
            assert "session_id" in result
            assert result["level"] == 1
            assert result["is_guest"] is False
        asyncio.run(run_test())
    
    def test_start_game_guest(self):
        async def run_test():
            mock_game_state = AsyncMock()
            service = MemoryGameService(mock_game_state, None, None)
            result = await service.start_game()
            assert result["can_play"] is True
            assert result["is_guest"] is True  
        asyncio.run(run_test())

    def test_generate_level_data(self):
        service = MemoryGameService(None, None, None)
        level_data = service._generate_level_data(1)
        assert "images" in level_data
        assert "target" in level_data
        assert "correct_answer" in level_data
        assert len (level_data["images"]) == 12
        assert level_data["canvas_width"] == 800
        assert level_data["canvas_height"] == 800

    def test_submit_answer(self):
        async def run_test():
            mock_game_state = AsyncMock()
            service = MemoryGameService(mock_game_state, None, None)
            result = await service.start_game(id=1, name="Test1")
            session_id = result["session_id"]
            session = service.active_sessions[session_id]
            correct = session["current_level_data"]["correct_answer"]
            result = await service.submit_answer(session_id, correct)
            assert result["is_correct"] is True
            assert result["score"] == 10
            assert result["game_over"] is False
        asyncio.run(run_test())

    def test_submit_answer_invalid_session(self):
        async def run_test():
            service = MemoryGameService(None, None, None)
            with pytest.raises(ValueError, match="Invalid session ID"):
                await service.submit_answer("invalid_session", 5)
        asyncio.run(run_test())

    def test_complete_game_and_save_scores(self):
        async def run_test():
            mock_game_state = AsyncMock()
            mock_game_history = AsyncMock()
            mock_leaderboard = AsyncMock()
            mock_event_repo = AsyncMock()

            service = MemoryGameService(mock_game_state, mock_game_history, mock_leaderboard, mock_event_repo)

            result = await service.start_game(id=1, name="Test")
            session_id = result["session_id"]

            session = service.active_sessions[session_id]
            session["level"] = 4
            session["score"] = 90

            correct = session["current_level_data"]["correct_answer"]
            result = await service.submit_answer(session_id, correct)

            assert result["game_over"] is True
            assert result["score_saved"] is True

            mock_game_history.add_entry.assert_called_once()
            mock_leaderboard.update_scores.assert_called_once()
        asyncio.run(run_test())

    def test_can_play_today_locker(self):
        async def run_test():
            mock_game_state = AsyncMock()
            next_play = datetime.now(timezone.utc) + timedelta(hours=5)
            mock_game_state.get_state.return_value = {"can_play": False, "next_play_time": next_play}

            service = MemoryGameService(mock_game_state, None, None)
            result = await service.can_play_today(1)

            assert result["can_play"] is False
            assert "next_play_time" in result
            assert "message" in result
        asyncio.run(run_test())

    def test_wrong_answer_does_not_increase_score(self):
        async def run_test():
            mock_game_state = AsyncMock()
            service = MemoryGameService(mock_game_state, None, None)
            result = await service.start_game(id=1, name="Test")
            session_id = result["session_id"]

            session = service.active_sessions[session_id]
            correct = session["current_level_data"]["correct_answer"]
            wrong_answer = correct + 5
            result = await service.submit_answer(session_id, wrong_answer)
            assert result["is_correct"] is False
            assert result["score"] == 0
        asyncio.run(run_test())

    def test_guest_game_does_not_save(self):
        async def run_test():
            mock_game_state = AsyncMock()
            mock_game_history = AsyncMock()
            mock_leaderboard = AsyncMock()
            mock_event_repo = AsyncMock()

            service = MemoryGameService(mock_game_state, mock_game_history, mock_leaderboard, mock_event_repo)

            result = await service.start_game()
            session_id = result["session_id"]

            session = service.active_sessions[session_id]
            session["level"] = 4
            session["score"] = 100

            correct = session["current_level_data"]["correct_answer"]
            result = await service.submit_answer(session_id, correct)

            assert result["game_over"] is True
            assert result["score_saved"] is False

            mock_game_history.add_entry.assert_not_called()
            mock_leaderboard.update_scores.assert_not_called()
        asyncio.run(run_test())