import { useState } from "react";

import ResultSwitcher from "./ResultSwitcher";
import TextResult from "./TextResult";
import TimelineResult from "./TimelineResult";
import MindmapResult from "./MindmapResult";
import BestTimeBanner from "./BestTimeBanner";
import convertToMindmap from "../../helper/convertToMindmap";

function BotResult({ tripData }) {
  const [view, setView] = useState("text");
  const safeTripData =
    tripData && Array.isArray(tripData.days)
      ? tripData
      : { title: "Trip", days: [] };
  const language = safeTripData.language === "en" ? "en" : "vi";

  const timelineData = safeTripData.days;
  const mindmapData = convertToMindmap(safeTripData, language);

  return (
    <div className="rounded-xl p-4 max-w-3xl">
      <BestTimeBanner
        bestTime={safeTripData.best_time}
        region={safeTripData.region}
        language={language}
      />
      <ResultSwitcher view={view} setView={setView} language={language} />
      {view === "text" && <TextResult data={timelineData} language={language} />}
      {view === "timeline" && (
        <TimelineResult data={timelineData} language={language} />
      )}
      {view === "mindmap" && <MindmapResult data={mindmapData} />}
    </div>
  );
}

export default BotResult;
