import React, { useState, useRef } from 'react';
import { Upload, AlertCircle, ShieldAlert, CheckCircle2, ChevronRight, FileText, Activity, ShieldCheck, Download, AlertTriangle } from 'lucide-react';
import { getToolApiConfig } from '../../../config/toolApiConfig';

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function AISecurityRiskDetectionPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  const toolName = tool?.name || 'AI Security Risk Detection';
  const apiConfig = getToolApiConfig(toolName) || { endpoint: '/api/pdf/security/ai-security-risk-detection' };

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
      
      if (!response.ok || data.success === false) {
        throw new Error(data.error || data.detail || 'Analysis failed.');
      }
      
      setResult(data);
    } catch (err) {
      setError(err.message || 'An error occurred during analysis. We could not complete the security analysis for this PDF.');
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (risk) => {
    const r = (risk || '').toUpperCase();
    if (r.includes('CRITICAL')) return 'text-red-700 bg-red-100 border-red-200';
    if (r.includes('HIGH')) return 'text-orange-700 bg-orange-100 border-orange-200';
    if (r.includes('MEDIUM')) return 'text-amber-700 bg-amber-100 border-amber-200';
    if (r.includes('LOW')) return 'text-blue-700 bg-blue-100 border-blue-200';
    if (r.includes('INFORMATIONAL')) return 'text-slate-700 bg-slate-100 border-slate-200';
    return 'text-emerald-700 bg-emerald-100 border-emerald-200'; // Secure
  };

  const getPriorityColor = (priority) => {
    const p = (priority || '').toLowerCase();
    if (p === 'critical') return 'text-red-600';
    if (p === 'high') return 'text-orange-600';
    if (p === 'medium') return 'text-amber-600';
    if (p === 'low') return 'text-blue-600';
    return 'text-slate-600';
  };

  // Calculate metrics
  const getMetrics = () => {
    const metrics = { Critical: 0, High: 0, Medium: 0, Low: 0, Informational: 0 };
    if (result?.findings) {
      result.findings.forEach(f => {
        const sev = (f.severity || '').toUpperCase();
        if (sev === 'CRITICAL') metrics.Critical++;
        else if (sev === 'HIGH') metrics.High++;
        else if (sev === 'MEDIUM') metrics.Medium++;
        else if (sev === 'LOW') metrics.Low++;
        else metrics.Informational++;
      });
    }
    return metrics;
  };

  const metrics = result ? getMetrics() : null;

  const handleDownloadReport = () => {
    if (!result) return;
    
    // Create a beautiful text/markdown report for download
    const reportText = `
==================================================
AI SECURITY RISK DETECTION REPORT
==================================================
File: ${result.filename || file?.name || 'Unknown'}
Date: ${new Date().toLocaleString()}
Status: ${result.overall_risk || 'Review Recommended'}
Score: ${result.risk_score || 'N/A'}

=== SECURITY OVERVIEW ===
Critical Risks: ${metrics.Critical}
High Risks: ${metrics.High}
Medium Risks: ${metrics.Medium}
Low Risks: ${metrics.Low}
Informational: ${metrics.Informational}

=== DETECTED RISKS ===
${result.findings && result.findings.length > 0 ? result.findings.map(f => `
[${f.severity || 'INFO'}] ${f.title}
Category: ${f.category || 'General'}
Detected: ${f.description || ''}
Evidence: ${f.evidence || ''}
Recommendation: ${f.recommendation || ''}
`).join('\n') : 'No significant security risks detected.'}

=== AI SECURITY RECOMMENDATIONS ===
${result.recommendations && result.recommendations.length > 0 ? result.recommendations.map(r => {
  if (typeof r === 'string') return `- ${r}`;
  return `
[Priority: ${r.priority || 'Medium'}] ${r.title || 'Recommendation'}
Why: ${r.description || ''}
Impact: ${r.impact || ''}
Action: ${r.implementation || ''}
`;
}).join('\n') : 'No recommendations available.'}
==================================================
    `.trim();

    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security_report_${(result.filename || 'report').replace('.pdf', '')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-[#f8faf7] p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        <button
          onClick={onBack}
          className="mb-6 flex items-center text-slate-500 hover:text-slate-700 transition-colors font-medium text-sm"
        >
          <ChevronRight className="w-4 h-4 rotate-180 mr-1" />
          Back to PDF Security
        </button>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-6 sm:p-8 border-b border-slate-100">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                <ShieldAlert className="w-6 h-6 text-[#1e2a52]" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-[#1e2a52]">{toolName}</h1>
                <p className="text-slate-500 mt-1 text-sm">
                  Upload a PDF to intelligently analyze its structure and content for security risks and AI recommendations.
                </p>
              </div>
            </div>
          </div>

          <div className="p-6 sm:p-8">
            {!result ? (
              <div className="space-y-6">
                <div 
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${file ? 'border-[#1e2a52] bg-[#f8faf7]' : 'border-slate-300 hover:border-[#1e2a52] bg-slate-50 hover:bg-[#f8faf7]'}`}
                  onClick={() => !loading && fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (!loading && e.dataTransfer.files && e.dataTransfer.files[0]) {
                      const selected = e.dataTransfer.files[0];
                      if (selected.type === 'application/pdf') {
                        setFile(selected);
                        setError('');
                        setResult(null);
                      } else {
                        setError('Only PDF files are supported.');
                      }
                    }
                  }}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf"
                    className="hidden"
                    disabled={loading}
                  />
                  
                  {file ? (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-white rounded-2xl shadow-sm flex items-center justify-center mb-4 text-[#1e2a52] border border-slate-100">
                        <FileText className="w-8 h-8" />
                      </div>
                      <p className="text-base font-bold text-slate-800 mb-1">{file.name}</p>
                      <p className="text-xs font-semibold text-slate-500 mb-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                      {!loading && (
                        <button
                          onClick={(e) => { e.stopPropagation(); setFile(null); }}
                          className="text-xs uppercase tracking-wider font-bold text-red-500 hover:text-red-700 bg-red-50 px-3 py-1.5 rounded-lg"
                        >
                          Remove file
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <div className="w-16 h-16 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mb-4 text-[#1e2a52]">
                        <Upload className="w-8 h-8" />
                      </div>
                      <p className="text-base font-bold text-slate-800 mb-1">Click to upload or drag and drop</p>
                      <p className="text-sm font-medium text-slate-500">PDF files only</p>
                    </div>
                  )}
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl flex items-start space-x-3">
                    <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-bold">Security Analysis Failed</h4>
                      <p className="text-sm mt-0.5">{error}</p>
                    </div>
                  </div>
                )}

                <div className="flex justify-end pt-4">
                  <button
                    onClick={handleAnalyze}
                    disabled={!file || loading}
                    className={`px-8 py-3.5 rounded-full font-bold flex items-center space-x-2 transition-all shadow-md ${!file || loading ? 'bg-slate-200 text-slate-500 cursor-not-allowed shadow-none' : 'bg-[#1e2a52] hover:bg-blue-900 text-white hover:-translate-y-0.5'}`}
                  >
                    {loading ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Analyzing PDF Security...</span>
                      </>
                    ) : (
                      <>
                        <Activity className="w-5 h-5" />
                        <span>Analyze PDF</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                
                {/* 1. Header & Overview */}
                <div className="text-center space-y-3 mb-8 pb-8 border-b border-slate-100">
                  <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                  </div>
                  <h2 className="text-2xl font-black text-slate-900">✓ Security Analysis Complete</h2>
                  <p className="text-slate-600 font-medium">Your PDF has been analyzed for potential security risks.</p>
                  <p className="text-sm font-mono text-slate-500 bg-slate-50 inline-block px-3 py-1 rounded-md border border-slate-200">
                    {result.filename || file?.name || 'document.pdf'}
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Security Overview Card */}
                  <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200 flex flex-col">
                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">Security Overview</h3>
                    
                    <div className="mb-6 flex flex-col items-center justify-center py-4 rounded-xl bg-white border border-slate-100 shadow-sm">
                      <span className="text-xs font-bold text-slate-500 uppercase mb-1">Security Status</span>
                      <span className={`text-xl font-black px-4 py-1.5 rounded-lg border ${getRiskColor(result.overall_risk || (metrics.Critical > 0 ? 'CRITICAL' : metrics.High > 0 ? 'HIGH' : metrics.Medium > 0 ? 'MEDIUM' : 'LOW'))}`}>
                        {result.overall_risk || (metrics.Critical > 0 ? 'Review Recommended' : 'Low Risk')}
                      </span>
                    </div>

                    <div className="space-y-2 mt-auto">
                      <div className="flex justify-between items-center px-3 py-2 bg-white rounded-lg border border-slate-100">
                        <span className="text-sm font-medium text-slate-700">Critical Risks</span>
                        <span className="text-sm font-black text-red-600">{metrics.Critical}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-2 bg-white rounded-lg border border-slate-100">
                        <span className="text-sm font-medium text-slate-700">High Risks</span>
                        <span className="text-sm font-black text-orange-600">{metrics.High}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-2 bg-white rounded-lg border border-slate-100">
                        <span className="text-sm font-medium text-slate-700">Medium Risks</span>
                        <span className="text-sm font-black text-amber-600">{metrics.Medium}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-2 bg-white rounded-lg border border-slate-100">
                        <span className="text-sm font-medium text-slate-700">Low Risks</span>
                        <span className="text-sm font-black text-blue-600">{metrics.Low}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-2 bg-white rounded-lg border border-slate-100">
                        <span className="text-sm font-medium text-slate-700">Informational</span>
                        <span className="text-sm font-black text-slate-600">{metrics.Informational}</span>
                      </div>
                    </div>
                  </div>

                  {/* Security Checks Card */}
                  <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200">
                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">Security Checks</h3>
                    
                    <div className="divide-y divide-slate-100 bg-white rounded-xl border border-slate-100">
                      {[
                        { label: 'JavaScript', key: 'javascript' },
                        { label: 'External Links', key: 'external_links' },
                        { label: 'Embedded Files', key: 'embedded_files' },
                        { label: 'Launch Actions', key: 'launch_actions' },
                        { label: 'Forms', key: 'forms' },
                        { label: 'Encryption', key: 'encryption' },
                        { label: 'Digital Signature', key: 'digital_signature' },
                        { label: 'Metadata', key: 'metadata' }
                      ].map((check, idx) => {
                        const val = result.security_checks ? result.security_checks[check.key] : null;
                        let display = 'Not Checked';
                        let color = 'text-slate-500';
                        
                        if (val && val.status) {
                          const status = val.status.toLowerCase();
                          if (status === 'detected' || status === 'present' || status === 'enabled') {
                            display = val.count ? `${val.count} Detected` : status === 'present' ? 'Present' : status === 'enabled' ? 'Enabled' : 'Detected';
                            color = (status === 'enabled' || status === 'present' && check.key === 'digital_signature') ? 'text-blue-600 font-bold' : 'text-amber-600 font-bold';
                          } else if (status === 'not_detected' || status === 'not_present' || status === 'not_enabled') {
                            display = status === 'not_present' ? 'Not Present' : status === 'not_enabled' ? 'Not Enabled' : 'Not Detected';
                            color = 'text-emerald-600 font-medium';
                          } else if (status === 'unable_to_check') {
                            display = 'Unable to Check';
                            color = 'text-slate-400 font-medium italic';
                          } else if (status === 'not_checked') {
                            display = 'Not Checked';
                            color = 'text-slate-400 font-medium italic';
                          } else {
                            display = status;
                            color = 'text-slate-700 font-medium';
                          }
                          
                          if (val.details && display !== 'Unable to Check' && display !== 'Not Checked') {
                            // Optionally we can append details or keep it clean
                          }
                        }

                        return (
                          <div key={idx} className="flex justify-between items-center px-4 py-3">
                            <span className="text-sm font-medium text-slate-700">{check.label}</span>
                            <span className={`text-sm ${color}`}>{display}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* 3. Detected Security Risks */}
                <div>
                  <h3 className="text-xl font-black text-slate-900 mb-6 flex items-center gap-2">
                    <ShieldCheck className="w-6 h-6 text-[#1e2a52]" />
                    Detected Security Risks
                  </h3>
                  
                  {result.findings && result.findings.length > 0 ? (
                    <div className="space-y-4">
                      {result.findings.map((finding, idx) => (
                        <div key={idx} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                          <div className="flex items-start justify-between mb-4">
                            <h4 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                              {finding.severity === 'CRITICAL' || finding.severity === 'HIGH' ? (
                                <AlertTriangle className="w-5 h-5 text-red-600" />
                              ) : (
                                <AlertCircle className="w-5 h-5 text-amber-600" />
                              )}
                              {finding.title || finding.category}
                            </h4>
                            <span className={`px-3 py-1 text-xs font-bold rounded-lg border ${getRiskColor(finding.severity)}`}>
                              Severity: {finding.severity}
                            </span>
                          </div>
                          
                          <div className="space-y-4">
                            <div>
                              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">What was detected</span>
                              <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">{finding.description || finding.evidence || 'No details provided.'}</p>
                            </div>
                            
                            {finding.recommendation && (
                              <div>
                                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Recommendation</span>
                                <p className="text-sm text-slate-800 font-medium leading-relaxed bg-blue-50/50 p-3 rounded-lg border border-blue-100">{finding.recommendation}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-8 text-center">
                      <CheckCircle2 className="w-10 h-10 mx-auto mb-3 text-emerald-600" />
                      <h4 className="text-lg font-bold text-emerald-800 mb-2">✓ No Significant Security Risks Detected</h4>
                      <p className="text-sm text-emerald-700 font-medium">No significant security indicators were identified during the analysis.</p>
                    </div>
                  )}
                </div>

                {/* 4. AI Security Recommendations */}
                {result.recommendations && result.recommendations.length > 0 && (
                  <div>
                    <h3 className="text-xl font-black text-slate-900 mb-6 flex items-center gap-2">
                      <Activity className="w-6 h-6 text-[#1e2a52]" />
                      AI Security Recommendations
                    </h3>
                    
                    <div className="grid grid-cols-1 gap-4">
                      {result.recommendations.map((rec, idx) => {
                        // Handle simple string recommendations
                        if (typeof rec === 'string') {
                          return (
                            <div key={idx} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex items-start gap-3">
                              <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                                <span className="text-blue-600 font-bold text-sm">{idx + 1}</span>
                              </div>
                              <p className="text-sm font-medium text-slate-700 leading-relaxed pt-1">{rec}</p>
                            </div>
                          );
                        }
                        
                        // Handle structured recommendation objects
                        return (
                          <div key={idx} className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow">
                            <div className="flex items-start justify-between mb-4">
                              <h4 className="text-lg font-bold text-slate-900">{rec.title || `Recommendation ${idx + 1}`}</h4>
                              {rec.priority && (
                                <span className={`text-sm font-bold ${getPriorityColor(rec.priority)} bg-slate-50 px-3 py-1 rounded-lg border border-slate-100`}>
                                  Priority: <span className="capitalize">{rec.priority}</span>
                                </span>
                              )}
                            </div>
                            
                            <div className="space-y-4">
                              {rec.description && (
                                <div>
                                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Why this is recommended</span>
                                  <p className="text-sm text-slate-700 leading-relaxed">{rec.description}</p>
                                </div>
                              )}
                              
                              {rec.impact && (
                                <div>
                                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Security Impact</span>
                                  <p className="text-sm text-slate-700 leading-relaxed">{rec.impact}</p>
                                </div>
                              )}
                              
                              {rec.implementation && (
                                <div className="pt-2">
                                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Recommended Action</span>
                                  <p className="text-sm font-bold text-[#1e2a52] bg-blue-50 px-4 py-3 rounded-xl inline-block border border-blue-100">
                                    {rec.implementation.startsWith('/') ? 'Execute ' + rec.implementation.split('/').pop().replace('-', ' ') : rec.implementation}
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row items-center justify-between pt-8 border-t border-slate-200 mt-8 gap-4">
                  <button
                    onClick={handleDownloadReport}
                    className="w-full sm:w-auto px-6 py-3 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-bold rounded-full transition-colors flex items-center justify-center gap-2 border border-emerald-200"
                  >
                    <Download className="w-4 h-4" />
                    Download Report
                  </button>
                  
                  <button
                    onClick={() => {
                      setResult(null);
                      setFile(null);
                    }}
                    className="w-full sm:w-auto px-8 py-3 bg-[#1e2a52] hover:bg-blue-900 text-white font-bold rounded-full transition-colors"
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
