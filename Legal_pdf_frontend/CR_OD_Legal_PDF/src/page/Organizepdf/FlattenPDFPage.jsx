import React, { useState, useRef, useEffect } from 'react';
import { pdfjs as pdfjsLib } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Set worker for pdfjs-dist analysis
pdfjsLib.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

export default function FlattenPDFPage() {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [finalDownloadUrl, setFinalDownloadUrl] = useState(null);
  
  const fileInputRef = useRef(null);

  // Analysis State
  const [analysis, setAnalysis] = useState({
    isAnalyzing: false,
    forms: 0,
    comments: 0,
    highlights: 0,
    signatures: 0,
    completed: false
  });

  // Advanced Options State
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [options, setOptions] = useState({
    flatten_forms: true,
    flatten_comments: true,
    flatten_highlights: true,
    flatten_annotations: true,
    flatten_stamps: true,
    flatten_signature: true,
    flatten_entire_document: false
  });

  const handleOptionChange = (key) => {
    setOptions(prev => ({ ...prev, [key]: !prev[key] }));
  };

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
      handleFileChange({ target: { files: e.dataTransfer.files } });
    }
  };

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.type !== 'application/pdf') {
          alert('Please upload a valid PDF file.');
          return;
      }
      setFiles([file]);
      
      // Create preview URL
      const blob = new Blob([file], { type: 'application/pdf' });
      setPreviewUrl(URL.createObjectURL(blob));

      // Start Analysis
      setAnalysis({ isAnalyzing: true, forms: 0, comments: 0, highlights: 0, signatures: 0, completed: false });
      
      try {
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        
        let forms = 0, comments = 0, highlights = 0, signatures = 0;

        for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const annotations = await page.getAnnotations();
            
            annotations.forEach(annot => {
                if (annot.subtype === 'Widget') {
                    if (annot.fieldType === 'Sig') signatures++;
                    else forms++;
                } else if (annot.subtype === 'Text' || annot.subtype === 'FreeText') {
                    comments++;
                } else if (['Highlight', 'Underline', 'StrikeOut', 'Squiggly'].includes(annot.subtype)) {
                    highlights++;
                }
            });
        }
        
        setAnalysis({ isAnalyzing: false, forms, comments, highlights, signatures, completed: true });
      } catch (err) {
        console.error("PDF Analysis Error: ", err);
        setAnalysis(prev => ({ ...prev, isAnalyzing: false, completed: true }));
      }
    }
  };

  const removeFile = () => {
    setFiles([]);
    setIsSuccess(false);
    setIsProcessing(false);
    setPreviewUrl(null);
    if (finalDownloadUrl) {
        window.URL.revokeObjectURL(finalDownloadUrl);
        setFinalDownloadUrl(null);
    }
    setAnalysis({ isAnalyzing: false, forms: 0, comments: 0, highlights: 0, signatures: 0, completed: false });
  };

  const resetAll = () => {
    removeFile();
  };

  // API Submission
  const handleProcess = async () => {
    if (files.length === 0) return;
    setIsFlying(true);

    setIsProcessing(true);
    setIsFlying(true);

    const formData = new FormData();
    formData.append('file', files[0]);
    
    Object.keys(options).forEach(key => {
        formData.append(key, options[key] ? 'true' : 'false');
    });

    const API_BASE_URL = import.meta.env.VITE_API_URL || '';
    try {
        const response = await fetch(`${API_BASE_URL}/api/pdf/flatten_pdf`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.download_url) {
            const fileRes = await fetch(`${API_BASE_URL}${data.download_url}`);
            if (!fileRes.ok) throw new Error('Failed to download file');
            const blob = await fileRes.blob();
            const url = window.URL.createObjectURL(blob);
            setFinalDownloadUrl(url);
            setIsSuccess(true);
        } else {
            alert(data.detail || 'An error occurred while flattening the PDF.');
        }
    } catch (err) {
        alert('Network error during file processing: ' + err.message);
        console.error(err);
    } finally {
        setIsProcessing(false);
        setIsFlying(false);
    }
  };

  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 min-h-screen flex flex-col items-center">
      {/* Background Decorative Gradients */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-emerald-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-32 left-1/2 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
      
      <div className="w-full max-w-6xl relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
          <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
            Flatten PDF
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
            Make your PDF non-editable. Convert forms, signatures, and annotations to flat text instantly.
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
                onClick={() => fileInputRef.current?.click()}
              >
                <input type="file" accept=".pdf" hidden ref={fileInputRef} onChange={handleFileChange} />
                <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                  <svg className="w-10 h-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <p className="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                  {files.length > 0 ? `${files.length} File selected` : 'Drag & drop a PDF here'}
                </p>
                {files.length === 0 && <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse</span></p>}
              </div>

              {/* File List */}
              {files.length > 0 && (
                <div className="file-list mt-6 space-y-3">
                  <div className="file-item flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-[1px] transition-all group">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                        <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                      </div>
                      <div className="flex flex-col truncate">
                         <span className="font-medium text-slate-700 truncate">{files[0].name}</span>
                         <span className="text-xs text-slate-500">{(files[0].size / 1024 / 1024).toFixed(2)} MB</span>
                      </div>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); removeFile(); }} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0" title="Remove file">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Preview UI */}
              {files.length > 0 && (
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

          {/* Right Column (Options & Analysis) */}
          {files.length > 0 && !isProcessing && !isSuccess && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden mx-auto lg:mx-0 transition-all duration-500 animate-fade-in-up">
              
              <div className="space-y-6">
                
                {/* Analysis Section */}
                <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Analysis Results</h3>
                  
                  {analysis.isAnalyzing ? (
                    <div className="flex flex-col items-center justify-center py-6">
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
                        <p className="text-sm font-medium text-slate-500">Analyzing PDF elements...</p>
                    </div>
                  ) : analysis.completed ? (
                    (analysis.forms === 0 && analysis.comments === 0 && analysis.highlights === 0 && analysis.signatures === 0) ? (
                        <div className="p-4 bg-emerald-50 rounded-xl text-emerald-700 text-sm font-semibold flex items-center gap-3">
                            <svg className="w-6 h-6 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                            No interactive elements detected. The document is already flat.
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 gap-3">
                            {analysis.forms > 0 && (
                                <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl flex items-center gap-2">
                                    <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                    <span className="text-sm font-bold text-indigo-900">{analysis.forms} Forms</span>
                                </div>
                            )}
                            {analysis.comments > 0 && (
                                <div className="p-3 bg-pink-50 border border-pink-100 rounded-xl flex items-center gap-2">
                                    <svg className="w-5 h-5 text-pink-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
                                    <span className="text-sm font-bold text-pink-900">{analysis.comments} Comments</span>
                                </div>
                            )}
                            {analysis.highlights > 0 && (
                                <div className="p-3 bg-yellow-50 border border-yellow-100 rounded-xl flex items-center gap-2">
                                    <svg className="w-5 h-5 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                                    <span className="text-sm font-bold text-yellow-900">{analysis.highlights} Highlights</span>
                                </div>
                            )}
                            {analysis.signatures > 0 && (
                                <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl flex items-center gap-2">
                                    <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
                                    <span className="text-sm font-bold text-emerald-900">{analysis.signatures} Signatures</span>
                                </div>
                            )}
                        </div>
                    )
                  ) : null}
                </div>

                {/* Advanced Options */}
                <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
                    <button onClick={() => setShowAdvanced(!showAdvanced)} className="w-full p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                        <span className="text-sm font-semibold text-slate-700">Advanced Options</span>
                        <svg className={`w-5 h-5 text-slate-400 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                    </button>
                    
                    {showAdvanced && (
                        <div className="p-5 pt-0 grid gap-3 border-t border-slate-100 mt-2">
                            {[
                                { id: 'flatten_forms', label: 'Flatten Forms' },
                                { id: 'flatten_comments', label: 'Flatten Comments' },
                                { id: 'flatten_highlights', label: 'Flatten Highlights' },
                                { id: 'flatten_annotations', label: 'Flatten Annotations' },
                                { id: 'flatten_stamps', label: 'Flatten Stamps' },
                                { id: 'flatten_signature', label: 'Flatten Signature' }
                            ].map((opt) => (
                                <label key={opt.id} className="flex items-center gap-3 cursor-pointer group">
                                    <input type="checkbox" checked={options[opt.id]} onChange={() => handleOptionChange(opt.id)} className="w-5 h-5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer" />
                                    <span className="text-sm font-medium text-slate-600 group-hover:text-indigo-700 transition-colors">{opt.label}</span>
                                </label>
                            ))}
                            <hr className="my-2 border-slate-100" />
                            <label className="flex items-center gap-3 cursor-pointer group p-2 bg-red-50 rounded-lg">
                                <input type="checkbox" checked={options.flatten_entire_document} onChange={() => handleOptionChange('flatten_entire_document')} className="w-5 h-5 rounded border-red-300 text-red-600 focus:ring-red-500 cursor-pointer" />
                                <span className="text-sm font-bold text-red-700">Flatten Entire Document</span>
                            </label>
                        </div>
                    )}
                </div>

                <button 
                  onClick={handleProcess} 
                  disabled={isFlying || analysis.isAnalyzing}
                  className={`w-full bg-gradient-to-r from-red-500 to-rose-600 hover:from-red-600 hover:to-rose-700 text-white font-bold py-4 px-8 rounded-xl shadow-xl shadow-red-200 transform transition-all duration-500 flex items-center justify-center gap-2 group mt-8 relative overflow-hidden ${(isFlying || analysis.isAnalyzing) ? 'scale-95 opacity-80 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-[0.98]'}`}
                >
                  <span className={`transition-all duration-500 ${isFlying ? '-translate-x-4 opacity-0' : ''}`}>Make Non-Editable</span>
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
              <h3 className="text-xl font-bold text-slate-800 mb-2">Flattening PDF Elements</h3>
              <p className="text-slate-500 text-center text-sm">Please wait... converting interactive fields to flat text.</p>
            </div>
          )}

          {isSuccess && !isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <svg className="w-12 h-12 text-emerald-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-3">Flatten Completed!</h3>
              <p className="text-slate-500 text-center mb-8 font-medium">Your PDF is now secure and non-editable.</p>
              
              <a href={finalDownloadUrl} download="flattened.pdf" className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-emerald-200 transition-all active:scale-95 flex justify-center items-center gap-2 mb-3">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                Download
              </a>
              <button onClick={resetAll} className="w-full bg-slate-800 hover:bg-slate-900 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-slate-300 transition-all active:scale-95 flex justify-center items-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                Flatten another file
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
