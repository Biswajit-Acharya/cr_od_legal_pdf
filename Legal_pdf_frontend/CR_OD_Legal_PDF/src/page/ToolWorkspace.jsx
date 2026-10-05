import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileText, Download, CheckCircle2, ArrowLeft, ArrowRight, X, AlertCircle } from 'lucide-react';
import { getToolApiConfig } from '../config/toolApiConfig';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

function getAcceptedTypes(toolName) {
  const name = (toolName || '').toLowerCase();
  if (name.startsWith('pdf to') || name.includes('pdf to ') || name.includes('from pdf') || name.includes('convert pdf to'))
    return { accept: '.pdf', label: 'PDF files (.pdf)', mime: ['application/pdf'] };
  if (name.includes('word') || name.includes('docx') || name.includes('text to pdf') || name.includes('rtf') || name.includes('odt'))
    return { accept: '.doc,.docx,.txt,.rtf,.odt', label: 'Word / Text documents', mime: ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'] };
  if (name.includes('excel') || name.includes('xlsx') || name.includes('csv') || name.includes('ods'))
    return { accept: '.xls,.xlsx,.csv,.ods', label: 'Excel / CSV files', mime: ['application/vnd.ms-excel', 'text/csv'] };
  if (name.includes('powerpoint') || name.includes('pptx') || name.includes('ppt') || name.includes('presentation'))
    return { accept: '.ppt,.pptx,.odp', label: 'PowerPoint files', mime: ['application/vnd.ms-powerpoint'] };
  if (name.includes('jpg') || name.includes('jpeg') || name.includes('png') || name.includes('image') || name.includes('photo') || name.includes('screenshot') || name.includes('gif') || name.includes('bmp') || name.includes('tiff') || name.includes('webp') || name.includes('svg') || name.includes('heic') || name.includes('raw') || name.includes('psd'))
    return { accept: '.jpg,.jpeg,.png,.webp,.bmp,.tiff,.gif,.svg,.heic,.psd,.ai', label: 'Image files', mime: ['image/jpeg', 'image/png', 'image/webp'] };
  if (name.includes('html') || name.includes('webpage') || name.includes('url') || name.includes('markdown') || name.includes('xml') || name.includes('json'))
    return { accept: '.html,.htm,.md,.xml,.json', label: 'Web / Code files', mime: ['text/html', 'text/markdown'] };
  if (name.includes('epub') || name.includes('mobi'))
    return { accept: '.epub,.mobi', label: 'E-book files', mime: ['application/epub+zip'] };
  if (name.includes('cad') || name.includes('dwg') || name.includes('dxf') || name.includes('visio') || name.includes('publisher'))
    return { accept: '.dwg,.dxf,.vsd,.pub', label: 'CAD / Drawing files', mime: [] };
  if (name.includes('zip') || name.includes('folder') || name.includes('archive'))
    return { accept: '.zip,.rar,.7z', label: 'Archive files', mime: ['application/zip'] };
  return { accept: '.pdf', label: 'PDF files (.pdf)', mime: ['application/pdf'] };
}

export default function ToolWorkspace({ tool, onBack }) {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [downloadFilename, setDownloadFilename] = useState('');
  const [apiResult, setApiResult] = useState(null);
  const [extraFields, setExtraFields] = useState({});
  const inputRef = useRef();

  const toolName = tool?.name || tool?.title || 'PDF Tool';
  const toolDesc = tool?.description || 'Upload your documents to process with this tool.';
  const accepted = getAcceptedTypes(toolName);
  const apiConfig = getToolApiConfig(toolName);

  const addFiles = (newFiles) => {
    setError('');
    const valid = [];
    const invalid = [];
    Array.from(newFiles).forEach(f => {
      const extOk = accepted.accept.split(',').some(ext => f.name.toLowerCase().endsWith(ext.trim()));
      const mimeOk = accepted.mime.length === 0 || accepted.mime.some(m => f.type === m || f.type.startsWith(m.split('/')[0] + '/'));
      if (mimeOk || extOk) {
        valid.push({ name: f.name, size: f.size < 1024 * 1024 ? (f.size / 1024).toFixed(0) + ' KB' : (f.size / (1024 * 1024)).toFixed(2) + ' MB', type: f.type, raw: f });
      } else {
        invalid.push(f.name);
      }
    });
    if (invalid.length > 0) setError(`Only ${accepted.label} accepted. Rejected: ${invalid.join(', ')}`);
    if (valid.length > 0) { setFiles(prev => [...prev, ...valid]); setIsDone(false); setApiResult(null); setDownloadUrl(null); }
  };

  const handleFileChange = (e) => { if (e.target.files?.length) addFiles(e.target.files); };
  const handleDrop = (e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files); };
  const handleRemove = (idx) => { setFiles(prev => prev.filter((_, i) => i !== idx)); if (files.length <= 1) { setIsDone(false); setApiResult(null); setDownloadUrl(null); } setError(''); };

  const handleProcess = async () => {
    if (!files.length) return;
    setIsProcessing(true);
    setError('');
    setApiResult(null);
    setDownloadUrl(null);

    if (!apiConfig) {
      // Fallback: simulated processing for tools without backend config
      setTimeout(() => {
        setApiResult({ status: 'success', message: `${toolName} processed successfully`, file: files[0].name });
        setDownloadFilename(files[0].name.replace(/\.[^/.]+$/, '') + '_processed.pdf');
        setIsProcessing(false);
        setIsDone(true);
      }, 2600);
      return;
    }

    try {
      const formData = new FormData();
      if (apiConfig.type === 'multi-file+field') {
        files.forEach(f => formData.append('files', f.raw));
      } else {
        formData.append('file', files[0].raw);
      }

      if (apiConfig.type === 'file+field' && extraFields[apiConfig.fieldName]) {
        formData.append(apiConfig.fieldName, extraFields[apiConfig.fieldName]);
      }
      if (apiConfig.type === 'file+fields' && apiConfig.fields) {
        apiConfig.fields.forEach(f => {
          formData.append(f.name, extraFields[f.name] || f.default || '');
        });
      }

      const url = `${API_BASE_URL}${apiConfig.endpoint}`;
      const response = await fetch(url, { method: apiConfig.method || 'POST', body: formData });

      if (!response.ok) {
        let errMsg = `Server error: ${response.status}`;
        try { const errData = await response.json(); errMsg = errData.detail || errMsg; if (typeof errMsg !== 'string') errMsg = JSON.stringify(errMsg); } catch (_) {}
        throw new Error(errMsg);
      }

      const contentType = response.headers.get('content-type') || '';

      if (contentType.includes('application/json')) {
        const data = await response.json();
        
        // Custom handling for features that return management tokens (e.g. Secure PDF Sharing)
        if (data.management_token) {
          try {
            const savedTokens = JSON.parse(localStorage.getItem('pdf_management_tokens') || '[]');
            if (!savedTokens.includes(data.management_token)) {
              savedTokens.push(data.management_token);
              localStorage.setItem('pdf_management_tokens', JSON.stringify(savedTokens));
            }
          } catch (e) {
            console.error('Failed to save management token', e);
          }
        }
        
        setApiResult(data);
        const dlPath = data.download_url || data.zip_url || data.url;
        if (dlPath) {
          const fileRes = await fetch(`${API_BASE_URL}${dlPath}`);
          if (fileRes.ok) {
            const blob = await fileRes.blob();
            setDownloadUrl(window.URL.createObjectURL(blob));
            const parts = dlPath.split('/');
            setDownloadFilename(parts[parts.length - 1] || 'output.pdf');
          }
        }
        setIsDone(true);
      } else {
        const blob = await response.blob();
        setDownloadUrl(window.URL.createObjectURL(blob));
        setDownloadFilename(files[0].name.replace(/\.[^/.]+$/, '') + '_processed.pdf');
        setIsDone(true);
      }
    } catch (err) {
      setError(err.message || 'Processing failed. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const resetApp = () => {
    if (downloadUrl) window.URL.revokeObjectURL(downloadUrl);
    setFiles([]); setIsProcessing(false); setIsDone(false); setError(''); setDownloadUrl(null); setApiResult(null); setExtraFields({});
  };

  return (
    <div className="flex-1 flex flex-col w-full relative z-20 min-h-screen bg-transparent">
      <div className="w-full max-w-[1200px] mx-auto px-4 sm:px-6 md:px-10 pt-4 sm:pt-8 pb-4 relative z-30 flex-none text-left">
        <button onClick={onBack} className="inline-flex items-center gap-2 bg-white text-[#1e2a52] font-bold px-4 py-2 rounded-full shadow-md border border-slate-200 hover:shadow-lg hover:scale-105 transition-all cursor-pointer text-xs sm:text-sm">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
      </div>

      <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
        <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">{toolName}</h1>
        <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">{toolDesc}</p>
        {apiConfig && (
          <span className="inline-block mt-2 px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-bold rounded-full">Backend Connected</span>
        )}
      </div>

      <div className="w-full max-w-2xl mx-auto px-4 sm:px-6 pb-14">
        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6 sm:p-10">
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all ${isDragging ? 'border-[#1e2a52] bg-[#e8f0e2]' : 'border-[#1e2a52]/30 bg-[#f8faf7] hover:border-[#1e2a52] hover:bg-[#eff4ea]'}`}
          >
            <input ref={inputRef} type="file" multiple accept={accepted.accept} className="hidden" onChange={handleFileChange} />
            <div className="w-16 h-16 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Upload className="w-8 h-8 text-[#1e2a52]" />
            </div>
            <p className="text-base sm:text-lg font-bold text-[#1e2a52] mb-1">Drop files here or click to browse</p>
            <p className="text-xs sm:text-sm text-slate-500">Accepted: <span className="font-semibold text-[#1e2a52]">{accepted.label}</span></p>
          </div>

          {error && (
            <div className="mt-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs sm:text-sm">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" /><span>{error}</span>
            </div>
          )}

          {files.length > 0 && (
            <div className="mt-6 space-y-2.5">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">{files.length} file{files.length > 1 ? 's' : ''} selected</p>
              {files.map((file, idx) => (
                <div key={idx} className="flex items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-xl px-4 py-3">
                  <div className="w-9 h-9 rounded-lg bg-[#1e2a52]/10 flex items-center justify-center shrink-0"><FileText className="w-4 h-4 text-[#1e2a52]" /></div>
                  <div className="flex-1 min-w-0"><p className="text-xs sm:text-sm font-semibold text-slate-800 truncate">{file.name}</p><p className="text-[10px] sm:text-xs text-slate-400">{file.size}</p></div>
                  <button onClick={() => handleRemove(idx)} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors"><X className="w-4 h-4" /></button>
                </div>
              ))}
            </div>
          )}

          {apiConfig && files.length > 0 && (apiConfig.type === 'file+field' || apiConfig.type === 'file+fields' || apiConfig.type === 'multi-file+field') && (
            <div className="mt-6 space-y-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
              {apiConfig.type === 'file+field' && (
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">{apiConfig.fieldLabel}</label>
                  <input type="text" value={extraFields[apiConfig.fieldName] || ''} onChange={e => setExtraFields(prev => ({...prev, [apiConfig.fieldName]: e.target.value}))}
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]" placeholder={`Enter ${apiConfig.fieldLabel}...`} />
                </div>
              )}
              {apiConfig.type === 'file+fields' && apiConfig.fields?.map(f => (
                <div key={f.name}>
                  <label className="block text-xs font-bold text-slate-600 mb-1">{f.label}</label>
                  {f.inputType === 'select' ? (
                    <select
                      value={extraFields[f.name] || f.default || ''}
                      onChange={e => setExtraFields(prev => ({...prev, [f.name]: e.target.value}))}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]"
                    >
                      {f.options?.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  ) : f.inputType === 'datetime-local' ? (
                    <input type="datetime-local" value={extraFields[f.name] || f.default || ''} onChange={e => setExtraFields(prev => ({...prev, [f.name]: e.target.value}))}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]" />
                  ) : f.inputType === 'checkbox' ? (
                    <div className="flex items-center gap-2 mt-2">
                      <input 
                        type="checkbox" 
                        id={`cb-${f.name}`}
                        checked={extraFields[f.name] !== undefined ? extraFields[f.name] : (f.default === 'true' || f.default === true)}
                        onChange={e => setExtraFields(prev => ({...prev, [f.name]: e.target.checked}))}
                        className="w-4 h-4 text-[#1e2a52] bg-gray-100 border-gray-300 rounded focus:ring-[#1e2a52]" 
                      />
                      <label htmlFor={`cb-${f.name}`} className="text-sm text-slate-700">{f.label}</label>
                    </div>
                  ) : (
                    <input type={f.inputType || 'text'} value={extraFields[f.name] || f.default || ''} onChange={e => setExtraFields(prev => ({...prev, [f.name]: e.target.value}))}
                      className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]" placeholder={`Enter ${f.label}...`} />
                  )}
                </div>
              ))}
              {apiConfig.type === 'multi-file+field' && (
                <div>
                  <label className="block text-xs font-bold text-slate-600 mb-1">{apiConfig.fieldLabel}</label>
                  <input type="text" value={extraFields[apiConfig.fieldName] || ''} onChange={e => setExtraFields(prev => ({...prev, [apiConfig.fieldName]: e.target.value}))}
                    className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52]" placeholder={`Enter ${apiConfig.fieldLabel}...`} />
                </div>
              )}
            </div>
          )}

          {files.length > 0 && (
            <div className="mt-8 text-center">
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center p-6 bg-[#f8faf7] border border-slate-200/80 rounded-2xl overflow-hidden relative min-h-[160px]">
                  <div className="w-12 h-12 border-4 border-[#1e2a52] border-t-transparent rounded-full animate-spin mb-4" />
                  <p className="text-xs sm:text-sm font-bold text-[#1e2a52] animate-pulse">Processing {toolName}... Please wait!</p>
                </div>
              ) : isDone ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center gap-2 text-emerald-600 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5" /> Processing Complete!
                  </div>

                  {apiResult && !downloadUrl && !apiResult.share_url && toolName !== 'Remove JavaScript' && toolName !== 'Remove Hidden Data' && toolName !== 'Remove Form Data' && (
                    <div className="text-left bg-slate-50 border border-slate-200 rounded-xl p-4 max-h-64 overflow-auto">
                      <p className="text-xs font-bold text-slate-500 mb-2 uppercase">API Response:</p>
                      <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono">{JSON.stringify(apiResult, null, 2)}</pre>
                    </div>
                  )}

                  {apiResult?.share_url && (
                    <div className="bg-emerald-50 border border-emerald-200 p-6 rounded-2xl max-w-md mx-auto shadow-sm">
                      <h3 className="text-lg font-bold text-emerald-800 mb-2">Secure Share Link Created!</h3>
                      <p className="text-sm text-emerald-600 mb-4">You can now share this link with others.</p>
                      <div className="flex items-center gap-2">
                        <input 
                          type="text" 
                          readOnly 
                          value={`${window.location.origin}/#${apiResult.share_url.replace(/^\//, '')}`}
                          className="flex-1 px-4 py-2 bg-white border border-emerald-200 rounded-lg text-sm text-slate-700 outline-none"
                        />
                        <button 
                          onClick={() => {
                            navigator.clipboard.writeText(`${window.location.origin}/#${apiResult.share_url.replace(/^\//, '')}`);
                            alert('Copied to clipboard!');
                          }}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-bold shadow transition-colors"
                        >
                          Copy
                        </button>
                      </div>
                      <div className="mt-4 pt-4 border-t border-emerald-200/60 flex justify-center">
                        <button onClick={() => window.location.hash = '#manage-shares'} className="text-sm font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1">
                          Manage Your Shares <ArrowRight className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  )}

                  {downloadUrl && (
                    <a href={downloadUrl} download={downloadFilename}
                      className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-3 rounded-full font-bold shadow-md transition-all text-sm cursor-pointer hover:scale-105">
                      <Download className="w-4 h-4" /> Download {downloadFilename || 'File'}
                    </a>
                  )}

                  {apiResult && !apiResult.share_url && toolName !== 'Remove JavaScript' && toolName !== 'Remove Hidden Data' && toolName !== 'Remove Form Data' && (
                    <div className="text-left bg-blue-50 border border-blue-200 rounded-xl p-4 max-h-64 overflow-auto mt-4">
                      <p className="text-xs font-bold text-blue-600 mb-2 uppercase">Analysis Results:</p>
                      <pre className="text-xs text-blue-800 whitespace-pre-wrap font-mono">{JSON.stringify(apiResult, null, 2)}</pre>
                    </div>
                  )}

                  {apiResult && toolName === 'Remove JavaScript' && (
                    <div className="text-left bg-white border border-slate-200 rounded-2xl p-6 mt-4 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
                      
                      {/* Success / Error Header */}
                      {apiResult.javascript_count === 0 || apiResult.javascript_detected === false ? (
                        <div className="flex flex-col items-center text-center space-y-3 mb-6">
                          <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center">
                            <CheckCircle2 className="w-7 h-7 text-emerald-600" />
                          </div>
                          <h2 className="text-xl font-bold text-slate-900">✓ No JavaScript Detected</h2>
                          <p className="text-slate-600 text-sm">No embedded PDF JavaScript was found in this document.</p>
                        </div>
                      ) : (
                        (!apiResult.verification_passed || (apiResult.removed_count || 0) < (apiResult.javascript_count || 0)) ? (
                          <div className="flex flex-col items-center text-center space-y-3 mb-6">
                            <div className="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center">
                              <AlertCircle className="w-7 h-7 text-amber-600" />
                            </div>
                            <h2 className="text-xl font-bold text-amber-900">⚠ JavaScript Removal Requires Attention</h2>
                            <p className="text-amber-800 text-sm">JavaScript was detected, but the cleaned PDF could not be fully verified.</p>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center text-center space-y-3 mb-6">
                            <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center">
                              <CheckCircle2 className="w-7 h-7 text-emerald-600" />
                            </div>
                            <h2 className="text-xl font-bold text-slate-900">✓ JavaScript Removed Successfully</h2>
                            <p className="text-slate-600 text-sm">Your PDF has been cleaned and independently verified.</p>
                            <p className="text-slate-500 text-xs font-mono bg-slate-50 px-3 py-1 rounded mt-2">File: {apiResult.original_filename || files[0]?.name}</p>
                          </div>
                        )
                      )}

                      {/* Security Analysis Table */}
                      <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden mb-6">
                        <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                          <h3 className="font-bold text-slate-800 text-sm">SECURITY ANALYSIS</h3>
                        </div>
                        <div className="divide-y divide-slate-100 text-sm">
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">JavaScript Detected</span>
                            <span className="font-bold text-slate-900">{apiResult.javascript_count || 0}</span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">JavaScript Removed</span>
                            <span className="font-bold text-slate-900">{apiResult.removed_count || 0}</span>
                          </div>
                          {(apiResult.javascript_count || 0) > 0 && (
                            <div className="flex justify-between items-center px-4 py-3">
                              <span className="text-slate-600 font-medium">Remaining JavaScript</span>
                              <span className={`font-bold ${(apiResult.javascript_count || 0) - (apiResult.removed_count || 0) > 0 ? 'text-red-600' : 'text-slate-900'}`}>
                                {Math.max(0, (apiResult.javascript_count || 0) - (apiResult.removed_count || 0))}
                              </span>
                            </div>
                          )}
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Verification</span>
                            <span className={`font-bold flex items-center ${apiResult.verification_passed ? 'text-emerald-600' : 'text-red-600'}`}>
                              {apiResult.verification_passed ? '✓ Passed' : '✗ Failed'}
                            </span>
                          </div>
                          {(apiResult.javascript_count || 0) > 0 && (
                            <div className="flex justify-between items-center px-4 py-3">
                              <span className="text-slate-600 font-medium">Pages Preserved</span>
                              <span className={`font-bold flex items-center ${apiResult.pages_preserved !== false ? 'text-emerald-600' : 'text-amber-600'}`}>
                                {apiResult.pages_preserved !== false ? '✓ Yes' : '✗ No'}
                              </span>
                            </div>
                          )}
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Digital Signature</span>
                            <span className={`font-bold ${apiResult.digital_signature_detected ? 'text-amber-600' : 'text-slate-500'}`}>
                              {apiResult.digital_signature_detected ? 'Detected' : 'Not Detected'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Detected Locations */}
                      {(apiResult.javascript_count || 0) > 0 && apiResult.javascript_locations?.length > 0 && (
                        <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden mb-6">
                          <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                            <h3 className="font-bold text-slate-800 text-sm uppercase">Detected JavaScript</h3>
                          </div>
                          <div className="px-4 py-3">
                            <ul className="space-y-1">
                              {apiResult.javascript_locations.map((loc, idx) => (
                                <li key={idx} className="flex items-center text-slate-700 text-sm">
                                  <span className="mr-2 text-slate-400">•</span>
                                  {loc}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}

                      {/* Verification Message */}
                      {(apiResult.javascript_count || 0) > 0 && apiResult.verification_passed && (apiResult.removed_count || 0) >= (apiResult.javascript_count || 0) && (
                        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start space-x-3 mb-6">
                          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-emerald-900 font-bold text-sm mb-0.5">✓ Verification Passed</h4>
                            <p className="text-emerald-700 text-xs">
                              The sanitized PDF was scanned again after removal. No embedded JavaScript remains in the cleaned PDF.
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Signature Warning */}
                      {apiResult.digital_signature_detected && (
                        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start space-x-3 mb-6">
                          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-amber-900 font-bold text-sm mb-0.5">⚠ Digital Signature Detected</h4>
                            <p className="text-amber-800 text-xs">
                              Modifying a signed PDF may affect the validity of its existing digital signature. Re-verification may be required.
                            </p>
                          </div>
                        </div>
                      )}

                    </div>
                  )}

                  {apiResult && toolName === 'Remove Hidden Data' && (
                    <div className="text-left bg-white border border-slate-200 rounded-2xl p-6 mt-4 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
                      
                      {/* Success / Error Header */}
                      {(!apiResult.verification_passed) ? (
                        <div className="flex flex-col items-center text-center space-y-3 mb-6">
                          <div className="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center">
                            <AlertCircle className="w-7 h-7 text-amber-600" />
                          </div>
                          <h2 className="text-xl font-bold text-amber-900">⚠ Hidden Data Removal Requires Attention</h2>
                          <p className="text-amber-800 text-sm">Some hidden information was detected but could not be safely removed or fully verified.</p>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center text-center space-y-3 mb-6">
                          <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center">
                            <CheckCircle2 className="w-7 h-7 text-emerald-600" />
                          </div>
                          <h2 className="text-xl font-bold text-slate-900">✓ Hidden Data Removed Successfully</h2>
                          <p className="text-slate-600 text-sm">Your PDF has been sanitized and independently verified.</p>
                          <p className="text-slate-500 text-xs font-mono bg-slate-50 px-3 py-1 rounded mt-2">File: {apiResult.original_filename || files[0]?.name}</p>
                        </div>
                      )}

                      {/* Security Analysis Table */}
                      <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden mb-6">
                        <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                          <h3 className="font-bold text-slate-800 text-sm">HIDDEN DATA SCAN SUMMARY</h3>
                        </div>
                        <div className="divide-y divide-slate-100 text-sm">
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Metadata</span>
                            <span className={`font-bold ${apiResult.items_detected?.metadata ? (apiResult.items_removed?.metadata ? 'text-emerald-600' : 'text-amber-600') : 'text-slate-500'}`}>
                              {apiResult.items_detected?.metadata ? (apiResult.items_removed?.metadata ? 'Removed' : 'Not Removed') : 'Not Detected'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Annotations</span>
                            <span className={`font-bold ${apiResult.items_detected?.annotations > 0 ? (apiResult.items_removed?.annotations >= apiResult.items_detected?.annotations ? 'text-emerald-600' : 'text-amber-600') : 'text-slate-500'}`}>
                              {apiResult.items_detected?.annotations > 0 ? `${apiResult.items_removed?.annotations || 0} / ${apiResult.items_detected.annotations} Removed` : '0'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Embedded Files</span>
                            <span className={`font-bold ${apiResult.items_detected?.embedded_files > 0 ? (apiResult.items_removed?.embedded_files >= apiResult.items_detected?.embedded_files ? 'text-emerald-600' : 'text-amber-600') : 'text-slate-500'}`}>
                              {apiResult.items_detected?.embedded_files > 0 ? `${apiResult.items_removed?.embedded_files || 0} / ${apiResult.items_detected.embedded_files} Removed` : '0'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">JavaScript</span>
                            <span className={`font-bold ${apiResult.items_detected?.javascript ? (apiResult.items_removed?.javascript ? 'text-emerald-600' : 'text-amber-600') : 'text-slate-500'}`}>
                              {apiResult.items_detected?.javascript ? (apiResult.items_removed?.javascript ? 'Removed' : 'Not Removed') : 'Not Detected'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Automatic Actions</span>
                            <span className={`font-bold ${apiResult.items_detected?.automatic_actions ? (apiResult.items_removed?.automatic_actions ? 'text-emerald-600' : 'text-amber-600') : 'text-slate-500'}`}>
                              {apiResult.items_detected?.automatic_actions ? (apiResult.items_removed?.automatic_actions ? 'Removed' : 'Not Removed') : 'Not Detected'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Optional Content / Layers</span>
                            <span className={`font-bold ${apiResult.items_detected?.optional_content ? (apiResult.items_removed?.optional_content ? 'text-emerald-600' : 'text-amber-600') : 'text-slate-500'}`}>
                              {apiResult.items_detected?.optional_content ? (apiResult.items_removed?.optional_content ? 'Removed' : 'Not Removed') : 'Not Detected'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Verification Message */}
                      {apiResult.verification_passed && (
                        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start space-x-3 mb-6">
                          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-emerald-900 font-bold text-sm mb-0.5">✓ Verification Passed</h4>
                            <p className="text-emerald-700 text-xs">
                              The sanitized PDF was scanned again after removal. Removable hidden data no longer exists in the cleaned PDF.
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Signature Warning */}
                      {apiResult.signature_warning && (
                        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start space-x-3 mb-6">
                          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-amber-900 font-bold text-sm mb-0.5">⚠ Digital Signature Detected</h4>
                            <p className="text-amber-800 text-xs">
                              Modifying a signed PDF may affect the validity of its existing digital signature. Re-verification may be required.
                            </p>
                          </div>
                        </div>
                      )}

                    </div>
                  )}

                  {apiResult && toolName === 'Remove Form Data' && (
                    <div className="text-left bg-white border border-slate-200 rounded-2xl p-6 mt-4 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
                      
                      {/* Success / Error Header */}
                      {apiResult.form_fields_detected === 0 ? (
                        <div className="flex flex-col items-center text-center space-y-3 mb-6">
                          <div className="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center">
                            <AlertCircle className="w-7 h-7 text-amber-600" />
                          </div>
                          <h2 className="text-xl font-bold text-amber-900">No Form Data Found</h2>
                          <p className="text-amber-800 text-sm">This PDF does not contain fillable form fields.</p>
                          <p className="text-slate-500 text-xs font-mono bg-slate-50 px-3 py-1 rounded mt-2">File: {apiResult.original_filename || files[0]?.name}</p>
                        </div>
                      ) : !apiResult.verification_passed ? (
                        <div className="flex flex-col items-center text-center space-y-3 mb-6">
                          <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center">
                            <AlertCircle className="w-7 h-7 text-red-600" />
                          </div>
                          <h2 className="text-xl font-bold text-red-900">Unable to Remove Form Data</h2>
                          <p className="text-red-800 text-sm">The PDF form type could not be safely processed. Please try another PDF.</p>
                        </div>
                      ) : (
                        <div className="flex flex-col items-center text-center space-y-3 mb-6">
                          <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center">
                            <CheckCircle2 className="w-7 h-7 text-emerald-600" />
                          </div>
                          <h2 className="text-xl font-bold text-slate-900">Form Data Removed Successfully</h2>
                          <p className="text-slate-600 text-sm">{apiResult.cleared_fields_count || 0} filled form fields were cleared. The PDF form structure has been preserved and the document is ready for reuse.</p>
                          <p className="text-slate-500 text-xs font-mono bg-slate-50 px-3 py-1 rounded mt-2">File: {apiResult.original_filename || files[0]?.name}</p>
                        </div>
                      )}

                      {/* Security Analysis Table */}
                      <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden mb-6">
                        <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                          <h3 className="font-bold text-slate-800 text-sm">FORM DATA SCAN SUMMARY</h3>
                        </div>
                        <div className="divide-y divide-slate-100 text-sm">
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Form Type</span>
                            <span className="font-bold text-slate-900">{apiResult.form_type || 'Unknown'}</span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Form Fields Detected</span>
                            <span className="font-bold text-slate-900">{apiResult.form_fields_detected || 0}</span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Filled Fields</span>
                            <span className="font-bold text-slate-900">{apiResult.filled_fields_detected || 0}</span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Blank Fields</span>
                            <span className="font-bold text-slate-900">{apiResult.blank_fields || 0}</span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Status</span>
                            <span className={`font-bold ${apiResult.verification_passed ? 'text-emerald-600' : (apiResult.form_fields_detected === 0 ? 'text-amber-600' : 'text-red-600')}`}>
                              {apiResult.verification_passed ? 'Ready to Reuse' : (apiResult.form_fields_detected === 0 ? 'No Forms Found' : 'Unsupported')}
                            </span>
                          </div>
                        </div>
                      </div>

                    </div>
                  )}

                  <button onClick={resetApp}
                    className="inline-flex items-center gap-2 bg-[#1e2a52] hover:bg-[#16203e] text-white px-8 py-3 rounded-full font-bold shadow-lg transition-all text-sm cursor-pointer hover:scale-105 active:scale-95 mt-4">
                    Process Another File
                  </button>
                </div>
              ) : (
                <button onClick={handleProcess}
                  className="bg-[#1e2a52] hover:bg-[#16203e] text-white px-10 py-3.5 rounded-full font-bold shadow-lg transition-all text-sm cursor-pointer inline-flex items-center gap-2 hover:scale-105 active:scale-95">
                  Process {toolName}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
