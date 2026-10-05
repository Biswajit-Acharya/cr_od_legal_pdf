import React, { useState, useRef, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export default function PDFtoSingleLongImagePage() {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  const fileInputRef = useRef(null);

  const handleFile = (f) => {
    if (f && f.type === 'application/pdf') {
      setFile(f);
      setErrorMsg(null);
    } else {
      setErrorMsg('Please upload a valid PDF file.');
    }
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files?.length) handleFile(e.dataTransfer.files[0]);
  }, []);

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => setIsDragOver(false), []);

  const handleProcess = async () => {
    if (!file) return;
    setIsProcessing(true);
    setErrorMsg(null);
    setIsDone(false);

    try {
      // 1. Upload
      const uploadForm = new FormData();
      uploadForm.append('file', file);

      const uploadRes = await fetch(`${API_BASE_URL}/api/pdf/pdf-to-long-image/upload`, {
        method: 'POST',
        body: uploadForm,
      });

      if (!uploadRes.ok) throw new Error('Upload failed.');
      const uploadData = await uploadRes.json();
      
      // 2. Process
      const processForm = new FormData();
      processForm.append('request_id', uploadData.request_id);
      processForm.append('filename', uploadData.filename);

      const processRes = await fetch(`${API_BASE_URL}/api/pdf/pdf-to-long-image/process`, {
        method: 'POST',
        body: processForm,
      });

      if (!processRes.ok) {
        const err = await processRes.json().catch(() => ({}));
        throw new Error(err.detail || `Processing failed (${processRes.status})`);
      }

      const processData = await processRes.json();
      const dlUrl = processData.download_url;
      if (!dlUrl) throw new Error('Download URL not provided by server.');

      // 3. Prepare Download
      const blobRes = await fetch(`${API_BASE_URL}${dlUrl}`);
      if (!blobRes.ok) throw new Error('Failed to fetch result file.');
      const blob = await blobRes.blob();
      const blobUrl = URL.createObjectURL(blob);
      setDownloadUrl(blobUrl);
      setPreviewBlobUrl(blobUrl);
      setIsDone(true);
      setShowPreview(true);
    } catch (err) {
      setErrorMsg(err.message || 'An unexpected error occurred.');
    } finally {
      setIsProcessing(false);
    }
  };

  const resetApp = () => {
    setFile(null);
    setIsProcessing(false);
    setIsDone(false);
    setErrorMsg(null);
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    setDownloadUrl(null);
    setPreviewBlobUrl(null);
    setShowPreview(false);
  };

  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 flex flex-col items-center">
      <div className="w-full max-w-4xl relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-4 mb-8 px-4">
          <h1 className="text-3xl font-black text-[#1e2a52]">PDF to Long Image</h1>
          <p className="text-sm text-slate-600 mt-2">Process your PDF using our advanced tools.</p>
        </div>

        {!isProcessing && !isDone && (
          <div className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-10 max-w-4xl mx-auto w-full">
            {errorMsg && (
              <div className="mb-5 p-4 text-red-700 bg-red-50 border border-red-200 rounded-xl text-sm font-medium">
                {errorMsg}
              </div>
            )}

            <div
              className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-14 text-center cursor-pointer transition-all duration-300 ${isDragOver ? 'border-indigo-500 bg-indigo-100' : 'border-indigo-200 bg-indigo-50/30'}`}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                ref={fileInputRef}
                onChange={e => handleFile(e.target.files[0])}
              />
              <p className="text-xl font-bold text-slate-800">
                {file ? file.name : 'Drag & Drop your PDF here'}
              </p>
            </div>

            <div className="text-center mt-8">
              <button
                onClick={handleProcess}
                disabled={!file}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 px-12 rounded-xl shadow-xl disabled:opacity-50"
              >
                Start Processing
              </button>
            </div>
          </div>
        )}

        {isProcessing && (
          <div className="flex flex-col items-center justify-center p-12 bg-white/70 shadow-2xl rounded-3xl min-h-[400px]">
            <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-8" />
            <h3 className="text-xl font-bold text-[#1e2a52]">Processing...</h3>
          </div>
        )}

        {isDone && (
          <div className="mt-6 flex flex-col items-center p-10 bg-emerald-50 rounded-3xl border border-emerald-100 shadow-2xl">
            <h3 className="text-2xl font-bold text-emerald-800 mb-4">Done!</h3>
            <div className="flex gap-4">
              <a
                href={downloadUrl}
                download
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 px-8 rounded-xl shadow-lg"
              >
                Download File
              </a>
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-xl shadow-lg"
              >
                {showPreview ? 'Hide Preview' : 'Preview PDF'}
              </button>
              <button
                onClick={resetApp}
                className="bg-slate-800 hover:bg-slate-900 text-white font-bold py-3 px-8 rounded-xl shadow-lg"
              >
                Process Another
              </button>
            </div>

            {showPreview && (
              <div className="w-full mt-8 border border-slate-300 rounded-xl overflow-hidden shadow-inner bg-white p-4">
                <img
                  src={previewBlobUrl}
                  alt="Long Image Preview"
                  className="w-full h-auto object-contain"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
