import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, Shield, CheckCircle2, ChevronRight, FileText, Search, EyeOff } from 'lucide-react';
import { getToolApiConfig } from '../../../config/toolApiConfig';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function AISensitiveDataDetectionPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const apiConfig = getToolApiConfig('AI Sensitive Data Detection') || { endpoint: '/api/pdf/security/ai-sensitive-data-detection' };

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

  const handleAnalyze = async () => {
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
        throw new Error(data.error || data.detail || 'Analysis failed.');
      }
      
      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred during analysis.');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL': return 'text-red-700 bg-red-100 border-red-200';
      case 'HIGH': return 'text-orange-700 bg-orange-100 border-orange-200';
      case 'MEDIUM': return 'text-yellow-700 bg-yellow-100 border-yellow-200';
      case 'LOW': return 'text-emerald-700 bg-emerald-100 border-emerald-200';
      default: return 'text-slate-700 bg-slate-100 border-slate-200';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-5xl mx-auto">
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
                <Shield className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'AI Sensitive Data Detection'}</h1>
                <p className="text-slate-500 mt-1">
                  Analyze PDF documents for hidden PII, financial data, and credentials using contextual heuristics.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {!result ? (
              <div className="space-y-6 max-w-3xl mx-auto">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${file ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
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
                      <p className="text-xs text-slate-500">PDF files only (max 100MB)</p>
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
                    onClick={handleAnalyze}
                    disabled={!file || loading}
                    className={`px-6 py-3 rounded-xl font-medium flex items-center space-x-2 transition-all ${!file || loading ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm hover:shadow'}`}
                  >
                    {loading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Scanning for secrets...</span>
                      </>
                    ) : (
                      <>
                        <Search className="w-5 h-5" />
                        <span>Detect Sensitive Data</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Stats Headers */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                    <p className="text-xs font-semibold text-slate-500 uppercase">Total Detections</p>
                    <p className="text-3xl font-black text-indigo-600 mt-1">{result.total_detections}</p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                    <p className="text-xs font-semibold text-slate-500 uppercase">Pages Analyzed</p>
                    <p className="text-3xl font-black text-slate-700 mt-1">{result.total_pages}</p>
                  </div>
                  <div className="bg-red-50 border border-red-200 p-4 rounded-xl text-center">
                    <p className="text-xs font-semibold text-red-600 uppercase">High/Critical</p>
                    <p className="text-3xl font-black text-red-700 mt-1">
                      {(result.risk_summary?.high || 0) + (result.risk_summary?.critical || 0)}
                    </p>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                    <p className="text-xs font-semibold text-slate-500 uppercase">Text Extraction</p>
                    <p className="text-lg font-bold text-slate-700 mt-3 capitalize">{result.text_extraction_status}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Category Summary */}
                  <div className="col-span-1 bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                    <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 border-b pb-2">Category Summary</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-600">Personal Info</span>
                        <span className="font-semibold text-slate-800">{result.summary?.personal_information || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-600">Identification</span>
                        <span className="font-semibold text-slate-800">{result.summary?.identification_information || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-600">Financial Info</span>
                        <span className="font-semibold text-slate-800">{result.summary?.financial_information || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-600">Business Confidential</span>
                        <span className="font-semibold text-slate-800">{result.summary?.confidential_business_information || 0}</span>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-slate-600">Credentials & Secrets</span>
                        <span className="font-semibold text-slate-800">{result.summary?.credentials_and_secrets || 0}</span>
                      </div>
                    </div>
                  </div>

                  {/* Detections List */}
                  <div className="col-span-1 md:col-span-2">
                    <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 border-b pb-2">Detection Details</h3>
                    
                    {result.detections && result.detections.length > 0 ? (
                      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                        {result.detections.map((detection, idx) => (
                          <div key={idx} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
                            <div className="flex flex-wrap sm:flex-nowrap justify-between items-start mb-2 gap-2">
                              <div>
                                <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-1 rounded-md mr-2">
                                  {detection.category}
                                </span>
                                <h4 className="font-bold text-slate-800 inline-block mt-1 sm:mt-0">{detection.type}</h4>
                              </div>
                              <span className={`px-2 py-1 text-[10px] font-bold rounded uppercase tracking-wider border whitespace-nowrap ${getSeverityColor(detection.severity)}`}>
                                {detection.severity} RISK
                              </span>
                            </div>
                            
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 flex items-center justify-between mt-3">
                              <div className="flex items-center space-x-2 overflow-hidden">
                                <EyeOff className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                <span className="font-mono text-sm text-slate-700 truncate">{detection.masked_value}</span>
                              </div>
                              <div className="text-xs text-slate-500 font-medium whitespace-nowrap ml-4">
                                Page {detection.page}
                              </div>
                            </div>
                            
                            <div className="flex justify-between items-center mt-3 text-xs">
                              <span className="text-slate-400">ID: {detection.id}</span>
                              <div className="flex items-center space-x-1">
                                <span className="text-slate-500">Confidence:</span>
                                <span className="font-semibold text-slate-700">{(detection.confidence * 100).toFixed(0)}%</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-8 text-center text-emerald-700 h-full flex flex-col items-center justify-center">
                        <CheckCircle2 className="w-12 h-12 mb-4 text-emerald-500" />
                        <h3 className="text-lg font-bold mb-1">No Sensitive Information Detected</h3>
                        <p className="text-sm font-medium opacity-80">
                          No sensitive information was detected by the configured detection methods in this document.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end pt-4 border-t border-slate-100">
                  <button
                    onClick={() => {
                      setResult(null);
                      setFile(null);
                    }}
                    className="px-6 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-colors"
                  >
                    Analyze Another File
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
