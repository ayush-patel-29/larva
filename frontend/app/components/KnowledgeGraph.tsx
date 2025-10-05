'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';

type D3Node = d3.SimulationNodeDatum & {
  id: string;
  label: string;
  importance?: number;
  frequency?: number;
  degree?: number;
  component?: number;
};

type D3Edge = {
  source: string;
  target: string;
  weight?: number;
  co_occurrence_count?: number;
};

interface KnowledgeGraphProps {
  data: {
    graph: {
      nodes: Array<{ id: string; label: string; size?: number; importance?: number; frequency?: number; degree?: number }>;
      edges: D3Edge[];
    };
    top_entities?: Array<{ name: string; importance?: number; frequency?: number; degree?: number }>;
  };
  onEntitySelect: (entityName: string) => void;
  onEntityDeselect: () => void;
  selectedEntity: string | null;
}

export function KnowledgeGraph({ data, onEntitySelect, onEntityDeselect, selectedEntity }: KnowledgeGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomBehaviorRef = useRef<d3.ZoomBehavior<Element, unknown> | null>(null);
  const [zoomK, setZoomK] = useState(1);
  const [showLabels, setShowLabels] = useState(true);
  const nodeSelRef = useRef<d3.Selection<SVGCircleElement, D3Node, any, any> | null>(null);
  const labelSelRef = useRef<d3.Selection<SVGTextElement, D3Node, any, any> | null>(null);

  const { nodes, edges } = useMemo(() => {
    const nodesIn = (data?.graph?.nodes || []).map((n) => ({
      id: n.id,
      label: n.label ?? n.id,
      importance: (n as any).importance ?? Math.max((n as any).size || 1, 1) / 5,
      frequency: n.frequency ?? 0,
      degree: n.degree ?? 0,
    })) as D3Node[];

    const nodeIdSet = new Set(nodesIn.map((n) => n.id));
    const edgesIn = (data?.graph?.edges || []).filter((e) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target));

    // Compute connected components for clustering
    const adj = new Map<string, string[]>();
    nodesIn.forEach((n) => adj.set(n.id, []));
    edgesIn.forEach((e) => {
      adj.get(e.source)!.push(e.target);
      adj.get(e.target)!.push(e.source);
    });
    let comp = 0;
    const visited = new Set<string>();
    for (const n of nodesIn) {
      if (visited.has(n.id)) continue;
      comp += 1;
      const stack = [n.id];
      visited.add(n.id);
      while (stack.length) {
        const cur = stack.pop()!;
        const curNode = nodesIn.find((x) => x.id === cur)!;
        curNode.component = comp;
        for (const nb of adj.get(cur) || []) {
          if (!visited.has(nb)) {
            visited.add(nb);
            stack.push(nb);
          }
        }
      }
    }

    // Ensure one connected component by adding light synthetic connectors between components
    const comps = Array.from(new Set(nodesIn.map((n) => n.component || 0))).sort((a, b) => a - b);
    const representativeByComp = new Map<number, string>();
    for (const c of comps) {
      const rep = nodesIn.find((n) => (n.component || 0) === c);
      if (rep) representativeByComp.set(c, rep.id);
    }
    const syntheticEdges: D3Edge[] = [];
    for (let i = 0; i < comps.length - 1; i++) {
      const a = representativeByComp.get(comps[i]);
      const b = representativeByComp.get(comps[i + 1]);
      if (a && b) syntheticEdges.push({ source: a, target: b, weight: 0.1 });
    }

    return { nodes: nodesIn, edges: [...edgesIn, ...syntheticEdges] };
  }, [data]);

  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;

    const width = Math.max(svgEl.clientWidth || 800, 300);
    const height = Math.max(svgEl.clientHeight || 600, 300);

    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();
    svg.attr('viewBox', `0 0 ${width} ${height}`).attr('preserveAspectRatio', 'xMidYMid meet');

    const container = svg.append('g');

    const zoomBehavior = d3
      .zoom()
      .scaleExtent([0.1, 6])
      .on('zoom', (event) => {
        container.attr('transform', event.transform);
        setZoomK(event.transform.k);
      });
    svg.call(zoomBehavior as any);
    zoomBehaviorRef.current = zoomBehavior as any;

    // Scales
    const sizeScale = d3
      .scaleSqrt()
      .domain(d3.extent(nodes.map((n) => Math.max(n.importance || 1, 0.5))) as [number, number])
      .range([6, 18]);
    const linkWidth = d3.scaleSqrt().domain(d3.extent(edges.map((e) => e.weight || 1)) as [number, number]).range([0.6, 3]);

    // Cluster centers laid out on a circle
    const comps = Array.from(new Set(nodes.map((n) => n.component || 0)));
    const r = Math.min(width, height) * 0.35;
    const centers = new Map<number, { x: number; y: number }>();
    comps.forEach((c, i) => {
      const angle = (2 * Math.PI * i) / Math.max(comps.length, 1);
      centers.set(c, { x: width / 2 + r * Math.cos(angle), y: height / 2 + r * Math.sin(angle) });
    });

    // Simulation
    const sim = d3
      .forceSimulation(nodes)
      .force(
        'link',
        d3
          .forceLink(edges as any)
          .id((d: any) => d.id)
          .distance((d: any) => 70 + 30 / Math.sqrt((d.weight || 1)))
          .strength(0.6)
      )
      .force('charge', d3.forceManyBody().strength(-80))
      .force('collide', d3.forceCollide().radius((d: any) => sizeScale(Math.max(d.importance || 1, 0.5)) + 6))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force(
        'clusterX',
        d3.forceX((d: any) => centers.get(d.component || 0)?.x ?? width / 2).strength(0.06)
      )
      .force(
        'clusterY',
        d3.forceY((d: any) => centers.get(d.component || 0)?.y ?? height / 2).strength(0.06)
      );

    // Draw links
    const link = container
      .append('g')
      .attr('stroke', '#9ca3af')
      .attr('stroke-opacity', 0.6)
      .selectAll('line')
      .data(edges)
      .enter()
      .append('line')
      .attr('stroke-width', (d) => linkWidth(d.weight || 1));

    // Draw nodes
    const node = container
      .append('g')
      .selectAll('circle')
      .data(nodes)
      .enter()
      .append('circle')
      .attr('r', (d) => sizeScale(Math.max(d.importance || 1, 0.5)))
      .attr('fill', (d) => (selectedEntity === d.id ? '#ef4444' : '#3b82f6'))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('click', (_, d) => {
        if (selectedEntity === d.id) onEntityDeselect();
        else onEntitySelect(d.id);
      })
      .on('mouseover', function () {
        d3.select(this).attr('stroke-width', 3);
      })
      .on('mouseout', function () {
        d3.select(this).attr('stroke-width', 2);
      });
    nodeSelRef.current = node as any;

    // Labels
    const label = container
      .append('g')
      .selectAll('text')
      .data(nodes)
      .enter()
      .append('text')
      .text((d) => d.label)
      .attr('font-size', '10px')
      .attr('text-anchor', 'middle')
      .attr('dy', (d) => sizeScale(Math.max(d.importance || 1, 0.5)) + 12)
      .attr('fill', '#374151')
      .style('pointer-events', 'none')
      .style('user-select', 'none')
      .style('display', showLabels ? 'block' : 'none');
    labelSelRef.current = label as any;

    sim.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('cx', (d: any) => d.x).attr('cy', (d: any) => d.y);

      label.attr('x', (d: any) => d.x).attr('y', (d: any) => d.y);
    });

    // Resize handling: refit on window resize
    const onResize = () => {
      const w = Math.max(svgEl.clientWidth || 800, 300);
      const h = Math.max(svgEl.clientHeight || 600, 300);
      svg.attr('viewBox', `0 0 ${w} ${h}`);
    };
    window.addEventListener('resize', onResize);

    return () => {
      window.removeEventListener('resize', onResize);
      sim.stop();
    };
  }, [nodes, edges, onEntitySelect, onEntityDeselect, showLabels]);

  // Only recolor nodes/labels when selection changes to avoid simulation jitter
  useEffect(() => {
    if (!nodeSelRef.current) return;
    nodeSelRef.current
      .transition()
      .duration(150)
      .attr('fill', (d: any) => (selectedEntity === d.id ? '#ef4444' : '#3b82f6'));
  }, [selectedEntity]);

  const reset = () => {
    if (!svgRef.current || !zoomBehaviorRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomBehaviorRef.current.transform as any, d3.zoomIdentity);
  };

  return (
    <div className="relative h-full">
      <div className="absolute top-4 right-4 z-10 bg-white rounded-lg shadow-sm border border-gray-200 p-2">
        <div className="flex items-center space-x-3">
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={showLabels}
              onChange={(e) => setShowLabels(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>Labels</span>
          </label>
          <div className="text-xs text-gray-500">Zoom: {(zoomK * 100).toFixed(0)}%</div>
          <button onClick={reset} className="text-xs px-2 py-1 border rounded hover:bg-gray-50">Reset</button>
        </div>
      </div>

      <svg ref={svgRef} width="100%" height="100%" className="border border-gray-200 rounded-lg" style={{ minHeight: '500px' }} />
    </div>
  );
}
