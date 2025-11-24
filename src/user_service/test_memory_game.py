import pytest
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
    