import pytest

from src.recommend.content_based import ContentBasedRecommender
from src.schemas import Place, TripRequest


def make_place(
    place_id: str,
    tags: list[str],
    rating: float,
) -> Place:
    return Place(
        place_id=place_id,
        name=place_id,
        region="Đà Lạt",
        lat=0.0,
        lng=0.0,
        tags=tags,
        rating=rating,
        avg_duration_minutes=60,
        opening_hours=None,
        description="test description",
    )


def make_request(tags: list[str]) -> TripRequest:
    return TripRequest(
        raw_query="Tôi muốn đi Đà Lạt, thích cafe và thác nước",
        region="Đà Lạt",
        days=2,
        tags=tags,
        budget=None,
        start_date=None,
    )


def test_content_score_prioritizes_more_matching_tags():
    recommender = ContentBasedRecommender()
    request = make_request(["cafe", "thác nước"])

    places = [
        make_place("one-match", ["cafe", "view"], 4.0),
        make_place("two-matches", ["cafe", "thác nước", "view"], 4.0),
        make_place("no-match", ["bảo tàng"], 5.0),
    ]

    result = recommender.score(places, request)

    assert result[0].place_id == "two-matches"
    assert result[0].recommend_score > result[1].recommend_score
    assert result[1].recommend_score > result[2].recommend_score


def test_content_score_uses_rating_as_tie_breaker():
    recommender = ContentBasedRecommender()
    request = make_request(["cafe"])

    low_rating = make_place("low-rating", ["cafe", "view"], 3.0)
    high_rating = make_place("high-rating", ["cafe", "view"], 5.0)

    result = recommender.score([low_rating, high_rating], request)

    assert result[0].place_id == "high-rating"
    assert result[0].recommend_score > result[1].recommend_score


def test_jaccard_similarity_normalizes_case_and_spaces():
    recommender = ContentBasedRecommender()

    score = recommender._jaccard_similarity(
        [" Cafe ", "VIEW"],
        ["cafe", "view"],
    )

    assert score == pytest.approx(1.0)
