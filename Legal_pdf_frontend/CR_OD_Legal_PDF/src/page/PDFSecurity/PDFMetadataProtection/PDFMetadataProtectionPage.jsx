import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle2, ChevronRight, Shield, FileText, FileLock2, AlertTriangle, Download, Lock } from 'lucide-react';
import { getToolApiConfig } from '../../../config/toolApiConfig';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function PDFMetadataProtectionPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Phase 1: Analysis Result
  const [analysisResult, setAnalysisResult] = useState(null);
  
  // Phase 2: Protection State
  const [password, setPassword] = useState('');
  const [protecting, setProtecting] = useState(false);
  const [protectionResult, setProtectionResult] = useState(null);

  const fileInputRef = useRef(null);

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.type !== 'application/pdf') {
        setError('Only PDF files are supported.');
        return;
      }
      setFile(selected);
      setError('');
      setAnalysisResult(null);
      setProtectionResult(null);
      setPassword('');
      
      // Auto-analyze
      await analyzeFile(selected);
    }
  };

  const analyzeFile = async (selectedFile) => {
    setLoading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(`${API_BASE}/api/pdf/security/metadata-protection/analyze`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.detail || 'Failed to analyze document.');
      }
      
      setAnalysisResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred during analysis.');
      setFile(null); // Reset file so user can try again
    } finally {
      setLoading(false);
    }
  };

  const handleProtect = async () => {
    if (!file) return;
    setProtecting(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);
    if (password) {
      formData.append('password', password);
    }

    try {
      const response = await fetch(`${API_BASE}/api/pdf/security/metadata-protection`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.detail || 'Failed to protect document.');
      }
      
      setProtectionResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred during protection.');
    } finally {
      setProtecting(false);
    }
  };

  const handleDownload = () => {
    if (protectionResult && protectionResult.download_url) {
      window.location.href = `${API_BASE}${protectionResult.download_url}`;
    }
  };

  const resetAll = () => {
    setFile(null);
    setAnalysisResult(null);
    setProtectionResult(null);
    setPassword('');
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
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <FileLock2 className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'PDF Metadata Protection'}</h1>
                <p className="text-slate-500 mt-1">
                  Analyze, sanitize, and protect sensitive document metadata to prevent information leakage.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {/* STAGE 1: UPLOAD */}
            {!file && !loading && (
              <div className="space-y-6 max-w-2xl mx-auto">
                <div 
                  className="border-2 border-dashed rounded-xl p-8 text-center transition-colors border-slate-300 hover:border-slate-400 bg-slate-50 cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf"
                    className="hidden"
                  />
                  <div className="flex flex-col items-center">
                    <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-slate-400">
                      <Upload className="w-8 h-8" />
                    </div>
                    <p className="text-sm font-medium text-slate-700 mb-1">Click to upload or drag and drop</p>
                    <p className="text-xs text-slate-500">PDF files only</p>
                  </div>
                </div>
              </div>
            )}

            {/* STAGE 1.5: LOADING ANALYSIS */}
            {loading && (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                <p className="text-slate-600 font-medium">Analyzing PDF Metadata...</p>
              </div>
            )}

            {/* ERROR DISPLAY */}
            {error && (
              <div className="mb-6 bg-red-50 border border-red-200 text-red-600 p-4 rounded-lg flex items-start space-x-3 max-w-2xl mx-auto">
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <p className="text-sm">{error}</p>
              </div>
            )}

            {/* STAGE 2: ANALYSIS RESULT */}
            {analysisResult && !protectionResult && !loading && (
              <div className="space-y-8 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {analysisResult.metadata_present ? (
                  <>
                    <div className="flex flex-col items-center text-center space-y-3">
                      <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
                        <FileText className="w-8 h-8 text-blue-600" />
                      </div>
                      <h2 className="text-2xl font-bold text-slate-900">Metadata Detected</h2>
                      <p className="text-slate-600">
                        {analysisResult.metadata_count} metadata field(s) were found in this document.
                      </p>
                      <p className="text-xs text-slate-500 font-mono bg-slate-50 px-3 py-1 rounded">
                        File: {analysisResult.original_filename}
                      </p>
                    </div>

                    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                      <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex justify-between items-center">
                        <h3 className="font-semibold text-slate-800">Detected Metadata</h3>
                        <span className="text-xs font-bold bg-blue-100 text-blue-800 px-2.5 py-1 rounded-full">
                          {analysisResult.metadata_count} Fields
                        </span>
                      </div>
                      <div className="divide-y divide-slate-100">
                        {Object.entries(analysisResult.metadata || {}).map(([key, value]) => (
                          <div key={key} className="flex flex-col sm:flex-row sm:items-center px-6 py-3">
                            <span className="text-slate-500 font-medium sm:w-1/3 mb-1 sm:mb-0">{key}</span>
                            <span className="font-medium text-slate-900 sm:w-2/3 truncate" title={value}>{value}</span>
                          </div>
                        ))}
                        {analysisResult.xmp_present && (
                          <div className="flex flex-col sm:flex-row sm:items-center px-6 py-3 bg-amber-50/50">
                            <span className="text-amber-700 font-medium sm:w-1/3 mb-1 sm:mb-0">XMP Metadata</span>
                            <span className="font-bold text-amber-800 sm:w-2/3 flex items-center">
                              <AlertTriangle className="w-4 h-4 mr-1.5" /> Present
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="bg-slate-50 border border-slate-200 p-6 rounded-xl">
                      <h3 className="font-bold text-slate-800 mb-4 flex items-center">
                        <Lock className="w-5 h-5 mr-2 text-slate-500" /> Optional: Lock Document
                      </h3>
                      <p className="text-sm text-slate-600 mb-4">
                        Provide an owner password to encrypt the PDF and restrict modification permissions. This prevents unauthorized users from altering the metadata again.
                      </p>
                      <input
                        type="password"
                        placeholder="Enter Owner Password (Optional)"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>

                    <div className="flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-3 pt-4">
                      <button
                        onClick={resetAll}
                        className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors w-full sm:w-auto"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleProtect}
                        disabled={protecting}
                        className={`px-8 py-3 rounded-xl font-medium flex items-center justify-center space-x-2 transition-all w-full sm:w-auto ${protecting ? 'bg-blue-400 text-white cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow'}`}
                      >
                        {protecting ? (
                          <>
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            <span>Protecting...</span>
                          </>
                        ) : (
                          <>
                            <FileLock2 className="w-5 h-5" />
                            <span>Sanitize & Protect</span>
                          </>
                        )}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-col items-center text-center space-y-4 py-8">
                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center">
                      <AlertCircle className="w-8 h-8 text-slate-500" />
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900">No Metadata Found</h2>
                    <p className="text-slate-600 max-w-md">
                      No meaningful PDF metadata or XMP data was detected in this document. There is no metadata available to protect.
                    </p>
                    <p className="text-xs text-slate-500 font-mono bg-slate-50 px-3 py-1 rounded">
                      File: {analysisResult.original_filename}
                    </p>
                    <button
                      onClick={resetAll}
                      className="mt-6 px-6 py-3 bg-blue-50 text-blue-700 hover:bg-blue-100 font-medium rounded-xl transition-colors"
                    >
                      Scan Another File
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* STAGE 3: PROTECTION RESULT */}
            {protectionResult && (
              <div className="space-y-8 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex flex-col items-center text-center space-y-3 mb-8">
                  <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                  </div>
                  <h2 className="text-2xl font-bold text-slate-900">Metadata Protection Complete</h2>
                  <p className="text-slate-600">The PDF has been sanitized and successfully verified.</p>
                </div>

                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
                    <h3 className="font-semibold text-slate-800">Verification Report</h3>
                  </div>
                  <div className="divide-y divide-slate-100">
                    <div className="flex justify-between items-center px-6 py-4">
                      <span className="text-slate-600">Original Metadata Fields</span>
                      <span className="font-medium text-slate-900">{protectionResult.original_analysis?.metadata_count || 0}</span>
                    </div>
                    <div className="flex justify-between items-center px-6 py-4">
                      <span className="text-slate-600">Original XMP Metadata</span>
                      <span className="font-medium text-slate-900">{protectionResult.original_analysis?.xmp_present ? 'Present' : 'None'}</span>
                    </div>
                    <div className="flex justify-between items-center px-6 py-4">
                      <span className="text-slate-600">Processed Status</span>
                      <span className="font-medium text-emerald-600 flex items-center">
                        <CheckCircle2 className="w-4 h-4 mr-1.5" /> Cleared
                      </span>
                    </div>
                  </div>
                </div>

                {protectionResult.verification_passed ? (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 flex items-start space-x-4">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-emerald-900 font-semibold mb-1">Verification Passed</h4>
                      <p className="text-emerald-700 text-sm">
                        The generated PDF was re-analyzed. Sensitive metadata and XMP data have been successfully removed.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-start space-x-4">
                    <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-amber-900 font-semibold mb-1">Verification Warning</h4>
                      <p className="text-amber-800 text-sm">
                        The PDF was processed, but re-analysis detected that some metadata structure still remains.
                      </p>
                    </div>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-3 pt-6 border-t border-slate-200">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm w-full sm:w-auto"
                  >
                    Process Another File
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-8 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-xl transition-all shadow-sm hover:shadow flex items-center justify-center space-x-2 w-full sm:w-auto"
                  >
                    <Download className="w-5 h-5" />
                    <span>Download Protected PDF</span>
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
