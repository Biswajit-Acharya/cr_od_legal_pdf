import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle2, ChevronRight, Lock, Shield, FileText } from 'lucide-react';
import { getToolApiConfig } from '../../../config/toolApiConfig';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function RestrictPageExtractionPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const apiConfig = getToolApiConfig('Restrict Page Extraction') || { endpoint: '/api/pdf/security/restrict-page-extraction' };

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

  const handleRestrict = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}${apiConfig.endpoint}`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.detail || 'Failed to apply restriction.');
      }
      
      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred during restriction.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (result && result.download_url) {
      window.location.href = `${API_BASE}${result.download_url}`;
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
              <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                <Lock className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'Restrict Page Extraction'}</h1>
                <p className="text-slate-500 mt-1">
                  Prevent unauthorized page extraction and copying by applying PDF permission flags.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {!result ? (
              <div className="space-y-6 max-w-2xl mx-auto">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${file ? 'border-red-300 bg-red-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
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
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-red-600">
                        <FileText className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">{file.name}</p>
                      <p className="text-xs text-slate-500 mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                      <button
                        onClick={() => setFile(null)}
                        className="text-sm text-red-500 hover:text-red-600 font-medium"
                      >
                        Remove file
                      </button>
                    </div>
                  ) : (
                     <div className="flex flex-col items-center cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-slate-400">
                        <Upload className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">Click to upload or drag and drop</p>
                      <p className="text-xs text-slate-500">PDF files only</p>
                    </div>
                  )}
                </div>

                <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex items-start space-x-3">
                   <Shield className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                   <div>
                     <p className="text-sm text-amber-800 font-medium">Security Behavior Notice</p>
                     <p className="text-xs text-amber-700 mt-1">
                        PDF permission restrictions are enforced by compliant PDF viewers. This will prevent native page extraction tools, but cannot prevent screenshots, OCR, or third-party bypass tools.
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
                    onClick={handleRestrict}
                    disabled={!file || loading}
                    className={`px-6 py-3 rounded-xl font-medium flex items-center space-x-2 transition-all ${!file || loading ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700 text-white shadow-sm hover:shadow'}`}
                  >
                    {loading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Applying Restriction...</span>
                      </>
                    ) : (
                      <>
                        <Lock className="w-5 h-5" />
                        <span>Apply Restriction</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="bg-emerald-50 border-2 border-emerald-200 rounded-2xl p-8 text-center">
                  <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900 mb-2">Page Extraction: Restricted</h2>
                  <p className="text-slate-600 mb-6">{result.message}</p>
                  
                  <button
                    onClick={handleDownload}
                    className="w-full sm:w-auto px-8 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-xl transition-all shadow-sm hover:shadow flex items-center justify-center mx-auto space-x-2"
                  >
                    <Lock className="w-5 h-5" />
                    <span>Download Protected PDF</span>
                  </button>
                </div>

                <div className="flex justify-center pt-4">
                  <button
                    onClick={() => {
                      setResult(null);
                      setFile(null);
                    }}
                    className="px-6 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-colors"
                  >
                    Protect Another Document
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
