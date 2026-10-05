import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, FileText, Activity, ShieldAlert, ShieldCheck, Info, ChevronRight, Lock, Hash, Shield } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function PDFForensicAnalysisPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [viewState, setViewState] = useState('upload'); // 'upload', 'analyzing', 'report'
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
      const response = await fetch(`${API_BASE}/api/pdf/security/forensic-analysis`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to analyze document.');
      }
      
      setReport(data);
      setViewState('report');
    } catch (err) {
      setError(err.message || 'An error occurred during forensic analysis.');
      setViewState('upload');
    }
  };

  const resetAll = () => {
    setFile(null);
    setReport(null);
    setError('');
    setViewState('upload');
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'CRITICAL': return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH RISK': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'WARNING': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'INFO': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'CRITICAL':
      case 'HIGH RISK': return <ShieldAlert className="w-5 h-5 text-red-600" />;
      case 'WARNING': return <AlertCircle className="w-5 h-5 text-amber-600" />;
      case 'INFO': return <Info className="w-5 h-5 text-blue-600" />;
      default: return <ShieldCheck className="w-5 h-5 text-emerald-600" />;
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
              <div className="w-12 h-12 bg-slate-800 rounded-xl flex items-center justify-center">
                <Hash className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'PDF Forensic Analysis'}</h1>
                <p className="text-slate-500 mt-1">
                  Perform detailed static forensic examination of the PDF structure and metadata.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {/* UPLOAD STATE */}
            {viewState === 'upload' && (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-slate-800 bg-slate-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
                  onClick={() => !file && fileInputRef.current?.click()}
                >
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf" className="hidden" />
                  
                  {file ? (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-slate-800">
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
                      <p className="text-sm font-medium text-slate-700 mb-1">Upload PDF for Forensic Analysis</p>
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
                    className={`px-8 py-3 rounded-xl font-medium flex items-center transition-all ${!file ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-slate-900 hover:bg-slate-800 text-white shadow-sm'}`}
                  >
                    Run Forensic Scan
                  </button>
                </div>
              </div>
            )}

            {/* ANALYZING STATE */}
            {viewState === 'analyzing' && (
              <div className="flex flex-col items-center justify-center py-16 space-y-6">
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-slate-100 rounded-full"></div>
                  <div className="w-20 h-20 border-4 border-slate-900 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
                  <Activity className="w-8 h-8 text-slate-900 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800">Analyzing Document Objects...</h3>
              </div>
            )}

            {/* REPORT STATE */}
            {viewState === 'report' && report && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Overall Assessment */}
                <div className={`p-6 rounded-2xl border flex items-center space-x-4 ${report.overall_status === 'Pass' ? 'bg-emerald-50 border-emerald-200' : 'bg-orange-50 border-orange-200'}`}>
                  {report.overall_status === 'Pass' ? (
                    <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <ShieldCheck className="w-8 h-8 text-emerald-600" />
                    </div>
                  ) : (
                    <div className="w-14 h-14 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <ShieldAlert className="w-8 h-8 text-orange-600" />
                    </div>
                  )}
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">Security Status: {report.overall_status}</h2>
                    <p className={`text-sm mt-1 ${report.overall_status === 'Pass' ? 'text-emerald-700' : 'text-orange-700'}`}>
                      {report.overall_status === 'Pass' ? 'No high-risk structural anomalies detected.' : 'Forensic scan detected items requiring manual review.'}
                    </p>
                  </div>
                </div>

                {/* Document Information */}
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center"><FileText className="w-5 h-5 mr-2 text-slate-500" /> Document Information</h3>
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <div className="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-slate-100">
                      <div className="divide-y divide-slate-100">
                        {Object.entries(report.document_info).slice(0, 5).map(([key, value]) => (
                          <div key={key} className="px-5 py-3 flex justify-between">
                            <span className="text-sm text-slate-500">{key}</span>
                            <span className="text-sm font-medium text-slate-800 text-right truncate max-w-[50%]">{value}</span>
                          </div>
                        ))}
                      </div>
                      <div className="divide-y divide-slate-100">
                        {Object.entries(report.document_info).slice(5).map(([key, value]) => (
                          <div key={key} className="px-5 py-3 flex justify-between">
                            <span className="text-sm text-slate-500">{key}</span>
                            <span className="text-sm font-medium text-slate-800 text-right truncate max-w-[50%]">{value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="px-5 py-3 border-t border-slate-100 bg-slate-50">
                       <p className="text-xs text-slate-500 font-mono break-all"><span className="font-semibold">SHA-256:</span> {report.document_info["SHA-256 Hash"]}</p>
                    </div>
                  </div>
                </div>

                {/* Scope Checks */}
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center"><Activity className="w-5 h-5 mr-2 text-slate-500" /> Forensic Scope</h3>
                  <div className="flex flex-wrap gap-2">
                    {report.forensic_checks.map((check, i) => (
                      <span key={i} className={`px-3 py-1 text-xs font-medium rounded-full border ${check.status === 'Clean' || check.status === 'Checked' ? 'bg-slate-50 border-slate-200 text-slate-600' : 'bg-amber-50 border-amber-200 text-amber-700'}`}>
                        {check.status === 'Flagged' ? '⚠ ' : '✓ '}
                        {check.check}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Findings List */}
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-4 flex items-center"><Shield className="w-5 h-5 mr-2 text-slate-500" /> Forensic Findings</h3>
                  {report.findings.length === 0 ? (
                    <div className="p-6 bg-slate-50 border border-slate-200 rounded-xl text-center text-slate-500">
                      No suspicious indicators were detected during the available static analysis.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {report.findings.map((finding, idx) => (
                        <div key={idx} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
                          <div className="flex items-start">
                            <div className="mt-0.5 mr-3 flex-shrink-0">
                              {getSeverityIcon(finding.severity)}
                            </div>
                            <div className="flex-1">
                              <div className="flex justify-between items-start mb-2">
                                <h4 className="font-bold text-slate-900">{finding.finding}</h4>
                                <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getSeverityColor(finding.severity)}`}>
                                  {finding.severity}
                                </span>
                              </div>
                              <p className="text-sm text-slate-600 mb-3">{finding.description}</p>
                              <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 text-sm space-y-2">
                                <div className="grid grid-cols-[100px_1fr] gap-2">
                                  <span className="text-slate-400 font-medium text-xs uppercase">Evidence</span>
                                  <span className="text-slate-800 font-mono text-xs break-all">{finding.evidence}</span>
                                </div>
                                <div className="grid grid-cols-[100px_1fr] gap-2">
                                  <span className="text-slate-400 font-medium text-xs uppercase">Action</span>
                                  <span className="text-slate-800 text-xs">{finding.recommendation}</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex justify-end pt-6 border-t border-slate-200">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm"
                  >
                    Scan Another Document
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
