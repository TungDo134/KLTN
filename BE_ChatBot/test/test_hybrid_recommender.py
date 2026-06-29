import pytest

from src.recommend.hybrid_recommender import HybridRecommender
from src.schemas import Place, TripRequest


class FakeRecommender:
    def __init__(self, scores: list[float]):
        self.scores = scores

    def score(self, places: list[Place], request: TripRequest) -> list[Place]:
        for place, score in zip(places, self.scores):
            place.recommend_score = score
        return places


def make_place(name: str) -> Place:
    return Place(
        place_id="same-id",
        name=name,
        region="Đà Lạt",
        lat=0.0,
        lng=0.0,
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


def test_hybrid_score_combines_weighted_scores_without_place_id_dependency():
    recommender = HybridRecommender(
        top_k=2,
        content_weight=0.6,
        location_weight=0.4,
    )
    recommender.content_rcm = FakeRecommender([1.0, 0.0, 0.5])
    recommender.location_rcm = FakeRecommender([0.0, 1.0, 0.5])

    places = [
        make_place("content-best"),
        make_place("location-best"),
        make_place("balanced"),
    ]

    result = recommender.score(places, make_request())

    assert result[0].name == "content-best"
    assert result[1].name == "balanced"
    assert result[2].name == "location-best"
    assert result[0].recommend_score == pytest.approx(0.6)
    assert result[1].recommend_score == pytest.approx(0.5)
    assert result[2].recommend_score == pytest.approx(0.4)


def test_recommend_returns_top_k_and_original_request():
    request = make_request()
    recommender = HybridRecommender(
        top_k=2,
        content_weight=0.6,
        location_weight=0.4,
    )
    recommender.content_rcm = FakeRecommender([1.0, 0.0, 0.5])
    recommender.location_rcm = FakeRecommender([0.0, 1.0, 0.5])

    places = [
        make_place("content-best"),
        make_place("location-best"),
        make_place("balanced"),
    ]

    result = recommender.recommend(places, request)

    assert result.trip_request is request
    assert len(result.places) == 2
    assert [place.name for place in result.places] == ["content-best", "balanced"]
