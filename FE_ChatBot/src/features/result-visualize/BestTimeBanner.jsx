import { FiCalendar } from "react-icons/fi";

function formatBestTime(bestTime) {
  if (!bestTime) return null;

  return String(bestTime)
    .split("&")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => `Tháng ${part}`)
    .join(" hoặc ");
}

function BestTimeBanner({ bestTime, region }) {
  const label = formatBestTime(bestTime);

  if (!label) return null;

  return (
    <div className="mb-3 flex items-start gap-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-50">
      <FiCalendar className="mt-0.5 shrink-0 text-emerald-300" size={18} />
      <div>
        {/* Banner hien thi mua du lich phu hop nhat tu JSON trip plan cua backend. */}
        <p className="font-medium">
          Thời điểm đẹp nhất{region ? ` cho ${region}` : ""}
        </p>
        <p className="mt-1 text-emerald-100/80">{label}</p>
      </div>
    </div>
  );
}

export default BestTimeBanner;
