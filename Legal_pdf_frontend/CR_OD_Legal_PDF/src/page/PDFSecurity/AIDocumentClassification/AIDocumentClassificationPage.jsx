import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle2, ChevronRight, FileText, Search, BookOpen, Layers, BarChart, FileQuestion } from 'lucide-react';
import { getToolApiConfig } from '../../../config/toolApiConfig';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function AIDocumentClassificationPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const apiConfig = getToolApiConfig('AI Document Classification') || { endpoint: '/api/pdf/security/ai-document-classification' };

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

  const getConfidenceStyle = (confidence) => {
    if (confidence > 0.75) return { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'High Confidence' };
    if (confidence >= 0.5) return { color: 'text-yellow-600', bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'Medium Confidence' };
    return { color: 'text-slate-600', bg: 'bg-slate-50', border: 'border-slate-200', text: 'Low Confidence / Uncertain' };
  };

  const getCategoryIcon = (category) => {
    const c = category?.toLowerCase() || '';
    if (c.includes('invoice') || c.includes('financial') || c.includes('tax')) return <BarChart className="w-8 h-8 text-indigo-500" />;
    if (c.includes('legal') || c.includes('contract')) return <BookOpen className="w-8 h-8 text-indigo-500" />;
    if (c.includes('unknown') || c.includes('ocr')) return <FileQuestion className="w-8 h-8 text-indigo-500" />;
    return <Layers className="w-8 h-8 text-indigo-500" />;
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
                <Layers className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'AI Document Classification'}</h1>
                <p className="text-slate-500 mt-1">
                  Automatically categorize your PDF documents using AI context analysis.
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
                        <span>Analyzing Document...</span>
                      </>
                    ) : (
                      <>
                        <Search className="w-5 h-5" />
                        <span>Classify Document</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Main Classification Result Card */}
                <div className="bg-white border-2 border-indigo-100 rounded-2xl p-6 md:p-10 shadow-sm text-center relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-400 to-purple-500"></div>
                  
                  <div className="flex justify-center mb-6">
                    <div className="w-20 h-20 bg-indigo-50 rounded-full flex items-center justify-center">
                      {getCategoryIcon(result.category)}
                    </div>
                  </div>
                  
                  <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Detected Category</h2>
                  <p className="text-4xl md:text-5xl font-black text-slate-900 mb-6">{result.category}</p>
                  
                  <div className="max-w-md mx-auto">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="font-semibold text-slate-600">Confidence Score</span>
                      <span className={`font-bold ${getConfidenceStyle(result.confidence).color}`}>
                        {(result.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2.5 mb-2 overflow-hidden">
                      <div 
                        className={`h-2.5 rounded-full ${result.confidence > 0.75 ? 'bg-emerald-500' : result.confidence > 0.5 ? 'bg-yellow-500' : 'bg-slate-400'}`} 
                        style={{ width: `${Math.max(result.confidence * 100, 5)}%` }}
                      ></div>
                    </div>
                    <p className={`text-xs font-medium ${getConfidenceStyle(result.confidence).color}`}>
                      {getConfidenceStyle(result.confidence).text}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Reasoning Card */}
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
                    <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center">
                      <CheckCircle2 className="w-4 h-4 mr-2 text-indigo-500" />
                      Classification Reasoning
                    </h3>
                    <p className="text-slate-600 text-sm leading-relaxed">
                      {result.reason}
                    </p>
                    
                    <div className="mt-6 pt-4 border-t border-slate-200">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-500">File Analyzed:</span>
                        <span className="font-medium text-slate-800">{result.filename}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs mt-2">
                        <span className="text-slate-500">Pages Parsed:</span>
                        <span className="font-medium text-slate-800">{result.total_pages}</span>
                      </div>
                      <div className="flex items-center justify-between text-xs mt-2">
                        <span className="text-slate-500">Text Extraction:</span>
                        <span className="font-medium text-slate-800 capitalize">{result.text_extraction_status}</span>
                      </div>
                    </div>
                  </div>

                  {/* Secondary Categories */}
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
                    <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center">
                      <Layers className="w-4 h-4 mr-2 text-indigo-500" />
                      Secondary Matches
                    </h3>
                    
                    {result.secondary_categories && result.secondary_categories.length > 0 ? (
                      <div className="space-y-3">
                        {result.secondary_categories.map((cat, idx) => (
                          <div key={idx} className="bg-white border border-slate-200 rounded-lg p-3 flex justify-between items-center shadow-sm">
                            <span className="font-medium text-slate-700">{cat}</span>
                            <span className="text-xs bg-slate-100 text-slate-500 px-2 py-1 rounded">Alternative</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <p className="text-sm text-slate-500">No strong secondary categories detected.</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end pt-4">
                  <button
                    onClick={() => {
                      setResult(null);
                      setFile(null);
                    }}
                    className="px-6 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium rounded-lg transition-colors"
                  >
                    Classify Another Document
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
