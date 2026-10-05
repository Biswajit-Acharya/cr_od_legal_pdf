import React, { useState, useRef } from 'react';
import { Upload, FileText, Download, CheckCircle2, ArrowLeft, X, AlertCircle, Paperclip, Plus, Archive, FileJson, File, FileImage, Trash2, Info } from 'lucide-react';
import apiClient from '../../api/apiClient';

export default function FileAttachmentsPage({ onBack }) {
  const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
  const toolName = "File Attachments";
  const toolDesc = "Manage embedded file attachments within PDF documents — view, add, download, or remove attachments.";
  
  const [selectedPdf, setSelectedPdf] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');

  const [attachments, setAttachments] = useState([]);
  const [stagedFiles, setStagedFiles] = useState([]);
  
  // Modal state
  const [detailsModal, setDetailsModal] = useState({ isOpen: false, data: null });

  const inputRef = useRef(null);
  const addInputRef = useRef(null);

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handlePdfFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handlePdfFile(e.target.files[0]);
    }
  };

  const handlePdfFile = async (file) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a valid PDF file.');
      return;
    }
    
    setSelectedPdf(file);
    setError('');
    setSuccess('');
    setDownloadUrl('');
    setAttachments([]);
    setStagedFiles([]);
    setIsAnalyzing(true);
    
    const minDelay = new Promise(resolve => setTimeout(resolve, 1500));
    
    try {
      const fd = new FormData();
      fd.append('file', file);
      
      const res = await fetch(`${API_BASE_URL}/document-management/file-attachments/analyze`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to analyze PDF.');
      
      await minDelay;
      
      if (data.attachments) {
        setAttachments(data.attachments);
      }
      
    } catch (err) {
      setError('Error analyzing PDF: ' + err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const resetAll = () => {
    setSelectedPdf(null);
    setAttachments([]);
    setStagedFiles([]);
    setError('');
    setSuccess('');
    setDownloadUrl('');
    if (inputRef.current) inputRef.current.value = '';
    if (addInputRef.current) addInputRef.current.value = '';
  };

  const handleAddFilesSelected = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setStagedFiles(Array.from(e.target.files));
    }
  };

  const removeStaged = (index) => {
    setStagedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearStaged = () => {
    setStagedFiles([]);
    if (addInputRef.current) addInputRef.current.value = '';
  };

  const uploadStagedFiles = async () => {
    if (!selectedPdf || stagedFiles.length === 0) return;
    
    setIsProcessing(true);
    setError('');
    setSuccess('');
    
    const minDelay = new Promise(resolve => setTimeout(resolve, 2000));
    
    try {
      const attData = [];
      
      const fileToBase64 = (file) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64String = reader.result.split(',')[1];
          resolve(base64String);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      for (const f of stagedFiles) {
        const base64 = await fileToBase64(f);
        attData.push({
          name: f.name,
          filename: f.name,
          description: '',
          bytes_b64: base64
        });
      }

      const fd = new FormData();
      fd.append('file', selectedPdf);
      fd.append('attachments_json', JSON.stringify(attData));

      const res = await fetch(`${API_BASE_URL}/document-management/file-attachments/add`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to add attachments.');
      
      let msg = `${data.added_count} attachment(s) added.`;
      if (data.skipped_duplicates && data.skipped_duplicates.length > 0) {
          msg += ' Skipped duplicates: ' + data.skipped_duplicates.join(', ');
      }
      
      await minDelay;
      
      setStagedFiles([]);
      if (addInputRef.current) addInputRef.current.value = '';
      setSuccess(msg);
      
      // Refresh the PDF analysis to show new attachments
      await handlePdfFile(selectedPdf);
      
    } catch (err) {
      setError('Failed to upload: ' + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const viewDetails = async (attName) => {
    if (!selectedPdf) return;
    
    const fd = new FormData();
    fd.append('file', selectedPdf);
    fd.append('attachment_name', attName);

    let data;
    try {
      const res = await fetch(`${API_BASE_URL}/document-management/file-attachments/details`, { method: 'POST', body: fd });
      data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
    } catch (err) {
      console.error('Failed to get details:', err);
      setError('Failed to fetch details.');
      return;
    }
    
    setDetailsModal({ isOpen: true, data });
  };

  const downloadAttachment = async (attName) => {
    if (!selectedPdf) return;

    const fd = new FormData();
    fd.append('file', selectedPdf);
    fd.append('attachment_name', attName);

    try {
      const res = await fetch(`${API_BASE_URL}/document-management/file-attachments/download-attachment`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error('Failed to download attachment');
      
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      let filename = attName;
      const disposition = res.headers.get('content-disposition');
      if (disposition) {
        const match = disposition.match(/filename="?([^"]+)"?/);
        if (match) filename = match[1];
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Download failed for: ${attName}`);
    }
  };

  const removeAttachment = async (attName) => {
    if (!selectedPdf) return;
    if (!window.confirm(`Remove attachment "${attName}"?`)) return;

    setError('');
    setSuccess('');

    const fd = new FormData();
    fd.append('file', selectedPdf);
    fd.append('attachment_name', attName);

    try {
      const res = await fetch(`${API_BASE_URL}/document-management/file-attachments/remove`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to remove attachment.');
      
      setSuccess(`Attachment "${attName}" removed.`);
      await handlePdfFile(selectedPdf);
    } catch (err) {
      setError('Failed to remove: ' + err.message);
    }
  };

  const handleSavePdf = async () => {
    if (!selectedPdf) return;
    
    setIsProcessing(true);
    setError('');
    setSuccess('');
    
    const minDelay = new Promise(resolve => setTimeout(resolve, 2500));
    
    try {
      const fd = new FormData();
      fd.append('file', selectedPdf);

      const res = await fetch(`${API_BASE_URL}/document-management/file-attachments/add`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to save PDF.');
      
      await minDelay;
      
      setSuccess('PDF saved successfully!');
      setDownloadUrl(data.download_url);
      
    } catch (err) {
      setError('Failed to save: ' + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const getFileIcon = (ext) => {
    const e = (ext || '').toLowerCase();
    if (['pdf'].includes(e)) return <FileText className="w-5 h-5 text-red-500" />;
    if (['zip', 'rar', '7z', 'tar', 'gz'].includes(e)) return <Archive className="w-5 h-5 text-orange-500" />;
    if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(e)) return <FileImage className="w-5 h-5 text-purple-500" />;
    if (['json'].includes(e)) return <FileJson className="w-5 h-5 text-yellow-500" />;
    if (['csv', 'txt', 'xml', 'md'].includes(e)) return <FileText className="w-5 h-5 text-slate-500" />;
    return <File className="w-5 h-5 text-blue-500" />;
  };

  return (
    <div className="react-wrapper-file_attachments">
      <style>{`
        .fa-wrap { max-width: 1100px; margin: 0 auto; padding: 0 1rem 3rem 1rem; }
        .fa-hdr { text-align: center; margin-bottom: 2rem; }
        .fa-hdr h1 { font-size: 2.1rem; font-weight: 800; color: #0f172a; margin: 0 0 8px 0; }
        .fa-hdr p { color: #64748b; font-size: 1rem; margin: 0; }
        
        .fa-back-btn { display: inline-flex; align-items: center; gap: 8px; background: #fff; color: #1e2a52; font-weight: 700; padding: 8px 16px; border-radius: 9999px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; cursor: pointer; transition: all 0.2s; font-size: 0.88rem; margin-bottom: 1.5rem; }
        .fa-back-btn:hover { box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); transform: scale(1.05); }

        .fa-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 2rem; margin-bottom: 1.5rem; box-shadow: 0 4px 14px rgba(0,0,0,0.03); }
        .fa-card h2 { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; }
        
        .fa-file-info { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #f8fafc; border-radius: 10px; margin-top: 1rem; border: 1px solid #e2e8f0; }
        .fa-file-icon { font-size: 1.5rem; }
        .fa-file-details { flex: 1; min-width: 0; }
        .fa-file-name { font-weight: 700; color: #1e293b; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .fa-file-size { font-size: 0.82rem; color: #64748b; }
        
        .fa-loading { text-align: center; padding: 2rem; }
        .fa-spinner { width: 40px; height: 40px; border: 4px solid #e2e8f0; border-top-color: #2563eb; border-radius: 50%; animation: fa-spin 0.8s linear infinite; margin: 0 auto 1rem; }
        @keyframes fa-spin { to { transform: rotate(360deg); } }
        
        .fa-btn { padding: 10px 18px; font-size: 0.9rem; font-weight: 700; border: none; border-radius: 8px; cursor: pointer; transition: all 0.15s; }
        .fa-btn-primary { background: #7c3aed; color: #fff; }
        .fa-btn-primary:hover { background: #6d28d9; }
        .fa-btn-success { background: #1e2a52; color: #fff; }
        .fa-btn-success:hover { background: #16203e; }
        .fa-btn-secondary { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
        .fa-btn-secondary:hover { background: #e2e8f0; }
        .fa-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .fa-main-actions { display: flex; gap: 12px; margin-top: 1.5rem; flex-wrap: wrap; }
        .fa-main-actions .fa-btn { flex: 1; min-width: 180px; text-align: center; justify-content: center; display: flex; align-items: center; }
        
        .fa-download-area { margin-top: 1.5rem; padding: 1.5rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; text-align: center; }
        .fa-download-area p { margin: 0 0 1rem 0; font-weight: 700; color: #166534; }
        .fa-download-link { display: inline-block; padding: 12px 24px; background: #16a34a; color: #fff; text-decoration: none; border-radius: 8px; font-weight: 700; transition: background 0.15s; }
        .fa-download-link:hover { background: #15803d; }
        
        .fa-error { padding: 1rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; color: #991b1b; font-size: 0.9rem; margin-top: 1rem; }
        .fa-success { padding: 1rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; color: #166534; font-size: 0.9rem; margin-top: 1rem; }
        
        .fa-attach-list { display: flex; flex-direction: column; gap: 8px; }
        .fa-attach-item { display: grid; grid-template-columns: auto 1fr auto; gap: 12px; align-items: center; padding: 12px 14px; background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; transition: all 0.15s; }
        .fa-attach-item:hover { border-color: #cbd5e1; background: #f8fafc; }
        
        .fa-attach-icon { width: 40px; height: 40px; border-radius: 10px; background: #f1f5f9; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .fa-attach-info { min-width: 0; }
        .fa-attach-name { font-weight: 700; color: #1e293b; font-size: 0.9rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .fa-attach-meta { font-size: 0.78rem; color: #64748b; display: flex; gap: 8px; }
        
        .fa-attach-actions { display: flex; gap: 6px; }
        .fa-btn-icon { padding: 6px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; cursor: pointer; color: #475569; transition: all 0.15s; }
        .fa-btn-icon:hover { background: #f1f5f9; color: #1e293b; }
        .fa-btn-icon.delete:hover { background: #fef2f2; color: #dc2626; border-color: #fecaca; }
        
        .fa-empty { text-align: center; padding: 3rem 1.5rem; background: #f8fafc; border-radius: 12px; border: 2px dashed #e2e8f0; margin-top: 1rem; }
        .fa-empty h3 { margin: 12px 0 8px 0; font-size: 1.1rem; font-weight: 700; color: #1e293b; }
        .fa-empty p { margin: 0; font-size: 0.9rem; color: #64748b; }
        
        .fa-add-trigger { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 18px; border: 2px dashed #cbd5e1; border-radius: 10px; background: #f8fafc; cursor: pointer; transition: all 0.2s; color: #475569; font-weight: 600; font-size: 0.92rem; margin-top: 1.5rem; }
        .fa-add-trigger:hover { border-color: #7c3aed; background: #f5f3ff; color: #7c3aed; }
        
        .fa-modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15,23,42,0.6); backdrop-filter: blur(4px); z-index: 9999; display: flex; justify-content: center; align-items: center; }
        .fa-modal { background: #fff; border-radius: 16px; width: 90%; max-width: 500px; max-height: 90vh; overflow-y: auto; box-shadow: 0 25px 60px rgba(0,0,0,0.15); }
        .fa-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 1.25rem 1.5rem; border-bottom: 1px solid #e2e8f0; }
        .fa-modal-header h3 { margin: 0; font-size: 1.1rem; font-weight: 800; color: #1e2a52; }
        .fa-modal-close { background: none; border: none; cursor: pointer; color: #94a3b8; border-radius: 6px; padding: 4px; }
        .fa-modal-close:hover { background: #f1f5f9; color: #475569; }
        .fa-modal-body { padding: 1.5rem; }
        .fa-detail-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
        .fa-detail-row:last-child { border-bottom: none; }
        .fa-detail-label { font-weight: 600; color: #475569; font-size: 0.88rem; }
        .fa-detail-value { color: #1e293b; font-size: 0.88rem; text-align: right; max-width: 60%; word-break: break-word; font-weight: 500; }
        .fa-modal-footer { display: flex; gap: 10px; justify-content: flex-end; padding: 1rem 1.5rem; border-top: 1px solid #e2e8f0; background: #f8fafc; }
      `}</style>

      <div className="fa-wrap">
        {onBack && (
          <button onClick={onBack} className="fa-back-btn">
            <ArrowLeft size={16} /> Back
          </button>
        )}
        
        <div className="fa-hdr">
          <h1>{toolName}</h1>
          <p>{toolDesc}</p>
        </div>

        <div className="fa-card">
          <h2>Select PDF Document</h2>
          <div
            className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all ${isDragging
                ? 'border-[#1e2a52] bg-[#e8f0e2]'
                : 'border-[#1e2a52]/30 bg-[#f8faf7] hover:border-[#1e2a52] hover:bg-[#eff4ea]'
              }`}
            onClick={() => inputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input className="hidden" type="file" ref={inputRef} accept=".pdf" onChange={handleInputChange} />
            <div className="w-16 h-16 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Upload className="w-8 h-8 text-[#1e2a52]" />
            </div>
            <p className="text-base sm:text-lg font-bold text-[#1e2a52] mb-1">
              {selectedPdf ? selectedPdf.name : 'Drop files here or click to browse'}
            </p>
            <p className="text-xs sm:text-sm text-slate-500">
              Accepted: <span className="font-semibold text-[#1e2a52]">PDF files (.pdf)</span>
            </p>
          </div>

          {selectedPdf && !isAnalyzing && (
            <div className="fa-file-info">
              <span className="fa-file-icon">📄</span>
              <div className="fa-file-details">
                <div className="fa-file-name">{selectedPdf.name}</div>
                <div className="fa-file-size">{formatSize(selectedPdf.size)}</div>
              </div>
            </div>
          )}

          {isAnalyzing && (
            <div className="fa-loading">
              <div className="fa-spinner"></div>
              <div style={{ color: '#64748b', fontSize: '0.95rem' }}>Analyzing PDF attachments...</div>
            </div>
          )}

          {error && <div className="fa-error">{error}</div>}
        </div>

        {selectedPdf && !isAnalyzing && (
          <div className="fa-card">
            <h2 className="flex items-center gap-2">
              <Paperclip size={18} className="text-[#1e2a52]" /> 
              Embedded Attachments 
              <span className="bg-slate-100 text-slate-500 px-2 py-0.5 rounded-md text-[0.8rem] ml-2">
                {attachments.length}
              </span>
            </h2>

            {attachments.length === 0 ? (
              <div className="fa-empty">
                <Paperclip className="w-12 h-12 mx-auto text-slate-300" />
                <h3>No embedded attachments found</h3>
                <p>This PDF does not contain any embedded file attachments.</p>
              </div>
            ) : (
              <div className="fa-attach-list">
                {attachments.map((att, idx) => (
                  <div key={idx} className="fa-attach-item">
                    <div className="fa-attach-icon">
                      {getFileIcon(att.extension)}
                    </div>
                    <div className="fa-attach-info">
                      <div className="fa-attach-name">{att.filename || att.name}</div>
                      <div className="fa-attach-meta">
                        <span className="font-semibold text-slate-500">{att.size_human}</span>
                        <span className="text-slate-400">&bull;</span>
                        <span className="uppercase">{att.extension}</span>
                      </div>
                    </div>
                    <div className="fa-attach-actions">
                      <button className="fa-btn-icon" onClick={() => viewDetails(att.name)} title="Details">
                        <Info size={16} />
                      </button>
                      <button className="fa-btn-icon" onClick={() => downloadAttachment(att.name)} title="Download">
                        <Download size={16} />
                      </button>
                      <button className="fa-btn-icon delete" onClick={() => removeAttachment(att.name)} title="Remove">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-8 border-t border-slate-100 pt-6">
              <h3 className="text-sm font-bold text-[#1e2a52] mb-3">Add New Attachments</h3>
              <div 
                className="fa-add-trigger" 
                onClick={() => addInputRef.current?.click()}
              >
                <Plus size={18} /> Add File Attachments
              </div>
              <input type="file" className="hidden" multiple ref={addInputRef} onChange={handleAddFilesSelected} />
              
              {stagedFiles.length > 0 && (
                <div className="mt-4 bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <div className="text-sm font-bold text-slate-600 mb-3 flex justify-between items-center">
                    <span>Files to attach ({stagedFiles.length}):</span>
                  </div>
                  <div className="flex flex-col gap-2 mb-4">
                    {stagedFiles.map((f, i) => (
                      <div key={i} className="flex items-center justify-between bg-white border border-slate-200 p-2.5 rounded-lg">
                        <div className="flex flex-col min-w-0 flex-1 mr-3">
                          <span className="text-sm font-semibold text-slate-800 truncate">{f.name}</span>
                          <span className="text-xs text-slate-400">{formatSize(f.size)}</span>
                        </div>
                        <button onClick={() => removeStaged(i)} className="text-slate-400 hover:text-red-500 transition-colors p-1">
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <button className="fa-btn fa-btn-primary flex-1" onClick={uploadStagedFiles} disabled={isProcessing}>
                      Upload & Attach
                    </button>
                    <button className="fa-btn fa-btn-secondary" onClick={clearStaged} disabled={isProcessing}>
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>

            {isProcessing ? (
              <div className="flex flex-col items-center justify-center p-6 bg-[#f8faf7] border border-slate-200/80 rounded-2xl overflow-hidden relative min-h-[160px] mt-6">
                <div className="speeder-loader-wrapper">
                  <div className="loader">
                    <span>
                      <span></span>
                      <span></span>
                      <span></span>
                      <span></span>
                    </span>
                    <div className="base">
                      <span></span>
                      <div className="face"></div>
                    </div>
                  </div>
                  <div className="longfazers">
                    <span></span>
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
                <p className="text-xs sm:text-sm font-bold text-[#1e2a52] mt-2 animate-pulse">
                  Processing… Please wait!
                </p>
              </div>
            ) : (
              <div className="fa-main-actions mt-6 pt-6 border-t border-slate-100">
                <button
                  type="button"
                  className="fa-btn fa-btn-success flex items-center justify-center gap-2"
                  onClick={handleSavePdf}
                >
                  <Download size={18} /> Save & Download Updated PDF
                </button>
                <button type="button" className="fa-btn fa-btn-secondary flex-none" onClick={resetAll}>
                  Reset
                </button>
              </div>
            )}

            {success && (
              <div className="mt-6 flex items-start gap-2 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl px-4 py-3 text-sm">
                <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5 text-emerald-500" />
                <span>{success}</span>
              </div>
            )}

            {downloadUrl && (
              <div className="fa-download-area">
                <p>PDF updated successfully!</p>
                <a href={apiClient.getFullUrl(downloadUrl)} className="fa-download-link" download>Download Updated PDF</a>
              </div>
            )}
          </div>
        )}
      </div>

      {detailsModal.isOpen && detailsModal.data && (
        <div className="fa-modal-overlay">
          <div className="fa-modal">
            <div className="fa-modal-header">
              <h3>Attachment Details</h3>
              <button className="fa-modal-close" onClick={() => setDetailsModal({ isOpen: false, data: null })}>
                <X size={20} />
              </button>
            </div>
            <div className="fa-modal-body">
              <div className="fa-detail-row">
                <div className="fa-detail-label">Name</div>
                <div className="fa-detail-value">{detailsModal.data.name}</div>
              </div>
              <div className="fa-detail-row">
                <div className="fa-detail-label">Filename</div>
                <div className="fa-detail-value">{detailsModal.data.filename}</div>
              </div>
              <div className="fa-detail-row">
                <div className="fa-detail-label">Extension</div>
                <div className="fa-detail-value uppercase">{detailsModal.data.extension}</div>
              </div>
              <div className="fa-detail-row">
                <div className="fa-detail-label">Description</div>
                <div className="fa-detail-value">{detailsModal.data.description || 'N/A'}</div>
              </div>
              <div className="fa-detail-row">
                <div className="fa-detail-label">Size</div>
                <div className="fa-detail-value">{detailsModal.data.size_human} ({detailsModal.data.size} bytes)</div>
              </div>
              <div className="fa-detail-row">
                <div className="fa-detail-label">Index</div>
                <div className="fa-detail-value">{detailsModal.data.index}</div>
              </div>
              <div className="fa-detail-row">
                <div className="fa-detail-label">Creation Date</div>
                <div className="fa-detail-value">{detailsModal.data.creation_date || 'N/A'}</div>
              </div>
              <div className="fa-detail-row">
                <div className="fa-detail-label">Modification Date</div>
                <div className="fa-detail-value">{detailsModal.data.modification_date || 'N/A'}</div>
              </div>
            </div>
            <div className="fa-modal-footer">
              <button className="fa-btn fa-btn-secondary" onClick={() => setDetailsModal({ isOpen: false, data: null })}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
