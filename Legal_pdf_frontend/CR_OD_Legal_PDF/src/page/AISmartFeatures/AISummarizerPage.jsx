import React, { useState, useRef, useEffect } from 'react';
import {
  ArrowLeft, Upload, FileText, Bot, RefreshCw, CheckCircle2,
  AlertCircle, Copy, Download, Trash2, Clock, FileKey, AlignLeft
} from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Ensure PDF.js worker is loaded correctly
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
const MAX_UPLOAD_MB = 50;

export default function AISummarizerPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [summaryType, setSummaryType] = useState('medium');
  const [isUploading, setIsUploading] = useState(false);
  
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(null); // 'Extracting text', 'Summarizing', etc
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  
  const [history, setHistory] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  
  const [numPages, setNumPages] = useState(null);
  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    fetchHistory();
    return () => stopPolling();
  }, []);

  const fetchHistory = async () => {
    setIsHistoryLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/pdf/ai-summary/history`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      }
    } catch (err) {
      console.error("Failed to load history", err);
    } finally {
      setIsHistoryLoading(false);
    }
  };

  const handleFile = (incomingFile) => {
    setError('');
    setResult(null);
    setJobId(null);
    setStatus(null);
    setProgress(0);
    
    if (!incomingFile) return;
    if (incomingFile.type !== 'application/pdf' && !incomingFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF documents can be uploaded.');
      return;
    }
    if (incomingFile.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`PDF is too large. Maximum upload size is ${MAX_UPLOAD_MB} MB.`);
      return;
    }
    setFile(incomingFile);
  };

  const startSummarization = async () => {
    if (!file) return;
    setIsUploading(true);
    setError('');
    setResult(null);
    setStatus('Uploading document...');
    setProgress(5);

    try {
      // 1. Upload file
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadRes = await fetch(`${API_BASE_URL}/api/pdf/ai-summary/upload`, {
        method: 'POST',
        body: formData,
      });
      const uploadData = await uploadRes.json();
      
      if (!uploadRes.ok) throw new Error(uploadData.detail || 'Upload failed');
      
      const newJobId = uploadData.job_id;
      setJobId(newJobId);
      
      // 2. Start processing
      const processForm = new FormData();
      processForm.append('job_id', newJobId);
      processForm.append('summary_type', summaryType);
      
      setStatus('Starting AI engine...');
      setProgress(10);
      
      // Start polling status
      startPolling(newJobId);
      
      // Execute processing
      const processRes = await fetch(`${API_BASE_URL}/api/pdf/ai-summary/process`, {
        method: 'POST',
        body: processForm,
      });
      const processData = await processRes.json();
      
      if (!processRes.ok) {
         throw new Error(processData.detail || 'Summarization failed');
      }
      
      setResult(processData.summary);
      setStatus('Completed');
      setProgress(100);
      fetchHistory();
      
    } catch (err) {
      setError(err.message || 'An error occurred during summarization.');
      setStatus(null);
    } finally {
      setIsUploading(false);
      stopPolling();
    }
  };

  const startPolling = (currentJobId) => {
    stopPolling();
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/pdf/ai-summary/status/${currentJobId}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status) setStatus(data.status);
          if (data.progress) setProgress(data.progress);
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    }, 1500);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const deleteHistory = async (id) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/pdf/ai-summary/history/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchHistory();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadFromHistory = (item) => {
    setResult(item.result);
    setFile(null); // Reset file view to show history result clearly
    setJobId(item.id);
    setStatus('Completed');
    setProgress(100);
  };

  const copyToClipboard = () => {
    if (result) {
      navigator.clipboard.writeText(result);
    }
  };

  const downloadSummary = () => {
    if (result) {
      const blob = new Blob([result], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Summary_${jobId || 'document'}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="flex min-h-screen w-full flex-col bg-slate-50">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between px-4 pb-4 pt-6">
        <button onClick={onBack} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <div className="text-center">
          <h1 className="text-2xl font-black tracking-tight text-slate-900 flex items-center justify-center gap-2">
            <Bot className="h-6 w-6 text-blue-600" /> AI Summarizer
          </h1>
          <p className="text-sm font-medium text-slate-500">Powered by local AI models</p>
        </div>
        <div className="w-[92px]" />
      </div>

      <div className="mx-auto flex w-full max-w-[1440px] flex-col lg:flex-row gap-6 px-4 pb-12 items-start">
        
        {/* LEFT PANEL */}
        <aside className="w-full lg:w-[420px] shrink-0 space-y-4">
          
          {error && (
            <div className="flex items-start gap-2 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-semibold text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
            </div>
          )}

          {/* UPLOAD SECTION */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 flex items-center gap-2 font-black text-slate-800"><FileText className="h-4 w-4" /> 1. Upload PDF</h2>
            {!file ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); handleFile(e.dataTransfer.files?.[0]); }}
                className="flex min-h-32 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center transition hover:bg-slate-100"
              >
                <Upload className="mb-3 h-8 w-8 text-slate-400" />
                <p className="text-sm font-bold text-slate-700">Drag and drop your PDF here</p>
                <p className="text-xs text-slate-500 mt-1">Up to {MAX_UPLOAD_MB}MB</p>
                <button onClick={() => fileInputRef.current?.click()} className="mt-4 rounded-xl bg-slate-800 px-5 py-2 text-sm font-bold text-white hover:bg-slate-900">
                  Browse Files
                </button>
                <input ref={fileInputRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
              </div>
            ) : (
              <div className="rounded-xl border border-blue-100 bg-blue-50 p-3 flex justify-between items-center">
                <div className="truncate pr-2">
                  <p className="truncate text-sm font-black text-blue-950" title={file.name}>{file.name}</p>
                  <p className="mt-1 text-xs font-semibold text-blue-700">{(file.size / (1024*1024)).toFixed(2)} MB</p>
                </div>
                {!isUploading && status !== 'Completed' && (
                  <button onClick={() => setFile(null)} className="text-xs font-bold text-blue-600 underline shrink-0">Remove</button>
                )}
              </div>
            )}
          </section>

          {/* OPTIONS SECTION */}
          <section className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm ${(isUploading || status === 'Completed') ? 'opacity-50 pointer-events-none' : ''}`}>
             <h2 className="mb-3 flex items-center gap-2 font-black text-slate-800"><AlignLeft className="h-4 w-4" /> 2. Summary Detail</h2>
             <div className="grid grid-cols-3 gap-2">
                {['short', 'medium', 'detailed'].map(t => (
                  <button 
                    key={t}
                    onClick={() => setSummaryType(t)}
                    className={`rounded-xl py-2 px-1 text-xs font-bold border transition ${summaryType === t ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'}`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
             </div>
             
             <button 
                onClick={startSummarization}
                disabled={!file || isUploading}
                className="w-full mt-4 rounded-xl bg-blue-600 px-4 py-3 text-sm font-black text-white hover:bg-blue-700 disabled:opacity-50 disabled:bg-slate-400 flex items-center justify-center gap-2"
              >
                {isUploading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                {isUploading ? 'Processing...' : 'Generate AI Summary'}
              </button>
              
              {/* PROGRESS BAR */}
              {status && status !== 'Completed' && (
                 <div className="mt-4 space-y-2">
                    <div className="flex justify-between text-xs font-bold text-blue-800">
                       <span>{status}</span>
                       <span>{progress}%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-blue-100 overflow-hidden">
                       <div className="h-full bg-blue-600 transition-all duration-300 ease-out" style={{ width: `${progress}%` }}></div>
                    </div>
                 </div>
              )}
          </section>
          
          {/* HISTORY SECTION */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm max-h-[400px] overflow-y-auto">
             <div className="flex justify-between items-center mb-3">
                <h2 className="flex items-center gap-2 font-black text-slate-800"><Clock className="h-4 w-4" /> Recent Summaries</h2>
                <button onClick={fetchHistory} className="text-slate-400 hover:text-blue-600"><RefreshCw className={`h-3 w-3 ${isHistoryLoading ? 'animate-spin' : ''}`} /></button>
             </div>
             
             {history.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">No recent summaries found.</p>
             ) : (
                <div className="space-y-2">
                   {history.map(item => (
                      <div key={item.id} className="group relative rounded-xl border border-slate-100 bg-slate-50 p-3 hover:border-blue-200 transition cursor-pointer">
                         <div onClick={() => loadFromHistory(item)}>
                            <p className="text-xs font-bold text-slate-800 truncate pr-6">{item.original_filename}</p>
                            <div className="flex gap-2 mt-1 text-[10px] text-slate-500">
                               <span className="capitalize px-1.5 py-0.5 bg-white rounded border">{item.summary_type}</span>
                               <span className="py-0.5">{new Date(item.completed_at).toLocaleDateString()}</span>
                            </div>
                         </div>
                         <button 
                            onClick={(e) => { e.stopPropagation(); deleteHistory(item.id); }}
                            className="absolute right-2 top-2 p-1 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"
                         >
                            <Trash2 className="h-3 w-3" />
                         </button>
                      </div>
                   ))}
                </div>
             )}
          </section>

        </aside>

        {/* RIGHT PANEL (Preview & Result) */}
        <main className="w-full flex-1 flex flex-col gap-4">
           {/* RESULT VIEWER */}
           {result && (
             <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 shadow-sm overflow-hidden flex flex-col">
                <div className="flex items-center justify-between border-b border-emerald-100 bg-emerald-100/50 px-4 py-3">
                   <div className="flex items-center gap-2 text-sm font-black text-emerald-900">
                     <CheckCircle2 className="h-4 w-4 text-emerald-600" /> AI Summary Generated
                   </div>
                   <div className="flex gap-2">
                      <button onClick={copyToClipboard} className="flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-slate-700 border hover:bg-slate-50">
                         <Copy className="h-3 w-3" /> Copy
                      </button>
                      <button onClick={downloadSummary} className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-700">
                         <Download className="h-3 w-3" /> Save
                      </button>
                   </div>
                </div>
                <div className="p-6 text-sm text-slate-800 leading-relaxed whitespace-pre-wrap max-h-[600px] overflow-y-auto">
                   {result}
                </div>
             </div>
           )}

           {/* PDF PREVIEW */}
           {file && (
             <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col min-h-[400px]">
                <div className="flex items-center border-b border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="flex items-center gap-2 text-sm font-black text-slate-700">
                    <FileText className="h-4 w-4" /> Document Preview
                  </div>
                </div>
                <div className="flex flex-1 justify-center overflow-auto bg-slate-200/50 p-4 relative min-h-[400px]">
                   <Document file={file} onLoadSuccess={({numPages}) => setNumPages(numPages)} loading="Loading PDF...">
                     <Page pageNumber={1} renderAnnotationLayer={false} renderTextLayer={false} width={600} />
                   </Document>
                   {numPages > 1 && (
                      <div className="absolute bottom-4 right-4 bg-slate-800/80 text-white text-xs font-bold px-3 py-1.5 rounded-full backdrop-blur-sm">
                         Page 1 of {numPages}
                      </div>
                   )}
                </div>
             </div>
           )}
           
           {!file && !result && (
              <div className="flex-1 rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col items-center justify-center text-slate-400 min-h-[400px]">
                 <Bot className="mb-4 h-16 w-16 opacity-20" />
                 <p className="font-bold text-slate-500">Upload a document to generate an AI summary</p>
                 <p className="text-sm mt-2 max-w-md text-center leading-relaxed">
                    Our local AI engine extracts text, performs OCR on scanned pages, and intelligently summarizes complex documents securely.
                 </p>
              </div>
           )}
        </main>
      </div>
    </div>
  );
}
