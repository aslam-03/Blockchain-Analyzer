import { useState } from 'react';
import AlertsView from './components/AlertsView';
import TraceView from './components/TraceView';
import { triggerClustering, uploadBlacklist } from './api';

function useStatus() {
  const [message, setMessage] = useState(null);
  const [variant, setVariant] = useState('success');

  const showMessage = (text, type = 'success') => {
    setMessage(text);
    setVariant(type);
    setTimeout(() => setMessage(null), 4000);
  };

  return {
    message,
    variant,
    showMessage,
  };
}

export default function App() {
  const { message, variant, showMessage } = useStatus();
  const [selectedAddress, setSelectedAddress] = useState('');
  const [blacklistUploading, setBlacklistUploading] = useState(false);
  const [clustering, setClustering] = useState(false);

  const handleAlertSelect = (address) => {
    setSelectedAddress(address);
    showMessage(`Loaded trace defaults for ${address}`, 'info');
  };

  const handleClusterRun = async () => {
    setClustering(true);
    try {
      const { assigned_addresses: assigned } = await triggerClustering();
      showMessage(`Clustered ${assigned} addresses`);
    } catch (err) {
      showMessage(err.message, 'error');
    } finally {
      setClustering(false);
    }
  };

  const handleBlacklistUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBlacklistUploading(true);
    try {
      const { updated } = await uploadBlacklist(file);
      showMessage(`Marked ${updated} addresses as sanctioned`);
    } catch (err) {
      showMessage(err.message, 'error');
    } finally {
      setBlacklistUploading(false);
      event.target.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-8">
        <header className="flex flex-col gap-3 border-b border-slate-800 pb-6">
          <h1 className="text-2xl font-bold text-slate-100">Blockchain Analyzer</h1>
          <p className="max-w-3xl text-sm text-slate-400">
            Explore Ethereum transaction flows, detect anomalies, and monitor compliance alerts in real time.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleClusterRun}
              disabled={clustering}
              className="rounded bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
            >
              {clustering ? 'Clustering…' : 'Run Clustering'}
            </button>
            <label className="flex items-center gap-2 rounded border border-dashed border-slate-600 px-3 py-2 text-xs text-slate-300 hover:border-slate-400">
              <span>{blacklistUploading ? 'Uploading…' : 'Upload Blacklist CSV'}</span>
              <input type="file" accept=".csv" className="hidden" onChange={handleBlacklistUpload} disabled={blacklistUploading} />
            </label>
          </div>
          {message && (
            <div
              className={`rounded px-4 py-2 text-sm ${
                variant === 'error'
                  ? 'bg-red-900/40 text-red-200'
                  : variant === 'info'
                  ? 'bg-sky-900/40 text-sky-200'
                  : 'bg-emerald-900/40 text-emerald-200'
              }`}
            >
              {message}
            </div>
          )}
        </header>

        <section className="grid gap-8 lg:grid-cols-5">
          <div className="lg:col-span-3 space-y-4">
            <h2 className="text-lg font-semibold text-slate-200">Trace Explorer</h2>
            <TraceView defaultFrom={selectedAddress} />
          </div>
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-lg font-semibold text-slate-200">Alerts</h2>
            <AlertsView onSelectAddress={handleAlertSelect} />
          </div>
        </section>
      </div>
    </div>
  );
}
