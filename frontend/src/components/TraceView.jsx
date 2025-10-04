import { useEffect, useMemo, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { postTrace } from '../api';

const layout = { name: 'cose', animate: false, fit: true };

const defaultStyle = [
  {
    selector: 'node',
    style: {
      'background-color': '#2563eb',
      color: '#0f172a',
      'border-width': 2,
      'border-color': '#1e293b',
      label: 'data(label)',
      'font-size': 10,
      'text-wrap': 'wrap',
      'text-max-width': 120,
    },
  },
  {
    selector: 'node[isAnomaly = "true"]',
    style: { 'background-color': '#dc2626', color: '#ffffff' },
  },
  {
    selector: 'node[isSanctioned = "true"]',
    style: { 'border-color': '#9333ea', 'border-width': 4 },
  },
  {
    selector: 'edge',
    style: {
      width: 2,
      'line-color': '#94a3b8',
      'target-arrow-color': '#94a3b8',
      'target-arrow-shape': 'triangle',
      label: 'data(label)',
      'font-size': 8,
      'edge-text-rotation': 'autorotate',
    },
  },
];

function formatValueWei(valueWei) {
  if (!valueWei) return '0 ETH';
  return `${(Number(valueWei) / 1e18).toFixed(4)} ETH`;
}

function buildElements(data) {
  if (!data) return [];
  const clusterPalette = ['#06b6d4', '#10b981', '#f97316', '#f59e0b', '#8b5cf6'];
  const clusterMap = new Map();

  const nodes = data.nodes.map((node) => {
    const clusterId = node.cluster_id || 'unclustered';
    if (!clusterMap.has(clusterId)) {
      const color = clusterPalette[clusterMap.size % clusterPalette.length];
      clusterMap.set(clusterId, color);
    }

    return {
      data: {
        id: node.address,
        label: `${node.address}\nCluster: ${clusterId}`,
        isAnomaly: node.is_anomaly ? 'true' : 'false',
        isSanctioned: node.is_sanctioned ? 'true' : 'false',
        clusterColor: clusterMap.get(clusterId),
      },
      style: {
        'background-color': node.is_anomaly ? '#dc2626' : clusterMap.get(clusterId),
      },
    };
  });

  const edges = data.edges.map((edge) => ({
    data: {
      id: edge.tx_hash || `${edge.source}->${edge.target}`,
      source: edge.source,
      target: edge.target,
      label: `${formatValueWei(edge.value_wei)}\nBlock ${edge.block_number || 'n/a'}`,
    },
  }));

  return [...nodes, ...edges];
}

export default function TraceView({ defaultFrom = '', defaultTo = '' }) {
  const [form, setForm] = useState({
    from: defaultFrom,
    to: defaultTo,
    max_hops: 4,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [traceData, setTraceData] = useState(null);

  useEffect(() => {
    setForm((prev) => ({ ...prev, from: defaultFrom, to: defaultTo }));
  }, [defaultFrom, defaultTo]);

  const elements = useMemo(() => buildElements(traceData), [traceData]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = { from: form.from, max_hops: Number(form.max_hops) };
      if (form.to) payload.to = form.to;
      const response = await postTrace(payload);
      setTraceData(response);
    } catch (err) {
      setError(err.message);
      setTraceData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="grid gap-4 md:grid-cols-4 bg-slate-900 p-4 rounded-lg shadow">
        <div className="md:col-span-2 flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wide text-slate-400">From Address</label>
          <input
            name="from"
            value={form.from}
            onChange={handleChange}
            required
            className="rounded border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 focus:outline-none focus:ring focus:ring-sky-500"
          />
        </div>
        <div className="md:col-span-2 flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wide text-slate-400">To Address (optional)</label>
          <input
            name="to"
            value={form.to}
            onChange={handleChange}
            className="rounded border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 focus:outline-none focus:ring focus:ring-sky-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wide text-slate-400">Max Hops</label>
          <input
            type="number"
            name="max_hops"
            min={1}
            max={8}
            value={form.max_hops}
            onChange={handleChange}
            className="rounded border border-slate-700 bg-slate-800 px-3 py-2 text-slate-100 focus:outline-none focus:ring focus:ring-sky-500"
          />
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-sky-600 px-4 py-2 font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
          >
            {loading ? 'Tracing…' : 'Trace Path'}
          </button>
        </div>
      </form>

      {error && <p className="rounded bg-red-900/40 px-4 py-2 text-red-200">{error}</p>}

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        {traceData ? (
          <CytoscapeComponent elements={elements} style={{ width: '100%', height: '480px' }} layout={layout} stylesheet={defaultStyle} />
        ) : (
          <p className="text-sm text-slate-400">Run a trace to visualize relationships between addresses.</p>
        )}
      </div>
    </div>
  );
}
