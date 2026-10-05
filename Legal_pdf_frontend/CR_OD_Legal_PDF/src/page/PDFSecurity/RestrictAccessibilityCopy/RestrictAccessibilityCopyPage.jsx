import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, FileText, Activity, ShieldCheck, Download, ChevronRight, Lock } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function RestrictAccessibilityCopyPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [viewState, setViewState] = useState('upload'); // 'upload', 'processing', 'success', 'error'
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
      setViewState('upload');
    }
  };

  const processFile = async () => {
    if (!file) return;
    setViewState('processing');
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/api/pdf/security/restrict-accessibility-copy`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'The PDF could not be securely protected.');
      }
      
      setResult(data);
      setViewState('success');
    } catch (err) {
      setError(err.message || 'An error occurred while processing the document.');
      setViewState('error');
    }
  };

  const resetAll = () => {
    setFile(null);
    setResult(null);
    setError('');
    setViewState('upload');
  };

  const handleDownload = () => {
    if (result && result.download_url) {
      window.open(`${API_BASE}${result.download_url}`, '_blank');
    }
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
              <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center">
                <Lock className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'Restrict Accessibility Copy'}</h1>
                <p className="text-slate-500 mt-1">
                  Apply PDF security to actively restrict content extraction and copying capabilities.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {/* UPLOAD STATE */}
            {viewState === 'upload' && (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-red-300 bg-red-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
                  onClick={() => !file && fileInputRef.current?.click()}
                >
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf" className="hidden" />
                  
                  {file ? (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-red-600">
                        <FileText className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">{file.name}</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null); }}
                        className="mt-4 text-sm text-red-500 hover:text-red-600 font-medium px-4 py-2 bg-red-100 rounded-lg"
                      >
                        Remove file
                      </button>
                    </div>
                  ) : (
                     <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-slate-400">
                        <Upload className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">Upload PDF to Restrict Copying</p>
                    </div>
                  )}
                </div>

                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex items-start space-x-3 text-sm text-amber-800">
                  <AlertCircle className="w-5 h-5 flex-shrink-0 text-amber-600 mt-0.5" />
                  <div>
                    <strong>Note:</strong> This will encrypt your document using AES-256 and restrict copy permissions. The document will remain viewable but content extraction will be disabled.
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    onClick={processFile}
                    disabled={!file}
                    className={`px-8 py-3 rounded-xl font-medium flex items-center transition-all ${!file ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700 text-white shadow-sm'}`}
                  >
                    Restrict Content Access
                  </button>
                </div>
              </div>
            )}

            {/* PROCESSING STATE */}
            {viewState === 'processing' && (
              <div className="flex flex-col items-center justify-center py-16 space-y-6">
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-red-100 rounded-full"></div>
                  <div className="w-20 h-20 border-4 border-red-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
                  <Activity className="w-8 h-8 text-red-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800">Applying Security Restrictions...</h3>
              </div>
            )}

            {/* ERROR STATE */}
            {viewState === 'error' && (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in">
                <div className="bg-red-50 border border-red-200 text-red-600 p-6 rounded-xl flex flex-col items-center text-center">
                  <AlertCircle className="w-12 h-12 mb-4 text-red-500" />
                  <h3 className="text-lg font-bold mb-2">Processing Failed</h3>
                  <p className="text-sm">{error}</p>
                </div>
                <div className="flex justify-center">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm"
                  >
                    Try Another Document
                  </button>
                </div>
              </div>
            )}

            {/* SUCCESS STATE */}
            {viewState === 'success' && result && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto">
                
                <div className="flex flex-col items-center text-center">
                  <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-6">
                    <ShieldCheck className="w-10 h-10 text-green-600" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900 mb-2">Accessibility Copy Restricted</h2>
                  <p className="text-slate-600">{result.message}</p>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
                  <div className="space-y-4">
                    <div className="flex justify-between items-center py-2 border-b border-slate-200">
                      <span className="text-sm text-slate-500">File</span>
                      <span className="text-sm font-medium text-slate-800 truncate max-w-[200px]">{result.original_filename}</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-slate-200">
                      <span className="text-sm text-slate-500">Status</span>
                      <span className="text-sm font-bold text-green-600">Protected</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-slate-200">
                      <span className="text-sm text-slate-500">Accessibility Copy</span>
                      <span className="text-sm font-bold text-red-600">Restricted</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-slate-200">
                      <span className="text-sm text-slate-500">Content Extraction</span>
                      <span className="text-sm font-bold text-red-600">Restricted</span>
                    </div>
                    <div className="flex justify-between items-center py-2">
                      <span className="text-sm text-slate-500">PDF Security</span>
                      <span className="text-sm font-bold text-green-600">Enabled (AES-256)</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm flex-1 sm:flex-none text-center"
                  >
                    Process Another
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white font-medium rounded-xl transition-colors shadow-sm flex items-center justify-center flex-1 sm:flex-none"
                  >
                    <Download className="w-5 h-5 mr-2" />
                    Download Protected PDF
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
