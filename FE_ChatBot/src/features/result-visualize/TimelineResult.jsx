import { FiCalendar, FiClock, FiMapPin } from "react-icons/fi";
import PlaceInsights from "./PlaceInsights";
import EntranceFeeBadge, {
  formatKnownEntranceFeeTotal,
} from "./EntranceFeeBadge";

const DAY_TONES = [
  {
    header:
      "border-[var(--color-success-border)] bg-[var(--color-success-surface)] text-[var(--color-success-text)]",
    icon:
      "bg-[var(--color-surface-panel)] text-[var(--color-success-accent)]",
    dot: "bg-[var(--color-success-text)] ring-[var(--color-success-surface)]",
    chip:
      "border-[var(--color-success-border)] bg-[var(--color-success-surface)] text-[var(--color-success-text)]",
  },
  {
    header:
      "border-[var(--color-info-border)] bg-[var(--color-info-surface)] text-[var(--color-info-text)]",
    icon: "bg-[var(--color-surface-panel)] text-[var(--color-info-accent)]",
    dot: "bg-[var(--color-info-accent)] ring-[var(--color-info-surface)]",
    chip:
      "border-[var(--color-info-border)] bg-[var(--color-surface-panel)] text-[var(--color-info-text)]",
  },
  {
    header:
      "border-[var(--color-warning-border)] bg-[var(--color-warning-surface)] text-[var(--color-warning-text)]",
    icon:
      "bg-[var(--color-surface-panel)] text-[var(--color-warning-accent)]",
    dot: "bg-[var(--color-warning-accent)] ring-[var(--color-warning-surface)]",
    chip:
      "border-[var(--color-warning-border)] bg-[var(--color-surface-panel)] text-[var(--color-warning-text)]",
  },
];

function getTags(tags) {
  return Array.isArray(tags) ? tags.filter(Boolean).slice(0, 3) : [];
}

function formatTimeRange(place, language) {
  if (place.arrival && place.departure) {
    return `${place.arrival} - ${place.departure}`;
  }

  return (
    place.arrival ||
    place.departure ||
    (language === "en" ? "Time unavailable" : "Chưa có giờ")
  );
}

function stripDayPrefix(title) {
  return String(title || "").replace(/^(Ngày|Day)\s+\d+\s*:\s*/i, "");
}

function TimelineResult({ data, language = "vi", showBudget = false }) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div className="mt-2 rounded-lg border border-[var(--color-border-default)] bg-[var(--color-surface-panel)] px-4 py-3 text-sm text-[var(--color-text-secondary)]">
        {language === "en"
          ? "No itinerary is available to display."
          : "Chưa có lịch trình để hiển thị."}
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-5">
      {data.map((day, dayIndex) => {
        const places = Array.isArray(day.places) ? day.places : [];
        const tone = DAY_TONES[dayIndex % DAY_TONES.length];

        return (
          <section key={`${day.day}-${dayIndex}`} className="space-y-3">
            <div
              className={`flex items-start gap-3 rounded-lg border px-4 py-3 ${tone.header}`}
            >
              <div className={`mt-0.5 rounded-md p-2 ${tone.icon}`}>
                <FiCalendar size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold">
                    {language === "en" ? "Day" : "Ngày"} {day.day}:{" "}
                    {stripDayPrefix(day.title)}
                  </h3>
                  <span className="rounded-full border border-[var(--color-border-default)] bg-[var(--color-surface-panel)] px-2 py-0.5 text-xs text-[var(--color-text-secondary)]">
                    {places.length}{" "}
                    {language === "en"
                      ? places.length === 1
                        ? "place"
                        : "places"
                      : "địa điểm"}
                  </span>
                  {showBudget && (
                    <span className="rounded-full border border-[var(--color-border-default)] bg-[var(--color-surface-panel)] px-2 py-0.5 text-xs text-[var(--color-text-secondary)]">
                      {language === "en" ? "Known fees" : "Phí đã biết"}: {" "}
                      {formatKnownEntranceFeeTotal(
                        day.estimated_entrance_fee_total,
                        places,
                        language,
                      )}
                    </span>
                  )}
                </div>
                {day.description && (
                  <p className="mt-1 text-sm text-[var(--color-text-primary)]">
                    {day.description}
                  </p>
                )}
              </div>
            </div>

            <div className="relative ml-4 border-l border-[var(--color-border-default)] pl-5">
              {places.map((place, placeIndex) => {
                const tags = getTags(place.tags);

                return (
                  <article
                    key={`${day.day}-${place.name}-${placeIndex}`}
                    className="relative pb-4 last:pb-0"
                  >
                    <span
                      className={`absolute -left-[29px] top-4 h-3 w-3 rounded-full ring-4 ${tone.dot}`}
                    />
                    <div className="rounded-lg border border-[var(--color-border-default)] bg-[var(--color-surface-panel)] px-4 py-3 shadow-sm">
                      <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                        <span className="inline-flex items-center gap-1">
                          <FiClock size={13} />
                          {formatTimeRange(place, language)}
                        </span>
                      </div>

                      <div className="mt-2 flex items-start gap-2">
                        <FiMapPin
                          className="mt-0.5 shrink-0 text-[var(--color-action-secondary)]"
                          size={15}
                        />
                        <div className="min-w-0">
                          <h4 className="text-sm font-medium text-[var(--color-text-primary)]">
                            {place.name}
                          </h4>
                          {tags.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {tags.map((tag) => (
                                <span
                                  key={`${place.name}-${tag}`}
                                  className={`rounded-full border px-2 py-0.5 text-xs ${tone.chip}`}
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                          {showBudget && (
                            <EntranceFeeBadge
                              fee={place.entrance_fee}
                              status={place.entrance_fee_status}
                              language={language}
                            />
                          )}
                          <PlaceInsights
                            reasons={place.recommendation_reasons}
                            language={language}
                          />
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

export default TimelineResult;
