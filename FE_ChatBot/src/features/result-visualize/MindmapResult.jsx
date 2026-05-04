import ReactFlow, { Background, Controls } from "reactflow";
import "reactflow/dist/style.css";

function MindmapResult({ data }) {
  const nodes = data.nodes;
  const edges = data.edges;

  return (
    <div className="h-60 sm:h-100 mt-2 bg-neutral-900 rounded-xl">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}

export default MindmapResult;
