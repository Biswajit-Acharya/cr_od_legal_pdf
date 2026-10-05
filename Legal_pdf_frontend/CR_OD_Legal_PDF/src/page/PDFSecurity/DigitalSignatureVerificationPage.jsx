import React, { useState, useRef } from 'react';
import { Upload, FileText, Download, CheckCircle2, ArrowLeft, X, AlertCircle, ShieldAlert, ShieldCheck, ShieldX, FileQuestion } from 'lucide-react';
import { getToolApiConfig } from '../../config/toolApiConfig';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function DigitalSignatureVerificationPage({ tool, onBack }) {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [apiResult, setApiResult] = useState(null);
  const inputRef = useRef();

  const toolName = tool?.name || 'Digital Signature Verification';
  const toolDesc = tool?.description || 'Verify cryptographic digital signatures and document integrity.';
  const accepted = { accept: '.pdf', label: 'PDF files (.pdf)' };
  
  // Use config or hardcode
  const apiConfig = getToolApiConfig('Digital Signature Verification') || {
    endpoint: '/api/pdf/security/digital-signature-verify',
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
      setFiles([valid[0]]); // only single file verification
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

  const getStatusIcon = (status) => {
    switch (status) {
      case 'VERIFIED':
        return <ShieldCheck className="w-12 h-12 text-emerald-500" />;
      case 'NO_SIGNATURE':
      case 'NO_CRYPTOGRAPHIC_SIGNATURE':
        return <FileQuestion className="w-12 h-12 text-amber-500" />;
      case 'PARTIALLY_VERIFIED':
        return <ShieldAlert className="w-12 h-12 text-amber-500" />;
      default:
        return <ShieldX className="w-12 h-12 text-red-500" />;
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'VERIFIED': return 'Digital Signature Verified';
      case 'NO_SIGNATURE': return 'No Digital Signature Detected';
      case 'NO_CRYPTOGRAPHIC_SIGNATURE': return 'No Cryptographic Signature Detected';
      case 'PARTIALLY_VERIFIED': return 'Partially Verified (Trust Unknown)';
      case 'INVALID_SIGNATURE': return 'Digital Signature Invalid';
      case 'MODIFIED_AFTER_SIGNING': return 'Document Modified After Signing';
      default: return 'Verification Failed / Unknown';
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
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">File selected</p>
                  <div className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-xl px-4 py-3">
                    <div className="w-9 h-9 rounded-lg bg-[#1e2a52]/10 flex items-center justify-center shrink-0"><FileText className="w-4 h-4 text-[#1e2a52]" /></div>
                    <div className="flex-1 min-w-0"><p className="text-xs sm:text-sm font-semibold text-slate-800 truncate">{files[0].name}</p><p className="text-[10px] sm:text-xs text-slate-400">{files[0].size}</p></div>
                    <button onClick={() => setFiles([])} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
                  </div>
                </div>
              )}

              {files.length > 0 && (
                <div className="mt-8 text-center">
                  <button onClick={handleProcess} className="bg-[#1e2a52] hover:bg-[#2a3a6a] text-white px-10 py-3 rounded-full font-bold shadow-md hover:shadow-lg transition-all">
                    Verify Signature
                  </button>
                </div>
              )}
            </>
          )}

          {isProcessing && (
            <div className="flex flex-col items-center justify-center p-10 bg-[#f8faf7] border border-slate-200/80 rounded-2xl">
              <div className="w-12 h-12 border-4 border-[#1e2a52] border-t-transparent rounded-full animate-spin mb-4" />
              <p className="text-sm font-bold text-[#1e2a52] animate-pulse">Verifying Document Integrity... Please wait!</p>
            </div>
          )}

          {isDone && apiResult && (
            <div className="space-y-6">
              
              {/* STATUS HEADER */}
              <div className="flex flex-col items-center justify-center p-8 bg-slate-50 border border-slate-200 rounded-2xl text-center">
                <div className="mb-4">{getStatusIcon(apiResult.overall_status)}</div>
                <h2 className="text-2xl font-black text-slate-800 mb-2">{getStatusLabel(apiResult.overall_status)}</h2>
                {apiResult.message && <p className="text-sm font-medium text-slate-500 max-w-md">{apiResult.message}</p>}
              </div>

              {/* DOCUMENT INFO */}
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="bg-slate-100 px-6 py-3 border-b border-slate-200">
                  <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Document Information</h3>
                </div>
                <div className="p-6 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                  <div><p className="text-slate-500 font-semibold mb-1">File Name</p><p className="text-slate-800 truncate font-medium">{apiResult.filename}</p></div>
                  <div><p className="text-slate-500 font-semibold mb-1">File Size</p><p className="text-slate-800 font-medium">{apiResult.document_info?.file_size} bytes</p></div>
                  <div><p className="text-slate-500 font-semibold mb-1">Page Count</p><p className="text-slate-800 font-medium">{apiResult.document_info?.page_count}</p></div>
                  <div><p className="text-slate-500 font-semibold mb-1">PDF Version</p><p className="text-slate-800 font-medium">{apiResult.document_info?.pdf_version}</p></div>
                  <div><p className="text-slate-500 font-semibold mb-1">Encrypted</p><p className="text-slate-800 font-medium">{apiResult.document_info?.is_encrypted ? 'Yes' : 'No'}</p></div>
                  <div><p className="text-slate-500 font-semibold mb-1">Verification Date</p><p className="text-slate-800 font-medium">{new Date(apiResult.verified_at).toLocaleString()}</p></div>
                </div>
              </div>

              {/* SIGNATURE INFORMATION SUMMARY */}
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="bg-slate-100 px-6 py-3 border-b border-slate-200">
                  <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Signature Information</h3>
                </div>
                <div className="p-6 grid grid-cols-2 gap-4 text-sm">
                  <div><p className="text-slate-500 font-semibold mb-1">Signatures Found</p><p className="text-slate-800 font-bold">{apiResult.signature_count}</p></div>
                  <div><p className="text-slate-500 font-semibold mb-1">Cryptographic Signature</p><p className="text-slate-800 font-bold">{apiResult.signature_type === 'CRYPTOGRAPHIC' ? 'Detected' : 'Not Detected'}</p></div>
                </div>
              </div>

              {apiResult.signature_count === 0 && (
                <>
                  <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                    <div className="bg-slate-100 px-6 py-3 border-b border-slate-200">
                      <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Certificate</h3>
                    </div>
                    <div className="p-6 text-sm"><p className="text-slate-500 font-medium">Not Available</p></div>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                    <div className="bg-slate-100 px-6 py-3 border-b border-slate-200">
                      <h3 className="text-sm font-bold text-slate-700 uppercase tracking-wide">Document Integrity</h3>
                    </div>
                    <div className="p-6 text-sm"><p className="text-slate-500 font-medium">Not Verifiable</p></div>
                  </div>
                </>
              )}

              {/* SIGNATURES */}
              {apiResult.signatures && apiResult.signatures.length > 0 && apiResult.signatures.map((sig, idx) => (
                <div key={idx} className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                  <div className="bg-emerald-50 px-6 py-3 border-b border-emerald-100">
                    <h3 className="text-sm font-bold text-emerald-800 uppercase tracking-wide">Signature {sig.signature_index} Information</h3>
                  </div>
                  
                  <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-6">
                    {/* Cryptographic Details */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-wider border-b border-slate-100 pb-2">Integrity</h4>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Signer</span><span className="text-slate-800 font-semibold truncate max-w-[200px]">{sig.signer_name || 'Unknown'}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Signature Status</span><span className="text-slate-800 font-bold">{sig.signature_status}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Document Integrity</span><span className="text-slate-800 font-semibold">{sig.document_integrity_status}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Modified After Signing</span><span className="text-slate-800 font-semibold">{sig.document_modified_after_signing ? 'Yes' : 'No'}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Timestamp</span><span className="text-slate-800 text-xs mt-0.5">{sig.signature_timestamp || 'N/A'}</span></div>
                      </div>
                    </div>

                    {/* Certificate Details */}
                    <div>
                      <h4 className="text-xs font-bold text-slate-400 mb-3 uppercase tracking-wider border-b border-slate-100 pb-2">Certificate</h4>
                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Cert Status</span><span className="text-slate-800 font-bold">{sig.certificate_status}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Trust Status</span><span className="text-slate-800 font-semibold">{sig.trust_status}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Issuer</span><span className="text-slate-800 font-medium truncate max-w-[150px]">{sig.certificate_issuer || 'N/A'}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Valid From</span><span className="text-slate-800 text-xs mt-0.5">{sig.certificate_valid_from || 'N/A'}</span></div>
                        <div className="flex justify-between"><span className="text-slate-500 font-medium">Valid Until</span><span className="text-slate-800 text-xs mt-0.5">{sig.certificate_valid_until || 'N/A'}</span></div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* DOWNLOAD REPORT & PROCESS ANOTHER */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-6">
                {apiResult.report_url && (
                  <a href={`${API_BASE_URL}${apiResult.report_url}`} download 
                    className="inline-flex items-center justify-center gap-2 bg-[#1e2a52] hover:bg-[#2a3a6a] text-white px-8 py-3 rounded-full font-bold shadow-md transition-all text-sm cursor-pointer hover:scale-105 min-w-[240px]">
                    <Download className="w-4 h-4" /> Download Verification Report
                  </a>
                )}
                <button onClick={() => { setFiles([]); setIsDone(false); setApiResult(null); }} className="inline-flex items-center justify-center gap-2 bg-slate-200 hover:bg-slate-300 text-slate-800 px-8 py-3 rounded-full font-bold shadow-sm transition-all text-sm cursor-pointer min-w-[240px]">
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
