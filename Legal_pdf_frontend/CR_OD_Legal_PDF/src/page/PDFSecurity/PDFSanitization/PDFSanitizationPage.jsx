import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle2, ChevronRight, Shield, FileText, Activity, Trash2, ArrowRight, Download, AlertTriangle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function PDFSanitizationPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  
  // View states: 'upload', 'analyzing', 'analysis_result', 'sanitizing', 'report'
  const [viewState, setViewState] = useState('upload');
  
  const [error, setError] = useState('');
  
  const [analysisData, setAnalysisData] = useState(null);
  const [sanitizationResult, setSanitizationResult] = useState(null);

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
      setAnalysisData(null);
      setSanitizationResult(null);
      setViewState('upload');
    }
  };

  const startAnalysis = async () => {
    if (!file) return;
    setViewState('analyzing');
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/api/pdf/security/sanitization/analyze`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to analyze document.');
      }
      
      setAnalysisData(data);
      setViewState('analysis_result');
    } catch (err) {
      setError(err.message || 'An error occurred during analysis.');
      setViewState('upload');
    }
  };

  const startSanitization = async () => {
    if (!file) return;
    setViewState('sanitizing');
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/api/pdf/security/sanitization/process`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to sanitize document.');
      }
      
      setSanitizationResult(data);
      setViewState('report');
    } catch (err) {
      setError(err.message || 'An error occurred during sanitization.');
      setViewState('analysis_result');
    }
  };

  const handleDownload = () => {
    if (sanitizationResult && sanitizationResult.download_url) {
      window.location.href = `${API_BASE}${sanitizationResult.download_url}`;
    }
  };

  const resetAll = () => {
    setFile(null);
    setAnalysisData(null);
    setSanitizationResult(null);
    setError('');
    setViewState('upload');
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
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <Trash2 className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'PDF Sanitization'}</h1>
                <p className="text-slate-500 mt-1">
                  Remove unsafe content, hidden scripts, and embedded objects.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            
            {/* --- UPLOAD STATE --- */}
            {viewState === 'upload' && (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-blue-300 bg-blue-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
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
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-blue-600">
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

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <p className="text-sm">{error}</p>
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    onClick={startAnalysis}
                    disabled={!file}
                    className={`px-8 py-3 rounded-xl font-medium flex items-center space-x-2 transition-all ${!file ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow'}`}
                  >
                    <span>Analyze PDF</span>
                    <ArrowRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            )}

            {/* --- ANALYZING / SANITIZING LOADING STATES --- */}
            {(viewState === 'analyzing' || viewState === 'sanitizing') && (
              <div className="flex flex-col items-center justify-center py-16 space-y-6">
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-blue-100 rounded-full"></div>
                  <div className="w-20 h-20 border-4 border-blue-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
                  <Activity className="w-8 h-8 text-blue-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800">
                  {viewState === 'analyzing' ? 'Analyzing Document...' : 'Sanitizing PDF...'}
                </h3>
                <p className="text-slate-500">
                  {viewState === 'analyzing' 
                    ? 'Detecting unsafe elements, metadata, and active content.'
                    : 'Removing unsafe content and rebuilding the document safely.'}
                </p>
              </div>
            )}

            {/* --- ANALYSIS RESULT STATE --- */}
            {viewState === 'analysis_result' && analysisData && (
              <div className="space-y-6 max-w-3xl mx-auto animate-in fade-in">
                
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-2xl font-bold text-slate-900">PDF Sanitization Analysis</h2>
                  <span className="text-sm font-medium text-slate-500">File: {analysisData.original_filename}</span>
                </div>

                {analysisData.is_signed && (
                  <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex items-start space-x-3 mb-6">
                    <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-amber-800 font-semibold mb-1">Digital Signature Detected</h4>
                      <p className="text-amber-700 text-sm">
                        Sanitizing this PDF may invalidate its existing digital signature because the document will be modified.
                        You can still proceed, but the signature will likely break.
                      </p>
                    </div>
                  </div>
                )}

                {!analysisData.needs_sanitization ? (
                  <div className="bg-emerald-50 border border-emerald-200 p-6 rounded-xl text-center">
                    <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                    <h3 className="text-xl font-bold text-emerald-800 mb-2">No Issues Detected</h3>
                    <p className="text-emerald-700">No supported sanitizable security elements were detected in this document.</p>
                  </div>
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
                      <h3 className="font-semibold text-slate-800">Security Elements Detected</h3>
                    </div>
                    <div className="divide-y divide-slate-100">
                      {analysisData.elements.map((el, i) => (
                        <div key={i} className="flex justify-between items-center px-6 py-3">
                          <span className="text-slate-700 font-medium">{el.element}</span>
                          <div className="flex items-center space-x-4">
                            <span className={`text-sm font-medium ${el.status === 'Detected' ? 'text-amber-600' : 'text-emerald-600'}`}>
                              {el.status}
                            </span>
                            <span className="text-slate-400 font-mono text-sm w-6 text-right">{el.count}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <p className="text-sm">{error}</p>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-3 pt-6 border-t border-slate-200">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm w-full sm:w-auto"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={startSanitization}
                    disabled={!analysisData.needs_sanitization}
                    className={`px-8 py-3 rounded-xl font-medium flex items-center justify-center space-x-2 transition-all w-full sm:w-auto ${!analysisData.needs_sanitization ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow'}`}
                  >
                    <Shield className="w-5 h-5" />
                    <span>Proceed with Sanitization</span>
                  </button>
                </div>
              </div>
            )}

            {/* --- REPORT STATE --- */}
            {viewState === 'report' && sanitizationResult && (
              <div className="space-y-6 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                <div className="flex flex-col items-center text-center space-y-3 mb-6">
                  {sanitizationResult.verification_passed ? (
                    <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                      <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                    </div>
                  ) : (
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                      <AlertTriangle className="w-8 h-8 text-red-600" />
                    </div>
                  )}
                  <h2 className="text-2xl font-bold text-slate-900">
                    {sanitizationResult.verification_passed ? 'PDF Sanitization Complete' : 'Sanitization Verification Failed'}
                  </h2>
                  <p className="text-slate-600">File: {sanitizationResult.original_analysis.original_filename}</p>
                </div>

                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex justify-between items-center">
                    <h3 className="font-semibold text-slate-800">Security Elements</h3>
                  </div>
                  <div className="divide-y divide-slate-100">
                    {sanitizationResult.report_items.map((el, i) => (
                      <div key={i} className="flex justify-between items-center px-6 py-3">
                        <span className="text-slate-700 font-medium">{el.element}</span>
                        <div className="flex items-center space-x-4">
                          <span className={`text-sm font-medium flex items-center ${
                            el.status === 'Verification Failed' ? 'text-red-600' : 
                            el.status === 'Preserved' ? 'text-blue-600' : 'text-emerald-600'
                          }`}>
                            {el.status === 'Removed' || el.status === 'Sanitized' ? <CheckCircle2 className="w-4 h-4 mr-1.5" /> : null}
                            {el.status === 'Verification Failed' ? <AlertTriangle className="w-4 h-4 mr-1.5" /> : null}
                            {el.status}
                          </span>
                          <span className="text-slate-400 font-mono text-sm w-6 text-right">{el.count}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className={`p-4 rounded-xl border flex items-start space-x-3 ${sanitizationResult.verification_passed ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
                  {sanitizationResult.verification_passed ? (
                    <Shield className="w-6 h-6 text-emerald-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <h4 className={`font-semibold mb-1 ${sanitizationResult.verification_passed ? 'text-emerald-800' : 'text-red-800'}`}>
                      Verification
                    </h4>
                    <p className={`text-sm leading-relaxed ${sanitizationResult.verification_passed ? 'text-emerald-700' : 'text-red-700'}`}>
                      {sanitizationResult.verification_passed 
                        ? 'Sanitized PDF re-analyzed successfully. Supported unsafe active content and hidden data were removed.' 
                        : 'Sanitization verification failed. Some targeted elements could not be fully removed.'}
                    </p>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-3 pt-6 border-t border-slate-200">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm w-full sm:w-auto"
                  >
                    Process Another File
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-all shadow-sm hover:shadow flex items-center justify-center space-x-2 w-full sm:w-auto"
                  >
                    <Download className="w-5 h-5" />
                    <span>Download Sanitized PDF</span>
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
