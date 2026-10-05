import React, { useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Check,
  Clipboard,
  Download,
  FileCheck2,
  FileText,
  Fingerprint,
  Info,
  Loader2,
  RefreshCcw,
  Scale,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  ShieldX,
  Upload,
  X,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
const VERIFY_ENDPOINT = '/api/pdf/document-integrity/verify';

const formatBytes = (bytes) => {
  const value = Number(bytes);
  if (!Number.isFinite(value)) return 'N/A';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
};

const formatDate = (value) => {
  if (!value) return 'N/A';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};

const asText = (value) => {
  if (value === true) return 'Yes';
  if (value === false) return 'No';
  if (value === null || value === undefined || value === '') return 'N/A';
  return String(value);
};

const titleCaseStatus = (value) => {
  if (!value) return 'Not available';
  return String(value)
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const truncateHash = (hash) => {
  if (!hash) return 'N/A';
  if (hash.length <= 28) return hash;
  return `${hash.slice(0, 18)}...${hash.slice(-12)}`;
};

const getStatusTone = (status) => {
  switch (status) {
    case 'VERIFIED':
    case 'SIGNATURE_PRESENT':
      return {
        icon: ShieldCheck,
        label: status === 'VERIFIED' ? 'Trusted Reference Match' : 'Signature Evidence Present',
        badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        panel: 'bg-emerald-50/80 border-emerald-200',
        iconWrap: 'bg-emerald-100 text-emerald-700',
      };
    case 'STRUCTURAL_WARNING':
    case 'SIGNATURE_UNVALIDATED':
      return {
        icon: ShieldAlert,
        label: status === 'SIGNATURE_UNVALIDATED' ? 'Signature Needs Review' : 'Structure Needs Review',
        badge: 'bg-amber-50 text-amber-700 border-amber-200',
        panel: 'bg-amber-50/80 border-amber-200',
        iconWrap: 'bg-amber-100 text-amber-700',
      };
    case 'REFERENCE_MISMATCH':
    case 'MODIFIED':
    case 'SIGNATURE_INVALID':
    case 'CORRUPTED':
      return {
        icon: status === 'CORRUPTED' ? ShieldX : ShieldAlert,
        label: status === 'REFERENCE_MISMATCH' ? 'Reference Difference Detected' : titleCaseStatus(status),
        badge: 'bg-red-50 text-red-700 border-red-200',
        panel: 'bg-red-50/80 border-red-200',
        iconWrap: 'bg-red-100 text-red-700',
      };
    default:
      return {
        icon: ShieldQuestion,
        label: 'Unable To Prove Authenticity',
        badge: 'bg-slate-100 text-slate-700 border-slate-200',
        panel: 'bg-slate-50 border-slate-200',
        iconWrap: 'bg-slate-200 text-slate-700',
      };
  }
};

function UploadPanel({ label, helper, file, inputRef, onFiles, onRemove, optional = false }) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files?.length) onFiles(event.dataTransfer.files);
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`rounded-2xl border p-4 transition-all ${
        dragging ? 'border-[#1e2a52] bg-[#eef3eb]' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-black text-[#1e2a52]">{label}</p>
          <p className="mt-1 text-xs font-medium leading-relaxed text-slate-500">{helper}</p>
        </div>
        {optional && (
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] font-black uppercase tracking-wide text-slate-500">
            Optional
          </span>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        className="hidden"
        onChange={(event) => {
          if (event.target.files?.length) onFiles(event.target.files);
          event.target.value = '';
        }}
      />

      {file ? (
        <div className="mt-4 flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#1e2a52]/10 text-[#1e2a52]">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-slate-800">{file.name}</p>
            <p className="text-xs font-medium text-slate-500">{formatBytes(file.size)}</p>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 focus:outline-none focus:ring-2 focus:ring-red-200"
            aria-label={`Remove ${label}`}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-4 flex w-full flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#1e2a52]/25 bg-[#f8faf7] px-4 py-8 text-center transition-all hover:border-[#1e2a52] hover:bg-[#eef3eb] focus:outline-none focus:ring-2 focus:ring-[#1e2a52]/30"
        >
          <Upload className="h-7 w-7 text-[#1e2a52]" />
          <span className="mt-3 text-sm font-black text-[#1e2a52]">Drop PDF here or click to browse</span>
          <span className="mt-1 text-xs font-semibold text-slate-500">PDF files only</span>
        </button>
      )}
    </div>
  );
}

function Section({ icon: Icon, title, children, right }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 px-5 py-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-[#1e2a52]" />
          <h3 className="text-xs font-black uppercase tracking-wide text-slate-700">{title}</h3>
        </div>
        {right}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}

function Fact({ label, value }) {
  return (
    <div className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-[11px] font-black uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-bold text-slate-800" title={asText(value)}>
        {asText(value)}
      </p>
    </div>
  );
}

function StatusPill({ children, tone = 'slate' }) {
  const tones = {
    emerald: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    amber: 'border-amber-200 bg-amber-50 text-amber-700',
    red: 'border-red-200 bg-red-50 text-red-700',
    slate: 'border-slate-200 bg-slate-50 text-slate-700',
  };

  return (
    <span className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-black ${tones[tone] || tones.slate}`}>
      {children}
    </span>
  );
}

