import React, { useState, useRef } from 'react';
import { Upload, FileText, ArrowLeft, X, AlertCircle, Square, Check } from 'lucide-react';
import { getToolApiConfig } from '../../config/toolApiConfig';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function BlackoutAreasPage({ tool, onBack }) {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [apiResult, setApiResult] = useState(null);
  const inputRef = useRef();

  // Manual Coordinates for Redaction
  const [areas, setAreas] = useState([{ page: 1, rect: [100, 100, 300, 200] }]);

  const toolName = tool?.name || 'Blackout Areas';
  const toolDesc = tool?.description || 'Permanently redact sensitive regions in your PDF.';
  const accepted = { accept: '.pdf', label: 'PDF files (.pdf)' };
  
  const apiConfig = getToolApiConfig('Blackout Areas') || {
    endpoint: '/api/pdf/security/blackout-areas',
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
      formData.append('areas', JSON.stringify(areas));

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

  const addArea = () => {
    setAreas([...areas, { page: 1, rect: [0, 0, 100, 100] }]);
  };

  const updateArea = (index, field, value) => {
    const newAreas = [...areas];
    if (field === 'page') newAreas[index].page = parseInt(value) || 1;
    else newAreas[index].rect[field] = parseFloat(value) || 0;
    setAreas(newAreas);
  };

  const removeArea = (index) => {
    setAreas(areas.filter((_, i) => i !== index));
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

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
                    <h3 className="font-bold text-[#1e2a52] mb-4 text-lg">Define Redaction Areas</h3>
                    <p className="text-sm text-slate-600 mb-4">Enter coordinates (x0, y0, x1, y1) for permanent redaction.</p>
                    
                    {areas.map((area, idx) => (
                      <div key={idx} className="flex flex-wrap items-center gap-3 mb-3">
                        <label className="text-sm font-semibold text-slate-700">Page:</label>
                        <input type="number" min="1" value={area.page} onChange={e => updateArea(idx, 'page', e.target.value)} className="w-16 p-2 border border-slate-300 rounded-md" />
                        
                        <label className="text-sm font-semibold text-slate-700">x0:</label>
                        <input type="number" value={area.rect[0]} onChange={e => updateArea(idx, 0, e.target.value)} className="w-20 p-2 border border-slate-300 rounded-md" />
                        <label className="text-sm font-semibold text-slate-700">y0:</label>
                        <input type="number" value={area.rect[1]} onChange={e => updateArea(idx, 1, e.target.value)} className="w-20 p-2 border border-slate-300 rounded-md" />
                        <label className="text-sm font-semibold text-slate-700">x1:</label>
                        <input type="number" value={area.rect[2]} onChange={e => updateArea(idx, 2, e.target.value)} className="w-20 p-2 border border-slate-300 rounded-md" />
                        <label className="text-sm font-semibold text-slate-700">y1:</label>
                        <input type="number" value={area.rect[3]} onChange={e => updateArea(idx, 3, e.target.value)} className="w-20 p-2 border border-slate-300 rounded-md" />
                        
                        {areas.length > 1 && (
                          <button onClick={() => removeArea(idx)} className="p-2 text-red-500 hover:bg-red-50 rounded-md"><X className="w-5 h-5"/></button>
                        )}
                      </div>
                    ))}
                    <button onClick={addArea} className="mt-2 text-sm font-bold text-[#3b82f6] hover:underline">+ Add Another Area</button>
                  </div>

                  <button onClick={handleProcess} className="w-full mt-4 bg-[#1e2a52] text-white font-bold py-3 px-6 rounded-xl shadow-md hover:bg-slate-800 transition-all cursor-pointer">
                    Apply Blackout Areas
                  </button>
                </div>
              )}

              {error && (
                <div className="mt-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs sm:text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /><span>{error}</span>
                </div>
              )}
            </>
          )}

          {isProcessing && (
            <div className="py-16 text-center">
              <div className="w-16 h-16 border-4 border-slate-200 border-t-[#1e2a52] rounded-full animate-spin mx-auto mb-6"></div>
              <p className="text-lg font-bold text-[#1e2a52]">Applying permanent redactions...</p>
            </div>
          )}

          {isDone && apiResult && (
            <div className="text-center">
              <div className="flex justify-center mb-6">
                <Check className="w-16 h-16 text-emerald-500 bg-emerald-50 rounded-full p-2" />
              </div>
              <h2 className="text-2xl font-black mb-2 text-emerald-600">Redaction Complete</h2>
              <p className="text-slate-600 mb-6 font-medium">The selected areas have been permanently blacked out.</p>

              <div className="flex flex-col sm:flex-row justify-center gap-4 mt-8">
                <a href={API_BASE_URL + apiResult.downloadUrl} className="px-6 py-3 bg-[#1e2a52] text-white font-bold rounded-xl shadow-md hover:bg-slate-800 transition-colors inline-flex items-center justify-center gap-2">
                  <Square className="w-5 h-5" fill="currentColor"/> Download Redacted PDF
                </a>
                <button onClick={() => { setIsDone(false); setFiles([]); }} className="px-6 py-3 bg-slate-100 text-[#1e2a52] font-bold rounded-xl border border-slate-200 hover:bg-slate-200 transition-colors">
                  Process Another File
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
