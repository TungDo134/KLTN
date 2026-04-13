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
from src.core.schemas import Place, TripRequest, ScheduledPlace, DayPlan, TripPlan


class Scheduler:

    START_HOUR = 8        # 08:00
    END_HOUR   = 21       # 21:00 — giới hạn cuối ngày

    def schedule(
        self,
        ordered_places_per_day: list[list[Place]],
        travel_matrix: dict,
        request: TripRequest,
    ) -> TripPlan:
        """
        Nhận vào danh sách places đã được chia theo ngày (và đã sort thứ tự tối ưu).
        Pseudo:
          day_plans = []
          for day_idx, places in enumerate(ordered_places_per_day):
            current_time = START_HOUR * 60  # minutes from midnight
            scheduled    = []
            for order, place in enumerate(places):
              travel_mins = travel_matrix[prev_id][place.place_id] if order > 0 else 0
              arrival     = current_time + travel_mins
              departure   = arrival + place.avg_duration_minutes

              if departure > END_HOUR * 60: break  # hết giờ trong ngày

              scheduled.append(ScheduledPlace(
                place=place, day=day_idx+1, order=order+1,
                arrival_time=_mins_to_hhmm(arrival),
                departure_time=_mins_to_hhmm(departure),
                travel_time_from_prev=travel_mins
              ))
              current_time = departure
              prev_id = place.place_id

            day_plans.append(DayPlan(...))

          return TripPlan(trip_request=request, days=day_plans, ...)
        """
        # TODO: implement
        pass

    def split_places_into_days(
        self, places: list[Place], num_days: int
    ) -> list[list[Place]]:
        """
        Chia đều list places thành num_days nhóm.
        Pseudo:
          chunk_size = ceil(len(places) / num_days)
          return [places[i:i+chunk_size] for i in range(0, len(places), chunk_size)]
        """
        # TODO: implement
        pass

    def _mins_to_hhmm(self, total_minutes: int) -> str:
        """
        Convert phút từ 00:00 sang chuỗi "HH:MM".
        Pseudo:
          h = total_minutes // 60
          m = total_minutes % 60
          return f"{h:02d}:{m:02d}"
        """
        # TODO: implement
        pass