function HashRow({ algorithm, value, verified, onCopy, copied }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:items-center">
      <div className="min-w-[86px]">
        <p className="text-xs font-black text-[#1e2a52]">{algorithm}</p>
        {verified && <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-emerald-600">Reference match</p>}
      </div>
      <code className="min-w-0 flex-1 break-all rounded-lg bg-white px-3 py-2 text-xs font-semibold text-slate-700">
        {truncateHash(value)}
      </code>
      <button
        type="button"
        onClick={() => onCopy(value, algorithm)}
        disabled={!value}
        className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-700 transition-colors hover:border-[#1e2a52] hover:text-[#1e2a52] focus:outline-none focus:ring-2 focus:ring-[#1e2a52]/20 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {copied === algorithm ? <Check className="h-3.5 w-3.5" /> : <Clipboard className="h-3.5 w-3.5" />}
        {copied === algorithm ? 'Copied' : 'Copy'}
      </button>
    </div>
  );
}

export default function DocumentIntegrityVerificationPage({ tool, onBack }) {
  const [primaryFile, setPrimaryFile] = useState(null);
  const [referenceFile, setReferenceFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState('');
  const primaryInputRef = useRef(null);
  const referenceInputRef = useRef(null);

  const toolName = tool?.name || 'Document Integrity Verification';
  const toolDesc = tool?.description || 'Verify PDF structure, fingerprints, signatures, and trusted reference matches.';

  const addFile = (files, setter) => {
    setError('');
    const file = Array.from(files || [])[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf') && file.type !== 'application/pdf') {
      setError('Only PDF files are accepted.');
      return;
    }
    setter(file);
    setResult(null);
  };

  const resetWorkflow = () => {
    setPrimaryFile(null);
    setReferenceFile(null);
    setResult(null);
    setError('');
    setCopied('');
  };

  const handleCopy = async (value, label) => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
      window.setTimeout(() => setCopied(''), 1400);
    } catch (_) {
      setError('Unable to copy fingerprint in this browser.');
    }
  };

  const handleVerify = async () => {
    if (!primaryFile) {
      setError('Upload a primary PDF before running verification.');
      return;
    }

    setIsProcessing(true);
    setError('');
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', primaryFile);
      if (referenceFile) formData.append('reference_file', referenceFile);

      const response = await fetch(`${API_BASE_URL}${VERIFY_ENDPOINT}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let message = `Server error: ${response.status}`;
        try {
          const body = await response.json();
          message = body.detail || body.error || message;
        } catch (_) {}
        throw new Error(message);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || 'Document integrity verification failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const status = result?.status || 'UNABLE_TO_VERIFY';
  const tone = getStatusTone(status);
  const StatusIcon = tone.icon;
  const pdf = result?.pdf_integrity || {};
  const signatures = result?.digital_signature || {};
  const incremental = result?.incremental_updates || {};
  const metadata = result?.metadata || {};
  const reference = result?.reference_comparison || {};
  const warnings = result?.warnings || [];
  const errors = result?.errors || [];
  const reportHref = result?.report_url ? `${API_BASE_URL}${result.report_url}` : '';

  return (
    <div className="relative z-20 min-h-screen w-full bg-transparent pb-14">
      <div className="mx-auto flex w-full max-w-[1200px] items-center justify-between px-4 pb-4 pt-4 sm:px-6 sm:pt-8 md:px-10">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-bold text-[#1e2a52] shadow-md transition-all hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-[#1e2a52]/20 sm:text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      </div>

      <div className="mx-auto max-w-3xl px-4 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#1e2a52] text-white shadow-lg shadow-[#1e2a52]/15">
          <Scale className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-black leading-tight text-[#1e2a52] sm:text-4xl">{toolName}</h1>
        <p className="mx-auto mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">{toolDesc}</p>
      </div>

      <main className="mx-auto mt-8 w-full max-w-6xl px-4 sm:px-6">
        {!result && (
          <div className="rounded-3xl border border-slate-200/80 bg-white p-5 shadow-[0_12px_40px_rgba(15,23,42,0.06)] sm:p-8">
            <div className="grid gap-4 lg:grid-cols-2">
              <UploadPanel
                label="Primary PDF"
                helper="Upload the document you want to verify for fingerprints, structure, signatures, and metadata."
                file={primaryFile}
                inputRef={primaryInputRef}
                onFiles={(files) => addFile(files, setPrimaryFile)}
                onRemove={() => {
                  setPrimaryFile(null);
                  setResult(null);
                }}
              />
              <UploadPanel
                label="Trusted Reference PDF"
                helper="Add a known-good copy to compare bytes and strengthen authenticity evidence."
                file={referenceFile}
                inputRef={referenceInputRef}
                onFiles={(files) => addFile(files, setReferenceFile)}
                onRemove={() => {
                  setReferenceFile(null);
                  setResult(null);
                }}
                optional
              />
            </div>

            {error && (
              <div className="mt-5 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="mt-6 flex flex-col items-stretch justify-between gap-3 border-t border-slate-200 pt-6 sm:flex-row sm:items-center">
              <p className="text-xs font-semibold leading-relaxed text-slate-500">
                Hashes identify exact bytes. Authenticity still requires a trusted reference or a validated digital signature.
              </p>
              <button
                type="button"
                onClick={handleVerify}
                disabled={!primaryFile || isProcessing}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1e2a52] px-7 py-3 text-sm font-black text-white shadow-md transition-all hover:bg-[#2a3a6a] hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-[#1e2a52]/30 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
              >
                {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCheck2 className="h-4 w-4" />}
                {isProcessing ? 'Verifying Document...' : 'Verify Document Integrity'}
              </button>
            </div>
          </div>
        )}

        {isProcessing && (
          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-5 py-6 text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-[#1e2a52]" />
            <p className="mt-3 text-sm font-black text-[#1e2a52]">Reading structure, signatures, and fingerprints...</p>
          </div>
        )}

        {result && (
          <div className="space-y-5">
            <section className={`rounded-3xl border p-5 shadow-sm sm:p-7 ${tone.panel}`}>
              <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex gap-4">
                  <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl ${tone.iconWrap}`}>
                    <StatusIcon className="h-7 w-7" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-xl font-black text-slate-900 sm:text-2xl">{tone.label}</h2>
                      <span className={`rounded-md border px-2.5 py-1 text-xs font-black ${tone.badge}`}>{titleCaseStatus(status)}</span>
                    </div>
                    <p className="mt-2 max-w-3xl text-sm font-semibold leading-relaxed text-slate-700">
                      {result.message || result.error || 'Document integrity verification completed.'}
                    </p>
                    {status === 'UNABLE_TO_VERIFY' && (
                      <div className="mt-3 flex items-start gap-2 rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-xs font-semibold leading-relaxed text-slate-600">
                        <Info className="mt-0.5 h-4 w-4 shrink-0 text-[#1e2a52]" />
                        <span>A valid PDF or matching hash is not proof of authenticity without a trusted reference file or validated digital signature.</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
                  {reportHref && (
                    <a
                      href={reportHref}
                      download
                      className="inline-flex items-center justify-center gap-2 rounded-full bg-[#1e2a52] px-5 py-2.5 text-sm font-black text-white shadow-md transition-all hover:bg-[#2a3a6a] focus:outline-none focus:ring-2 focus:ring-[#1e2a52]/30"
                    >
                      <Download className="h-4 w-4" />
                      Download Verification Report
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={resetWorkflow}
                    className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-300 bg-white px-5 py-2.5 text-sm font-black text-slate-700 transition-colors hover:border-[#1e2a52] hover:text-[#1e2a52] focus:outline-none focus:ring-2 focus:ring-[#1e2a52]/20"
                  >
                    <RefreshCcw className="h-4 w-4" />
                    Process Another File
                  </button>
                </div>
              </div>
            </section>

            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Fact label="File Name" value={result.filename} />
              <Fact label="File Size" value={formatBytes(result.file_size)} />
              <Fact label="Pages" value={pdf.page_count} />
              <Fact label="Encrypted" value={pdf.encrypted} />
              <Fact label="PDF Version" value={pdf.pdf_version || metadata.pdf_version || metadata.format} />
              <Fact label="Verification ID" value={result.verification_id} />
              <Fact label="Verification Date" value={formatDate(result.verified_at)} />
              <Fact label="MIME Type" value={result.mime_type} />
              <Fact label="Reference Used" value={reference.performed} />
            </section>

            <Section icon={Fingerprint} title="Fingerprints">
              <div className="space-y-3">
                <HashRow
                  algorithm="SHA-256"
                  value={result.file_integrity?.sha256}
                  verified={Boolean(reference.performed && reference.exact_match)}
                  onCopy={handleCopy}
                  copied={copied}
                />
                <HashRow algorithm="SHA-512" value={result.file_integrity?.sha512} onCopy={handleCopy} copied={copied} />
              </div>
            </Section>

            <div className="grid gap-5 lg:grid-cols-2">
              <Section icon={FileCheck2} title="PDF Structure">
                <div className="grid gap-3 sm:grid-cols-2">
                  <Fact label="Valid PDF" value={pdf.is_valid_pdf} />
                  <Fact label="Parser Status" value={titleCaseStatus(pdf.parser_status)} />
                  <Fact label="EOF Marker" value={pdf.eof_marker_present} />
                  <Fact label="Catalog" value={pdf.document_catalog_present} />
                  <Fact label="Trailer" value={pdf.trailer_present} />
                  <Fact label="XRef Objects" value={pdf.cross_reference_objects} />
                </div>
              </Section>

              <Section
                icon={ShieldCheck}
                title="Digital Signature"
                right={<StatusPill tone={signatures.signature_present ? 'emerald' : 'slate'}>{signatures.signature_present ? 'Present' : 'Not found'}</StatusPill>}
              >
                <div className="grid gap-3 sm:grid-cols-2">
                  <Fact label="Signature Count" value={signatures.signature_count ?? 0} />
                  <Fact label="Validation Status" value={titleCaseStatus(signatures.validation_status)} />
                </div>
                {signatures.signature_details?.length > 0 ? (
                  <div className="mt-4 space-y-3">
                    {signatures.signature_details.map((signature, index) => (
                      <div key={`${signature.signature_field_name || 'signature'}-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <p className="text-sm font-black text-slate-800">Signature {index + 1}</p>
                        <div className="mt-3 grid gap-3 sm:grid-cols-2">
                          <Fact label="Signer" value={signature.signer_name} />
                          <Fact label="Status" value={titleCaseStatus(signature.signature_status)} />
                          <Fact label="Certificate" value={titleCaseStatus(signature.certificate_status)} />
                          <Fact label="Modified After Signing" value={signature.document_modified_after_signing} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600">
                    No cryptographic signature details were available for this document.
                  </p>
                )}
              </Section>
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <Section
                icon={RefreshCcw}
                title="Incremental Updates"
                right={<StatusPill tone={incremental.detected ? 'amber' : 'emerald'}>{incremental.detected ? 'Detected' : 'Not detected'}</StatusPill>}
              >
                <p className="mb-4 text-sm font-semibold leading-relaxed text-slate-600">
                  Incremental updates can be legitimate PDF revisions, such as signing or saving changes. Treat them as context for review, not as proof of tampering by themselves.
                </p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Fact label="Revision Count" value={incremental.revision_count} />
                  <Fact label="StartXRef Count" value={incremental.startxref_count} />
                  <Fact label="EOF Markers" value={incremental.eof_marker_count} />
                  <Fact label="Previous XRef Markers" value={incremental.previous_xref_markers} />
                </div>
              </Section>

              <Section
                icon={Scale}
                title="Reference Comparison"
                right={
                  reference.performed ? (
                    <StatusPill tone={reference.exact_match ? 'emerald' : 'red'}>{reference.exact_match ? 'Exact match' : 'Different'}</StatusPill>
                  ) : (
                    <StatusPill>Not performed</StatusPill>
                  )
                }
              >
                <p className="text-sm font-semibold leading-relaxed text-slate-600">
                  {reference.performed
                    ? reference.message ||
                      (reference.exact_match
                        ? 'Uploaded file exactly matches the trusted reference.'
                        : 'Uploaded file differs from the trusted reference. This should be reviewed with document context.')
                    : 'No trusted reference file was provided, so this verification cannot compare against a known-good copy.'}
                </p>
                {reference.performed && (
                  <div className="mt-4 grid gap-3">
                    <Fact label="Uploaded SHA-256" value={truncateHash(reference.uploaded_sha256)} />
                    <Fact label="Reference SHA-256" value={truncateHash(reference.reference_sha256)} />
                  </div>
                )}
              </Section>
            </div>

            <Section icon={FileText} title="Metadata">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Fact label="Title" value={metadata.title} />
                <Fact label="Author" value={metadata.author} />
                <Fact label="Subject" value={metadata.subject} />
                <Fact label="Creator" value={metadata.creator} />
                <Fact label="Producer" value={metadata.producer} />
                <Fact label="Format" value={metadata.format} />
                <Fact label="Created" value={metadata.creation_date} />
                <Fact label="Modified" value={metadata.modification_date} />
                <Fact label="Extraction Status" value={metadata.extraction_status || 'Complete'} />
              </div>
            </Section>

            {(warnings.length > 0 || errors.length > 0 || pdf.warnings?.length > 0 || pdf.errors?.length > 0) && (
              <Section icon={AlertCircle} title="Warnings And Errors">
                <div className="grid gap-4 lg:grid-cols-2">
                  <div>
                    <p className="mb-2 text-xs font-black uppercase tracking-wide text-amber-700">Warnings</p>
                    {(warnings.length || pdf.warnings?.length) ? (
                      <ul className="space-y-2">
                        {[...warnings, ...(pdf.warnings || [])].map((item, index) => (
                          <li key={`warning-${index}`} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm font-semibold text-slate-500">None reported.</p>
                    )}
                  </div>
                  <div>
                    <p className="mb-2 text-xs font-black uppercase tracking-wide text-red-700">Errors</p>
                    {(errors.length || pdf.errors?.length) ? (
                      <ul className="space-y-2">
                        {[...errors, ...(pdf.errors || [])].map((item, index) => (
                          <li key={`error-${index}`} className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-800">
                            {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm font-semibold text-slate-500">None reported.</p>
                    )}
                  </div>
                </div>
              </Section>
            )}

            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
