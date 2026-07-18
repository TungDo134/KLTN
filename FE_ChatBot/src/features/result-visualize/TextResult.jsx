function stripDayPrefix(title) {
  return String(title || "").replace(/^(Ngày|Day)\s+\d+\s*:\s*/i, "");
}

function TextResult({ data, language = "vi" }) {
  return (
    <div className="text-neutral-200 leading-relaxed">
      <ul className="list-disc ml-6 mt-2 space-y-3">
        {data.map((item, index) => (
          <li key={index}>
            <div>
              {language === "en" ? "Day" : "Ngày"} {item.day}:{" "}
              {stripDayPrefix(item.title)}
              {item.description ? ` - ${item.description}` : ""}
            </div>

            {Array.isArray(item.places) && item.places.length > 0 && (
              <ul className="list-disc ml-6 mt-2 space-y-1 text-sm text-neutral-300">
                {item.places.map((place, placeIndex) => (
                  <li key={`${item.day}-${place.name}-${placeIndex}`}>
                    <span className="text-neutral-400">
                      {place.arrival} - {place.departure}
                    </span>
                    : {place.name}
                    {Array.isArray(place.tags) && place.tags.length > 0
                      ? ` (${place.tags.join(", ")})`
                      : ""}
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
