import { useEffect, useMemo, useState } from 'react';
import { fetchAlerts, refreshAlerts, recomputeSeverity } from '../api';

const severityColors = {
  HIGH: 'bg-red-500/20 text-red-200 border-red-400/40',
  MEDIUM: 'bg-amber-500/20 text-amber-200 border-amber-400/40',
  ELEVATED: 'bg-sky-500/20 text-sky-100 border-sky-400/40',
  LOW: 'bg-slate-700/40 text-slate-300 border-slate-600/40',
};

function formatPercent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function buildCsv(alerts) {
  if (!alerts.length) return '';
  const header = ['address', 'cluster_id', 'risk_score', 'severity', 'is_anomaly', 'is_sanctioned'];
  const rows = alerts.map((alert) =>
    header
      .map((key) => {
        const value = alert[key];
        if (value === undefined || value === null) return '';
        if (typeof value === 'string' && value.includes(',')) {
          return `"${value}"`;
        }
        return value;
      })
      .join(',')
  );
  return [header.join(','), ...rows].join('\n');
}

export default function AlertsView({ onSelectAddress }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchAlerts();
      setAlerts(response.alerts);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      await refreshAlerts();
      await recomputeSeverity();
      await loadAlerts();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = () => {
    const csv = buildCsv(alerts);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'alerts.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  const handleRowClick = (address) => {
    if (onSelectAddress) {
      onSelectAddress(address);
    }
  };

  const renderedAlerts = useMemo(() => alerts, [alerts]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="rounded bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {loading ? 'Refreshing…' : 'Refresh Alerts'}
        </button>
        <button
          onClick={handleExport}
          disabled={!alerts.length}
          className="rounded border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:border-slate-400 disabled:opacity-50"
        >
          Export CSV
        </button>
        <p className="text-xs text-slate-400">Click an alert row to load traces for the selected address.</p>
      </div>

      {error && <p className="rounded bg-red-900/40 px-4 py-2 text-red-200">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900">
        <table className="min-w-full text-left text-sm text-slate-200">
          <thead className="bg-slate-800/80 text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="px-4 py-3">Address</th>
              <th className="px-4 py-3">Cluster</th>
              <th className="px-4 py-3">Risk</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Flags</th>
            </tr>
          </thead>
          <tbody>
            {renderedAlerts.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                  No alerts yet. Run ingestion and refresh alerts to populate this table.
                </td>
              </tr>
            )}
            {renderedAlerts.map((alert) => (
              <tr
                key={alert.address}
                onClick={() => handleRowClick(alert.address)}
                className="cursor-pointer border-t border-slate-800/60 hover:bg-slate-800/70"
              >
                <td className="px-4 py-3 font-mono text-xs">{alert.address}</td>
                <td className="px-4 py-3 text-xs">{alert.cluster_id || '—'}</td>
                <td className="px-4 py-3 text-xs">{formatPercent(alert.risk_score)}</td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold ${
                      severityColors[alert.severity] || severityColors.LOW
                    }`}
                  >
                    {alert.severity}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs">
                  <div className="flex flex-wrap gap-1">
                    {alert.is_anomaly && <span className="rounded bg-rose-500/30 px-2 py-0.5 text-rose-100">Anomaly</span>}
                    {alert.is_sanctioned && (
                      <span className="rounded bg-purple-500/30 px-2 py-0.5 text-purple-100">Sanctioned</span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
