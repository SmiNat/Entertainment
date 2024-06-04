from unittest.mock import patch

from entertainment.enums import GamesReviewDetailed, GamesReviewOverall


def test_games_review_overall_list_of_values():
    expected_result = ["Negative", "Mixed", "Positive"]
    assert GamesReviewOverall.list_of_values() == expected_result


def test_games_review_detailed_list_of_values():
    with patch("entertainment.enums.GamesReviewDetailed.list_of_values") as mocked_list:
        mocked_list.return_value = ["a", "b", "c"]
        assert GamesReviewDetailed.list_of_values() == ["a", "b", "c"]
