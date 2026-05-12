import { useEffect, useRef } from 'react';
import { Graph } from '@antv/g6';
import { XMLParser } from 'fast-xml-parser';

const wrapText = (text: string, maxLength = 14) => {
  if (!text) return '';
  const result: string[] = [];
  let current = '';

  for (const char of text) {
    current += char;
    if (current.length >= maxLength) {
      result.push(current);
      current = '';
    }
  }

  if (current) result.push(current);
  return result.join('\n');
};

const normalizeXmlString = (xml: string) => {
  if (!xml || typeof xml !== 'string') return '';

  let result = xml.trim();

  result = result.replace(/^```xml\s*/i, '');
  result = result.replace(/^```\s*/i, '');
  result = result.replace(/```$/i, '');

  return result.trim();
};

const parseXMLToGraphData = (xmlData: string) => {
  const normalizedXml = normalizeXmlString(xmlData);

  if (!normalizedXml) {
    return { nodes: [], edges: [] };
  }

  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: '',
    parseAttributeValue: true,
    isArray: (name) => ['job', 'child', 'parent'].includes(name),
  });

  try {
    const parsedData = parser.parse(normalizedXml);
    const dagData = parsedData?.adag || parsedData?.adga || {};

    const nodes: any[] = [];
    const edges: any[] = [];

    const jobs = dagData?.job || [];
    jobs.forEach((job: any) => {
      const id = String(job?.id ?? '');
      const rawLabel = String(job?.name ?? id);

      if (id) {
        nodes.push({
          id,
          label: wrapText(rawLabel, 14),
          rawLabel,
        });
      }
    });

    const children = dagData?.child || [];
    children.forEach((child: any) => {
      const childId = String(child?.ref ?? '');
      const parents = child?.parent || [];

      parents.forEach((parent: any) => {
        const parentId = String(parent?.ref ?? '');
        if (parentId && childId) {
          edges.push({
            source: parentId,
            target: childId,
          });
        }
      });
    });

    return { nodes, edges };
  } catch (error) {
    console.error('parseXMLToGraphData error =', error);
    return { nodes: [], edges: [] };
  }
};

const parseTaskDataToGraphData = (taskData: any) => {
  if (!taskData || typeof taskData !== 'object') {
    return { nodes: [], edges: [] };
  }

  const rawNodes = Array.isArray(taskData?.task_nodes) ? taskData.task_nodes : [];
  const rawLinks = Array.isArray(taskData?.task_links) ? taskData.task_links : [];

  const nodes = rawNodes.map((node: any, index: number) => {
    const taskName = String(node?.task || node?.name || node?.label || `Node-${index + 1}`);
    return {
      id: taskName,
      label: wrapText(taskName, 14),
      rawLabel: taskName,
    };
  });

  const edges = rawLinks
    .filter((link: any) => link?.source && link?.target)
    .map((link: any) => ({
      source: String(link.source),
      target: String(link.target),
    }));

  return { nodes, edges };
};

interface FlowGraphProps {
  width?: string | number;
  height?: string | number;
  xmlData?: string;
  taskData?: any;
}

const FlowGraph = ({
  width = '100%',
  height = 420,
  xmlData,
  taskData,
}: FlowGraphProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const graphRef = useRef<Graph | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let graphData = { nodes: [], edges: [] };

    if (taskData) {
      graphData = parseTaskDataToGraphData(taskData);
    } else if (xmlData) {
      graphData = parseXMLToGraphData(xmlData);
    } else {
      return;
    }

    const graphWidth = containerRef.current.scrollWidth || 1000;
    const graphHeight =
      typeof height === 'number' ? height : containerRef.current.scrollHeight || 420;

    if (!graphRef.current) {
      graphRef.current = new Graph({
        container: containerRef.current,
        width: graphWidth,
        height: graphHeight,
        autoFit: 'view',
        behaviors: ['drag-canvas', 'zoom-canvas'],
        layout: {
          type: 'dagre',
          rankdir: 'LR',
          nodesep: 80,
          ranksep: 120,
        },
        node: {
          type: 'rect',
          style: {
            size: [120, 56],
            radius: 10,
            fill: '#ffffff',
            stroke: '#5B8FF9',
            lineWidth: 2,
            labelText: (d: any) => d.label || d.id,
            labelFill: '#1d1d1f',
            labelFontSize: 14,
            labelFontWeight: 600,
            labelPlacement: 'center',
          },
        },
        edge: {
          type: 'polyline',
          style: {
            stroke: '#94a3b8',
            lineWidth: 2,
            endArrow: true,
            radius: 10,
          },
        },
        data: graphData,
      });

      graphRef.current.render();
    } else {
      graphRef.current.setSize(graphWidth, graphHeight);
      graphRef.current.setData(graphData);
      graphRef.current.render();
    }

    return () => {
      if (graphRef.current) {
        graphRef.current.destroy();
        graphRef.current = null;
      }
    };
  }, [xmlData, taskData, height]);

  return (
    <div
      ref={containerRef}
      style={{
        width,
        height,
        background: '#f8fafc',
        borderRadius: 12,
        padding: 8,
      }}
    />
  );
};

export default FlowGraph;