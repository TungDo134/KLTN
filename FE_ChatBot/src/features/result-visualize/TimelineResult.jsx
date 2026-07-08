import { FiCalendar, FiClock, FiMapPin } from "react-icons/fi";

const DAY_TONES = [
  {
    header: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100",
    icon: "bg-emerald-500/20 text-emerald-300",
    dot: "bg-emerald-400 ring-emerald-500/20",
    chip: "border-emerald-500/20 bg-emerald-500/10 text-emerald-200",
  },
  {
    header: "border-sky-500/30 bg-sky-500/10 text-sky-100",
    icon: "bg-sky-500/20 text-sky-300",
    dot: "bg-sky-400 ring-sky-500/20",
    chip: "border-sky-500/20 bg-sky-500/10 text-sky-200",
  },
  {
    header: "border-amber-500/30 bg-amber-500/10 text-amber-100",
    icon: "bg-amber-500/20 text-amber-300",
    dot: "bg-amber-400 ring-amber-500/20",
    chip: "border-amber-500/20 bg-amber-500/10 text-amber-200",
  },
];

function getTags(tags) {
  return Array.isArray(tags) ? tags.filter(Boolean).slice(0, 3) : [];
}

function formatTimeRange(place) {
  if (place.arrival && place.departure) {
    return `${place.arrival} - ${place.departure}`;
  }

  return place.arrival || place.departure || "Chưa có giờ";
}

function TimelineResult({ data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div className="mt-2 rounded-lg border border-neutral-800 bg-neutral-900/70 px-4 py-3 text-sm text-neutral-400">
        Chưa có lịch trình để hiển thị.
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
                    Ngày {day.day}: {day.title}
                  </h3>
                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-0.5 text-xs text-neutral-300">
                    {places.length} địa điểm
                  </span>
                </div>
                {day.description && (
                  <p className="mt-1 text-sm text-neutral-300">
                    {day.description}
                  </p>
                )}
              </div>
            </div>

            <div className="relative ml-4 border-l border-neutral-700/80 pl-5">
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
                    <div className="rounded-lg border border-neutral-800 bg-neutral-900/80 px-4 py-3 shadow-sm">
                      <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-400">
                        <span className="inline-flex items-center gap-1">
                          <FiClock size={13} />
                          {formatTimeRange(place)}
                        </span>
                      </div>

                      <div className="mt-2 flex items-start gap-2">
                        <FiMapPin
                          className="mt-0.5 shrink-0 text-neutral-500"
                          size={15}
                        />
                        <div className="min-w-0">
                          <h4 className="text-sm font-medium text-neutral-100">
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
