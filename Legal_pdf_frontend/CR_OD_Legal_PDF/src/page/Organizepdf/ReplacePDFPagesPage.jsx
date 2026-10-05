import React, { useState, useRef, useEffect } from 'react';

export default function ReplacePDFPagesPage() {
  const [pdfFiles, setPdfFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrls, setPreviewUrls] = useState({});
  const [downloadUrl, setDownloadUrl] = useState(null);
  const pdfInputRef = useRef(null);

  // Advanced Options state
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Replace Options
  const [settings, setSettings] = useState({
    replaceMode: 'single', // single, multiple, range, entire
    rangeText: '',
    sizeMode: 'fit', // fit, stretch, center, keep, auto
    preserveBookmarks: true,
    preserveHyperlinks: true,
    preserveMetadata: true,
    preserveLabels: true,
    preserveAnnotations: true,
  });

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };
  
  const handleDragLeave = () => setIsDragOver(false);
  
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handlePdfChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (files) => {
    const validFiles = Array.from(files).filter(f => f.type === 'application/pdf');
    if (validFiles.length !== files.length) {
        alert('Some files were rejected. Please upload only valid PDF files.');
    }
    
    if(validFiles.length > 0) {
        setPdfFiles(prev => [...prev, ...validFiles]);
        
        // Generate preview URLs
        validFiles.forEach(file => {
            const blob = new Blob([file], { type: 'application/pdf' });
            setPreviewUrls(prev => ({...prev, [file.name]: URL.createObjectURL(blob)}));
        });
    }
  };

  const removePdf = (indexToRemove, fileName) => {
    setPdfFiles(prev => prev.filter((_, idx) => idx !== indexToRemove));
    setPreviewUrls(prev => {
        const newUrls = {...prev};
        delete newUrls[fileName];
        return newUrls;
    });
    if(pdfFiles.length === 1) { // Will be 0
        setIsSuccess(false);
        setIsProcessing(false);
    }
  };

  const resetAll = () => {
    setPdfFiles([]);
    setPreviewUrls({});
    setIsSuccess(false);
    setIsProcessing(false);
    setDownloadUrl(null);
  };

  const processFiles = async () => {
    if (pdfFiles.length < 2) {
        alert("Please upload both Original PDF and Replacement PDF.");
        return;
    }
    setIsFlying(true);

    setTimeout(async () => {
        setIsProcessing(true);
        
        try {
            const API_BASE_URL = import.meta.env.VITE_API_URL || ''; 
            
            let mapping = [];
            let replPage = 1;
            const parts = (settings.rangeText || '1').split(',').map(p => p.trim());
            for (const part of parts) {
                if (!part) continue;
                if (part.includes('-')) {
                    const [start, end] = part.split('-').map(Number);
                    if (!isNaN(start) && !isNaN(end)) {
                        for (let i = start; i <= end; i++) {
                            mapping.push({ orig: i, repl: replPage++ });
                        }
                    }
                } else {
                    const num = Number(part);
                    if (!isNaN(num)) {
                        mapping.push({ orig: num, repl: replPage++ });
                    }
                }
            }
            if (mapping.length === 0) {
                 mapping = [{ orig: 1, repl: 1 }]; 
            }

            const processForm = new FormData();
            processForm.append('orig_file', pdfFiles[0]);
            processForm.append('repl_file', pdfFiles[1]);
            processForm.append('mapping', JSON.stringify(mapping));
            processForm.append('size_mode', settings.sizeMode);
            processForm.append('preserve_bookmarks', settings.preserveBookmarks);
            processForm.append('preserve_metadata', settings.preserveMetadata);
            processForm.append('preserve_labels', settings.preserveLabels);
            processForm.append('preserve_hyperlinks', settings.preserveHyperlinks);
            processForm.append('preserve_annotations', settings.preserveAnnotations);
            
            const processRes = await fetch(`${API_BASE_URL}/api/pdf/replace-pdf-pages/process`, {
                method: 'POST',
                body: processForm
            });
            
            if (!processRes.ok) {
                let errDesc = 'Processing failed';
                try {
                    const err = await processRes.json();
                    errDesc = err.detail || errDesc;
                } catch (_) {}
                throw new Error(errDesc);
            }
            
            const processData = await processRes.json();
            
            if (processData.download_url) {
                const fileRes = await fetch(`${API_BASE_URL}${processData.download_url}`);
                if (!fileRes.ok) throw new Error('Failed to download file');
                const blob = await fileRes.blob();
                const dlUrl = window.URL.createObjectURL(blob);
                setDownloadUrl(dlUrl);
            }
            
            setIsSuccess(true);
        } catch (err) {
            console.error('API Error:', err);
            alert('Failed to replace pages: ' + err.message);
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
             Replace PDF Pages
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
             Swap out old pages with new ones from a replacement PDF file seamlessly.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 justify-center items-start w-full">
          {/* Left Column (Upload and Preview) */}
          <div className="w-full lg:max-w-2xl flex flex-col gap-6 mx-auto lg:mx-0 transition-all duration-500">
            <div className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden flex-1">
              
              {/* Upload Zone */}
              <div
                className={`upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 border-indigo-200 bg-indigo-50/30 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group flex flex-col justify-center min-h-[250px] ${isDragOver ? 'border-indigo-500 bg-indigo-50 scale-[1.01]' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => pdfInputRef.current?.click()}
              >
                <input type="file" accept=".pdf" multiple hidden ref={pdfInputRef} onChange={handlePdfChange} />
                
                <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                  <svg className="w-10 h-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                  </svg>
                </div>
                <p className="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                  {pdfFiles.length === 0 ? 'Upload Original and Replacement PDFs' : 'Add More PDFs'}
                </p>
                <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse</span></p>
              </div>

              {/* PDF File List */}
              {pdfFiles.length > 0 && (
                <div className="file-list mt-6 space-y-3 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
                  {pdfFiles.map((file, idx) => (
                      <div key={idx} className="file-item flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-[1px] transition-all group">
                        <div className="flex items-center gap-3 overflow-hidden">
                          <div className={`p-2 rounded-lg shrink-0 ${idx === 0 ? 'bg-indigo-100 text-indigo-700' : 'bg-emerald-100 text-emerald-700'}`}>
                            <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                            </svg>
                          </div>
                          <div className="flex flex-col truncate">
                            <span className="font-medium text-slate-700 truncate">{file.name}</span>
                            <span className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB {idx === 0 ? '(Original)' : '(Replacement)'}</span>
                          </div>
                        </div>
                        <button onClick={(e) => { e.stopPropagation(); removePdf(idx, file.name); }} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0" title="Remove PDF">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        </button>
                      </div>
                  ))}
                  {pdfFiles.length < 2 && (
                      <div className="text-xs text-amber-600 bg-amber-50 border border-amber-100 p-3 rounded-lg flex items-center gap-2">
                        <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        Please upload a second PDF to serve as the replacement pages.
                      </div>
                  )}
                </div>
              )}

              {/* Preview UI */}
              {pdfFiles.length > 0 && (
                <div className="preview-section mt-6 rounded-2xl border border-slate-200 bg-slate-50/50 overflow-hidden h-[300px] sm:h-[400px] flex flex-col items-center justify-center shadow-inner w-full relative p-4">
                  <div className="flex w-full h-full gap-4 overflow-x-auto pb-2 custom-scrollbar snap-x">
                      {pdfFiles.map((file, idx) => (
                          <div key={idx} className="flex-shrink-0 w-full h-full relative snap-center bg-white shadow-sm border border-slate-200 rounded-xl overflow-hidden">
                              <div className={`absolute top-0 left-0 w-full text-white text-xs px-3 py-1 font-medium z-10 truncate backdrop-blur-sm ${idx === 0 ? 'bg-indigo-600/90' : 'bg-emerald-600/90'}`}>
                                  {idx === 0 ? 'Original: ' : 'Replacement: '} {file.name}
                              </div>
                              {previewUrls[file.name] ? (
                                <iframe src={`${previewUrls[file.name]}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`} className="w-full h-full border-none" title={`PDF Preview ${idx}`} />
                              ) : (
                                <div className="w-full h-full flex items-center justify-center text-slate-400">Loading...</div>
                              )}
                          </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column (Options & Actions) */}
          {pdfFiles.length > 0 && !isProcessing && !isSuccess && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden mx-auto lg:mx-0 transition-all duration-500 animate-fade-in-up">
              
              <div className="space-y-6">
                <div className="p-5 bg-indigo-50/50 rounded-2xl shadow-sm border border-indigo-100/50">
                   <h3 className="text-lg font-bold text-[#1e2a52] flex items-center gap-2 mb-2">
                      <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" /></svg>
                      Replace Settings
                   </h3>
                   <p className="text-sm text-slate-600">
                     Configure how pages should be swapped.
                   </p>
                </div>

                <div className="space-y-4">
                  {/* Selection Method */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200">
                    <label className="block text-sm font-semibold text-slate-700 mb-2">Selection Method</label>
                    <select 
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                      value={settings.replaceMode}
                      onChange={(e) => setSettings({...settings, replaceMode: e.target.value})}
                    >
                      <option value="single">Single Page</option>
                      <option value="multiple">Multiple Pages</option>
                      <option value="range">Page Range</option>
                      <option value="entire">Entire PDF</option>
                    </select>

                    {settings.replaceMode === 'range' && (
                      <div className="mt-3">
                        <label className="block text-xs font-semibold text-slate-700 mb-1">Enter Page Range</label>
                        <input type="text" placeholder="e.g. 1-3, 5, 8-10" className="w-full px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-sm" value={settings.rangeText} onChange={(e) => setSettings({...settings, rangeText: e.target.value})} />
                      </div>
                    )}
                  </div>

                  {/* Mismatch size */}
                  <div className="bg-white p-4 rounded-xl border border-slate-200">
                     <label className="block text-sm font-semibold text-slate-700 mb-2">Page Size Mismatch</label>
                     <select 
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                        value={settings.sizeMode}
                        onChange={(e) => setSettings({...settings, sizeMode: e.target.value})}
                      >
                        <option value="fit">Fit (Proportional) - Recommended</option>
                        <option value="stretch">Stretch to fill canvas</option>
                        <option value="center">Place at center</option>
                        <option value="keep">Keep replacement size</option>
                        <option value="auto">Auto detect</option>
                      </select>
                  </div>

                  {/* Advanced Toggle */}
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden transition-all">
                    <button onClick={() => setShowAdvanced(!showAdvanced)} className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors">
                      <span className="text-sm font-semibold text-slate-700">Preservation Options</span>
                      <svg className={`w-4 h-4 text-slate-500 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                    </button>
                    
                    {showAdvanced && (
                      <div className="p-4 border-t border-slate-200 space-y-2">
                          <label className="flex items-center gap-2"><input type="checkbox" className="rounded text-indigo-600" checked={settings.preserveBookmarks} onChange={(e) => setSettings({...settings, preserveBookmarks: e.target.checked})} /><span className="text-sm text-slate-700">Preserve Bookmarks</span></label>
                          <label className="flex items-center gap-2"><input type="checkbox" className="rounded text-indigo-600" checked={settings.preserveHyperlinks} onChange={(e) => setSettings({...settings, preserveHyperlinks: e.target.checked})} /><span className="text-sm text-slate-700">Preserve Hyperlinks</span></label>
                          <label className="flex items-center gap-2"><input type="checkbox" className="rounded text-indigo-600" checked={settings.preserveMetadata} onChange={(e) => setSettings({...settings, preserveMetadata: e.target.checked})} /><span className="text-sm text-slate-700">Preserve Metadata</span></label>
                          <label className="flex items-center gap-2"><input type="checkbox" className="rounded text-indigo-600" checked={settings.preserveLabels} onChange={(e) => setSettings({...settings, preserveLabels: e.target.checked})} /><span className="text-sm text-slate-700">Preserve Page Labels</span></label>
                          <label className="flex items-center gap-2"><input type="checkbox" className="rounded text-indigo-600" checked={settings.preserveAnnotations} onChange={(e) => setSettings({...settings, preserveAnnotations: e.target.checked})} /><span className="text-sm text-slate-700">Preserve Annotations</span></label>
                      </div>
                    )}
                  </div>
                </div>

                <button 
                  onClick={processFiles} 
                  disabled={isFlying || pdfFiles.length < 2}
                  className={`w-full bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-bold py-4 px-8 rounded-xl shadow-xl shadow-indigo-200 transform transition-all duration-500 flex items-center justify-center gap-2 group mt-8 relative overflow-hidden ${isFlying || pdfFiles.length < 2 ? 'scale-95 opacity-80 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-[0.98]'}`}
                >
                  <span className={`transition-all duration-500 ${isFlying ? '-translate-x-4 opacity-0' : ''}`}>Execute Action</span>
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
                  <span><span></span><span></span><span></span><span></span></span>
                  <div className="base"><span></span><div className="face"></div></div>
                </div>
                <div className="longfazers"><span></span><span></span><span></span><span></span></div>
              </div>
              <h3 className="text-xl font-bold text-[#1e2a52] mb-2">Processing...</h3>
              <p className="text-slate-500 text-center text-sm">Please wait while we replace the pages.</p>
            </div>
          )}

          {isSuccess && !isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <svg className="w-12 h-12 text-emerald-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="text-2xl font-bold text-[#1e2a52] mb-3">Done!</h3>
              <p className="text-slate-500 text-center mb-8 font-medium">Pages have been successfully replaced.</p>
              
              {downloadUrl && (
                <a href={downloadUrl} download="replaced.pdf" className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-emerald-200 transition-all active:scale-95 flex justify-center items-center gap-2 mb-3">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                  Download Replaced PDF
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
