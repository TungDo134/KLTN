import { FiAlertCircle, FiDollarSign } from "react-icons/fi";

export function formatVnd(amount, language = "vi") {
  const locale = language === "en" ? "en-US" : "vi-VN";
  const value = Number.isFinite(Number(amount)) ? Number(amount) : 0;
  return `${new Intl.NumberFormat(locale, {
    maximumFractionDigits: 0,
  }).format(value)} VND`;
}

export function formatKnownEntranceFeeTotal(
  amount,
  places,
  language = "vi",
) {
  const hasKnownFee =
    Array.isArray(places) &&
    places.some((place) => place.entrance_fee_status === "estimated");

  if (!hasKnownFee) {
    return language === "en"
      ? "No classified fee data"
      : "Chưa có dữ liệu phí được phân loại";
  }

  return formatVnd(amount, language);
}

function EntranceFeeBadge({ fee, status, language = "vi" }) {
  const isEstimated = status === "estimated" && Number(fee) > 0;

  return (
    <span
      className={`mt-2 inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-xs ${
        isEstimated
          ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
          : "border-amber-500/25 bg-amber-500/10 text-amber-200"
      }`}
    >
      {isEstimated ? <FiDollarSign size={13} /> : <FiAlertCircle size={13} />}
      {isEstimated
        ? `${language === "en" ? "Estimated fee" : "Phí ước tính"}: ${formatVnd(
            fee,
            language,
          )}`
        : language === "en"
          ? "Entrance fee not classified"
          : "Chưa phân loại phí tham quan"}
    </span>
  );
}

export default EntranceFeeBadge;
