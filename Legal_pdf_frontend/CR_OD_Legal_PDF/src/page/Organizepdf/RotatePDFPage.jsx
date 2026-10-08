import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

// Setup pdf.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

export default function RotatePDFPage() {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [rotation, setRotation] = useState(0);
  const [pages, setPages] = useState('all');
  const [customPages, setCustomPages] = useState('');
  
  const [previewFile, setPreviewFile] = useState(null);
  const containerRef = useRef(null);
  const fileInputRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(0);

  // Update container width for PDF scale
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth);
      }
    };
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, [previewFile]);

  const handleDragOver = (e) => { e.preventDefault(); setIsDragOver(true); };
  const handleDragLeave = () => setIsDragOver(false);
  const handleDrop = (e) => {
    e.preventDefault(); setIsDragOver(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files);
  };
  
  const handleFiles = (fileList) => {
    const valid = Array.from(fileList).filter(f => f.type === 'application/pdf');
    if (valid.length > 0) {
      setFiles([valid[0]]);
      const reader = new FileReader();
      reader.onload = (e) => setPreviewFile(e.target.result);
      reader.readAsDataURL(valid[0]);
    }
  };
  
  const removeFile = () => {
    setFiles([]); setIsSuccess(false); setIsProcessing(false);
    setDownloadUrl(null); setErrorMsg(null);
    setPreviewFile(null);
    setRotation(0);
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setIsFlying(true);
    setErrorMsg(null);
    setTimeout(async () => {
      setIsProcessing(true);
      try {
        const formData = new FormData();
        formData.append('file', files[0]);
        formData.append('rotation', rotation);
        formData.append('pages', pages === 'custom' ? customPages : pages);
        const response = await fetch(`${API_BASE_URL}/api/pdf/rotate`, { method: 'POST', body: formData });
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          let errorMessage = `Server error: ${response.status}`;
          if (errData.detail) {
            if (typeof errData.detail === 'string') {
              errorMessage = errData.detail;
            } else if (Array.isArray(errData.detail)) {
              errorMessage = errData.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join(', ');
            } else {
              errorMessage = JSON.stringify(errData.detail);
            }
          }
          throw new Error(errorMessage);
        }
        const contentType = response.headers.get('content-type') || '';
        let dlUrl;
        if (contentType.includes('application/json')) {
          const data = await response.json();
          const downloadPath = data.download_url || data.url;
          if (!downloadPath) throw new Error('No download URL in response');
          const fileRes = await fetch(`${API_BASE_URL}${downloadPath}`);
          if (!fileRes.ok) throw new Error('Failed to download processed file');
          const blob = await fileRes.blob();
          dlUrl = URL.createObjectURL(blob);
        } else {
          const blob = await response.blob();
          dlUrl = URL.createObjectURL(blob);
        }
        setDownloadUrl(dlUrl);
        setIsSuccess(true);
      } catch (err) {
        console.error('Rotate API error:', err);
        setErrorMsg(err.message || 'An error occurred. Please try again.');
      } finally {
        setIsProcessing(false);
        setIsFlying(false);
      }
    }, 300);
  };

  return (
    <div className="flex-1 flex flex-col w-full relative z-20 min-h-screen bg-transparent p-4 sm:p-8">
      {/* Background Ornaments */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob" />
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000" />
      
      <div className="w-full max-w-6xl mx-auto relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-2 mb-8 px-4">
          <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">Rotate PDF</h1>
          <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">Rotate pages in your PDF document effortlessly with live preview.</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 justify-center items-start w-full">
          {/* Left Column (Upload and Preview) */}
          <div className="w-full lg:max-w-2xl flex flex-col gap-6 mx-auto lg:mx-0 transition-all duration-500">
            <div className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden flex-1">
              
              {errorMsg && (
                <div className="mb-5 p-4 text-red-700 bg-red-50 border border-red-200 rounded-xl text-sm font-medium">{errorMsg}</div>
              )}

              {!previewFile && (
                <div
                  className={`upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 border-indigo-200 bg-indigo-50/30 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group flex flex-col justify-center min-h-[300px] ${isDragOver ? 'border-indigo-500 bg-indigo-50 scale-[1.01]' : ''}`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input type="file" accept=".pdf" hidden ref={fileInputRef} onChange={e => { if (e.target.files?.length) handleFiles(e.target.files); }} />
                  <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                    <svg className="w-10 h-10 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                  </div>
                  <p className="text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                    Drag & drop a PDF here
                  </p>
                  <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse</span></p>
                </div>
              )}

              {files.length > 0 && (
                <div className="file-item flex items-center justify-between p-4 mb-6 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                    </div>
                    <span className="font-medium text-slate-700 truncate">{files[0].name}</span>
                  </div>
                  <button onClick={removeFile} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
              )}

              {previewFile && (
                <div className="w-full flex flex-col items-center">
                  <div 
                    className="relative border border-slate-300 shadow-sm overflow-hidden bg-slate-100 flex items-center justify-center rounded-xl w-full" 
                    ref={containerRef}
                    style={{ minHeight: '300px' }}
                  >
                    <div className="p-2 sm:p-4 w-full flex justify-center items-center overflow-auto max-h-[60vh] lg:max-h-[70vh]">
                      <Document file={previewFile} loading="Loading PDF...">
                        <Page 
                          pageNumber={1} 
                          width={containerWidth ? (containerWidth > 640 ? containerWidth * 0.85 : containerWidth * 0.9) : 300} 
                          rotate={rotation}
                          renderTextLayer={false}
                          renderAnnotationLayer={false}
                          className="shadow-md transition-all duration-300"
                        />
                      </Document>
                    </div>

                    <button 
                      onClick={() => setRotation((prev) => (prev + 90) % 360)}
                      className="absolute bottom-3 right-3 sm:bottom-4 sm:right-4 bg-white/95 p-3 sm:p-4 rounded-full shadow-[0_4px_15px_rgba(0,0,0,0.2)] text-indigo-600 hover:text-white hover:bg-indigo-600 active:scale-95 transition-all z-10 border border-indigo-100"
                      title="Rotate 90° Clockwise"
                    >
                      <svg className="w-6 h-6 sm:w-7 sm:h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </button>
                    
                    {rotation !== 0 && (
                      <div className="absolute top-3 left-3 sm:top-4 sm:left-4 bg-indigo-600 text-white font-bold px-2 py-1 sm:px-3 sm:py-1.5 rounded-lg shadow-sm text-xs sm:text-sm">
                        Rotated {rotation}°
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column (Options) */}
          {files.length > 0 && !isProcessing && !isSuccess && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-5 sm:p-8 relative overflow-hidden mx-auto lg:mx-0 transition-all duration-500 animate-fade-in-up">
              <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100 mb-6">
                <label className="block text-xs sm:text-sm font-bold text-slate-700 mb-3 uppercase tracking-wide">Apply To Pages</label>
                <div className="grid grid-cols-2 gap-2 sm:gap-3">
                  {[['all', 'All Pages'], ['odd', 'Odd Pages'], ['even', 'Even Pages'], ['custom', 'Custom']].map(([val, label]) => (
                    <button key={val} onClick={() => setPages(val)}
                      className={`py-2.5 sm:py-3 px-2 rounded-xl font-semibold text-xs sm:text-sm border-2 transition-all ${pages === val ? 'border-indigo-500 bg-white text-indigo-700 shadow-sm' : 'border-slate-200 text-slate-500 hover:border-indigo-300 bg-white/50'}`}>
                      {label}
                    </button>
                  ))}
                </div>
                {pages === 'custom' && (
                  <input type="text" placeholder="e.g. 1,3,5-8" value={customPages}
                    onChange={e => setCustomPages(e.target.value)}
                    className="mt-4 w-full p-3.5 bg-white border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-100 focus:border-indigo-500 outline-none transition-all shadow-inner font-medium" />
                )}
              </div>

              <button 
                onClick={handleProcess} 
                disabled={isFlying}
                className={`w-full bg-[#1e2a52] hover:bg-[#2a3a6a] text-white font-bold py-4 px-8 rounded-xl shadow-xl transform transition-all duration-500 flex items-center justify-center gap-2 group mt-4 relative overflow-hidden ${isFlying ? 'scale-95 opacity-80' : 'hover:scale-[1.02] active:scale-[0.98]'}`}
              >
                <span className={`transition-all duration-500 ${isFlying ? '-translate-x-4 opacity-0' : ''}`}>
                  Rotate PDF {rotation > 0 ? `(${rotation}°)` : ''}
                </span>
                <svg 
                  className={`w-5 h-5 absolute right-1/4 transition-all duration-500 ease-in-out ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150 rotate-45' : 'group-hover:translate-x-1 opacity-0 group-hover:opacity-100'}`} 
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                <svg 
                  className={`w-5 h-5 transition-all duration-500 ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150' : 'group-hover:translate-x-1'}`} 
                  fill="none" viewBox="0 0 24 24" stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          )}

          {/* Processing state */}
          {isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px] mx-auto lg:mx-0">
              <h3 className="text-xl font-bold text-slate-800 mb-2">Rotating PDF</h3>
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mt-4"></div>
              <p className="text-slate-500 text-center text-sm mt-4">Please wait while we process your file...</p>
            </div>
          )}

          {/* Success state */}
          {isSuccess && !isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px] mx-auto lg:mx-0">
              <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <svg className="w-12 h-12 text-emerald-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-3">Done!</h3>
              {downloadUrl && (
                <a href={downloadUrl} download={files[0] ? `rotated_${files[0].name}` : 'rotated_output.pdf'} className="w-full text-center bg-[#1e2a52] hover:bg-[#2a3a6a] text-white font-bold py-4 px-8 rounded-xl shadow-lg transition-all active:scale-95 flex justify-center items-center gap-2 mb-3">
                  Download PDF
                </a>
              )}
              <button onClick={removeFile} className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-4 px-8 rounded-xl shadow-sm transition-all active:scale-95 flex justify-center items-center gap-2">
                Rotate more files
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
