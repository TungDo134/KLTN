import { FiAlertTriangle, FiCheckCircle, FiDollarSign } from "react-icons/fi";

import { formatVnd } from "./EntranceFeeBadge";

function BudgetSummary({ summary, language = "vi" }) {
  if (!summary) {
    return null;
  }

  const requestedBudget = Number(summary.requested_budget) || 0;
  const estimatedTotal = Number(summary.estimated_entrance_fee_total) || 0;
  const knownCount = Number(summary.known_fee_place_count) || 0;
  const unclassifiedCount = Number(summary.unclassified_fee_place_count) || 0;
  const totalCount = Number(summary.total_place_count) || 0;
  const isOverBudget = summary.status === "estimated_over_budget";
  const isPartial = summary.status === "partial";

  let statusText;
  if (isOverBudget) {
    const overAmount = formatVnd(
      Math.max(estimatedTotal - requestedBudget, 0),
      language,
    );
    statusText =
      language === "en"
        ? `Known entrance fees alone exceed the budget by about ${overAmount}.`
        : `Riêng phí tham quan đã biết đã vượt ngân sách khoảng ${overAmount}.`;
  } else if (isPartial) {
    statusText =
      language === "en"
        ? "There is not enough fee data to assess the whole trip."
        : "Chưa đủ dữ liệu phí để đánh giá toàn bộ chuyến đi.";
  } else {
    statusText =
      language === "en"
        ? "The estimated entrance fees are within the requested budget."
        : "Phí tham quan ước tính nằm trong ngân sách đã cung cấp.";
  }

  return (
    <section className="mb-4 mt-3 rounded-xl border border-neutral-800 bg-neutral-900/80 p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-lg bg-emerald-500/10 p-2 text-emerald-300">
          <FiDollarSign size={17} />
        </span>
        <h3 className="text-sm font-semibold text-neutral-100">
          {language === "en" ? "Budget transparency" : "Tổng quan về ngân sách"}
        </h3>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-black/20 px-3 py-2.5">
          <p className="text-xs text-neutral-400">
            {language === "en" ? "Requested budget" : "Ngân sách đã cung cấp"}
          </p>
          <p className="mt-1 text-sm font-semibold text-neutral-100">
            {formatVnd(requestedBudget, language)}
          </p>
        </div>
        <div className="rounded-lg bg-black/20 px-3 py-2.5">
          <p className="text-xs text-neutral-400">
            {language === "en"
              ? "Known entrance fees"
              : "Phí tham quan đã biết"}
          </p>
          <p className="mt-1 text-sm font-semibold text-neutral-100">
            {knownCount > 0
              ? formatVnd(estimatedTotal, language)
              : language === "en"
                ? "No classified fee data"
                : "Chưa có dữ liệu phí được phân loại"}
          </p>
        </div>
        <div className="rounded-lg bg-black/20 px-3 py-2.5">
          <p className="text-xs text-neutral-400">
            {language === "en" ? "Fee coverage" : "Mức độ bao phủ phí"}
          </p>
          <p className="mt-1 text-sm font-semibold text-neutral-100">
            {knownCount}/{totalCount}{" "}
            {language === "en" ? "places" : "địa điểm"}
          </p>
        </div>
      </div>

      {unclassifiedCount > 0 && (
        <p className="mt-3 flex items-center gap-2 text-xs text-amber-200">
          <FiAlertTriangle className="shrink-0" size={14} />
          {language === "en"
            ? `${unclassifiedCount} places have unclassified entrance fees.`
            : `${unclassifiedCount} địa điểm chưa phân loại phí tham quan.`}
        </p>
      )}

      <div
        className={`mt-3 flex items-start gap-2 rounded-lg border px-3 py-2.5 text-xs leading-relaxed ${
          isOverBudget
            ? "border-red-500/25 bg-red-500/10 text-red-200"
            : isPartial
              ? "border-amber-500/25 bg-amber-500/10 text-amber-200"
              : "border-emerald-500/25 bg-emerald-500/10 text-emerald-200"
        }`}
      >
        {isOverBudget || isPartial ? (
          <FiAlertTriangle className="mt-0.5 shrink-0" size={14} />
        ) : (
          <FiCheckCircle className="mt-0.5 shrink-0" size={14} />
        )}
        <span>{statusText}</span>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-neutral-500">
        {language === "en"
          ? "This estimate covers known entrance fees only; accommodation, food, transport, and incidental costs are not included."
          : "Ước tính chỉ bao gồm phí tham quan đã biết, chưa bao gồm lưu trú, ăn uống, di chuyển và chi phí phát sinh."}
      </p>
    </section>
  );
}

export default BudgetSummary;
