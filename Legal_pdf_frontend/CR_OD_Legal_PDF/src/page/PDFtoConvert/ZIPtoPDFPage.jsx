import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Download, CheckCircle2, ArrowLeft, X, AlertCircle, Eye } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function ZIPtoPDFPage({ onBack }) {
  const toolName = "ZIP to PDF";
  const toolDesc = "Convert ZIP to PDF";
  const apiSlug = "zip-to-pdf";

  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState('');
  const [downloadBlob, setDownloadBlob] = useState(null);
  const [downloadFilename, setDownloadFilename] = useState('');
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState(null);
  const [showPdfPreview, setShowPdfPreview] = useState(false);
  const inputRef = useRef();

  useEffect(() => {
    if (file && file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setFilePreview(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setFilePreview(null);
    }
  }, [file]);

  useEffect(() => {
    return () => {
      if (pdfPreviewUrl) URL.revokeObjectURL(pdfPreviewUrl);
    };
  }, [pdfPreviewUrl]);

  const addFile = (newFiles) => {
    setError('');
        const f = Array.from(newFiles)[0];
    if (!f) return;
    
    const fileExt = '.' + f.name.split('.').pop().toLowerCase();
    const allowedExts = ['.zip'];
    if (!allowedExts.includes(fileExt)) {
      setError(`Invalid file type. Please upload a valid ${allowedExts.join(', ')} file.`);
      return;
    }
    setFile(f);
    setIsDone(false);
    setDownloadBlob(null);
    setPdfPreviewUrl(null);
    setShowPdfPreview(false);
  };

  const handleFileChange = (e) => { if (e.target.files?.length) addFile(e.target.files); };
  const handleDrop = (e) => { e.preventDefault(); setIsDragging(false); if (e.dataTransfer.files?.length) addFile(e.dataTransfer.files); };

  const handleProcess = async () => {
    if (!file) return;
    setIsProcessing(true);
    setError('');
    try {
      const uploadForm = new FormData();
      uploadForm.append('file', file);
      const uploadRes = await fetch(`${API_BASE_URL}/api/convert-to-pdf/${apiSlug}/upload`, {
        method: 'POST',
        body: uploadForm,
      });
      if (!uploadRes.ok) {
        const err = await uploadRes.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${uploadRes.status})`);
      }
      const uploadData = await uploadRes.json();

      const processForm = new FormData();
      processForm.append('request_id', uploadData.request_id);
      processForm.append('filename', uploadData.filename);
      const processRes = await fetch(`${API_BASE_URL}/api/convert-to-pdf/${apiSlug}/process`, {
        method: 'POST',
        body: processForm,
      });
      if (!processRes.ok) {
        const err = await processRes.json().catch(() => ({}));
        throw new Error(err.detail || `Processing failed (${processRes.status})`);
      }
      const processData = await processRes.json();

      const dlUrl = processData.download_url || processData.zip_url;
      if (!dlUrl) throw new Error('No download URL returned from server.');

      const fileRes = await fetch(`${API_BASE_URL}${dlUrl}`);
      if (!fileRes.ok) throw new Error('Failed to fetch the converted file from server.');
      const blob = await fileRes.blob();

      const baseName = file.name.replace(/\.[^/.]+$/, '');
      const outputName = `${baseName}.pdf`;
      setDownloadFilename(outputName);
      setDownloadBlob(blob);

      // Create PDF preview URL
      const previewUrl = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      setPdfPreviewUrl(previewUrl);
      setIsDone(true);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!downloadBlob) return;
    const url = URL.createObjectURL(downloadBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleReset = () => {
    setFile(null);
    setIsDone(false);
    setError('');
    setDownloadBlob(null);
    setDownloadFilename('');
    setPdfPreviewUrl(null);
    setShowPdfPreview(false);
  };

  const fmtSize = (f) => f.size < 1024 * 1024 ? (f.size / 1024).toFixed(0) + ' KB' : (f.size / (1024 * 1024)).toFixed(2) + ' MB';

  return (
    <div className="flex-1 flex flex-col w-full bg-transparent relative z-20 min-h-screen">
      <div className="w-full max-w-[1200px] mx-auto px-4 sm:px-6 md:px-10 pt-1 sm:pt-5">
        <button onClick={onBack} className="inline-flex items-center gap-2 bg-white text-[#1e2a52] font-bold px-4 py-2 rounded-full shadow-sm border border-slate-200 hover:shadow-md hover:scale-105 transition-all cursor-pointer text-xs sm:text-sm">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
      </div>

      <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
        <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">{toolName}</h1>
        <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">{toolDesc}</p>
      </div>

      <div className="w-full max-w-2xl mx-auto px-4 sm:px-6 pb-14">
        <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6 sm:p-10">

          {!isDone && (
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all ${isDragging ? 'border-[#1e2a52] bg-[#e8f0e2]' : 'border-[#1e2a52]/30 bg-[#f8faf7] hover:border-[#1e2a52] hover:bg-[#eff4ea]'}`}
            >
              <input ref={inputRef} type="file" className="hidden" accept="application/zip" onChange={handleFileChange} />
              <div className="w-16 h-16 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Upload className="w-8 h-8 text-[#1e2a52]" />
              </div>
              <p className="text-base sm:text-lg font-bold text-[#1e2a52] mb-1">{file ? file.name : 'Drop file here or click to browse'}</p>
              <p className="text-xs sm:text-sm text-slate-500">Select file to convert to PDF</p>
            </div>
          )}

          {error && (
            <div className="mt-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs sm:text-sm">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {file && !isDone && (
            <div className="mt-6">
              <div className="flex flex-col items-center gap-3 bg-slate-50 border border-slate-200/80 rounded-xl p-4">
                {filePreview ? (
                  <img src={filePreview} alt="Preview" className="max-h-64 object-contain rounded-lg border border-slate-200 shadow-sm" />
                ) : (
                  <div className="w-16 h-16 rounded-xl bg-[#1e2a52]/10 flex items-center justify-center">
                    <FileText className="w-8 h-8 text-[#1e2a52]" />
                  </div>
                )}
                <div className="flex-1 min-w-0 text-center mt-2 w-full flex items-center justify-between">
                  <div className="text-left overflow-hidden">
                    <p className="text-sm font-semibold text-slate-800 truncate">{file.name}</p>
                    <p className="text-xs text-slate-400">{fmtSize(file)}</p>
                  </div>
                  <button onClick={handleReset} className="p-2 bg-slate-200 hover:bg-red-100 text-slate-500 hover:text-red-600 rounded-full transition-colors cursor-pointer shrink-0">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="mt-8 text-center">
                {isProcessing ? (
                  <div className="flex flex-col items-center justify-center p-8 bg-[#f8faf7] border border-slate-200/80 rounded-2xl min-h-[140px]">
                    <div className="w-12 h-12 border-4 border-[#1e2a52] border-t-transparent rounded-full animate-spin mb-4"></div>
                    <p className="text-xs sm:text-sm font-bold text-[#1e2a52] animate-pulse">Converting to PDF... Please wait!</p>
                  </div>
                ) : (
                  <button onClick={handleProcess} className="bg-[#1e2a52] hover:bg-[#16203e] text-white px-12 py-4 rounded-full font-bold shadow-lg transition-all text-sm cursor-pointer inline-flex items-center gap-2 hover:scale-105 active:scale-95">
                    Start {toolName}
                  </button>
                )}
              </div>
            </div>
          )}

          {isDone && (
            <div className="space-y-5">
              <div className="flex items-center justify-center gap-2 text-emerald-600 font-bold text-base pt-2">
                <CheckCircle2 className="w-6 h-6" /> Conversion Complete!
              </div>

              {pdfPreviewUrl && (
                <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between bg-slate-100 px-4 py-2">
                    <span className="text-xs font-semibold text-slate-600">PDF Preview</span>
                    <button
                      onClick={() => setShowPdfPreview(v => !v)}
                      className="text-xs text-[#1e2a52] font-bold hover:underline cursor-pointer"
                    >
                      {showPdfPreview ? 'Hide' : 'Show'} Preview
                    </button>
                  </div>
                  {showPdfPreview && (
                    <iframe
                      src={pdfPreviewUrl}
                      title="PDF Preview"
                      className="w-full"
                      style={{ height: '500px', border: 'none' }}
                    />
                  )}
                </div>
              )}

              <div className="flex justify-center gap-3 flex-wrap">
                {pdfPreviewUrl && !showPdfPreview && (
                  <button
                    onClick={() => setShowPdfPreview(true)}
                    className="inline-flex items-center gap-2 bg-[#1e2a52] hover:bg-[#16203e] text-white px-6 py-3 rounded-full font-bold shadow-md transition-all text-sm cursor-pointer hover:scale-105"
                  >
                    <Eye className="w-4 h-4" /> Preview PDF
                  </button>
                )}
                <button onClick={handleDownload} className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-3 rounded-full font-bold shadow-md transition-all text-sm cursor-pointer hover:scale-105">
                  <Download className="w-4 h-4" /> Download PDF
                </button>
                <button onClick={handleReset} className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-6 py-3 rounded-full font-bold transition-all text-sm cursor-pointer">
                  Convert Another
                </button>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
