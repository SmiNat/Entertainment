from unittest.mock import patch

import pytest

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


def test_games_review_detailed_full_values():
    partial_result = set(
        [
            (1, "Very Negative"),
            (2, "Negative"),
            (3, "Mostly Negative"),
            (4, "Mixed"),
        ]
    )
    assert partial_result <= set(GamesReviewDetailed.full_values())


def test_games_review_detailed__get_all_exceeding_values():
    value = "Positive"
    exp_result = ["Positive", "Very Positive", "Overwhelmingly Positive"]
    assert exp_result == GamesReviewDetailed._get_all_exceeding_values(value)


def test_games_review_detailed__get_all_exceeding_values_error():
    value = "Invalid"
    with pytest.raises(ValueError) as exc_info:
        GamesReviewDetailed._get_all_exceeding_values(value)
    assert "The value 'Invalid' not found in the GamesReviewDetailed class." in str(
        exc_info.value
    )


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
