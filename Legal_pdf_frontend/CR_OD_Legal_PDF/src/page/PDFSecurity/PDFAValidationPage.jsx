import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, ArrowLeft, X, AlertCircle, ShieldAlert, ShieldCheck, ShieldX, FileQuestion } from 'lucide-react';
import { getToolApiConfig } from '../../config/toolApiConfig';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function PDFAValidationPage({ tool, onBack }) {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [apiResult, setApiResult] = useState(null);
  const inputRef = useRef();

  const toolName = tool?.name || 'PDF/A Validation';
  const toolDesc = tool?.description || 'Validate if your document complies with PDF/A archival standards.';
  const accepted = { accept: '.pdf', label: 'PDF files (.pdf)' };
  
  const apiConfig = getToolApiConfig('PDF/A Validation') || {
    endpoint: '/api/pdf/security/pdfa-validate',
    method: 'POST'
  };

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
      setIsDone(false); 
      setApiResult(null); 
    }
  };

  const handleProcess = async () => {
    if (!files.length) return;
    setIsProcessing(true);
    setError('');
    setApiResult(null);

    try {
      const formData = new FormData();
      formData.append('file', files[0].raw);

      const url = `${API_BASE_URL}${apiConfig.endpoint}`;
      const response = await fetch(url, { method: apiConfig.method, body: formData });

      if (!response.ok) {
        let errMsg = `Server error: ${response.status}`;
        try { const errData = await response.json(); errMsg = errData.detail || errMsg; } catch (_) {}
        throw new Error(errMsg);
      }

      const data = await response.json();
      setApiResult(data);
      setIsDone(true);
    } catch (err) {
      setError(err.message || 'Processing failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
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
          
          {!isDone && !isProcessing && (
            <>
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

              {error && (
                <div className="mt-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs sm:text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /><span>{error}</span>
                </div>
              )}

              {files.length > 0 && (
                <div className="mt-6 space-y-2.5">
                  <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-xl px-4 py-3">
                    <div className="w-9 h-9 rounded-lg bg-[#1e2a52]/10 flex items-center justify-center shrink-0"><FileText className="w-4 h-4 text-[#1e2a52]" /></div>
                    <div className="flex-1 min-w-0"><p className="text-xs sm:text-sm font-semibold text-slate-800 truncate">{files[0].name}</p><p className="text-[10px] sm:text-xs text-slate-400">{files[0].size}</p></div>
                    <button onClick={() => setFiles([])} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
                  </div>
                  <button onClick={handleProcess} className="w-full mt-4 bg-[#ef4444] text-white font-bold py-3 px-6 rounded-xl shadow-md hover:bg-red-600 transition-all cursor-pointer">
                    Validate PDF/A
                  </button>
                </div>
              )}
            </>
          )}

          {isProcessing && (
            <div className="py-16 text-center">
              <div className="w-16 h-16 border-4 border-slate-200 border-t-[#ef4444] rounded-full animate-spin mx-auto mb-6"></div>
              <p className="text-lg font-bold text-[#1e2a52]">Validating PDF/A constraints...</p>
            </div>
          )}

          {isDone && apiResult && (
            <div className="text-center">
              <div className="flex justify-center mb-6">
                {apiResult.is_compliant ? <ShieldCheck className="w-16 h-16 text-emerald-500" /> : <ShieldAlert className="w-16 h-16 text-amber-500" />}
              </div>
              <h2 className={`text-2xl font-black mb-2 ${apiResult.is_compliant ? 'text-emerald-600' : 'text-amber-600'}`}>
                {apiResult.is_compliant ? 'PDF/A Compliant' : 'Non-Compliant'}
              </h2>
              <p className="text-slate-600 mb-6 font-medium">Detected Standard: {apiResult.detected_standard}</p>

              <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 text-left mb-6">
                <h3 className="font-bold text-[#1e2a52] mb-4 text-lg border-b border-slate-200 pb-2">Validation Summary</h3>
                <div className="space-y-4">
                  {apiResult.errors && apiResult.errors.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-red-600 flex items-center gap-2"><X className="w-4 h-4"/> Errors</h4>
                      <ul className="list-disc ml-5 mt-1 text-sm text-slate-700">
                        {apiResult.errors.map((e, i) => <li key={i}>{e.description}</li>)}
                      </ul>
                    </div>
                  )}
                  {apiResult.warnings && apiResult.warnings.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-amber-600 flex items-center gap-2"><AlertCircle className="w-4 h-4"/> Warnings</h4>
                      <ul className="list-disc ml-5 mt-1 text-sm text-slate-700">
                        {apiResult.warnings.map((w, i) => <li key={i}>{w.description}</li>)}
                      </ul>
                    </div>
                  )}
                  {apiResult.passed_checks && apiResult.passed_checks.length > 0 && (
                    <div>
                      <h4 className="font-semibold text-emerald-600 flex items-center gap-2"><CheckCircle2 className="w-4 h-4"/> Passed Checks</h4>
                      <ul className="list-disc ml-5 mt-1 text-sm text-slate-700">
                        {apiResult.passed_checks.map((p, i) => <li key={i}>{p}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col sm:flex-row justify-center gap-4 mt-8">
                <button onClick={() => { setIsDone(false); setFiles([]); }} className="px-6 py-3 bg-slate-100 text-[#1e2a52] font-bold rounded-xl border border-slate-200 hover:bg-slate-200 transition-colors">
                  Validate Another File
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
