import React, { useState, useRef } from 'react';

export default function FileExpirationPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [expirationType, setExpirationType] = useState('duration'); // 'date' or 'duration'
  const [expiresAt, setExpiresAt] = useState('');
  const [durationValue, setDurationValue] = useState(24);
  const [durationUnit, setDurationUnit] = useState(3600); // default hours
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [policyDetails, setPolicyDetails] = useState(null);

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
      setIsSuccess(false);
      setErrorMessage('');
    }
  };

  const handleProcess = async () => {
    if (!file) {
      setErrorMessage('Please select a PDF file first.');
      return;
    }
    if (expirationType === 'date' && !expiresAt) {
      setErrorMessage('Please select an expiration date and time.');
      return;
    }

    setIsProcessing(true);
    setErrorMessage('');
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('expiration_type', expirationType);
      
      if (expirationType === 'date') {
        // Convert to ISO 8601 with Z
        const isoDate = new Date(expiresAt).toISOString();
        formData.append('expires_at', isoDate);
      } else {
        const totalSeconds = durationValue * durationUnit;
        formData.append('duration_seconds', totalSeconds);
      }

      const response = await fetch('/api/pdf/security/file-expiration', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setDownloadUrl(data.download_url);
        setPolicyDetails(data.policy);
        setIsSuccess(true);
      } else {
        throw new Error(data.detail || 'An error occurred while applying the expiration policy.');
      }
    } catch (error) {
      setErrorMessage(error.message || 'An error occurred while applying the expiration policy.');
    } finally {
      setIsProcessing(false);
    }
  };

  const resetAll = () => {
    setFile(null);
    setIsSuccess(false);
    setDownloadUrl('');
    setPolicyDetails(null);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-br from-[#1e2a52] via-[#2a3a6a] to-[#4a5a8a] -skew-y-3 origin-top-left z-0 shadow-2xl"></div>
      
      <div className="relative z-10 container mx-auto px-4 py-8 lg:py-12 max-w-5xl flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button 
            onClick={onBack}
            className="w-10 h-10 bg-white/20 hover:bg-white/30 backdrop-blur-md rounded-full flex items-center justify-center text-white transition-all transform hover:-translate-x-1 shadow-lg"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-white/10 backdrop-blur-md rounded-xl flex items-center justify-center shadow-inner border border-white/20">
              <span className="text-2xl">{tool?.icon || '⏱️'}</span>
            </div>
            <div>
              <h1 className="text-3xl font-extrabold text-white tracking-tight">{tool?.title || 'File Expiration'}</h1>
              <p className="text-indigo-100 text-sm font-medium opacity-80 mt-1">{tool?.description || 'Set auto-destruction or expiration for sensitive PDFs.'}</p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex flex-col lg:flex-row gap-8 flex-1">
          {/* Left Column: Form */}
          {!isProcessing && !isSuccess && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 lg:p-8 flex flex-col relative animate-fade-in-up">
              <div className="space-y-6">
                
                {/* File Upload */}
                <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">1. Select PDF</h3>
                  <input type="file" ref={fileInputRef} accept=".pdf" onChange={handleFileChange} className="hidden" />
                  
                  {!file ? (
                    <button 
                      onClick={() => fileInputRef.current?.click()} 
                      className="w-full py-8 border-2 border-dashed border-slate-300 rounded-xl text-slate-500 font-semibold hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-600 transition-all flex flex-col items-center justify-center gap-2 group"
                    >
                      <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center group-hover:bg-indigo-100 transition-colors">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                      </div>
                      <span>Browse PDF File</span>
                    </button>
                  ) : (
                    <div className="flex items-center justify-between p-4 bg-emerald-50 border border-emerald-100 rounded-xl">
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center text-emerald-600 shrink-0">
                          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" /></svg>
                        </div>
                        <div className="truncate">
                          <p className="text-sm font-bold text-emerald-800 truncate">{file.name}</p>
                          <p className="text-xs text-emerald-600">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                      </div>
                      <button onClick={() => setFile(null)} className="p-2 text-emerald-600 hover:bg-emerald-100 rounded-full transition-colors shrink-0">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                  )}
                </div>

                {/* Expiration Settings */}
                <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">2. Expiration Policy</h3>
                  
                  <div className="flex gap-2 p-1 bg-slate-100 rounded-xl mb-4">
                    <button 
                      onClick={() => setExpirationType('duration')} 
                      className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${expirationType === 'duration' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                      Duration
                    </button>
                    <button 
                      onClick={() => setExpirationType('date')} 
                      className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${expirationType === 'date' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                      Exact Date
                    </button>
                  </div>

                  {expirationType === 'duration' ? (
                    <div className="flex gap-3">
                      <input 
                        type="number" 
                        min="1" 
                        value={durationValue} 
                        onChange={(e) => setDurationValue(e.target.value)}
                        className="w-1/2 p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 font-bold focus:ring-2 focus:ring-indigo-100 focus:border-indigo-400 outline-none"
                      />
                      <select 
                        value={durationUnit} 
                        onChange={(e) => setDurationUnit(Number(e.target.value))}
                        className="w-1/2 p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 font-bold focus:ring-2 focus:ring-indigo-100 focus:border-indigo-400 outline-none"
                      >
                        <option value={60}>Minutes</option>
                        <option value={3600}>Hours</option>
                        <option value={86400}>Days</option>
                      </select>
                    </div>
                  ) : (
                    <div>
                      <input 
                        type="datetime-local" 
                        value={expiresAt} 
                        onChange={(e) => setExpiresAt(e.target.value)}
                        className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-700 font-bold focus:ring-2 focus:ring-indigo-100 focus:border-indigo-400 outline-none"
                      />
                    </div>
                  )}
                </div>

                {errorMessage && (
                  <div className="p-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 font-semibold flex items-start gap-2">
                    <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    {errorMessage}
                  </div>
                )}

                <button 
                  onClick={handleProcess} 
                  className="w-full bg-[#1e2a52] hover:bg-[#2a3a6a] text-white font-bold py-4 px-8 rounded-xl shadow-xl transform transition-all flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-[0.98]"
                >
                  Apply Expiration
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {/* Processing State */}
          {isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              <h3 className="text-xl font-bold text-slate-800 mb-2">Applying Policy</h3>
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mt-4"></div>
              <p className="text-slate-500 text-center text-sm mt-4">Securing document with expiration rules...</p>
            </div>
          )}

          {/* Success State */}
          {isSuccess && !isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-8 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up">
              <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <svg className="w-10 h-10 text-emerald-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-2">Policy Applied!</h3>
              <p className="text-slate-500 text-center text-sm mb-6">The PDF is now secured and will expire at the configured time.</p>
              
              <div className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4 mb-6 text-sm text-center">
                <span className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Expires At</span>
                <span className="font-bold text-slate-700 text-lg">
                  {policyDetails ? new Date(policyDetails.expires_at).toLocaleString() : 'N/A'}
                </span>
              </div>

              {downloadUrl && (
                <a href={downloadUrl} target="_blank" rel="noopener noreferrer" className="w-full text-center bg-[#1e2a52] hover:bg-[#2a3a6a] text-white font-bold py-4 px-8 rounded-xl shadow-lg transition-all active:scale-95 flex justify-center items-center gap-2 mb-3">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                  Access Secure Link
                </a>
              )}
              <button onClick={resetAll} className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-4 px-8 rounded-xl shadow-sm transition-all active:scale-95 flex justify-center items-center gap-2">
                Protect Another File
              </button>
            </div>
          )}

          {/* Right Column: Info / Help */}
          <div className="flex-1 lg:pl-12 hidden lg:flex flex-col justify-center animate-fade-in">
             <div className="bg-white/10 backdrop-blur-md rounded-3xl p-8 border border-white/20 shadow-2xl text-white">
                <h2 className="text-2xl font-bold mb-4">How File Expiration Works</h2>
                <p className="text-indigo-100 mb-6 leading-relaxed">
                  Protect your highly confidential PDFs by setting a strict expiration policy. 
                  Once the specified time passes, the document becomes completely inaccessible through our secure link system.
                </p>
                <ul className="space-y-4">
                  <li className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-indigo-500/50 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-xs font-bold">1</span>
                    </div>
                    <p className="text-sm font-medium text-indigo-50">Choose between a precise exact date/time or a simple rolling duration (e.g., 24 hours).</p>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-indigo-500/50 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-xs font-bold">2</span>
                    </div>
                    <p className="text-sm font-medium text-indigo-50">Generate a unique, secured access link that enforces the policy server-side.</p>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="w-6 h-6 rounded-full bg-emerald-500/50 flex items-center justify-center shrink-0 mt-0.5">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    </div>
                    <p className="text-sm font-medium text-emerald-50">Once expired, the document is mathematically locked out and requests return a 403 Forbidden error.</p>
                  </li>
                </ul>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
