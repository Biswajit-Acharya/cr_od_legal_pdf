import React, { useState, useRef, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export default function ReorderBookmarksAfterPageChangesPage() {
  const [file, setFile] = useState(null);
  
  // Options
  const [mappingText, setMappingText] = useState('1:2, 2:1');
  const [preserveHierarchy, setPreserveHierarchy] = useState(true);
  const [preserveMetadata, setPreserveMetadata] = useState(true);

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
      const mappingObj = {};
      mappingText.split(',').forEach(pair => {
         const [k, v] = pair.split(':').map(s => s.trim());
         if(k && v) mappingObj[k] = parseInt(v, 10);
      });

      if (Object.keys(mappingObj).length === 0) {
          throw new Error("Please provide a valid mapping (e.g. 1:2, 2:1)");
      }

      const processForm = new FormData();
      processForm.append('file', file);
      processForm.append('page_mapping', JSON.stringify(mappingObj));
      processForm.append('preserve_hierarchy', preserveHierarchy);
      processForm.append('preserve_metadata', preserveMetadata);

      const processRes = await fetch(`${API_BASE_URL}/api/pdf/reorder-bookmarks/process`, {
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
      if (!processData.request_id || !processData.filename) {
          throw new Error('Download details not provided by server.');
      }
      const dlUrl = `/api/pdf/reorder-bookmarks/download/${processData.request_id}/${processData.filename}`;

      // Fetch blob for preview (to avoid download-forced headers)
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
    setPreviewUrl(null);
    setPreviewBlobUrl(null);
    setShowPreview(false);
  };

  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 flex flex-col items-center">
      <div className="w-full max-w-4xl relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-4 mb-8 px-4">
          <h1 className="text-3xl font-black text-[#1e2a52]">Reorder Bookmarks</h1>
          <p className="text-sm text-slate-600 mt-2">Update bookmark destinations after page changes.</p>
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
                  <label className="block text-sm font-semibold text-slate-700 mb-1">Page Mapping (Old:New)</label>
                  <input type="text" className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none" value={mappingText} onChange={e => setMappingText(e.target.value)} placeholder="e.g. 1:2, 2:1" />
                  <p className="text-xs text-slate-500 mt-1">Specify how old pages map to new pages, separated by commas.</p>
                </div>
                
                <label className="flex items-start gap-3 p-3 bg-white border border-slate-200 rounded-xl cursor-pointer hover:bg-indigo-50/50">
                    <input type="checkbox" className="mt-1 w-4 h-4 text-indigo-600 rounded border-slate-300" checked={preserveHierarchy} onChange={(e) => setPreserveHierarchy(e.target.checked)} />
                    <div>
                      <strong className="block text-sm font-semibold text-slate-700">Preserve Hierarchy</strong>
                      <span className="block text-xs text-slate-500 mt-0.5">Keep nested bookmark structures intact.</span>
                    </div>
                </label>
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
