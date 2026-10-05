import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle2, ChevronRight, Shield, FileText, Clock, AlertTriangle, Download } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function AtomicServerTimestampingPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.type !== 'application/pdf') {
        setError('Only PDF files are supported.');
        return;
      }
      setFile(selected);
      setError('');
      setResult(null);
    }
  };

  const handleProcess = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/api/pdf/security/atomic-server-timestamping`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.detail || 'Failed to process document.');
      }
      
      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred during timestamping.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (result && result.download_url) {
      window.location.href = `${API_BASE}${result.download_url}`;
    }
  };

  const resetAll = () => {
    setFile(null);
    setResult(null);
    setError('');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        <button
          onClick={onBack}
          className="mb-6 flex items-center text-slate-500 hover:text-slate-700 transition-colors"
        >
          <ChevronRight className="w-5 h-5 rotate-180 mr-1" />
          Back to PDF Security
        </button>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-6 sm:p-8 border-b border-slate-100">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
                <Clock className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'Atomic Server Timestamping'}</h1>
                <p className="text-slate-500 mt-1">
                  Apply a secure cryptographic server timestamp with document SHA-256 hashing.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {!result ? (
              <div className="space-y-6 max-w-2xl mx-auto">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
                  onClick={() => !file && fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf"
                    className="hidden"
                  />
                  
                  {file ? (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-indigo-600">
                        <FileText className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">{file.name}</p>
                      <p className="text-xs text-slate-500 mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null); }}
                        className="text-sm text-red-500 hover:text-red-600 font-medium px-4 py-2 bg-red-50 rounded-lg"
                      >
                        Remove file
                      </button>
                    </div>
                  ) : (
                     <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-slate-400">
                        <Upload className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">Click to upload or drag and drop</p>
                      <p className="text-xs text-slate-500">PDF files only</p>
                    </div>
                  )}
                </div>

                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl flex items-start space-x-3">
                   <Shield className="w-5 h-5 text-slate-500 flex-shrink-0 mt-0.5" />
                   <div>
                     <p className="text-sm text-slate-700 font-medium">Server Timestamp Verification</p>
                     <p className="text-xs text-slate-500 mt-1">
                        A SHA-256 hash of your document will be computed and securely embedded in the document's metadata along with the server time.
                     </p>
                   </div>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <p className="text-sm">{error}</p>
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    onClick={handleProcess}
                    disabled={!file || loading}
                    className={`px-8 py-3 rounded-xl font-medium flex items-center space-x-2 transition-all ${!file || loading ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow'}`}
                  >
                    {loading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Applying Timestamp...</span>
                      </>
                    ) : (
                      <>
                        <Clock className="w-5 h-5" />
                        <span>Timestamp PDF</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Result Header */}
                <div className="flex flex-col items-center text-center space-y-3 mb-8">
                  <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900">Timestamp Applied Successfully</h2>
                  <p className="text-slate-600">The PDF has been cryptographically hashed and timestamped.</p>
                </div>

                {/* Professional Report Table */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex justify-between items-center">
                    <h3 className="font-semibold text-slate-800">Timestamp Report</h3>
                    <span className="text-xs font-bold bg-indigo-100 text-indigo-800 px-2.5 py-1 rounded-full uppercase tracking-wider">
                      {result.verification_status}
                    </span>
                  </div>
                  <div className="divide-y divide-slate-100">
                    <div className="flex flex-col sm:flex-row px-6 py-4">
                      <span className="text-slate-500 font-medium w-48 mb-1 sm:mb-0">Document</span>
                      <span className="font-medium text-slate-900 break-all">{result.original_filename}</span>
                    </div>
                    <div className="flex flex-col sm:flex-row px-6 py-4">
                      <span className="text-slate-500 font-medium w-48 mb-1 sm:mb-0">Timestamp Type</span>
                      <span className="font-medium text-slate-900">{result.timestamp_type}</span>
                    </div>
                    <div className="flex flex-col sm:flex-row px-6 py-4">
                      <span className="text-slate-500 font-medium w-48 mb-1 sm:mb-0">Timestamp (UTC)</span>
                      <span className="font-medium text-slate-900">{result.timestamp}</span>
                    </div>
                    <div className="flex flex-col sm:flex-row px-6 py-4">
                      <span className="text-slate-500 font-medium w-48 mb-1 sm:mb-0">Document SHA-256</span>
                      <span className="font-mono text-sm text-slate-700 bg-slate-50 px-2 py-1 rounded break-all">{result.hash_sha256}</span>
                    </div>
                    <div className="flex flex-col sm:flex-row px-6 py-4">
                      <span className="text-slate-500 font-medium w-48 mb-1 sm:mb-0">Verification</span>
                      <span className={`font-medium flex items-center ${result.verification_passed ? 'text-emerald-600' : 'text-red-600'}`}>
                        {result.verification_passed ? <><CheckCircle2 className="w-4 h-4 mr-1.5" /> Timestamp verified</> : <><AlertTriangle className="w-4 h-4 mr-1.5" /> Verification failed</>}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Security Note Disclaimer */}
                <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-5 flex items-start space-x-4">
                  <Shield className="w-6 h-6 text-indigo-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-indigo-900 font-semibold mb-1">Security Note</h4>
                    <p className="text-indigo-700 text-sm leading-relaxed">
                      This timestamp is generated by the Nexora server and is not an independent RFC 3161 TSA timestamp. 
                      It securely associates the cryptographic hash of your document with the local server time.
                    </p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-3 pt-6 border-t border-slate-200">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm w-full sm:w-auto"
                  >
                    Process Another File
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-8 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition-all shadow-sm hover:shadow flex items-center justify-center space-x-2 w-full sm:w-auto"
                  >
                    <Download className="w-5 h-5" />
                    <span>Download Timestamped PDF</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
