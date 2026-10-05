import React, { useState, useRef } from 'react';
import { Upload, FileText, ArrowLeft, X, AlertCircle, Eye, CheckCircle2 } from 'lucide-react';
import { getToolApiConfig } from '../../config/toolApiConfig';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function HideSensitiveInformationPage({ tool, onBack }) {
  const [files, setFiles] = useState([]);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [detectedItems, setDetectedItems] = useState([]);
  const [selectedItemIds, setSelectedItemIds] = useState(new Set());
  const [downloadUrl, setDownloadUrl] = useState('');
  
  const inputRef = useRef();

  const toolName = tool?.name || 'Hide Sensitive Info';
  const toolDesc = tool?.description || 'Detect and permanently redact emails, phones, and IDs.';
  const accepted = { accept: '.pdf', label: 'PDF files (.pdf)' };
  
  const apiDetect = { endpoint: '/api/pdf/security/hide-sensitive-detect', method: 'POST' };
  const apiApply = { endpoint: '/api/pdf/security/hide-sensitive-apply', method: 'POST' };

  const addFiles = (newFiles) => {
    setError('');
    const valid = [];
    Array.from(newFiles).forEach(f => {
      if (f.name.toLowerCase().endsWith('.pdf') || f.type === 'application/pdf') {
        valid.push({ 
          name: f.name, 
          size: f.size < 1024 * 1024 ? (f.size / 1024).toFixed(0) + ' KB' : (f.size / (1024 * 1024)).toFixed(2) + ' MB', 
          raw: f 
        });
      } else {
        setError('Only PDF files are accepted.');
      }
    });
    if (valid.length > 0) { 
      setFiles([valid[0]]); 
      setDetectedItems([]);
      setSelectedItemIds(new Set());
      setIsDone(false); 
    }
  };

  const handleDetect = async () => {
    if (!files.length) return;
    setIsDetecting(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', files[0].raw);

      const url = `${API_BASE_URL}${apiDetect.endpoint}`;
      const response = await fetch(url, { method: apiDetect.method, body: formData });

      if (!response.ok) {
        let errMsg = `Server error: ${response.status}`;
        try { const errData = await response.json(); errMsg = errData.detail || errMsg; } catch (_) {}
        throw new Error(errMsg);
      }

      const data = await response.json();
      setDetectedItems(data.detected_items || []);
      const allIds = new Set((data.detected_items || []).map(i => i.id));
      setSelectedItemIds(allIds); // Select all by default
    } catch (err) {
      setError(err.message || 'Detection failed. Please try again.');
    } finally {
      setIsDetecting(false);
    }
  };

  const handleApply = async () => {
    if (!files.length) return;
    setIsApplying(true);
    setError('');

    try {
      // Filter the selected areas
      const areasToRedact = detectedItems
        .filter(item => selectedItemIds.has(item.id))
        .map(item => ({ page: item.page, rect: item.rect }));

      if (areasToRedact.length === 0) {
        throw new Error("No items selected for redaction.");
      }

      const formData = new FormData();
      formData.append('file', files[0].raw);
      formData.append('areas', JSON.stringify(areasToRedact));

      const url = `${API_BASE_URL}${apiApply.endpoint}`;
      const response = await fetch(url, { method: apiApply.method, body: formData });

      if (!response.ok) {
        let errMsg = `Server error: ${response.status}`;
        try { const errData = await response.json(); errMsg = errData.detail || errMsg; } catch (_) {}
        throw new Error(errMsg);
      }

      const data = await response.json();
      setDownloadUrl(data.downloadUrl);
      setIsDone(true);
    } catch (err) {
      setError(err.message || 'Application failed. Please try again.');
    } finally {
      setIsApplying(false);
    }
  };

  const toggleSelection = (id) => {
    const newSelected = new Set(selectedItemIds);
    if (newSelected.has(id)) newSelected.delete(id);
    else newSelected.add(id);
    setSelectedItemIds(newSelected);
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
      </div>

      <div className="w-full max-w-4xl mx-auto px-4 sm:px-6 pb-14">
        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6 sm:p-10">
          
          {!isDone && !isDetecting && !isApplying && detectedItems.length === 0 && (
            <>
              {!files.length ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files); }}
                  onClick={() => inputRef.current?.click()}
                  className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all ${isDragging ? 'border-[#1e2a52] bg-[#e8f0e2]' : 'border-[#1e2a52]/30 bg-[#f8faf7] hover:border-[#1e2a52] hover:bg-[#eff4ea]'}`}
                >
                  <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={(e) => { if (e.target.files?.length) addFiles(e.target.files); }} />
                  <div className="w-16 h-16 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <Upload className="w-8 h-8 text-[#1e2a52]" />
                  </div>
                  <p className="text-base sm:text-lg font-bold text-[#1e2a52] mb-1">Drop PDF here or click to browse</p>
                  <p className="text-xs sm:text-sm text-slate-500">Accepted: <span className="font-semibold text-[#1e2a52]">{accepted.label}</span></p>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-xl px-4 py-3">
                    <div className="w-9 h-9 rounded-lg bg-[#1e2a52]/10 flex items-center justify-center shrink-0"><FileText className="w-4 h-4 text-[#1e2a52]" /></div>
                    <div className="flex-1 min-w-0"><p className="text-xs sm:text-sm font-semibold text-slate-800 truncate">{files[0].name}</p><p className="text-[10px] sm:text-xs text-slate-400">{files[0].size}</p></div>
                    <button onClick={() => setFiles([])} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
                  </div>
                  <button onClick={handleDetect} className="w-full mt-4 bg-[#8b5cf6] text-white font-bold py-3 px-6 rounded-xl shadow-md hover:bg-purple-600 transition-all cursor-pointer">
                    Detect Sensitive Info
                  </button>
                </div>
              )}
            </>
          )}

          {isDetecting && (
            <div className="py-16 text-center">
              <div className="w-16 h-16 border-4 border-slate-200 border-t-[#8b5cf6] rounded-full animate-spin mx-auto mb-6"></div>
              <p className="text-lg font-bold text-[#1e2a52]">Scanning document for sensitive information...</p>
            </div>
          )}

          {isApplying && (
            <div className="py-16 text-center">
              <div className="w-16 h-16 border-4 border-slate-200 border-t-[#ef4444] rounded-full animate-spin mx-auto mb-6"></div>
              <p className="text-lg font-bold text-[#1e2a52]">Permanently redacting selected information...</p>
            </div>
          )}

          {!isDone && !isDetecting && !isApplying && detectedItems.length > 0 && (
            <div className="space-y-6">
              <h2 className="text-2xl font-black text-[#1e2a52] mb-4">Review Detected Information</h2>
              <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden max-h-[400px] overflow-y-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-100 text-slate-600 font-bold uppercase text-xs">
                    <tr>
                      <th className="p-3"><input type="checkbox" checked={selectedItemIds.size === detectedItems.length} onChange={(e) => setSelectedItemIds(e.target.checked ? new Set(detectedItems.map(i=>i.id)) : new Set())} /></th>
                      <th className="p-3">Type</th>
                      <th className="p-3">Value</th>
                      <th className="p-3">Page</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {detectedItems.map((item) => (
                      <tr key={item.id} className={selectedItemIds.has(item.id) ? "bg-white" : "bg-slate-50 opacity-60"}>
                        <td className="p-3">
                          <input type="checkbox" checked={selectedItemIds.has(item.id)} onChange={() => toggleSelection(item.id)} />
                        </td>
                        <td className="p-3 font-semibold text-purple-600">{item.type}</td>
                        <td className="p-3 text-slate-700 font-mono text-xs">{item.text}</td>
                        <td className="p-3 text-slate-500">Page {item.page}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex justify-between items-center mt-4">
                <p className="text-sm font-semibold text-slate-600">{selectedItemIds.size} of {detectedItems.length} items selected for redaction.</p>
                <button onClick={handleApply} disabled={selectedItemIds.size === 0} className="bg-[#ef4444] text-white font-bold py-2 px-6 rounded-xl shadow-md hover:bg-red-600 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
                  Apply Redactions
                </button>
              </div>
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs sm:text-sm">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /><span>{error}</span>
            </div>
          )}

          {isDone && downloadUrl && (
            <div className="text-center">
              <div className="flex justify-center mb-6">
                <CheckCircle2 className="w-16 h-16 text-emerald-500" />
              </div>
              <h2 className="text-2xl font-black mb-2 text-emerald-600">Redaction Complete</h2>
              <p className="text-slate-600 mb-6 font-medium">The selected sensitive information has been permanently removed.</p>

              <div className="flex flex-col sm:flex-row justify-center gap-4 mt-8">
                <a href={API_BASE_URL + downloadUrl} className="px-6 py-3 bg-[#1e2a52] text-white font-bold rounded-xl shadow-md hover:bg-slate-800 transition-colors inline-flex items-center justify-center gap-2">
                  <Eye className="w-5 h-5" /> Download Secure PDF
                </a>
                <button onClick={() => { setIsDone(false); setFiles([]); setDetectedItems([]); setSelectedItemIds(new Set()); }} className="px-6 py-3 bg-slate-100 text-[#1e2a52] font-bold rounded-xl border border-slate-200 hover:bg-slate-200 transition-colors">
                  Scan Another File
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
