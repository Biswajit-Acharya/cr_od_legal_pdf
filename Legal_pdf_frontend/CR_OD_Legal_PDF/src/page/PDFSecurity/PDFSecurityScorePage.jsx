import React, { useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Download,
  FileText,
  Gauge,
  Info,
  Loader2,
  Lock,
  RefreshCcw,
  ShieldAlert,
  ShieldCheck,
  Upload,
  X,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
const SCORE_ENDPOINT = '/api/pdf/security/security-score';

const formatBytes = (bytes) => {
  const value = Number(bytes);
  if (!Number.isFinite(value)) return 'N/A';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
};

const titleCase = (value) => {
  if (value === true) return 'Yes';
  if (value === false) return 'No';
  if (value === null || value === undefined || value === '') return 'N/A';
  return String(value).replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const severityTone = {
  CRITICAL: 'border-red-300 bg-red-50 text-red-800',
  HIGH: 'border-orange-300 bg-orange-50 text-orange-800',
  MEDIUM: 'border-amber-300 bg-amber-50 text-amber-800',
  LOW: 'border-slate-300 bg-slate-50 text-slate-700',
  INFO: 'border-blue-200 bg-blue-50 text-blue-800',
};

function UploadBox({ file, onFile, onRemove, inputRef }) {
  const [dragging, setDragging] = useState(false);

  const acceptFiles = (files) => {
    const selected = Array.from(files || [])[0];
    if (selected) onFile(selected);
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        acceptFiles(event.dataTransfer.files);
      }}
      className={`rounded-3xl border p-5 transition-all ${dragging ? 'border-[#1e2a52] bg-[#eef3eb]' : 'border-slate-200 bg-white'}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(event) => {
          acceptFiles(event.target.files);
          event.target.value = '';
        }}
      />

      {file ? (
        <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#1e2a52]/10 text-[#1e2a52]">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-black text-slate-800">{file.name}</p>
            <p className="text-xs font-semibold text-slate-500">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600"
            aria-label="Remove selected PDF"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-[#1e2a52]/25 bg-[#f8faf7] px-4 py-10 text-center transition-all hover:border-[#1e2a52] hover:bg-[#eef3eb]"
        >
          <Upload className="h-8 w-8 text-[#1e2a52]" />
          <span className="mt-3 text-sm font-black text-[#1e2a52]">Drop PDF here or click to browse</span>
          <span className="mt-1 text-xs font-semibold text-slate-500">PDF files only</span>
        </button>
      )}
    </div>
  );
}

function ScoreRing({ score, maxScore, rating }) {
  const pct = Math.max(0, Math.min(100, Math.round((score / (maxScore || 100)) * 100)));
  const tone = pct >= 75 ? 'text-emerald-600' : pct >= 60 ? 'text-amber-600' : pct >= 40 ? 'text-orange-600' : 'text-red-600';

  return (
    <div className="flex flex-col items-center justify-center rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div
        className="grid h-44 w-44 place-items-center rounded-full"
        style={{ background: `conic-gradient(#1e2a52 ${pct * 3.6}deg, #e2e8f0 0deg)` }}
      >
        <div className="grid h-36 w-36 place-items-center rounded-full bg-white">
          <div className="text-center">
            <p className="text-4xl font-black text-[#1e2a52]">{score}</p>
            <p className="text-xs font-black uppercase tracking-wide text-slate-500">/ {maxScore}</p>
          </div>
        </div>
      </div>
      <p className={`mt-4 text-lg font-black uppercase tracking-wide ${tone}`}>{rating}</p>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-[11px] font-black uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-bold text-slate-800" title={titleCase(value)}>{titleCase(value)}</p>
    </div>
  );
}

function CategoryCard({ item }) {
  const pct = Math.round((item.points / item.max_points) * 100);
  const tone = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-black text-slate-900">{item.category}</p>
          <p className="mt-1 text-xs font-bold uppercase tracking-wide text-slate-500">{titleCase(item.status)}</p>
        </div>
        <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-black text-slate-700">
          {item.points}/{item.max_points}
        </span>
      </div>
      <div className="mt-3 h-2 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-3 text-xs font-semibold leading-relaxed text-slate-600">{item.reason}</p>
    </div>
  );
}

function Findings({ findings }) {
  const groups = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'];
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="text-sm font-black uppercase tracking-wide text-slate-700">Risk Findings</h3>
      <div className="mt-4 space-y-4">
        {groups.map((severity) => {
          const items = findings.filter((item) => item.severity === severity);
          if (!items.length) return null;
          return (
            <div key={severity}>
              <p className="mb-2 text-xs font-black uppercase tracking-wide text-slate-500">{severity}</p>
              <div className="space-y-2">
                {items.map((item, index) => (
                  <div key={`${severity}-${index}`} className={`rounded-xl border px-4 py-3 ${severityTone[severity] || severityTone.INFO}`}>
                    <p className="text-sm font-black">{item.title}</p>
                    <p className="mt-1 text-xs font-semibold leading-relaxed">{item.description}</p>
                    <p className="mt-2 text-[11px] font-bold">Evidence: {item.evidence || 'N/A'}</p>
                    <p className="mt-1 text-[11px] font-bold">Recommendation: {item.recommendation || 'Review this finding.'}</p>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
        {!findings.length && <p className="text-sm font-semibold text-slate-500">No findings reported.</p>}
      </div>
    </section>
  );
}

export default function PDFSecurityScorePage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [password, setPassword] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const inputRef = useRef(null);

  const toolName = tool?.name || 'PDF Security Score';
  const toolDesc = tool?.description || 'Analyze detectable PDF security controls and generate a transparent score.';

  const handleFile = (selected) => {
    setError('');
    setResult(null);
    if (!selected.name.toLowerCase().endsWith('.pdf') && selected.type !== 'application/pdf') {
      setError('Please upload a valid PDF document.');
      return;
    }
    setFile(selected);
  };

  const analyze = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      if (password) formData.append('password', password);
      const response = await fetch(`${API_BASE_URL}${SCORE_ENDPOINT}`, { method: 'POST', body: formData });
      if (!response.ok) {
        let message = 'Security analysis could not be completed. Please try again.';
        try {
          const body = await response.json();
          message = body.detail || body.error || message;
        } catch (_) {}
        throw new Error(message);
      }
      setResult(await response.json());
      setPassword('');
    } catch (err) {
      setError(err.message || 'Security analysis could not be completed. Please try again.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const reset = () => {
    setFile(null);
    setPassword('');
    setResult(null);
    setError('');
  };

  const analysis = result?.analysis || {};
  const reportHref = result?.report_url ? `${API_BASE_URL}${result.report_url}` : '';
  const needsPassword = analysis.password_required && !analysis.password_authenticated;

  return (
    <div className="relative z-20 min-h-screen w-full bg-transparent pb-14">
      <div className="mx-auto w-full max-w-[1200px] px-4 pb-4 pt-4 sm:px-6 sm:pt-8 md:px-10">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-[#1e2a52] shadow-md transition-all hover:shadow-lg sm:text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      </div>

      <div className="mx-auto max-w-3xl px-4 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#1e2a52] text-white shadow-lg shadow-[#1e2a52]/15">
          <Gauge className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-black leading-tight text-[#1e2a52] sm:text-4xl">{toolName}</h1>
        <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">{toolDesc}</p>
      </div>

      <main className="mx-auto mt-8 w-full max-w-6xl px-4 sm:px-6">
        {!result && (
          <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-[0_12px_40px_rgba(15,23,42,0.06)] sm:p-8">
            <UploadBox file={file} onFile={handleFile} onRemove={() => setFile(null)} inputRef={inputRef} />

            <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <label className="mb-2 flex items-center gap-2 text-xs font-black uppercase tracking-wide text-slate-600">
                <Lock className="h-4 w-4" />
                PDF Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Only required for password-protected PDFs"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-semibold text-slate-800 outline-none focus:border-[#1e2a52] focus:ring-2 focus:ring-[#1e2a52]/15"
              />
            </div>

            {error && (
              <div className="mt-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="mt-6 flex flex-col items-stretch justify-between gap-3 border-t border-slate-200 pt-6 sm:flex-row sm:items-center">
              <p className="text-xs font-semibold leading-relaxed text-slate-500">
                The score is based on detected PDF security controls, not random or mock values.
              </p>
              <button
                type="button"
                onClick={analyze}
                disabled={!file || isAnalyzing}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1e2a52] px-7 py-3 text-sm font-black text-white shadow-md transition-all hover:bg-[#2a3a6a] disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                {isAnalyzing ? 'Analyzing Security...' : 'Analyze Security'}
              </button>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-5">
            <section className="grid gap-5 lg:grid-cols-[260px,1fr]">
              <ScoreRing score={result.score} maxScore={result.max_score} rating={result.rating} />
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-black text-[#1e2a52]">{result.rating} Security Controls</h2>
                    <p className="mt-2 text-sm font-semibold leading-relaxed text-slate-600">{result.disclaimer}</p>
                    {needsPassword && (
                      <div className="mt-4 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
                        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
                        <span>Password-protected PDF detected. Enter the authorized password and analyze again for complete permission details.</span>
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2 sm:min-w-[230px]">
                    {reportHref && (
                      <a href={reportHref} download className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1e2a52] px-5 py-2.5 text-sm font-black text-white hover:bg-[#2a3a6a]">
                        <Download className="h-4 w-4" />
                        Download Security Report
                      </a>
                    )}
                    <button type="button" onClick={reset} className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-black text-slate-700 hover:border-[#1e2a52]">
                      <RefreshCcw className="h-4 w-4" />
                      Analyze Another PDF
                    </button>
                  </div>
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <Metric label="Filename" value={result.filename} />
                  <Metric label="File Size" value={formatBytes(result.file_size)} />
                  <Metric label="Encrypted" value={analysis.encryption?.encrypted} />
                  <Metric label="Signature" value={analysis.digital_signature?.validation_status} />
                  <Metric label="JavaScript" value={analysis.active_content?.javascript} />
                  <Metric label="Analyzed" value={result.analyzed_at ? new Date(result.analyzed_at).toLocaleString() : 'N/A'} />
                </div>
              </div>
            </section>

            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {(result.breakdown || []).map((item) => <CategoryCard key={item.category} item={item} />)}
            </section>

            <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
              <div className="border-b border-slate-200 bg-slate-50 px-5 py-3">
                <h3 className="text-sm font-black uppercase tracking-wide text-slate-700">Security Score Breakdown</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead className="bg-white text-xs font-black uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-5 py-3">Category</th>
                      <th className="px-5 py-3 text-right">Score</th>
                      <th className="px-5 py-3 text-right">Max</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3">Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(result.breakdown || []).map((item) => (
                      <tr key={item.category}>
                        <td className="px-5 py-3 font-bold text-slate-800">{item.category}</td>
                        <td className="px-5 py-3 text-right font-black text-slate-800">{item.points}</td>
                        <td className="px-5 py-3 text-right font-semibold text-slate-500">{item.max_points}</td>
                        <td className="px-5 py-3 font-semibold text-slate-700">{titleCase(item.status)}</td>
                        <td className="px-5 py-3 text-xs font-semibold text-slate-600">{item.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <Findings findings={result.findings || []} />

            <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-wide text-slate-700">
                <Info className="h-4 w-4 text-[#1e2a52]" />
                Recommendations
              </h3>
              <ul className="mt-4 space-y-2">
                {(result.recommendations || []).map((item, index) => (
                  <li key={index} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700">
                    {item}
                  </li>
                ))}
                {!result.recommendations?.length && (
                  <li className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-500">
                    No targeted recommendations were generated from the detected properties.
                  </li>
                )}
              </ul>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
