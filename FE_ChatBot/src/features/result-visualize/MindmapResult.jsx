import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";

function MindmapResult({ data }) {
  const nodes = data.nodes;
  const edges = data.edges;

  return (
    <div className="mt-2 h-[460px] overflow-hidden rounded-xl border border-[var(--color-border-default)] bg-[var(--color-surface-panel)] sm:h-[680px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.28 }}
        nodesConnectable={false}
        nodesDraggable={false}
      >
        <Background color="var(--color-action-soft)" gap={20} />
        <MiniMap
          pannable
          zoomable
          nodeColor="var(--color-action-secondary)"
          maskColor="var(--color-overlay-mindmap)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default MindmapResult;
