import {
  VerticalTimeline,
  VerticalTimelineElement,
} from "react-vertical-timeline-component";

import "react-vertical-timeline-component/style.min.css";

function TimelineResult({ data }) {
  return (
    <div className="mt-2">
      <VerticalTimeline lineColor="#3f3f46">
        {data.map((item, index) => (
          <VerticalTimelineElement
            key={index}
            date={item.day}
            contentStyle={{
              background: "#262626",
              color: "#fff",
              borderRadius: "12px",
              boxShadow: "none",
            }}
            contentArrowStyle={{
              borderRight: "7px solid #262626",
            }}
            iconStyle={{
              background: "#3b82f6",
              color: "#fff",
            }}
          >
            <h3 className="font-semibold text-base">{item.title}</h3>
            <p className="text-sm text-neutral-300">{item.description}</p>
          </VerticalTimelineElement>
        ))}
      </VerticalTimeline>
    </div>
  );
}

export default TimelineResult;
