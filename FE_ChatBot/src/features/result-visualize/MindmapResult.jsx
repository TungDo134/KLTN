import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";

function MindmapResult({ data }) {
  const nodes = data.nodes;
  const edges = data.edges;

  return (
    <div className="mt-2 h-[460px] overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950 sm:h-[680px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.28 }}
        nodesConnectable={false}
        nodesDraggable={false}
      >
        <Background color="#334155" gap={20} />
        <MiniMap
          pannable
          zoomable
          nodeColor="#525252"
          maskColor="rgba(15, 23, 42, 0.72)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default MindmapResult;
