import os
import json
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add current directory to path to ensure proper imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.schemas import Place, TripRequest, RecommendResult
from src.planning.planner import TripPlanner

def load_places_from_json(json_path: str, limit: int = 12) -> list[Place]:
    """
    Load a list of places from the merged JSON file and map to Place schema.
    """
    if not os.path.exists(json_path):
        print(f"Error: File not found at {json_path}")
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    places = []
    # Take first N places to demo
    for idx, item in enumerate(raw_data[:limit]):
        # Safely extract values
        geo = item.get("geo", {})
        rating = item.get("rating", {})
        time_info = item.get("time", {})
        
        # Convert opening hours dict to string format if exists
        opening_hours = None
        if time_info:
            opening_hours = f"{time_info.get('open', '08:00')} - {time_info.get('close', '18:00')}"
            
        place = Place(
            place_id=item.get("id"),
            name=item.get("name"),
            region=item.get("region"),
            lat=float(geo.get("lat", 0.0)),
            lng=float(geo.get("lng", 0.0)),
            tags=item.get("tags", []),
            rating=float(rating.get("score", 0.0)),
            avg_duration_minutes=item.get("avg_duration_minutes", 90),
            opening_hours=opening_hours,
            description=item.get("description", ""),
            # Higher index has lower initial recommend_score just to test sorting
            recommend_score=10.0 - (idx * 0.5) 
        )
        places.append(place)
    return places

def print_trip_plan(plan):
    """
    Print the planned itinerary in a human-readable, structured format.
    """
    print("\n" + "=" * 60)
    print("TRIP ITINERARY DETAILS")
    print("=" * 60)
    print(f"Query: {plan.trip_request.raw_query}")
    print(f"Region: {plan.trip_request.region} | Days: {plan.trip_request.days}")
    print(f"Total Places Scheduled: {plan.total_places}")
    
    total_travel_all_days = 0
    total_duration_all_days = 0
    
    for day_plan in plan.days:
        print(f"\n=== DAY {day_plan.day} ===")
        print(f"  Total Travel Time: {day_plan.total_travel_minutes} mins")
        print(f"  Total Visit Duration: {day_plan.total_duration_minutes} mins")
        
        total_travel_all_days += day_plan.total_travel_minutes
        total_duration_all_days += day_plan.total_duration_minutes
        
        if not day_plan.places:
            print("  (No places scheduled for this day)")
            continue
            
        for s_place in day_plan.places:
            p = s_place.place
            print(f"  -> [{s_place.order}] {p.name} ({p.place_id})")
            print(f"     Time: {s_place.arrival_time} - {s_place.departure_time}")
            print(f"     Visit Duration: {p.avg_duration_minutes} mins")
            if s_place.travel_time_from_prev > 0:
                print(f"     Travel Time from previous: {s_place.travel_time_from_prev} mins")
            print(f"     Rating: {p.rating} | GPS: ({p.lat:.4f}, {p.lng:.4f})")
            
    print("\n" + "=" * 60)
    print(f"SUMMARY OVERVIEW:")
    print(f"  Total Travel Time: {total_travel_all_days} mins (~{total_travel_all_days/60:.1f} hours)")
    print(f"  Total Attraction Time: {total_duration_all_days} mins (~{total_duration_all_days/60:.1f} hours)")
    print(f"  Grand Total Time: {total_travel_all_days + total_duration_all_days} mins")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    # Path to dataGemini Dalat json
    dalat_json_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), 
        "../CRAWL_DATA_CHATBOT/data/dataGemini/dalat_100_tourist_spots.json"
    ))
    
    print(f"Loading test data from: {dalat_json_path}")
    places = load_places_from_json(dalat_json_path, limit=12)
    print(f"Loaded {len(places)} places.")
    
    # Create request
    trip_request = TripRequest(
        raw_query="Du lich tu tuc Da Lat 3 ngay mat me, thien nhien",
        region="Đà Lạt",
        days=3,
        tags=["thiên nhiên", "khám phá"],
        budget=None,
        start_date=None
    )
    
    recommend_result = RecommendResult(
        places=places,
        trip_request=trip_request
    )
    
    # Test Greedy Nearest Neighbor
    print("\n>>> RUNNING PLANNING WITH GREEDY ROUTE OPTIMIZATION...")
    greedy_planner = TripPlanner(weight_mode="time", route_algorithm="greedy")
    greedy_plan = greedy_planner.plan(recommend_result)
    print_trip_plan(greedy_plan)
    
    # Test Dijkstra Path
    print("\n>>> RUNNING PLANNING WITH DIJKSTRA ROUTE OPTIMIZATION...")
    dijkstra_planner = TripPlanner(weight_mode="time", route_algorithm="dijkstra")
    dijkstra_plan = dijkstra_planner.plan(recommend_result)
    print_trip_plan(dijkstra_plan)

