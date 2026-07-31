"""
planning/scheduler.py
Phân bổ địa điểm vào từng ngày và tính giờ cụ thể cho từng điểm dừng.

Logic phân bổ:
  - Chia đều địa điểm tối ưu vào N ngày (N = trip_request.days)
  - Mỗi ngày: bắt đầu 08:00, tự động tích lũy:
      arrival_time[i] = departure_time[i-1] + travel_time_to_i
      departure_time[i] = arrival_time[i] + place.avg_duration_minutes
  - Nếu departure > 21:00 → cắt, chuyển sang ngày hôm sau
"""
from src.schemas import Place, TripRequest, ScheduledPlace, DayPlan, TripPlan


class Scheduler:

    START_HOUR = 8        # 08:00
    END_HOUR   = 21       # 21:00 — giới hạn cuối ngày

    def schedule(
        self,
        ordered_places_per_day: list[list[Place]],
        travel_matrix: dict,
        request: TripRequest,
    ) -> TripPlan:
        day_plans = []
        total_places_count = 0
        carry_over = []
        
        for day_idx in range(request.days):
            current_time = self._start_minutes(request, day_idx)
            scheduled = []
            prev_id = None
            total_travel = 0
            total_duration = 0
            
            # Collect places for today: carry-overs first, then today's regular allocation
            day_places = []
            if carry_over:
                day_places.extend(carry_over)
                carry_over = []
            
            if day_idx < len(ordered_places_per_day):
                day_places.extend(ordered_places_per_day[day_idx])
                
            for place in day_places:
                travel_mins = 0
                if prev_id:
                    travel_mins = int(round(travel_matrix.get(prev_id, {}).get(place.place_id, 0.0)))
                
                arrival = current_time + travel_mins
                duration = place.avg_duration_minutes
                departure = arrival + duration
                
                # Check cutoff constraint (21:00)
                if departure > self.END_HOUR * 60:
                    carry_over.append(place)
                    continue
                
                scheduled.append(ScheduledPlace(
                    place=place,
                    day=day_idx + 1,
                    order=len(scheduled) + 1,
                    arrival_time=self._mins_to_hhmm(arrival),
                    departure_time=self._mins_to_hhmm(departure),
                    travel_time_from_prev=travel_mins
                ))
                
                total_travel += travel_mins
                total_duration += duration
                current_time = departure
                prev_id = place.place_id
                
            day_plans.append(DayPlan(
                day=day_idx + 1,
                places=scheduled,
                total_travel_minutes=total_travel,
                total_duration_minutes=total_duration
            ))
            total_places_count += len(scheduled)
            
        return TripPlan(
            trip_request=request,
            days=day_plans,
            total_places=total_places_count
        )

    def split_places_into_days(
        self, places: list[Place], num_days: int
    ) -> list[list[Place]]:
        import math
        if not places or num_days <= 0:
            return []
            
        chunk_size = math.ceil(len(places) / num_days)
        result = []
        for i in range(0, len(places), chunk_size):
            result.append(places[i:i+chunk_size])
            
        while len(result) < num_days:
            result.append([])
        return result

    def _mins_to_hhmm(self, total_minutes: int) -> str:
        h = (total_minutes // 60) % 24
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"

    def _start_minutes(self, request: TripRequest, day_idx: int) -> int:
        if day_idx != 0 or not request.day1_start_time:
            return self.START_HOUR * 60

        try:
            hour, minute = str(request.day1_start_time).split(":", 1)
            parsed = int(hour) * 60 + int(minute)
        except (TypeError, ValueError):
            return self.START_HOUR * 60

        if 0 <= parsed < 24 * 60:
            return parsed
        return self.START_HOUR * 60
