import { FiAlertTriangle, FiClock, FiMapPin } from "react-icons/fi";

function formatDateTime(value, language) {
  const match = String(value || "").match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/,
  );
  if (!match) return value || "-";

  const [, year, month, day, hour, minute] = match;
  return language === "en"
    ? `${month}/${day}/${year} ${hour}:${minute}`
    : `${hour}:${minute} ${day}/${month}/${year}`;
}

function formatMinutes(minutes, language) {
  const value = Number(minutes) || 0;
  const hours = Math.floor(value / 60);
  const remainder = value % 60;

  if (!hours) return `${remainder} ${language === "en" ? "min" : "phút"}`;
  if (!remainder) return `${hours} ${language === "en" ? "hr" : "giờ"}`;
  return `${hours} ${language === "en" ? "hr" : "giờ"} ${remainder} ${
    language === "en" ? "min" : "phút"
  }`;
}

function TravelTimingBanner({ advice, language = "vi" }) {
  if (!advice) return null;

  const safeWindow = advice.safe_departure_window || {};
  const breakdown = advice.duration_breakdown || {};
  const modeLabels = {
    car: language === "en" ? "Car" : "Ô tô",
    motorcycle: language === "en" ? "Motorcycle" : "Xe máy",
    plane: language === "en" ? "Plane" : "Máy bay",
  };
  const durationItems = [
    [
      language === "en" ? "Intercity travel" : "Di chuyển liên tỉnh",
      breakdown.intercity_travel_minutes,
    ],
    [
      language === "en" ? "Planned rests" : "Nghỉ dọc đường",
      breakdown.planned_rest_minutes,
    ],
    [
      language === "en" ? "To origin airport" : "Thời gian tới sân bay",
      breakdown.origin_airport_transfer_minutes,
    ],
    [
      language === "en" ? (
        "Check-in"
      ) : (
        <>
          Thời gian làm thủ tục <span className="font-bold">(dự kiến)</span>
        </>
      ),
      breakdown.check_in_minutes,
    ],
    [language === "en" ? "Flight" : "Thời gian bay", breakdown.flight_minutes],
    [
      language === "en"
        ? "From destination airport"
        : "Từ sân bay đến điểm đầu tiên theo lịch trình",
      breakdown.destination_airport_transfer_minutes,
    ],
    // [
    //   language === "en"
    //     ? "To the first stop"
    //     : "Thời gian từ trung tâm tới điểm đầu tiên",
    //   breakdown.local_transfer_minutes,
    // ],
    [
      language === "en" ? "Safety buffer" : "Thời gian dự phòng",
      breakdown.safety_buffer_minutes,
    ],
  ].filter(([, value]) => Number(value) > 0);

  return (
    <section className="mb-4 rounded-xl border border-sky-500/30 bg-sky-500/10 p-4 text-sky-50">
      <div className="flex items-start gap-3">
        <FiClock className="mt-0.5 shrink-0 text-sky-300" size={19} />
        <div className="min-w-0 flex-1">
          <p className="text-xl font-bold uppercase">
            {language === "en"
              ? "Recommended departure time"
              : "dự kiến giờ khởi hành"}
          </p>
          <p className="mt-1 text-lg font-bold text-white">
            {formatDateTime(advice.recommended_departure_at, language)}
          </p>
          <p className="mt-1 text-md text-sky-100/80">
            {language === "en" ? "Safe window" : "Khoảng an toàn"}:{" "}
            {formatDateTime(safeWindow.start, language)} –{" "}
            {formatDateTime(safeWindow.end, language)}
          </p>
        </div>
      </div>

      <div className="mt-3 flex items-start gap-2 text-xs text-sky-100/90">
        <FiMapPin className="mt-0.5 shrink-0" size={14} />
        <span className="flex flex-col gap-1">
          <span>
            {advice.origin_region} → {advice.destination_region}:{" "}
            {modeLabels[advice.mode] || advice.mode}
          </span>
          <span>
            {language === "en" ? "First stop" : "Điểm đầu tiên"}:{" "}
            {advice.target_first_place}
          </span>
        </span>
      </div>

      {durationItems.length > 0 && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {durationItems.map(([label, value]) => (
            <div
              key={label}
              className="flex justify-between gap-3 rounded-lg bg-black/20 px-3 py-2 text-xs"
            >
              <span className="text-sky-100/70">{label}</span>
              <span className="font-medium">
                {formatMinutes(value, language)}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2.5 text-xs leading-relaxed text-amber-100">
        <FiAlertTriangle className="mt-0.5 shrink-0" size={14} />
        <span>{advice.uncertainty_notice}</span>
      </div>
    </section>
  );
}

export default TravelTimingBanner;
