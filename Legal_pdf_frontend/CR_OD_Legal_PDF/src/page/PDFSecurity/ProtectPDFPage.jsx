import React, { useMemo, useRef, useState } from 'react';
import { AlertCircle, ArrowLeft, CheckCircle2, Download, FileText, Lock, Upload, X } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

const PERMISSIONS = [
  ['allow_print', 'Printing'],
  ['allow_high_quality_print', 'High-quality printing'],
  ['allow_copy', 'Copying'],
  ['allow_edit', 'Editing'],
  ['allow_form_fill', 'Form filling'],
  ['allow_comment', 'Commenting / annotations'],
  ['allow_accessibility', 'Accessibility access'],
  ['allow_page_extraction', 'Page extraction'],
  ['allow_document_assembly', 'Document assembly'],
];

const DEFAULT_PERMISSIONS = {
  allow_print: false,
  allow_high_quality_print: false,
  allow_copy: false,
  allow_edit: false,
  allow_form_fill: false,
  allow_comment: false,
  allow_accessibility: true,
  allow_page_extraction: false,
  allow_document_assembly: false,
};

function formatSize(bytes) {
  if (!bytes) return '0 KB';
  return bytes < 1024 * 1024 ? `${Math.round(bytes / 1024)} KB` : `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function getPasswordStrength(password) {
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  if (!password) return { label: 'Not set', color: 'bg-slate-300', width: '0%' };
  if (score <= 2) return { label: 'Weak', color: 'bg-red-500', width: '33%' };
  if (score <= 4) return { label: 'Medium', color: 'bg-amber-500', width: '66%' };
  return { label: 'Strong', color: 'bg-emerald-600', width: '100%' };
}

export default function ProtectPDFPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [ownerPassword, setOwnerPassword] = useState('');
  const [encryption, setEncryption] = useState('aes-256');
  const [permissions, setPermissions] = useState(DEFAULT_PERMISSIONS);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [downloadFilename, setDownloadFilename] = useState('');
  const inputRef = useRef(null);

  const strength = useMemo(() => getPasswordStrength(password), [password]);
  const toolName = tool?.name || 'Protect PDF';
  const toolDesc = tool?.description || 'Encrypt PDF files with password protection and permission controls.';

  const resetOutput = () => {
    if (downloadUrl) window.URL.revokeObjectURL(downloadUrl);
    setResult(null);
    setDownloadUrl(null);
    setDownloadFilename('');
  };

  const addFile = (selectedFile) => {
    setError('');
    resetOutput();
    if (!selectedFile) return;
    if (selectedFile.type !== 'application/pdf' && !selectedFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are accepted.');
      return;
    }
    setFile(selectedFile);
  };

  const handlePermissionChange = (key) => {
    setPermissions(prev => ({ ...prev, [key]: !prev[key] }));
    resetOutput();
  };

  const validate = () => {
    if (!file) return 'PDF file is required.';
    if (!password.trim()) return 'Open password is required.';
    if (password !== confirmPassword) return 'Password confirmation does not match.';
    return '';
  };

  const handleProtect = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsProcessing(true);
    setError('');
    resetOutput();

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_password', password);
      formData.append('confirm_password', confirmPassword);
      formData.append('owner_password', ownerPassword);
      formData.append('encryption', encryption);
      Object.entries(permissions).forEach(([key, value]) => formData.append(key, String(value)));

      const response = await fetch(`${API_BASE_URL}/api/pdf/security/protect`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let message = `Server error: ${response.status}`;
        try {
          const data = await response.json();
          message = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        } catch (_) {}
        throw new Error(message);
      }

      const data = await response.json();
      setResult(data);

      if (data.download_url) {
        const fileResponse = await fetch(`${API_BASE_URL}${data.download_url}`);
        if (!fileResponse.ok) throw new Error('Protected PDF was created, but download failed.');
        const blob = await fileResponse.blob();
        setDownloadUrl(window.URL.createObjectURL(blob));
        setDownloadFilename(data.output_file || data.download_url.split('/').pop() || 'protected.pdf');
      }
    } catch (err) {
      setError(err.message || 'Protect PDF failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    resetOutput();
    setFile(null);
    setPassword('');
    setConfirmPassword('');
    setOwnerPassword('');
    setEncryption('aes-256');
    setPermissions(DEFAULT_PERMISSIONS);
    setError('');
  };

  return (
    <div className="flex-1 flex flex-col w-full relative z-20 min-h-screen bg-transparent">
      <div className="w-full max-w-[1200px] mx-auto px-4 sm:px-6 md:px-10 pt-4 sm:pt-8 pb-4 relative z-30 flex-none text-left">
        <button onClick={onBack} className="inline-flex items-center gap-2 bg-white text-[#1e2a52] font-bold px-4 py-2 rounded-full shadow-md border border-slate-200 hover:shadow-lg hover:scale-105 transition-all cursor-pointer text-xs sm:text-sm">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
      </div>

      <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
        <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">{toolName}</h1>
        <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">{toolDesc}</p>
        <span className="inline-block mt-2 px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full">Backend Connected</span>
      </div>

      <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 pb-14">
        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6 sm:p-8">
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => { e.preventDefault(); setIsDragging(false); addFile(e.dataTransfer.files?.[0]); }}
            onClick={() => inputRef.current?.click()}
            className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${isDragging ? 'border-[#1e2a52] bg-[#e8f0e2]' : 'border-[#1e2a52]/30 bg-[#f8faf7] hover:border-[#1e2a52] hover:bg-[#eff4ea]'}`}
          >
            <input ref={inputRef} type="file" accept=".pdf,application/pdf" className="hidden" onChange={(e) => addFile(e.target.files?.[0])} />
            <div className="w-16 h-16 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Upload className="w-8 h-8 text-[#1e2a52]" />
            </div>
            <p className="text-base sm:text-lg font-bold text-[#1e2a52] mb-1">Drop PDF here or click to browse</p>
            <p className="text-xs sm:text-sm text-slate-500">Accepted: <span className="font-semibold text-[#1e2a52]">PDF files (.pdf)</span></p>
          </div>

          {file && (
            <div className="mt-5 flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-xl px-4 py-3">
              <div className="w-9 h-9 rounded-lg bg-[#1e2a52]/10 flex items-center justify-center shrink-0"><FileText className="w-4 h-4 text-[#1e2a52]" /></div>
              <div className="flex-1 min-w-0"><p className="text-xs sm:text-sm font-semibold text-slate-800 truncate">{file.name}</p><p className="text-[10px] sm:text-xs text-slate-400">{formatSize(file.size)}</p></div>
              <button onClick={() => { setFile(null); resetOutput(); }} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
            </div>
          )}

          <div className="mt-6 grid grid-cols-1 lg:grid-cols-[1fr_0.85fr] gap-6">
            <div className="space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Open password</label>
                  <input type="password" value={password} onChange={(e) => { setPassword(e.target.value); resetOutput(); }} autoComplete="new-password" className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]" />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">Confirm password</label>
                  <input type="password" value={confirmPassword} onChange={(e) => { setConfirmPassword(e.target.value); resetOutput(); }} autoComplete="new-password" className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]" />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-slate-600">Password strength</span>
                  <span className="text-xs font-bold text-slate-500">{strength.label}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-200 overflow-hidden"><div className={`h-full ${strength.color}`} style={{ width: strength.width }} /></div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 mb-1">Owner password</label>
                <input type="password" value={ownerPassword} onChange={(e) => { setOwnerPassword(e.target.value); resetOutput(); }} autoComplete="new-password" className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]" />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-600 mb-2">Encryption</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    ['aes-128', 'AES-128'],
                    ['aes-256', 'AES-256'],
                  ].map(([value, label]) => (
                    <button key={value} type="button" onClick={() => { setEncryption(value); resetOutput(); }} className={`px-4 py-3 rounded-xl border text-sm font-bold transition-all ${encryption === value ? 'bg-[#1e2a52] border-[#1e2a52] text-white shadow-md' : 'bg-white border-slate-200 text-slate-700 hover:border-[#1e2a52]'}`}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs font-bold text-slate-600 mb-2">Permissions</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {PERMISSIONS.map(([key, label]) => (
                    <label key={key} className="flex items-center justify-between gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 cursor-pointer">
                      <span className="text-xs sm:text-sm font-semibold text-slate-700">{label}</span>
                      <input type="checkbox" checked={permissions[key]} onChange={() => handlePermissionChange(key)} className="h-4 w-4 accent-[#1e2a52]" />
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5 h-fit">
              <div className="flex items-center gap-2 text-[#1e2a52] font-black mb-4"><Lock className="w-5 h-5" /> Security Summary</div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between gap-4"><span className="text-slate-500">File</span><span className="font-semibold text-slate-800 text-right truncate">{file?.name || 'Not selected'}</span></div>
                <div className="flex justify-between gap-4"><span className="text-slate-500">Encryption</span><span className="font-semibold text-slate-800">{encryption === 'aes-256' ? 'AES-256' : 'AES-128'}</span></div>
                <div className="flex justify-between gap-4"><span className="text-slate-500">Owner password</span><span className="font-semibold text-slate-800">{ownerPassword ? 'Set' : 'Not set'}</span></div>
              </div>
              <div className="mt-4 pt-4 border-t border-slate-200">
                <p className="text-xs font-bold text-slate-500 uppercase mb-2">Allowed actions</p>
                <div className="flex flex-wrap gap-2">
                  {PERMISSIONS.filter(([key]) => permissions[key]).map(([key, label]) => (
                    <span key={key} className="px-2.5 py-1 rounded-full bg-white border border-slate-200 text-[11px] font-semibold text-slate-700">{label}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="mt-5 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs sm:text-sm">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /><span>{error}</span>
            </div>
          )}

          <div className="mt-8 text-center">
            {isProcessing ? (
              <div className="flex flex-col items-center justify-center p-6 bg-[#f8faf7] border border-slate-200/80 rounded-2xl min-h-[150px]">
                <div className="w-12 h-12 border-4 border-[#1e2a52] border-t-transparent rounded-full animate-spin mb-4" />
                <p className="text-xs sm:text-sm font-bold text-[#1e2a52] animate-pulse">Protecting PDF... Please wait.</p>
              </div>
            ) : result ? (
              <div className="space-y-4">
                <div className="flex items-center justify-center gap-2 text-emerald-600 font-bold text-sm">
                  <CheckCircle2 className="w-5 h-5" /> PDF protected successfully
                </div>
                {downloadUrl && (
                  <a href={downloadUrl} download={downloadFilename} className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-3 rounded-full font-bold shadow-md transition-all text-sm cursor-pointer hover:scale-105">
                    <Download className="w-4 h-4" /> Download Protected PDF
                  </a>
                )}
                <div className="text-left bg-blue-50 border border-blue-200 rounded-xl p-4 max-h-64 overflow-auto mt-4">
                  <pre className="text-xs text-blue-800 whitespace-pre-wrap font-mono">{JSON.stringify(result, null, 2)}</pre>
                </div>
                <button onClick={handleReset} className="inline-flex items-center gap-2 bg-[#1e2a52] hover:bg-[#16203e] text-white px-8 py-3 rounded-full font-bold shadow-lg transition-all text-sm cursor-pointer hover:scale-105 active:scale-95">
                  Protect Another PDF
                </button>
              </div>
            ) : (
              <button onClick={handleProtect} className="bg-[#1e2a52] hover:bg-[#16203e] text-white px-10 py-3.5 rounded-full font-bold shadow-lg transition-all text-sm cursor-pointer inline-flex items-center gap-2 hover:scale-105 active:scale-95">
                <Lock className="w-4 h-4" /> Protect PDF
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
