import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, ArrowRight, X, AlertCircle, ShieldCheck, ShieldAlert, Key, Globe, Clock, Hash } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export default function BlockchainOwnershipVerificationPage({ tool, onBack }) {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  
  const [result, setResult] = useState(null);
  
  const inputRef = useRef();

  const toolName = tool?.name || tool?.title || 'Blockchain Ownership Verification';
  const toolDesc = tool?.description || 'Verify immutable blockchain ownership receipts and smart contract records embedded in your document.';
  
  const addFiles = (newFiles) => {
    setError('');
    const valid = [];
    const invalid = [];

    Array.from(newFiles).forEach(f => {
      if (f.name.toLowerCase().endsWith('.pdf') || f.type === 'application/pdf') {
        valid.push({
          name: f.name,
          size: f.size < 1024 * 1024 ? (f.size / 1024).toFixed(0) + ' KB' : (f.size / (1024 * 1024)).toFixed(2) + ' MB',
          type: f.type,
          originalFile: f
        });
      } else {
        invalid.push(f.name);
      }
    });

    if (invalid.length > 0) setError(`Only PDF files (.pdf) are accepted. Rejected: ${invalid.join(', ')}`);
    if (valid.length > 0) {
      setFiles([valid[0]]);
      setIsDone(false);
      setResult(null);
    }
  };

  const handleFileChange = (e) => { if (e.target.files?.length) addFiles(e.target.files); };
  
  const handleDrop = (e) => { 
    e.preventDefault(); 
    setIsDragging(false); 
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files); 
  };
  
  const handleRemove = (idx) => { 
    setFiles([]); 
    setIsDone(false); 
    setResult(null);
    setError(''); 
  };

  const handleProcess = async () => {
    if (!files.length) return;
    setIsProcessing(true);
    setError('');
    setResult(null);

    const fd = new FormData();
    fd.append('file', files[0].originalFile);

    try {
      const r = await fetch(`${API_BASE_URL}/api/pdf-copyright-protection/blockchain-ownership-verification/process`, { method: 'POST', body: fd });
      const d = await r.json();
      
      if (!r.ok) {
        throw new Error(d.detail || 'Verification failed');
      }
      
      setResult(d);
      setIsDone(true);
    } catch (ex) {
      setError('Error: ' + ex.message);
      setIsDone(false);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex flex-col items-center max-w-4xl mx-auto w-full pb-10">
      {/* Header */}
      <div className="w-full text-center mb-8">
        <h1 className="text-3xl md:text-4xl font-black text-[#1e2a52] mb-3 flex items-center justify-center gap-3">
          {toolName}
        </h1>
        <p className="text-slate-500 text-sm md:text-base max-w-2xl mx-auto">
          {toolDesc}
        </p>
      </div>

      <div className="bg-white rounded-3xl shadow-xl border border-slate-200/60 p-6 md:p-8 w-full max-w-2xl relative overflow-hidden">
        {/* Decorative elements */}
        <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500" />
        <div className="absolute -right-16 -top-16 w-32 h-32 bg-indigo-50 rounded-full blur-3xl opacity-60" />
        <div className="absolute -left-16 -bottom-16 w-32 h-32 bg-blue-50 rounded-full blur-3xl opacity-60" />

        <div className="relative z-10">
          {!isDone && (
            <>
              {error && (
                <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-2xl flex items-center gap-3 border border-red-100 animate-in fade-in slide-in-from-top-2">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <p className="text-sm font-medium">{error}</p>
                </div>
              )}

              {/* Upload Area */}
              <div
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                onClick={() => !files.length && inputRef.current?.click()}
                className={`relative border-2 border-dashed rounded-3xl p-8 md:p-12 text-center transition-all duration-300 ease-out flex flex-col items-center justify-center min-h-[280px]
                  ${isDragging ? 'border-indigo-500 bg-indigo-50/50 scale-[1.02]' : 'border-slate-300 hover:border-indigo-400 hover:bg-slate-50'}
                  ${files.length ? 'border-none bg-slate-50' : 'cursor-pointer'}`}
              >
                <input ref={inputRef} type="file" className="hidden" accept=".pdf" onChange={handleFileChange} />
                
                {!files.length ? (
                  <div className="flex flex-col items-center pointer-events-none">
                    <div className="w-20 h-20 bg-white shadow-sm rounded-2xl flex items-center justify-center mb-6 border border-slate-100 group-hover:shadow-md transition-all">
                      <Upload className="w-8 h-8 text-indigo-500" />
                    </div>
                    <h3 className="text-xl font-bold text-slate-800 mb-2">Drop PDF here or click to browse</h3>
                    <p className="text-slate-500 text-sm font-medium">Accepted: PDF files (.pdf)</p>
                  </div>
                ) : (
                  <div className="w-full text-left">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">File Selected</span>
                    </div>
                    <div className="flex items-center gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm animate-in zoom-in-95 duration-200">
                      <div className="w-12 h-12 bg-indigo-50 rounded-xl flex items-center justify-center flex-shrink-0">
                        <FileText className="w-6 h-6 text-indigo-600" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-slate-800 truncate text-sm">{files[0].name}</p>
                        <p className="text-xs font-medium text-slate-500 mt-0.5">{files[0].size}</p>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); handleRemove(0); }} className="p-2 hover:bg-red-50 text-slate-400 hover:text-red-500 rounded-xl transition-colors">
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={handleProcess}
                disabled={!files.length || isProcessing}
                className={`w-full mt-6 py-4 px-6 rounded-2xl font-bold text-white shadow-lg transition-all duration-300 relative overflow-hidden group
                  ${(!files.length || isProcessing) 
                    ? 'bg-slate-300 cursor-not-allowed shadow-none' 
                    : 'bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-500 hover:to-blue-500 hover:shadow-indigo-500/25 hover:-translate-y-0.5'}`}
              >
                {isProcessing ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Verifying Blockchain Data...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    Verify Ownership <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </span>
                )}
              </button>
            </>
          )}

          {isDone && result && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center justify-center gap-3 mb-8">
                {result.verification_result?.is_verified ? (
                  <>
                    <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center">
                      <ShieldCheck className="w-6 h-6 text-emerald-600" />
                    </div>
                    <h3 className="text-xl font-bold text-emerald-600">Verification Successful</h3>
                  </>
                ) : (
                  <>
                    <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                      <ShieldAlert className="w-6 h-6 text-red-600" />
                    </div>
                    <h3 className="text-xl font-bold text-red-600">No Blockchain Record Found</h3>
                  </>
                )}
              </div>

              {result.verification_result?.is_verified ? (
                 <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 mb-8 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5"><Key className="w-3.5 h-3.5"/> Owner</span>
                      <span className="text-sm font-medium text-slate-800 mt-1">{result.verification_result.owner}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5"><Globe className="w-3.5 h-3.5"/> Network</span>
                      <span className="text-sm font-medium text-slate-800 mt-1">{result.verification_result.network}</span>
                    </div>
                    <div className="flex flex-col md:col-span-2">
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5"><Hash className="w-3.5 h-3.5"/> Transaction ID</span>
                      <span className="text-sm font-medium text-slate-800 mt-1 break-all bg-white p-2 rounded-lg border border-slate-200 mt-2 font-mono">{result.verification_result.blockchain_tx_id}</span>
                    </div>
                    {result.verification_result.timestamp && (
                      <div className="flex flex-col md:col-span-2">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5"><Clock className="w-3.5 h-3.5"/> Registered On</span>
                        <span className="text-sm font-medium text-slate-800 mt-1">{result.verification_result.timestamp.replace("D:", "").replace("'", "").replace("Z", "")}</span>
                      </div>
                    )}
                  </div>
                 </div>
              ) : (
                <div className="bg-orange-50 border border-orange-200 text-orange-800 rounded-2xl p-6 mb-8 text-sm font-medium text-center leading-relaxed">
                  The uploaded document does not contain valid blockchain registration metadata. It may not have been registered on the blockchain, or the metadata could have been stripped.
                </div>
              )}

              <button
                onClick={() => {
                  setFiles([]);
                  setIsDone(false);
                  setResult(null);
                }}
                className="w-full py-4 px-6 rounded-2xl font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
              >
                Verify Another File
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
