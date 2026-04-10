function convertToMindmap(data) {
  const nodes = [
    {
      id: "root",
      position: { x: 250, y: 0 },
      data: { label: data.title },
      style: { background: "#3b82f6", color: "white" },
    },
  ];

  const edges = [];

  data.days.forEach((day, index) => {
    const id = `day-${index}`;

    nodes.push({
      id,
      position: { x: index * 200, y: 150 },
      data: { label: `${day.title}` },
    });

    edges.push({
      id: `e-root-${id}`,
      source: "root",
      target: id,
    });
  });

  return { nodes, edges };
}

export default convertToMindmap;
