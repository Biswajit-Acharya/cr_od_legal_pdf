import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, FileText, Activity, ShieldCheck, ShieldAlert, BadgeCheck, CheckCircle2, ChevronRight, Hash, User, Building, Calendar, FileKey, XCircle } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || 'http://localhost:8002';

export default function TrustedCertificatesPage({ tool, onBack }) {
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
      const response = await fetch(`${API_BASE}/api/pdf/security/trusted-certificates`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to validate certificates.');
      }
      
      setReport(data);
      setViewState('report');
    } catch (err) {
      setError(err.message || 'An error occurred during cryptographic validation.');
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
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <BadgeCheck className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">{tool?.name || 'Trusted Certificates'}</h1>
                <p className="text-slate-500 mt-1">
                  Cryptographically validate digital signatures and extract X.509 certificate chains.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {/* UPLOAD STATE */}
            {viewState === 'upload' && (
              <div className="space-y-6 max-w-2xl mx-auto animate-in fade-in">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-blue-300 bg-blue-50' : 'border-slate-300 hover:border-slate-400 bg-slate-50'}`}
                  onClick={() => !file && fileInputRef.current?.click()}
                >
                  <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".pdf" className="hidden" />
                  
                  {file ? (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-full shadow-sm flex items-center justify-center mb-4 text-blue-600">
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
                      <p className="text-sm font-medium text-slate-700 mb-1">Upload PDF to Validate Certificates</p>
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
                    className={`px-8 py-3 rounded-xl font-medium flex items-center transition-all ${!file ? 'bg-slate-100 text-slate-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm'}`}
                  >
                    Validate Signatures
                  </button>
                </div>
              </div>
            )}

            {/* ANALYZING STATE */}
            {viewState === 'analyzing' && (
              <div className="flex flex-col items-center justify-center py-16 space-y-6">
                <div className="relative">
                  <div className="w-20 h-20 border-4 border-blue-100 rounded-full"></div>
                  <div className="w-20 h-20 border-4 border-blue-600 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
                  <Activity className="w-8 h-8 text-blue-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-semibold text-slate-800">Performing Cryptographic Validation...</h3>
              </div>
            )}

            {/* REPORT STATE */}
            {viewState === 'report' && report && (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* Header Assessment */}
                <div className={`p-6 rounded-2xl border flex items-center space-x-4 ${report.overall_status === 'Trusted' ? 'bg-emerald-50 border-emerald-200' : report.overall_status === 'No Digital Signature Found' ? 'bg-slate-50 border-slate-200' : 'bg-amber-50 border-amber-200'}`}>
                  {report.overall_status === 'Trusted' ? (
                    <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <ShieldCheck className="w-8 h-8 text-emerald-600" />
                    </div>
                  ) : report.overall_status === 'No Digital Signature Found' ? (
                    <div className="w-14 h-14 bg-slate-200 rounded-full flex items-center justify-center flex-shrink-0">
                      <AlertCircle className="w-8 h-8 text-slate-600" />
                    </div>
                  ) : (
                    <div className="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <ShieldAlert className="w-8 h-8 text-amber-600" />
                    </div>
                  )}
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">{report.overall_status}</h2>
                    <p className="text-sm mt-1 text-slate-700">{report.validation_summary}</p>
                  </div>
                </div>

                {report.signature_count > 0 && (
                  <div className="space-y-6">
                    {report.signatures.map((sig, idx) => (
                      <div key={idx} className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                        <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex justify-between items-center">
                          <h3 className="font-bold text-slate-800 flex items-center">
                            <BadgeCheck className="w-5 h-5 mr-2 text-slate-500" />
                            Signature {idx + 1}
                          </h3>
                          <span className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full ${sig.signature_status === 'Cryptographically Valid' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {sig.signature_status}
                          </span>
                        </div>
                        
                        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                          
                          {/* Signer Info */}
                          <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center"><User className="w-4 h-4 mr-2" /> Signer</h4>
                            <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                              <p className="font-medium text-slate-800">{sig.signer.Name || 'Unknown'}</p>
                              {sig.signer.CN && <p className="text-sm text-slate-500 mt-1">CN: {sig.signer.CN}</p>}
                              {sig.signer.O && <p className="text-sm text-slate-500">Org: {sig.signer.O}</p>}
                            </div>
                          </div>

                          {/* Issuer Info */}
                          <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center"><Building className="w-4 h-4 mr-2" /> Issuer (CA)</h4>
                            <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
                              <p className="font-medium text-slate-800">{sig.issuer.Name || 'Unknown'}</p>
                            </div>
                          </div>

                          {/* Validity Info */}
                          <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center"><Calendar className="w-4 h-4 mr-2" /> Validity Period</h4>
                            <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 space-y-2 text-sm">
                              <div className="flex justify-between border-b border-slate-200 pb-2">
                                <span className="text-slate-500">Status</span>
                                <span className={`font-semibold ${sig.validity.status === 'Valid' ? 'text-green-600' : 'text-red-600'}`}>{sig.validity.status}</span>
                              </div>
                              <div className="flex justify-between border-b border-slate-200 pb-2">
                                <span className="text-slate-500">Not Before</span>
                                <span className="text-slate-800">{sig.validity.not_before}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Not After</span>
                                <span className="text-slate-800">{sig.validity.not_after}</span>
                              </div>
                            </div>
                          </div>

                          {/* Cryptographic Details */}
                          <div className="space-y-4">
                            <h4 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center"><FileKey className="w-4 h-4 mr-2" /> Technical Info</h4>
                            <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 space-y-2 text-sm">
                              <div className="flex justify-between border-b border-slate-200 pb-2">
                                <span className="text-slate-500">Serial No</span>
                                <span className="text-slate-800 font-mono text-xs">{sig.certificate.serial_number}</span>
                              </div>
                              <div className="flex justify-between border-b border-slate-200 pb-2">
                                <span className="text-slate-500">Algorithm</span>
                                <span className="text-slate-800">{sig.certificate.signature_algorithm}</span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-slate-500">Public Key</span>
                                <span className="text-slate-800">{sig.certificate.public_key_algorithm}</span>
                              </div>
                            </div>
                          </div>
                          
                        </div>
                        
                        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 space-y-3">
                            <div className="flex items-start">
                              {sig.integrity.includes('Valid') ? <CheckCircle2 className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" /> : <XCircle className="w-5 h-5 text-red-500 mr-2 flex-shrink-0" />}
                              <div>
                                <h4 className="text-sm font-bold text-slate-800">Document Integrity</h4>
                                <p className="text-xs text-slate-500">{sig.integrity}</p>
                              </div>
                            </div>
                            <div className="flex items-start">
                              {sig.trust === 'Trusted' ? <CheckCircle2 className="w-5 h-5 text-green-500 mr-2 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 text-amber-500 mr-2 flex-shrink-0" />}
                              <div>
                                <h4 className="text-sm font-bold text-slate-800">Trust Chain</h4>
                                <p className="text-xs text-slate-500">{sig.trust}</p>
                              </div>
                            </div>
                            <div className="flex items-start">
                              <AlertCircle className="w-5 h-5 text-slate-400 mr-2 flex-shrink-0" />
                              <div>
                                <h4 className="text-sm font-bold text-slate-800">Revocation</h4>
                                <p className="text-xs text-slate-500">{sig.revocation}</p>
                              </div>
                            </div>
                        </div>

                      </div>
                    ))}
                  </div>
                )}

                <div className="flex justify-end pt-6 border-t border-slate-200">
                  <button
                    onClick={resetAll}
                    className="px-6 py-3 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium rounded-xl transition-colors shadow-sm"
                  >
                    Validate Another Document
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
