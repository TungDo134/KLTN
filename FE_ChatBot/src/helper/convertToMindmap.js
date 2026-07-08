const DAY_TONES = [
  {
    dayBg: "#064e3b",
    dayBorder: "#10b981",
    edge: "#10b981",
  },
  {
    dayBg: "#075985",
    dayBorder: "#38bdf8",
    edge: "#38bdf8",
  },
  {
    dayBg: "#92400e",
    dayBorder: "#f59e0b",
    edge: "#f59e0b",
  },
];

function getTags(tags) {
  return Array.isArray(tags) ? tags.filter(Boolean).slice(0, 3) : [];
}

function getTimeRange(place) {
  if (place.arrival && place.departure) {
    return `${place.arrival} - ${place.departure}`;
  }

  return place.arrival || place.departure || "";
}

function convertToMindmap(data) {
  const days = Array.isArray(data.days) ? data.days : [];
  const dayX = 340;
  const placeX = 720;
  const placeGap = 120;
  const groupGap = 190;

  let cursorY = 0;
  const groups = days.map((day) => {
    const places = Array.isArray(day.places) ? day.places : [];
    const groupHeight = Math.max(places.length - 1, 0) * placeGap;
    const topY = cursorY;
    const dayY = topY + groupHeight / 2;

    cursorY += groupHeight + groupGap;

    return {
      day,
      places,
      topY,
      dayY,
      groupHeight,
    };
  });

  const firstGroup = groups[0];
  const lastGroup = groups[groups.length - 1];
  const rootY =
    firstGroup && lastGroup ? (firstGroup.dayY + lastGroup.dayY) / 2 : 0;

  const nodes = [
    {
      id: "root",
      position: { x: 0, y: rootY },
      sourcePosition: "right",
      data: {
        label: [data.title || "Trip", data.region].filter(Boolean).join("\n"),
      },
      style: {
        background: "#1d4ed8",
        color: "white",
        border: "1px solid #60a5fa",
        borderRadius: 8,
        padding: 12,
        width: 230,
        whiteSpace: "pre-line",
        textAlign: "center",
        fontWeight: 600,
        lineHeight: 1.35,
      },
    },
  ];

  const edges = [];

  groups.forEach(({ day, places, topY, dayY }, dayIndex) => {
    const tone = DAY_TONES[dayIndex % DAY_TONES.length];
    const dayId = `day-${dayIndex}`;

    nodes.push({
      id: dayId,
      position: { x: dayX, y: dayY },
      sourcePosition: "right",
      targetPosition: "left",
      data: {
        label: [
          `Ngày ${day.day}`,
          `${places.length} địa điểm`,
          day.description,
        ]
          .filter(Boolean)
          .join("\n"),
      },
      style: {
        background: tone.dayBg,
        color: "white",
        border: `1px solid ${tone.dayBorder}`,
        borderRadius: 8,
        padding: 10,
        width: 230,
        whiteSpace: "pre-line",
        textAlign: "center",
        lineHeight: 1.35,
      },
    });

    edges.push({
      id: `e-root-${dayId}`,
      source: "root",
      target: dayId,
      style: { stroke: tone.edge, strokeWidth: 2 },
    });

    places.forEach((place, placeIndex) => {
      const placeId = `${dayId}-place-${placeIndex}`;
      const tags = getTags(place.tags).join(", ");
      const timeRange = getTimeRange(place);

      nodes.push({
        id: placeId,
        position: { x: placeX, y: topY + placeIndex * placeGap },
        targetPosition: "left",
        data: {
          label: [place.name, timeRange, tags].filter(Boolean).join("\n"),
        },
        style: {
          background: "#171717",
          color: "#e5e5e5",
          border: "1px solid #404040",
          borderRadius: 8,
          padding: 10,
          width: 260,
          whiteSpace: "pre-line",
          fontSize: 12,
          lineHeight: 1.35,
        },
      });

      edges.push({
        id: `e-${dayId}-${placeId}`,
        source: dayId,
        target: placeId,
        style: { stroke: tone.edge, strokeWidth: 1.5 },
      });
    });
  });

  return { nodes, edges };
}

export default convertToMindmap;
