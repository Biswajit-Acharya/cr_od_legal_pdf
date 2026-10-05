import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, CheckCircle2, ChevronRight, Shield, FileText, Code2, AlertTriangle, List, Check, Download } from 'lucide-react';
import { getToolApiConfig } from '../../../config/toolApiConfig';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function RemoveJavaScriptPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const apiConfig = getToolApiConfig('Remove JavaScript') || { endpoint: '/api/pdf/security/remove-javascript' };

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
      const response = await fetch(`${API_BASE}${apiConfig.endpoint}`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.detail || 'Failed to process document.');
      }
      
      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred during sanitization.');
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
              <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center">
                <Code2 className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'Remove JavaScript'}</h1>
                <p className="text-slate-500 mt-1">
                  Securely neutralize embedded JavaScript and prevent script execution attacks.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {!result ? (
              <div className="space-y-6 max-w-2xl mx-auto">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${file ? 'border-amber-300 bg-amber-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
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
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-amber-600">
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

                <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl flex items-start space-x-3">
                   <Shield className="w-5 h-5 text-slate-500 flex-shrink-0 mt-0.5" />
                   <div>
                     <p className="text-sm text-slate-700 font-medium">Safe Processing Guarantee</p>
                     <p className="text-xs text-slate-500 mt-1">
                        Files are sanitized securely using object-level manipulation. We never execute the embedded code. Legitimate hyperlinks and content will be preserved.
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
                    className={`px-6 py-3 rounded-xl font-medium flex items-center space-x-2 transition-all ${!file || loading ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-amber-600 hover:bg-amber-700 text-white shadow-sm hover:shadow'}`}
                  >
                    {loading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Scanning & Sanitizing...</span>
                      </>
                    ) : (
                      <>
                        <Code2 className="w-5 h-5" />
                        <span>Remove JavaScript</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-6 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Result Header */}
                {result.javascript_count === 0 ? (
                  <div className="flex flex-col items-center text-center space-y-3 mb-8">
                    <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                      <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900">PDF Scan Complete</h2>
                    <p className="text-slate-600">No embedded JavaScript was detected in this PDF.</p>
                  </div>
                ) : (
                  (result.removed_count < result.javascript_count || !result.verification_passed) ? (
                    <div className="flex flex-col items-center text-center space-y-3 mb-8">
                      <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center">
                        <AlertTriangle className="w-8 h-8 text-amber-600" />
                      </div>
                      <h2 className="text-2xl font-bold text-amber-900">JavaScript Removal Requires Attention</h2>
                      <p className="text-amber-800">JavaScript was detected, but the cleaned PDF could not be fully verified.</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center text-center space-y-3 mb-8">
                      <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                        <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                      </div>
                      <h2 className="text-2xl font-bold text-slate-900">JavaScript Removed Successfully</h2>
                      <p className="text-slate-600">Your PDF has been cleaned and independently verified.</p>
                    </div>
                  )
                )}

                {/* Security Summary Table */}
                <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                  <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
                    <h3 className="font-semibold text-slate-800">Security Scan</h3>
                  </div>
                  <div className="divide-y divide-slate-100">
                    <div className="flex justify-between items-center px-6 py-3">
                      <span className="text-slate-600">JavaScript Detected</span>
                      <span className="font-medium text-slate-900">{result.javascript_count}</span>
                    </div>
                    <div className="flex justify-between items-center px-6 py-3">
                      <span className="text-slate-600">JavaScript Removed</span>
                      <span className="font-medium text-slate-900">{result.removed_count}</span>
                    </div>
                    {result.javascript_count > 0 && (
                      <div className="flex justify-between items-center px-6 py-3">
                        <span className="text-slate-600">Remaining JavaScript</span>
                        <span className={`font-medium ${result.javascript_count - result.removed_count > 0 ? 'text-red-600' : 'text-slate-900'}`}>
                          {result.javascript_count - result.removed_count}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between items-center px-6 py-3">
                      <span className="text-slate-600">Verification</span>
                      <span className={`font-medium flex items-center ${result.verification_passed ? 'text-emerald-600' : 'text-red-600'}`}>
                        {result.verification_passed ? <><CheckCircle2 className="w-4 h-4 mr-1.5" /> Passed</> : <><AlertTriangle className="w-4 h-4 mr-1.5" /> Failed</>}
                      </span>
                    </div>
                    {result.javascript_count > 0 && (
                      <div className="flex justify-between items-center px-6 py-3">
                        <span className="text-slate-600">Pages Preserved</span>
                        <span className={`font-medium flex items-center ${result.pages_preserved ? 'text-emerald-600' : 'text-amber-600'}`}>
                          {result.pages_preserved ? <><CheckCircle2 className="w-4 h-4 mr-1.5" /> Yes</> : <><AlertTriangle className="w-4 h-4 mr-1.5" /> No</>}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between items-center px-6 py-3">
                      <span className="text-slate-600">Digital Signature</span>
                      <span className={`font-medium ${result.digital_signature_detected ? 'text-amber-600' : 'text-slate-500'}`}>
                        {result.digital_signature_detected ? 'Detected' : 'Not Detected'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Detected Locations */}
                {result.javascript_count > 0 && (
                  <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                    <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
                      <h3 className="font-semibold text-slate-800">Detected JavaScript</h3>
                    </div>
                    <div className="px-6 py-4">
                      {result.javascript_locations && result.javascript_locations.length > 0 ? (
                        <ul className="space-y-2">
                          {result.javascript_locations.map((loc, idx) => (
                            <li key={idx} className="flex items-center text-slate-700">
                              <span className="w-1.5 h-1.5 bg-amber-500 rounded-full mr-3"></span>
                              {loc}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-slate-500 italic">No embedded JavaScript locations were detected.</p>
                      )}
                    </div>
                  </div>
                )}

                {/* Verification Message */}
                {result.javascript_count > 0 && result.verification_passed && result.removed_count >= result.javascript_count && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 flex items-start space-x-4">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-emerald-900 font-semibold mb-1">Verification Passed</h4>
                      <p className="text-emerald-700 text-sm">
                        The sanitized PDF was scanned again after processing. No embedded JavaScript remains in the cleaned document.
                      </p>
                    </div>
                  </div>
                )}

                {/* Signature Warning */}
                {result.digital_signature_detected && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-start space-x-4">
                    <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-amber-900 font-semibold mb-1">Digital Signature Detected</h4>
                      <p className="text-amber-800 text-sm">
                        Modifying a digitally signed PDF may invalidate its existing cryptographic signature. The document should be re-verified after sanitization.
                      </p>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-3 pt-6 border-t border-slate-200">
                  <button
                    onClick={() => {
                      setResult(null);
                      setFile(null);
                    }}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm w-full sm:w-auto"
                  >
                    Scan Another File
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-6 py-3 bg-amber-600 hover:bg-amber-700 text-white font-medium rounded-xl transition-all shadow-sm hover:shadow flex items-center justify-center space-x-2 w-full sm:w-auto"
                  >
                    <Download className="w-5 h-5" />
                    <span>Download Clean PDF</span>
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
