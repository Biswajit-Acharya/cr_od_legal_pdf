import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, FileText, Activity, ShieldCheck, ChevronRight, Tags, Info } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function PDFVersionSecurityCheckPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [viewState, setViewState] = useState('upload'); 
  const [error, setError] = useState('');
  const [report, setReport] = useState(null);
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
      setReport(null);
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
      const response = await fetch(`${API_BASE}/api/pdf/security/version-check`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to detect version.');
      }
      
      setReport(data);
      setViewState('report');
    } catch (err) {
      setError(err.message || 'An error occurred during version check.');
      setViewState('upload');
    }
  };

  const resetAll = () => {
    setFile(null);
    setReport(null);
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
              <div className="w-12 h-12 bg-teal-100 rounded-xl flex items-center justify-center">
                <Tags className="w-6 h-6 text-teal-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'PDF Version Security Check'}</h1>
                <p className="text-slate-500 mt-1">
                  Identify the PDF version and provide a technically accurate security compatibility assessment.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {/* UPLOAD STATE */}
            {viewState === 'upload' && (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-teal-300 bg-teal-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
                  onClick={() => !file && fileInputRef.current?.click()}
                >
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf" className="hidden" />
                  
                  {file ? (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-teal-600">
                        <FileText className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">{file.name}</p>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null); }}
                        className="mt-4 text-sm text-red-500 hover:text-red-600 font-medium px-4 py-2 bg-red-50 rounded-lg"
                      >
                        Remove file
                      </button>
                    </div>
                  ) : (
                     <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-slate-400">
                        <Upload className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-700 mb-1">Upload PDF for Version Check</p>
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
                    className={`px-8 py-3 rounded-xl font-medium flex items-center transition-all ${!file ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-teal-600 hover:bg-teal-700 text-white shadow-sm'}`}
                  >
                    Check Version
                  </button>
                </div>
              </div>
            )}

            {/* ANALYZING STATE */}
            {viewState === 'analyzing' && (
              <div className="flex flex-col items-center justify-center py-16 space-y-6">
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-teal-100 rounded-full"></div>
                  <div className="w-20 h-20 border-4 border-teal-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
                  <Activity className="w-8 h-8 text-teal-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800">Checking Document Version...</h3>
              </div>
            )}

            {/* REPORT STATE */}
            {viewState === 'report' && report && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Document Version Banner */}
                <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-6 sm:p-8 text-white flex flex-col sm:flex-row items-center justify-between shadow-lg">
                  <div className="text-center sm:text-left mb-4 sm:mb-0">
                    <p className="text-slate-400 font-medium uppercase tracking-wider text-sm mb-1">Document Version</p>
                    <h2 className="text-4xl sm:text-5xl font-black">{report.document_version}</h2>
                  </div>
                  <div className="bg-white/10 px-4 py-2 rounded-lg backdrop-blur-sm border border-white/10">
                    <span className="text-sm font-medium text-teal-300 flex items-center">
                      <ShieldCheck className="w-4 h-4 mr-2" />
                      {report.version_detection}
                    </span>
                  </div>
                </div>

                {/* Compatibility Assessment */}
                <div className={`p-5 rounded-xl border flex items-start space-x-3 ${report.assessment.includes('No version-specific security concern') ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-amber-50 border-amber-200 text-amber-800'}`}>
                  <AlertCircle className={`w-6 h-6 flex-shrink-0 mt-0.5 ${report.assessment.includes('No version-specific security concern') ? 'text-emerald-600' : 'text-amber-600'}`} />
                  <div>
                    <h4 className="font-bold mb-1">Assessment</h4>
                    <p className="text-sm leading-relaxed">{report.assessment}</p>
                  </div>
                </div>

                {/* Feature Compatibility */}
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-4">Security Compatibility</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {Object.entries(report.security_compatibility).map(([feature, status]) => (
                      <div key={feature} className="bg-white border border-slate-200 p-4 rounded-xl flex justify-between items-center shadow-sm">
                        <span className="font-medium text-slate-700">{feature}</span>
                        <span className={`text-sm font-bold px-2 py-1 rounded ${
                          status.includes('Present') || status.includes('Detected') || status === 'Enabled' 
                            ? 'bg-slate-100 text-slate-800 border border-slate-200' 
                            : 'bg-slate-50 text-slate-400'
                        }`}>
                          {status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Note */}
                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl flex items-start space-x-3 text-slate-600 text-sm">
                  <Info className="w-5 h-5 flex-shrink-0 text-slate-400 mt-0.5" />
                  <p>{report.vulnerability_note}</p>
                </div>

                <div className="flex justify-end pt-6 border-t border-slate-200">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm"
                  >
                    Check Another Document
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
