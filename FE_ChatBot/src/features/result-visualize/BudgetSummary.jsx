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
    <section className="mb-4 mt-3 rounded-xl border border-[var(--color-border-default)] bg-[var(--color-surface-panel)] p-4">
      <div className="flex items-center gap-2">
        <span className="rounded-lg bg-[var(--color-success-surface)] p-2 text-[var(--color-success-text)]">
          <FiDollarSign size={17} />
        </span>
        <h3 className="text-xl font-bold uppercase text-[var(--color-info-text)]">
          {language === "en" ? "Budget transparency" : "Tổng quan về ngân sách"}
        </h3>
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-[var(--color-surface-page)] px-3 py-2.5">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {language === "en" ? "Requested budget" : "Ngân sách đã cung cấp"}
          </p>
          <p className="mt-1 text-sm font-semibold text-[var(--color-text-primary)]">
            {formatVnd(requestedBudget, language)}
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-surface-page)] px-3 py-2.5">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {language === "en"
              ? "Known entrance fees"
              : "Phí tham quan đã biết"}
          </p>
          <p className="mt-1 text-sm font-semibold text-[var(--color-text-primary)]">
            {knownCount > 0
              ? formatVnd(estimatedTotal, language)
              : language === "en"
                ? "No classified fee data"
                : "Chưa có dữ liệu phí được phân loại"}
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-surface-page)] px-3 py-2.5">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {language === "en" ? "Fee coverage" : "Mức độ bao phủ phí"}
          </p>
          <p className="mt-1 text-sm font-semibold text-[var(--color-text-primary)]">
            {knownCount}/{totalCount}{" "}
            {language === "en" ? "places" : "địa điểm"}
          </p>
        </div>
      </div>

      {unclassifiedCount > 0 && (
        <p className="mt-3 flex items-center gap-2 text-xs text-[var(--color-warning-text)]">
          <FiAlertTriangle className="shrink-0" size={14} />
          {language === "en"
            ? `${unclassifiedCount} places have unclassified entrance fees.`
            : `${unclassifiedCount} địa điểm chưa phân loại phí tham quan.`}
        </p>
      )}

      <div
        className={`mt-3 flex items-start gap-2 rounded-lg px-3 py-2.5 text-xs leading-relaxed ${
          isOverBudget
            ? "border border-[var(--color-danger-border)] bg-[var(--color-danger-surface)] text-[var(--color-danger-text)]"
            : isPartial
              ? "border border-[var(--color-warning-border)] bg-[var(--color-warning-surface)] text-[var(--color-warning-text)]"
              : "border-0 bg-[var(--color-estimate-surface)] text-[var(--color-estimate-text)]"
        }`}
      >
        {isOverBudget || isPartial ? (
          <FiAlertTriangle className="mt-0.5 shrink-0" size={14} />
        ) : (
          <FiCheckCircle className="mt-0.5 shrink-0" size={14} />
        )}
        <span>{statusText}</span>
      </div>

      <p className="mt-3 text-xs leading-relaxed text-[var(--color-text-subtle)]">
        {language === "en"
          ? "This estimate covers known entrance fees only; accommodation, food, transport, and incidental costs are not included."
          : "Ước tính chỉ bao gồm phí tham quan đã biết, chưa bao gồm lưu trú, ăn uống, di chuyển và chi phí phát sinh."}
      </p>
    </section>
  );
}

export default BudgetSummary;
