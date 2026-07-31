import PlaceInsights from "./PlaceInsights";
import EntranceFeeBadge, {
  formatKnownEntranceFeeTotal,
} from "./EntranceFeeBadge";

function stripDayPrefix(title) {
  return String(title || "").replace(/^(Ngày|Day)\s+\d+\s*:\s*/i, "");
}

function TextResult({ data, language = "vi", showBudget = false }) {
  return (
    <div className="text-[var(--color-text-primary)] leading-relaxed">
      <ul className="list-disc ml-6 mt-2 space-y-3">
        {data.map((item, index) => (
          <li key={index}>
            <div>
              {language === "en" ? "Day" : "Ngày"} {item.day}:{" "}
              {stripDayPrefix(item.title)}
              {item.description ? ` - ${item.description}` : ""}
            </div>
            {showBudget && (
              <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                {language === "en"
                  ? "Known entrance fees for the day"
                  : "Phí tham quan đã biết trong ngày"}
                : {" "}
                {formatKnownEntranceFeeTotal(
                  item.estimated_entrance_fee_total,
                  item.places,
                  language,
                )}
              </p>
            )}

            {Array.isArray(item.places) && item.places.length > 0 && (
              <ul className="list-disc ml-6 mt-2 space-y-1 text-sm text-[var(--color-text-primary)]">
                {item.places.map((place, placeIndex) => (
                  <li key={`${item.day}-${place.name}-${placeIndex}`}>
                    <div>
                      <span className="text-[var(--color-text-secondary)]">
                        {place.arrival} - {place.departure}
                      </span>
                      : {place.name}
                      {Array.isArray(place.tags) && place.tags.length > 0
                        ? ` (${place.tags.join(", ")})`
                        : ""}
                    </div>
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
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default TextResult;
