from unittest.mock import patch

from entertainment.enums import (
    EntertainmentCategory,
    GamesReviewDetailed,
    GamesReviewOverall,
    MyRate,
    WishlistCategory,
)


def test_games_review_overall_list_of_values():
    expected_result = ["Negative", "Mixed", "Positive"]
    assert GamesReviewOverall.list_of_values() == expected_result


def test_games_review_detailed_list_of_values():
    with patch("entertainment.enums.GamesReviewDetailed.list_of_values") as mocked_list:
        mocked_list.return_value = ["a", "b", "c"]
        assert GamesReviewDetailed.list_of_values() == ["a", "b", "c"]


def test_entertainment_category_list_of_values():
    with patch(
        "entertainment.enums.EntertainmentCategory.list_of_values"
    ) as mocked_list:
        mocked_list.return_value = ["a", "b", "c"]
        assert EntertainmentCategory.list_of_values() == ["a", "b", "c"]


def test_my_rate_list_of_values():
    with patch("entertainment.enums.MyRate.list_of_values") as mocked_list:
        mocked_list.return_value = ["a", "b", "c"]
        assert MyRate.list_of_values() == ["a", "b", "c"]


def test_wishlist_category_list_of_values():
    with patch("entertainment.enums.WishlistCategory.list_of_values") as mocked_list:
        mocked_list.return_value = ["a", "b", "c"]
        assert WishlistCategory.list_of_values() == ["a", "b", "c"]
