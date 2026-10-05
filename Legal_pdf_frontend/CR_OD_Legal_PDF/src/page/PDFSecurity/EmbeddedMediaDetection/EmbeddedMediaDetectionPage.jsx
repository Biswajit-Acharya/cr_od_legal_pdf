import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, FileText, Activity, ImageIcon, PlaySquare, FileCheck, ChevronRight, Hash } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function EmbeddedMediaDetectionPage({ tool, onBack }) {
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
      const response = await fetch(`${API_BASE}/api/pdf/security/embedded-media`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to detect media.');
      }
      
      setReport(data);
      setViewState('report');
    } catch (err) {
      setError(err.message || 'An error occurred during media detection.');
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
              <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
                <ImageIcon className="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'Embedded Media Detection'}</h1>
                <p className="text-slate-500 mt-1">
                  Inspect the PDF for hidden media files, images, attachments, and multimedia annotations.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {/* UPLOAD STATE */}
            {viewState === 'upload' && (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
                  onClick={() => !file && fileInputRef.current?.click()}
                >
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf" className="hidden" />
                  
                  {file ? (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-indigo-600">
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
                      <p className="text-sm font-medium text-slate-700 mb-1">Upload PDF for Media Scan</p>
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
                    className={`px-8 py-3 rounded-xl font-medium flex items-center transition-all ${!file ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'}`}
                  >
                    Scan Media
                  </button>
                </div>
              </div>
            )}

            {/* ANALYZING STATE */}
            {viewState === 'analyzing' && (
              <div className="flex flex-col items-center justify-center py-16 space-y-6">
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-indigo-100 rounded-full"></div>
                  <div className="w-20 h-20 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
                  <Activity className="w-8 h-8 text-indigo-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800">Scanning for Embedded Content...</h3>
              </div>
            )}

            {/* REPORT STATE */}
            {viewState === 'report' && report && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Header Status */}
                <div className="flex justify-between items-center border-b border-slate-200 pb-4">
                  <h2 className="text-xl font-bold text-slate-900">Embedded Media Detection</h2>
                  <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-bold rounded-full uppercase tracking-wide">
                    Scan Completed
                  </span>
                </div>

                {/* Security Assessment */}
                <div className={`p-5 rounded-xl border flex items-center space-x-3 ${report.security_assessment.includes('No suspicious') ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-amber-50 border-amber-200 text-amber-800'}`}>
                  <AlertCircle className={`w-6 h-6 flex-shrink-0 ${report.security_assessment.includes('No suspicious') ? 'text-emerald-600' : 'text-amber-600'}`} />
                  <div>
                    <h4 className="font-bold mb-1">Security Assessment</h4>
                    <p className="text-sm">{report.security_assessment}</p>
                  </div>
                </div>

                {/* Summary Cards */}
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-4">Media Summary</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                      <span className="block text-2xl font-bold text-slate-800">{report.summary.Images}</span>
                      <span className="text-xs text-slate-500 font-medium uppercase mt-1 block">Images</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                      <span className="block text-2xl font-bold text-slate-800">{report.summary["Embedded files"]}</span>
                      <span className="text-xs text-slate-500 font-medium uppercase mt-1 block">Files</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                      <span className="block text-2xl font-bold text-slate-800">{report.summary["Multimedia annotations"]}</span>
                      <span className="text-xs text-slate-500 font-medium uppercase mt-1 block">Annotations</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-center">
                      <span className="block text-2xl font-bold text-slate-800">{report.summary.Audio + report.summary.Video}</span>
                      <span className="text-xs text-slate-500 font-medium uppercase mt-1 block">A/V Objects</span>
                    </div>
                  </div>
                </div>

                {/* Findings Table */}
                <div>
                  <h3 className="text-lg font-bold text-slate-900 mb-4">Media Findings</h3>
                  {report.findings.length === 0 ? (
                    <div className="p-6 bg-slate-50 border border-slate-200 rounded-xl text-center text-slate-500">
                      No media objects found in this document.
                    </div>
                  ) : (
                    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                              <th className="py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Type</th>
                              <th className="py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Location</th>
                              <th className="py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Details</th>
                              <th className="py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wider">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {report.findings.map((finding, idx) => (
                              <tr key={idx} className="hover:bg-slate-50 transition-colors">
                                <td className="py-3 px-4">
                                  <div className="flex items-center">
                                    {finding.Type === 'Image' ? <ImageIcon className="w-4 h-4 text-slate-400 mr-2" /> : 
                                     finding.Type === 'Embedded File' ? <FileCheck className="w-4 h-4 text-amber-500 mr-2" /> : 
                                     <PlaySquare className="w-4 h-4 text-blue-500 mr-2" />}
                                    <span className="text-sm font-medium text-slate-800">{finding.Type}</span>
                                  </div>
                                </td>
                                <td className="py-3 px-4 text-sm text-slate-600">
                                  {finding.Location_Page.includes('Document') ? finding.Location_Page : `Page ${finding.Location_Page}`}
                                </td>
                                <td className="py-3 px-4 text-sm text-slate-600 font-mono text-xs">
                                  {finding.Filename || finding.Object}<br/>
                                  <span className="text-slate-400">{finding.Size}</span>
                                </td>
                                <td className="py-3 px-4">
                                  <span className={`text-xs font-semibold px-2 py-1 rounded-full ${finding.Status === 'Review Required' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'}`}>
                                    {finding.Status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {report.summary.Images > 25 && (
                         <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 text-center">
                           Note: Only the first 25 image references are displayed in this table to preserve performance.
                         </div>
                      )}
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
