import { useEffect, useMemo, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import { postTrace } from '../api';

const layout = { name: 'cose', animate: false, fit: true };

const defaultStyle = [
  {
    selector: 'node',
    style: {
      'background-color': '#2563eb',
      color: '#f8fafc',
      'border-width': 2,
      'border-color': '#1e293b',
      label: 'data(label)',
      'font-size': 10,
      'text-wrap': 'wrap',
      'text-max-width': 120,
      'text-outline-width': 2,
      'text-outline-color': '#0f172a',
      'text-background-color': '#0f172a',
      'text-background-opacity': 0.65,
      'text-background-padding': 2,
    },
  },
  {
    selector: 'node[isAnomaly = "true"]',
    style: {
      'background-color': '#dc2626',
      color: '#ffffff',
      'text-outline-width': 2,
      'text-outline-color': '#7f1d1d',
      'text-background-color': '#7f1d1d',
      'text-background-opacity': 0.7,
    },
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
      color: '#e2e8f0',
      'text-outline-width': 1,
      'text-outline-color': '#1e293b',
      'text-background-color': '#0f172a',
      'text-background-opacity': 0.75,
      'text-background-padding': 1.5,
    },
  },
];

const legendItems = [
  {
    id: 'clusters',
    label: 'Cluster color',
    description: 'Addresses in the same cluster share a hue.',
    swatchClass: 'bg-gradient-to-r from-sky-500 to-emerald-500',
  },
  {
    id: 'anomaly',
    label: 'Anomaly node',
    description: 'Red nodes highlight anomaly scores.',
    swatchClass: 'bg-[#dc2626]',
  },
  {
    id: 'sanctioned',
    label: 'Sanctioned outline',
    description: 'Purple borders mark sanctioned addresses.',
    swatchClass: 'bg-transparent border-2 border-[#9333ea]',
  },
  {
    id: 'edge',
    label: 'Directional edge',
    description: 'Arrows show fund flow sender → receiver.',
    swatchClass: 'bg-[#94a3b8]',
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
  const [metadata, setMetadata] = useState(null);

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
      setMetadata(response?.metadata ?? null);
    } catch (err) {
      setError(err.message);
      setTraceData(null);
      setMetadata(null);
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

      {metadata && (
        <div className="grid gap-3 rounded-lg border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-200 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Source</p>
            <p className="mt-1 font-mono break-all">{metadata.source}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Target</p>
            <p className="mt-1 font-mono break-all">{metadata.target || 'Any destination'}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Nodes</p>
            <p className="mt-1 text-lg font-semibold">{metadata.node_count ?? traceData?.nodes?.length ?? 0}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Edges</p>
            <p className="mt-1 text-lg font-semibold">{metadata.edge_count ?? traceData?.edges?.length ?? 0}</p>
          </div>
        </div>
      )}

      {error && <p className="rounded bg-red-900/40 px-4 py-2 text-red-200">{error}</p>}

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        {traceData ? (
          <div className="flex flex-col gap-6 lg:flex-row">
            <div className="flex-1 min-h-[520px]">
              <CytoscapeComponent elements={elements} style={{ width: '100%', height: '100%' }} layout={layout} stylesheet={defaultStyle} />
            </div>
            <aside className="lg:w-72 space-y-4 rounded-lg border border-slate-800/60 bg-slate-950/40 p-4 text-sm text-slate-200">
              {metadata && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-slate-100">Graph Summary</h3>
                  <dl className="space-y-2">
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-slate-500">Paths explored</dt>
                      <dd className="text-base font-semibold">{metadata.path_count ?? 0}</dd>
                    </div>
                    <div className="flex justify-between text-xs text-slate-400">
                      <span>Max hops</span>
                      <span>{metadata.max_hops ?? form.max_hops}</span>
                    </div>
                  </dl>
                </div>
              )}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-100">Graph Legend</h3>
                <ul className="space-y-3 text-xs text-slate-300">
                  {legendItems.map((item) => (
                    <li key={item.id} className="flex items-start gap-3">
                      <span className={`mt-0.5 inline-flex h-4 w-4 rounded-full ${item.swatchClass}`} />
                      <div>
                        <p className="font-semibold text-slate-200">{item.label}</p>
                        <p className="text-slate-400">{item.description}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </aside>
          </div>
        ) : (
          <p className="text-sm text-slate-400">
            Run a trace to explore fund flows. Start with a source address, optionally provide a destination, and adjust hop depth to expand the network.
          </p>
        )}
      </div>
    </div>
  );
}
