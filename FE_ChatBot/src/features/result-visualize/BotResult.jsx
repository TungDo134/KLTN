import { useState } from "react";

import ResultSwitcher from "./ResultSwitcher";
import TextResult from "./TextResult";
import TimelineResult from "./TimelineResult";
import MindmapResult from "./MindmapResult";
import BestTimeBanner from "./BestTimeBanner";
import BudgetSummary from "./BudgetSummary";
import TravelTimingBanner from "./TravelTimingBanner";
import convertToMindmap from "../../helper/convertToMindmap";

function BotResult({ tripData }) {
  const [view, setView] = useState("text");
  const safeTripData =
    tripData && Array.isArray(tripData.days)
      ? tripData
      : { title: "Trip", days: [] };
  const language = safeTripData.language === "en" ? "en" : "vi";
  const budgetSummary = safeTripData.budget_summary ?? null;
  const timingAdvice = safeTripData.timing_advice ?? null;
  const showBudget = Boolean(budgetSummary);

  const timelineData = safeTripData.days;
  const mindmapData = convertToMindmap(safeTripData, language);

  return (
    <div className="rounded-xl p-4 max-w-3xl">
      {timingAdvice ? (
        <TravelTimingBanner advice={timingAdvice} language={language} />
      ) : (
        <BestTimeBanner
          bestTime={safeTripData.best_time}
          region={safeTripData.region}
          language={language}
        />
      )}
      <BudgetSummary summary={budgetSummary} language={language} />
      <ResultSwitcher view={view} setView={setView} language={language} />
      {view === "text" && (
        <TextResult
          data={timelineData}
          language={language}
          showBudget={showBudget}
        />
      )}
      {view === "timeline" && (
        <TimelineResult
          data={timelineData}
          language={language}
          showBudget={showBudget}
        />
      )}
      {view === "mindmap" && <MindmapResult data={mindmapData} />}
    </div>
  );
}

export default BotResult;
