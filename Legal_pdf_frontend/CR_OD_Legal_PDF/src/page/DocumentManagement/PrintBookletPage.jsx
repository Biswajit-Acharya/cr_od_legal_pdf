import React, { useState, useRef } from 'react';
import { Upload, FileText, Download, CheckCircle2, ArrowLeft, X, AlertCircle, Eye, Settings2, FileOutput, Maximize, Crop, Frame } from 'lucide-react';
import apiClient from '../../api/apiClient';

export default function PrintBookletPage({ onBack }) {
  const toolName = "Print Booklet";
  const toolDesc = "PDF booklet imposition: fold and staple ready layout with duplex support.";
  const accepted = { accept: ".pdf", label: "PDF files (.pdf)", mime: ["application/pdf"] };

  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  
  const [previewData, setPreviewData] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState('');

  // Form State
  const [pageRange, setPageRange] = useState('');
  const [paperSize, setPaperSize] = useState('a4');
  const [orientation, setOrientation] = useState('portrait');
  const [customW, setCustomW] = useState(210);
  const [customH, setCustomH] = useState(297);
  const [binding, setBinding] = useState('left');
  const [duplex, setDuplex] = useState('long-edge');
  
  const [marginInner, setMarginInner] = useState(15);
  const [marginOuter, setMarginOuter] = useState(10);
  const [gutter, setGutter] = useState(8);
  const [bleed, setBleed] = useState(0);
  
  const [showBorders, setShowBorders] = useState(false);
  const [showCropMarks, setShowCropMarks] = useState(false);

  const inputRef = useRef();

  const handleFileChange = (e) => {
    if (e.target.files?.length) {
      handleFiles(e.target.files);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFiles = (files) => {
    setError('');
    setPreviewData(null);
    setDownloadUrl('');
    
    const file = files[0];
    if (file.type === "application/pdf" || file.name.toLowerCase().endsWith('.pdf')) {
      setSelectedFile(file);
    } else {
      setError(`Only PDF files are accepted. Rejected: ${file.name}`);
    }
  };

  const handleRemove = () => {
    setSelectedFile(null);
    setPreviewData(null);
    setDownloadUrl('');
    setError('');
  };

  const buildFormData = () => {
    const fd = new FormData();
    fd.append('file', selectedFile);
    fd.append('page_range', pageRange);
    fd.append('paper_size', paperSize);
    fd.append('orientation', orientation);
    fd.append('binding', binding);
    fd.append('duplex', duplex);
    fd.append('margin_inner_mm', marginInner);
    fd.append('margin_outer_mm', marginOuter);
    fd.append('gutter_mm', gutter);
    fd.append('bleed_mm', bleed);
    if (paperSize === 'custom') {
      fd.append('custom_w', customW);
      fd.append('custom_h', customH);
    }
    fd.append('show_borders', showBorders);
    fd.append('show_crop_marks', showCropMarks);
    return fd;
  };

  const handlePreview = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError('');
    setPreviewData(null);
    setDownloadUrl('');

    try {
      const data = await apiClient.uploadFiles('/api/document-management/print-booklet/preview', buildFormData());
      if (data) {
        if (data.booklet) {
          setPreviewData({
            ...data.booklet,
            paper_size: data.paper_size || paperSize,
            binding: data.binding || binding
          });
        } else {
          setPreviewData(data);
        }
      }
    } catch (err) {
      setError(err.message || 'Error generating preview.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleGenerate = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError('');
    setDownloadUrl('');

    try {
      const data = await apiClient.uploadFiles('/api/document-management/print-booklet/generate', buildFormData());
      if (data && data.download_url) {
        setDownloadUrl(data.download_url);
      }
    } catch (err) {
      setError(err.message || 'Error generating booklet.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (downloadUrl === '#mock-download') {
      alert('Mock download started.');
      return;
    }
    if (downloadUrl) {
      const a = document.createElement('a');
      a.href = apiClient.getFullUrl(downloadUrl);
      a.download = selectedFile.name.replace('.pdf', '_booklet.pdf');
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  return (
    <div className="flex-1 flex flex-col w-full bg-transparent relative z-20 min-h-screen">
      <div className="w-full max-w-[1200px] mx-auto px-4 sm:px-6 md:px-10 pt-1 sm:pt-5">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 bg-white text-[#1e2a52] font-bold px-4 py-2 rounded-full shadow-sm border border-slate-200 hover:shadow-md hover:scale-105 transition-all cursor-pointer text-xs sm:text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>
      </div>

      <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
        <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
          {toolName}
        </h1>
        <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
          {toolDesc}
        </p>
      </div>

      <div className="w-full max-w-[1200px] mx-auto px-4 sm:px-6 pb-14">
        
        {/* Info Note */}
        <div className="bg-[#e8f0e2] border border-[#1e2a52]/20 rounded-2xl p-4 mb-8 text-sm text-[#1e2a52] font-medium flex items-start gap-3 shadow-sm max-w-4xl mx-auto">
           <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
           <p>
             Booklet printing rearranges pages so that after duplex printing, folding and stapling, pages read in correct order.
             Blank pages are auto-added when page count isn't divisible by 4.
           </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left Column: Controls */}
          <div className="lg:col-span-5 space-y-6">
            
            {/* File Source */}
            <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6">
              <h3 className="text-lg font-bold text-[#1e2a52] mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <FileText className="w-5 h-5" />
                PDF Source
              </h3>
              
              {!selectedFile ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  onClick={() => inputRef.current?.click()}
                  className={`relative border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
                    isDragging
                      ? 'border-[#1e2a52] bg-[#e8f0e2]'
                      : 'border-[#1e2a52]/30 bg-[#f8faf7] hover:border-[#1e2a52] hover:bg-[#eff4ea]'
                  }`}
                >
                  <input
                    ref={inputRef}
                    type="file"
                    accept={accepted.accept}
                    className="hidden"
                    onChange={handleFileChange}
                  />
                  <div className="w-12 h-12 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <Upload className="w-6 h-6 text-[#1e2a52]" />
                  </div>
                  <p className="text-sm font-bold text-[#1e2a52] mb-1">Drop PDF here or click to browse</p>
                </div>
              ) : (
                <div className="flex items-center gap-4 bg-[#f8faf7] border border-[#1e2a52]/20 rounded-2xl p-4">
                  <div className="w-10 h-10 bg-[#1e2a52]/10 rounded-xl flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-[#1e2a52]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-[#1e2a52] text-sm truncate">{selectedFile.name}</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <button
                    onClick={handleRemove}
                    className="w-8 h-8 flex items-center justify-center rounded-full bg-white border border-slate-200 text-slate-400 hover:text-red-500 hover:border-red-200 hover:bg-red-50 transition-all shrink-0"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              <div className="mt-4">
                <label className="block text-xs font-bold text-slate-700 mb-1.5">Page Range (e.g. 1-8, 10)</label>
                <input
                  type="text"
                  placeholder="All pages"
                  value={pageRange}
                  onChange={(e) => setPageRange(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52] outline-none text-sm font-medium bg-white"
                />
              </div>
            </div>

            {/* Booklet Settings */}
            <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6">
              <h3 className="text-lg font-bold text-[#1e2a52] mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <Settings2 className="w-5 h-5" />
                Booklet Settings
              </h3>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">Paper Size</label>
                  <select
                    value={paperSize}
                    onChange={(e) => setPaperSize(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
                  >
                    <option value="a4">A4</option>
                    <option value="a3">A3</option>
                    <option value="letter">Letter</option>
                    <option value="legal">Legal</option>
                    <option value="custom">Custom (mm)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">Orientation</label>
                  <select
                    value={orientation}
                    onChange={(e) => setOrientation(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
                  >
                    <option value="portrait">Portrait</option>
                    <option value="landscape">Landscape</option>
                  </select>
                </div>
              </div>

              {paperSize === 'custom' && (
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1.5">Width (mm)</label>
                    <input
                      type="number"
                      value={customW}
                      onChange={(e) => setCustomW(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1.5">Height (mm)</label>
                    <input
                      type="number"
                      value={customH}
                      onChange={(e) => setCustomH(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium"
                    />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">Binding Position</label>
                  <select
                    value={binding}
                    onChange={(e) => setBinding(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
                  >
                    <option value="left">Left</option>
                    <option value="right">Right</option>
                    <option value="top">Top</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">Duplex Edge</label>
                  <select
                    value={duplex}
                    onChange={(e) => setDuplex(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
                  >
                    <option value="long-edge">Long Edge</option>
                    <option value="short-edge">Short Edge</option>
                  </select>
                </div>
              </div>
            </div>


          </div>

          {/* Right Column: Preview & Actions */}
          <div className="lg:col-span-7">
            <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6 h-full flex flex-col">
              <h3 className="text-lg font-bold text-[#1e2a52] mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <Eye className="w-5 h-5" />
                Booklet Preview
              </h3>

              {/* Preview Area */}
              <div className="flex-1 bg-slate-50 border border-slate-200 rounded-2xl p-6 mb-4 min-h-[400px] flex flex-col items-center justify-center relative overflow-y-auto custom-scrollbar">
                
                {isProcessing ? (
                  <div className="w-full flex flex-col items-center justify-center">
                    <div className="speeder-loader-wrapper mb-4">
                      <div className="loader"><span><span></span><span></span><span></span><span></span></span><div className="base"><span></span><div className="face"></div></div></div>
                      <div className="longfazers"><span></span><span></span><span></span><span></span></div>
                    </div>
                    <p className="text-sm font-bold text-[#1e2a52] animate-pulse">Processing Layout...</p>
                  </div>
                ) : !previewData ? (
                  <div className="text-center text-slate-400">
                    <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm font-medium">Upload a PDF and click Preview to see booklet layout</p>
                  </div>
                ) : (
                  <div className="w-full flex flex-col items-center space-y-6">
                    {previewData.sheet_layouts.map((sheet, idx) => (
                      <div key={idx} className="bg-white border border-slate-300 rounded-xl p-4 shadow-sm w-full max-w-md">
                        <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 border-b border-slate-100 pb-2 text-center">
                          Sheet {sheet.sheet_number} of {previewData.sheets}
                        </div>
                        
                        <div className="flex flex-col gap-4">
                          {/* Front */}
                          <div>
                            <div className="flex bg-slate-100 p-2 rounded-lg border border-slate-200 shadow-inner">
                              <div className={`flex-1 flex items-center justify-center py-6 text-sm font-bold border-r border-slate-300 border-dashed ${sheet.front.left >= 0 ? 'bg-white text-[#1e2a52] border border-solid border-[#1e2a52]/20 shadow-sm mx-1 rounded' : 'text-slate-400'}`}>
                                {sheet.front.left >= 0 ? `P${sheet.front.left + 1}` : 'Blank'}
                              </div>
                              <div className={`flex-1 flex items-center justify-center py-6 text-sm font-bold ${sheet.front.right >= 0 ? 'bg-white text-[#1e2a52] border border-solid border-[#1e2a52]/20 shadow-sm mx-1 rounded' : 'text-slate-400'}`}>
                                {sheet.front.right >= 0 ? `P${sheet.front.right + 1}` : 'Blank'}
                              </div>
                            </div>
                            <div className="text-[10px] text-center text-slate-400 mt-1 uppercase font-bold">Front Side</div>
                          </div>

                          {/* Back */}
                          <div>
                            <div className="flex bg-slate-100 p-2 rounded-lg border border-slate-200 shadow-inner">
                              <div className={`flex-1 flex items-center justify-center py-6 text-sm font-bold border-r border-slate-300 border-dashed ${sheet.back.left >= 0 ? 'bg-white text-[#1e2a52] border border-solid border-[#1e2a52]/20 shadow-sm mx-1 rounded' : 'text-slate-400'}`}>
                                {sheet.back.left >= 0 ? `P${sheet.back.left + 1}` : 'Blank'}
                              </div>
                              <div className={`flex-1 flex items-center justify-center py-6 text-sm font-bold ${sheet.back.right >= 0 ? 'bg-white text-[#1e2a52] border border-solid border-[#1e2a52]/20 shadow-sm mx-1 rounded' : 'text-slate-400'}`}>
                                {sheet.back.right >= 0 ? `P${sheet.back.right + 1}` : 'Blank'}
                              </div>
                            </div>
                            <div className="text-[10px] text-center text-slate-400 mt-1 uppercase font-bold">Back Side</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {previewData && (
                <div className="text-center text-xs font-bold text-slate-500 mb-6 bg-slate-50 py-2 rounded-lg border border-slate-200">
                  {previewData.original_pages} original pages 
                  {previewData.blank_pages > 0 && ` → ${previewData.padded_pages} padded (+${previewData.blank_pages} blank)`}
                  {' | '} {previewData.sheets} sheets {' | '} {previewData.paper_size.toUpperCase()} {previewData.binding} binding
                </div>
              )}

              {error && (
                <div className="mb-4 flex items-start gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-xs sm:text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center justify-center gap-3">
                <button
                  onClick={handlePreview}
                  disabled={!selectedFile || isProcessing}
                  className="bg-[#e8f0e2] hover:bg-[#d5e3cb] text-[#1e2a52] px-6 py-2.5 rounded-xl font-bold shadow-sm transition-all text-sm cursor-pointer inline-flex items-center gap-2 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:pointer-events-none border border-[#1e2a52]/10"
                >
                  <Eye className="w-4 h-4" />
                  Preview Layout
                </button>
                <button
                  onClick={handleGenerate}
                  disabled={!selectedFile || isProcessing}
                  className="bg-[#1e2a52] hover:bg-[#16203e] text-white px-8 py-2.5 rounded-xl font-bold shadow-md transition-all text-sm cursor-pointer inline-flex items-center gap-2 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:pointer-events-none"
                >
                  <FileOutput className="w-4 h-4 text-[#c7dca7]" />
                  Generate Booklet
                </button>
              </div>

              {/* Download Result */}
              {downloadUrl && !isProcessing && (
                <div className="mt-6 pt-6 border-t border-slate-100 flex justify-center animate-in slide-in-from-bottom-4 fade-in">
                  <button
                    onClick={handleDownload}
                    className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-3.5 rounded-full font-bold shadow-md transition-all text-sm cursor-pointer hover:scale-105"
                  >
                    <Download className="w-4 h-4" />
                    Download Imposed Booklet PDF
                  </button>
                </div>
              )}

            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
