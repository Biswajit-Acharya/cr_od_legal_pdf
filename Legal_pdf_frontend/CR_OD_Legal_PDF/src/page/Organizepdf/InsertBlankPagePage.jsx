import React, { useState, useRef, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export default function InsertBlankPagePage() {
  const [file, setFile] = useState(null);
  
  // Tool options
  const [insertMode, setInsertMode] = useState('after');
  const [targetPage, setTargetPage] = useState(1);
  const [targetPageEnd, setTargetPageEnd] = useState('');
  const [blankPageCount, setBlankPageCount] = useState(1);
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewBlobUrl, setPreviewBlobUrl] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  const fileInputRef = useRef(null);

  const handleFile = (f) => {
    if (f && f.type === 'application/pdf') {
      setFile(f);
      setErrorMsg(null);
      const blob = new Blob([f], { type: 'application/pdf' });
      setPreviewUrl(URL.createObjectURL(blob));
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
      const processForm = new FormData();
      processForm.append('file', file);
      processForm.append('insert_mode', insertMode);
      processForm.append('target_page', targetPage);
      if (targetPageEnd) processForm.append('target_page_end', targetPageEnd);
      processForm.append('blank_page_count', blankPageCount);

      const processRes = await fetch(`${API_BASE_URL}/api/pdf/insert-blank-page/process`, {
        method: 'POST',
        body: processForm,
      });

      if (!processRes.ok) {
        let errDesc = `Processing failed (${processRes.status})`;
        try {
          const err = await processRes.json();
          errDesc = err.detail || errDesc;
        } catch (_) {}
        throw new Error(errDesc);
      }

      const processData = await processRes.json();
      const dlUrl = processData.download_url;
      if (!dlUrl) throw new Error('Download URL not provided by server.');

      // Fetch blob for both preview (inline) and download
      const blobRes = await fetch(`${API_BASE_URL}${dlUrl}`);
      if (!blobRes.ok) throw new Error('Failed to fetch result file.');
      const blob = await blobRes.blob();
      const blobUrl = URL.createObjectURL(blob);

      setDownloadUrl(blobUrl);
      setPreviewBlobUrl(blobUrl);
      setIsDone(true);
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
    setPreviewUrl(null);
    setShowPreview(false);
  };

  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 flex flex-col items-center">
      <div className="w-full max-w-4xl relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-4 mb-8 px-4">
          <h1 className="text-3xl font-black text-[#1e2a52]">Insert Blank Page</h1>
          <p className="text-sm text-slate-600 mt-2">Add blank pages anywhere in your PDF document.</p>
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

            {file && (
              <div className="mt-8 space-y-4 text-left bg-slate-50 p-6 rounded-xl border border-slate-200">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Insert Mode</label>
                  <select className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" value={insertMode} onChange={e => setInsertMode(e.target.value)}>
                    <option value="after">After Target Page</option>
                    <option value="before">Before Target Page</option>
                    <option value="start">At Start of Document</option>
                    <option value="end">At End of Document</option>
                    <option value="between">Between Pages (Target to End)</option>
                  </select>
                </div>
                {(insertMode === 'before' || insertMode === 'after' || insertMode === 'between') && (
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">Target Page</label>
                    <input type="number" min="1" className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" value={targetPage} onChange={e => setTargetPage(e.target.value)} />
                  </div>
                )}
                {insertMode === 'between' && (
                  <div>
                    <label className="block text-sm font-semibold text-slate-700 mb-1">End Page (Optional)</label>
                    <input type="number" min="1" className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" value={targetPageEnd} onChange={e => setTargetPageEnd(e.target.value)} placeholder="Leave empty to go to the end" />
                  </div>
                )}
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Number of Blank Pages</label>
                  <input type="number" min="1" className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" value={blankPageCount} onChange={e => setBlankPageCount(e.target.value)} />
                </div>
              </div>
            )}

            {file && previewUrl && (
              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50/50 overflow-hidden h-[400px] shadow-inner w-full">
                  <iframe src={`${previewUrl}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`} className="w-full h-full border-none" title="PDF Preview" />
              </div>
            )}

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
              <div className="w-full h-[600px] mt-8 border border-slate-300 rounded-xl overflow-hidden shadow-inner bg-white">
                <iframe
                  src={`${previewBlobUrl}#toolbar=0&navpanes=0&scrollbar=0&view=FitH`}
                  className="w-full h-full"
                  title="PDF Preview"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
