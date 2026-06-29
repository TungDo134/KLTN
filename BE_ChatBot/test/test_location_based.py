import pytest

from src.recommend.location_based import LocationBasedRecommender
from src.schemas import Place, TripRequest


def make_place(
    place_id: str,
    lat: float,
    lng: float,
) -> Place:
    return Place(
        place_id=place_id,
        name=place_id,
        region="Đà Lạt",
        lat=lat,
        lng=lng,
        tags=[],
        rating=4.0,
        avg_duration_minutes=60,
        opening_hours=None,
        description="test description",
    )


def make_request() -> TripRequest:
    return TripRequest(
        raw_query="Tôi muốn đi Đà Lạt",
        region="Đà Lạt",
        days=2,
        tags=[],
        budget=None,
        start_date=None,
    )


def test_haversine_returns_zero_for_same_point():
    recommender = LocationBasedRecommender()

    distance = recommender._haversine(11.903, 108.449, 11.903, 108.449)

    assert distance == pytest.approx(0.0)


def test_haversine_roughly_matches_one_latitude_degree():
    recommender = LocationBasedRecommender()

    distance = recommender._haversine(0.0, 0.0, 1.0, 0.0)

    assert distance == pytest.approx(111.19, rel=0.01)


def test_location_score_prefers_places_near_centroid_and_is_idempotent():
    recommender = LocationBasedRecommender()
    request = make_request()

    places = [
        make_place("near-a", 0.0, 0.0),
        make_place("near-b", 0.0, 0.01),
        make_place("far", 0.0, 1.0),
    ]

    first_result = recommender.score(places, request)
    first_scores = {place.place_id: place.recommend_score for place in first_result}

    second_result = recommender.score(places, request)
    second_scores = {place.place_id: place.recommend_score for place in second_result}

    assert first_scores == pytest.approx(second_scores)
    assert first_result[-1].place_id == "far"
    assert first_scores["far"] == pytest.approx(0.0)
    assert first_scores["near-a"] > first_scores["far"]
    assert first_scores["near-b"] > first_scores["far"]
