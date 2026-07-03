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

  const timelineData = safeTripData.days;
  const mindmapData = convertToMindmap(safeTripData);

  return (
    <div className="rounded-xl p-4 max-w-3xl">
      <BestTimeBanner
        bestTime={safeTripData.best_time}
        region={safeTripData.region}
      />
      <ResultSwitcher view={view} setView={setView} />
      {view === "text" && <TextResult data={timelineData} />}
      {view === "timeline" && <TimelineResult data={timelineData} />}
      {view === "mindmap" && <MindmapResult data={mindmapData} />}
    </div>
  );
}

export default BotResult;
