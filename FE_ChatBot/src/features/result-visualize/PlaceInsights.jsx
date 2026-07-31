import { FiCheckCircle } from "react-icons/fi";

function PlaceInsights({ reasons, language = "vi" }) {
  const safeReasons = Array.isArray(reasons)
    ? reasons.filter(Boolean).slice(0, 3)
    : [];

  if (safeReasons.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 rounded-lg border border-[var(--color-border-default)] bg-[var(--color-surface-page)] px-3 py-2.5">
      <p className="text-xs font-semibold text-[var(--color-text-primary)]">
        {language === "en"
          ? "Why this place was recommended"
          : "Vì sao địa điểm này được đề xuất"}
      </p>
      <ul className="mt-2 space-y-1.5">
        {safeReasons.map((reason, index) => (
          <li
            key={`${reason}-${index}`}
            className="flex items-start gap-2 text-xs leading-relaxed text-[var(--color-text-primary)]"
          >
            <FiCheckCircle
              className="mt-0.5 shrink-0 text-[var(--color-success-accent)]"
              size={13}
            />
            <span>{reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default PlaceInsights;
