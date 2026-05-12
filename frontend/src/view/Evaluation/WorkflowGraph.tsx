import React, { useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface Props {
  taskData: any;
  width?: number | string;
  height?: number | string;
}

const WorkflowGraph: React.FC<Props> = ({
  taskData,
  width = '100%',
  height = 420,
}) => {
  const { nodes, edges } = useMemo(() => {
    if (!taskData?.task_nodes || !Array.isArray(taskData.task_nodes)) {
      return { nodes: [], edges: [] };
    }

    const graphNodes: Node[] = taskData.task_nodes.map((node: any, index: number) => {
      const taskName = node.task || `Node-${index}`;

      return {
        id: taskName,
        data: {
          label: `${index + 1}. ${taskName}`,
        },
        position: {
          x: (index % 3) * 260,
          y: Math.floor(index / 3) * 140,
        },
        style: {
          border: '1px solid #d9d9d9',
          borderRadius: 12,
          padding: 10,
          background: '#fff',
          width: 180,
          fontSize: 14,
          textAlign: 'center' as const,
        },
      };
    });

    const graphEdges: Edge[] = Array.isArray(taskData.task_links)
      ? taskData.task_links.map((link: any, index: number) => ({
          id: `edge-${index}-${link.source}-${link.target}`,
          source: link.source,
          target: link.target,
        }))
      : [];

    return { nodes: graphNodes, edges: graphEdges };
  }, [taskData]);

  return (
    <div style={{ width, height }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default WorkflowGraph;