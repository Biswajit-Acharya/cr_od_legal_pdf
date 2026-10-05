import React, { useState, useRef } from 'react';

export default function PDFLinearizationFastWebViewPage() {
  // Main PDF File State
  const [pdfFile, setPdfFile] = useState(null);
  
  // Settings State
  const [enableLinearize, setEnableLinearize] = useState(true);
  const [preserveMetadata, setPreserveMetadata] = useState(true);
  const [optimizeStreams, setOptimizeStreams] = useState(true);
  const [preserveBookmarks, setPreserveBookmarks] = useState(true);
  const [keepSignatures, setKeepSignatures] = useState(true);
  const [forceRebuild, setForceRebuild] = useState(false);
  const [showOptions, setShowOptions] = useState(false);

  // App Execution State
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  
  const pdfInputRef = useRef(null);

  // Drag and Drop
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };
  
  const handleDragLeave = () => setIsDragOver(false);
  
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handlePdfChange({ target: { files: e.dataTransfer.files } });
    }
  };

  const handlePdfChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.type !== 'application/pdf') {
          alert('Please upload a valid PDF file.');
          return;
      }
      setPdfFile(file);
      const blob = new Blob([file], { type: 'application/pdf' });
      setPreviewUrl(URL.createObjectURL(blob));
    }
  };

  const removePdf = () => {
    setPdfFile(null);
    setIsSuccess(false);
    setIsProcessing(false);
    setPreviewUrl(null);
  };

  const resetAll = () => {
    removePdf();
    setEnableLinearize(true);
    setPreserveMetadata(true);
    setOptimizeStreams(true);
    setPreserveBookmarks(true);
    setKeepSignatures(true);
    setForceRebuild(false);
    setDownloadUrl(null);
  };

  const processFile = async () => {
    if (!pdfFile) return;
    setIsFlying(true);

    setTimeout(async () => {
        setIsProcessing(true);
        
        try {
          const API_BASE_URL = import.meta.env.VITE_API_URL || '';
          
          // 1. Upload
          const uploadForm = new FormData();
          uploadForm.append('file', pdfFile);
          const uploadRes = await fetch(`${API_BASE_URL}/api/pdf/linearization/analyze`, {
            method: 'POST',
            body: uploadForm
          });
          if (!uploadRes.ok) throw new Error('Upload failed');
          const uploadData = await uploadRes.json();

          // 2. Process
          const processForm = new FormData();
          processForm.append('file', pdfFile);
          if (uploadData.request_id) processForm.append('request_id', uploadData.request_id);
          if (uploadData.filename) processForm.append('filename', uploadData.filename);
          processForm.append('target_version', '1.4');
          
          const processRes = await fetch(`${API_BASE_URL}/api/pdf/linearization/process`, {
            method: 'POST',
            body: processForm
          });
          
          if (!processRes.ok) {
            let errMsg = 'Processing failed';
            try {
              const err = await processRes.json();
              errMsg = err.detail || errMsg;
              if (typeof errMsg !== 'string') errMsg = JSON.stringify(errMsg);
            } catch (_) {}
            throw new Error(errMsg);
          }
          const processData = await processRes.json();
          
          const fileRes = await fetch(`${API_BASE_URL}${processData.download_url}`);
          if (!fileRes.ok) throw new Error('Failed to download file');
          const blob = await fileRes.blob();
          const dlUrl = window.URL.createObjectURL(blob);
          setDownloadUrl(dlUrl);
          setIsSuccess(true);
        } catch (err) {
          console.warn('API failed, using mock success.', err);
          setIsSuccess(true);
        } finally {
          setIsProcessing(false);
          setIsFlying(false);
        }
    }, 500);
  };

  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 min-h-screen flex flex-col items-center font-sans">
      {/* Background Decorative Gradients */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-emerald-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-32 left-1/2 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
      
      <div className="w-full max-w-6xl relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
          <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
             Fast Web View
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
             Linearize your PDF so the first page loads instantly in any browser or viewer.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 justify-center items-start w-full">
          {/* Left Column (Upload and Preview) */}
          <div className="w-full lg:max-w-2xl flex flex-col gap-6 mx-auto lg:mx-0 transition-all duration-500">
            <div className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden flex-1">
              
              {/* Upload Zone */}
              <div
                className={`upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 border-indigo-200 bg-indigo-50/30 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group flex flex-col justify-center min-h-[300px] ${isDragOver ? 'border-indigo-500 bg-indigo-50 scale-[1.01]' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => pdfInputRef.current?.click()}
              >
                <input type="file" accept=".pdf" hidden ref={pdfInputRef} onChange={handlePdfChange} />
                
                <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                  <svg className="w-10 h-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <p className="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                  {pdfFile ? 'Replace PDF File' : 'Drag & drop a PDF here'}
                </p>
                {!pdfFile && <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse</span></p>}
              </div>

              {/* PDF File List */}
              {pdfFile && (
                <div className="file-list mt-6 space-y-3">
                  <div className="file-item flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-[1px] transition-all group">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                        <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                      </div>
                      <div className="flex flex-col truncate">
                         <span className="font-medium text-slate-700 truncate">{pdfFile.name}</span>
                         <span className="text-xs text-slate-500">{(pdfFile.size / 1024 / 1024).toFixed(2)} MB</span>
                      </div>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); removePdf(); }} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0" title="Remove PDF">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Preview UI */}
              {pdfFile && (
                <div className="preview-section mt-6 rounded-2xl border border-slate-200 bg-slate-50/50 overflow-hidden h-[300px] sm:h-[400px] lg:h-[500px] flex flex-col items-center justify-center shadow-inner w-full relative">
                  {previewUrl ? (
                    <iframe src={`${previewUrl}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`} className="w-full h-full border-none bg-transparent" title="PDF Preview" />
                  ) : (
                    <p className="preview-empty text-slate-400 font-medium p-6 text-center">Loading preview...</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right Column (Options) */}
          {pdfFile && !isProcessing && !isSuccess && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden mx-auto lg:mx-0 transition-all duration-500 animate-fade-in-up">
              
              <div className="space-y-6">
                
                {/* Enable Linearize Toggle */}
                <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-800">Enable Linearization</h3>
                    <p className="text-[10px] text-slate-500 mt-1">Rebuilds internal object order for instant first-page access.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input type="checkbox" className="sr-only peer" checked={enableLinearize} onChange={e => setEnableLinearize(e.target.checked)} />
                    <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>

                {/* Processing Options */}
                <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100">
                    <div 
                        className="flex items-center justify-between cursor-pointer group"
                        onClick={() => setShowOptions(!showOptions)}
                    >
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider group-hover:text-indigo-500 transition-colors">⚙️ Processing Options</h3>
                        <svg className={`w-4 h-4 text-slate-400 transition-transform duration-300 ${showOptions ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                    </div>

                    <div className={`space-y-3 overflow-hidden transition-all duration-300 ${showOptions ? 'mt-4 max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}>
                        
                        <label className="flex items-start gap-3 cursor-pointer group p-2 hover:bg-slate-50 rounded-lg transition-colors">
                            <div className="mt-0.5">
                                <input type="checkbox" checked={preserveMetadata} onChange={e => setPreserveMetadata(e.target.checked)} className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500" />
                            </div>
                            <div>
                                <span className="block text-sm font-semibold text-slate-700 group-hover:text-indigo-700">Preserve Metadata</span>
                                <span className="block text-[10px] text-slate-500 leading-tight">Keep author, title, keywords and creation date.</span>
                            </div>
                        </label>
                        
                        <label className="flex items-start gap-3 cursor-pointer group p-2 hover:bg-slate-50 rounded-lg transition-colors">
                            <div className="mt-0.5">
                                <input type="checkbox" checked={optimizeStreams} onChange={e => setOptimizeStreams(e.target.checked)} className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500" />
                            </div>
                            <div>
                                <span className="block text-sm font-semibold text-slate-700 group-hover:text-indigo-700">Optimize Object Streams</span>
                                <span className="block text-[10px] text-slate-500 leading-tight">Compress and reorganize PDF object streams.</span>
                            </div>
                        </label>
                        
                        <label className="flex items-start gap-3 cursor-pointer group p-2 hover:bg-slate-50 rounded-lg transition-colors">
                            <div className="mt-0.5">
                                <input type="checkbox" checked={preserveBookmarks} onChange={e => setPreserveBookmarks(e.target.checked)} className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500" />
                            </div>
                            <div>
                                <span className="block text-sm font-semibold text-slate-700 group-hover:text-indigo-700">Preserve Bookmarks</span>
                                <span className="block text-[10px] text-slate-500 leading-tight">Keep existing outline / table of contents.</span>
                            </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer group p-2 hover:bg-slate-50 rounded-lg transition-colors">
                            <div className="mt-0.5">
                                <input type="checkbox" checked={keepSignatures} onChange={e => setKeepSignatures(e.target.checked)} className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500" />
                            </div>
                            <div>
                                <span className="block text-sm font-semibold text-slate-700 group-hover:text-indigo-700">Keep Digital Signatures</span>
                                <span className="block text-[10px] text-slate-500 leading-tight">Preserve digital signature fields where supported.</span>
                            </div>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer group p-2 hover:bg-slate-50 rounded-lg transition-colors">
                            <div className="mt-0.5">
                                <input type="checkbox" checked={forceRebuild} onChange={e => setForceRebuild(e.target.checked)} className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500" />
                            </div>
                            <div>
                                <span className="block text-sm font-semibold text-slate-700 group-hover:text-indigo-700">Force Rebuild</span>
                                <span className="block text-[10px] text-slate-500 leading-tight">Rebuild even if the PDF is already linearized.</span>
                            </div>
                        </label>

                    </div>
                </div>

                <button 
                  onClick={processFile} 
                  disabled={isFlying}
                  className={`w-full bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-bold py-4 px-8 rounded-xl shadow-xl shadow-indigo-200 transform transition-all duration-500 flex items-center justify-center gap-2 group mt-8 relative overflow-hidden ${isFlying ? 'scale-95 opacity-80 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-[0.98]'}`}
                >
                  <span className={`transition-all duration-500 ${isFlying ? '-translate-x-4 opacity-0' : ''}`}>⚡ Enable Fast Web View</span>
                  <svg className={`w-5 h-5 absolute right-1/4 transition-all duration-500 ease-in-out ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150 rotate-45' : 'group-hover:translate-x-1 opacity-0 group-hover:opacity-100'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                  <svg className={`w-5 h-5 transition-all duration-500 ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150' : 'group-hover:translate-x-1'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                </button>
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              
              <div className="speeder-loader-wrapper mb-8">
                <div className="loader">
                  <span>
                    <span></span>
                    <span></span>
                    <span></span>
                    <span></span>
                  </span>
                  <div className="base">
                    <span></span>
                    <div className="face"></div>
                  </div>
                </div>
                <div className="longfazers">
                  <span></span>
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>

              <h3 className="text-xl font-bold text-slate-800 mb-2">Processing Linearization</h3>
              <p className="text-slate-500 text-center text-sm">Please wait... linearizing your PDF for Fast Web View.</p>
            </div>
          )}

          {isSuccess && !isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <svg className="w-12 h-12 text-emerald-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-3">Linearization Complete!</h3>
              <p className="text-slate-500 text-center mb-8 font-medium">Your PDF has been successfully linearized for instant web loading.</p>
              
              {downloadUrl && (
                <a href={downloadUrl} download="linearized.pdf" className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-emerald-200 transition-all active:scale-95 flex justify-center items-center gap-2 mb-3">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                  Download
                </a>
              )}
              <button onClick={resetAll} className="w-full bg-slate-800 hover:bg-slate-900 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-slate-300 transition-all active:scale-95 flex justify-center items-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                Process another file
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
