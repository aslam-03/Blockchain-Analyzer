import { useEffect, useState } from 'react';

const featureHighlights = [
  {
    title: 'Visual Trace Explorer',
    description:
      'Follow fund flows hop-by-hop with a responsive graph that reveals counterparties, anomaly scores, and sanction flags.',
  },
  {
    title: 'Automated Anomaly Detection',
    description:
      'IsolationForest scoring surfaces high-risk clusters by volume, velocity, and counterparties so you can prioritize reviews instantly.',
  },
  {
    title: 'Compliance Guardrails',
    description:
      'Upload sanctions lists, recompute severities, and monitor alerts in real time to keep investigations audit-ready.',
  },
];

function TypewriterText({ text, delay = 40 }) {
  const [displayed, setDisplayed] = useState('');

  useEffect(() => {
    let currentIndex = 0;
    const interval = setInterval(() => {
      currentIndex += 1;
      setDisplayed(text.slice(0, currentIndex));
      if (currentIndex >= text.length) {
        clearInterval(interval);
      }
    }, delay);

    return () => clearInterval(interval);
  }, [text, delay]);

  return <span>{displayed}</span>;
}

export default function IntroPage({ onEnter }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-slate-950 text-slate-100">
      <div className="animated-gradient pointer-events-none" aria-hidden="true" />
      <div className="absolute inset-0 opacity-70">
        <div className="floating-squares" />
      </div>

      <header className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col justify-center gap-10 px-6 py-16 md:py-24">
        <div className="space-y-6 text-center md:text-left">
          <p className="inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-4 py-2 text-xs uppercase tracking-[0.25em] text-slate-400 shadow-lg shadow-slate-900/60">
            Blockchain Intelligence Platform
          </p>
          <h1 className="text-4xl font-black tracking-tight text-slate-50 drop-shadow-lg md:text-6xl">
            Blockchain Analyzer
          </h1>
          <p className="mx-auto max-w-2xl text-base leading-relaxed text-slate-300 md:mx-0 md:text-lg">
            <TypewriterText text="Ingest Ethereum wallets, trace transaction paths, cluster related entities, and spotlight high-risk flows with automated compliance checks." />
          </p>
          <div className="flex justify-center sm:justify-start">
            <button
              type="button"
              onClick={onEnter}
              className="group relative inline-flex items-center justify-center rounded-full bg-gradient-to-r from-sky-500 via-emerald-500 to-purple-500 px-10 py-3 text-sm font-semibold tracking-wide text-white shadow-xl shadow-sky-900/40 transition-transform duration-300 hover:scale-105"
            >
              <span className="absolute inset-0 rounded-full bg-white/20 opacity-0 transition-opacity duration-300 group-hover:opacity-100" aria-hidden="true" />
              <span className="relative flex items-center gap-2">
                Try Blockchain Analyzer
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="h-4 w-4"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 19.5 19.5 4.5M19.5 4.5H8.25M19.5 4.5V15.75" />
                </svg>
              </span>
            </button>
          </div>
        </div>

        <section className="grid gap-6 rounded-3xl border border-slate-800/70 bg-slate-900/60 p-8 backdrop-blur md:grid-cols-3">
          {featureHighlights.map((feature) => (
            <article
              key={feature.title}
              className="flex flex-col gap-3 rounded-2xl bg-slate-900/50 p-6 shadow-lg shadow-slate-950/40 ring-1 ring-slate-800/60 transition-transform duration-300 hover:-translate-y-1"
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-sky-500/80 to-emerald-500/80 text-slate-950">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5">
                  <path d="M12 1.5A5.25 5.25 0 0 0 6.75 6.75v.778a3.001 3.001 0 0 0-2.477 4.919l2.694 3.232a3 3 0 0 0 2.31 1.071h5.446a3 3 0 0 0 2.31-1.07l2.693-3.233a3.001 3.001 0 0 0-2.475-4.92V6.75A5.25 5.25 0 0 0 12 1.5Z" />
                  <path d="M9 20.25a3 3 0 0 0 6 0v-.75H9v.75Z" />
                </svg>
              </span>
              <h3 className="text-lg font-semibold text-slate-100">{feature.title}</h3>
              <p className="text-sm leading-relaxed text-slate-400">{feature.description}</p>
            </article>
          ))}
        </section>
      </header>

      <footer className="relative z-10 mx-auto w-full max-w-6xl px-6 pb-10 text-xs text-slate-500">
        <div className="flex flex-wrap justify-between gap-4 border-t border-slate-800/60 pt-6">
          <p>© {new Date().getFullYear()} Blockchain Analyzer • Neo4j + FastAPI + React</p>
          <p>Tracing | Anomaly Detection | Compliance</p>
        </div>
      </footer>
    </div>
  );
}
