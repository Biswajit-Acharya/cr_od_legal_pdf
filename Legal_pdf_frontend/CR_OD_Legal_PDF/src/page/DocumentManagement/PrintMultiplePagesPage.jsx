import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Download, CheckCircle2, ArrowLeft, X, AlertCircle, Eye, Settings2, FileOutput, LayoutGrid, Frame, Crop } from 'lucide-react';
import apiClient from '../../api/apiClient';

export default function PrintMultiplePagesPage({ onBack }) {
  const toolName = "Print Multiple Pages per Sheet";
  const toolDesc = "N-up imposition: arrange multiple PDF pages onto single sheets for printing.";
  const accepted = { accept: ".pdf", label: "PDF files (.pdf)", mime: ["application/pdf"] };

  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  
  const [previewData, setPreviewData] = useState(null);
  const [downloadUrl, setDownloadUrl] = useState('');

  // Form State
  const [pageRange, setPageRange] = useState('');
  const [pagesPerSheet, setPagesPerSheet] = useState('4');
  const [paperSize, setPaperSize] = useState('a4');
  const [orientation, setOrientation] = useState('auto');
  const [customWidth, setCustomWidth] = useState(210);
  const [customHeight, setCustomHeight] = useState(297);
  const [pageOrder, setPageOrder] = useState('ltr');
  
  const [marginMm, setMarginMm] = useState(10);
  const [spacingMm, setSpacingMm] = useState(5);
  const [showBorders, setShowBorders] = useState(false);
  const [showCropMarks, setShowCropMarks] = useState(false);

  const inputRef = useRef();

  const handleFileChange = (e) => {
    if (e.target.files?.length) handleFiles(e.target.files);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) handleFiles(e.dataTransfer.files);
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

  const handlePreview = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError('');
    setPreviewData(null);
    setDownloadUrl('');

    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('page_range', pageRange);
      fd.append('pages_per_sheet', pagesPerSheet);
      fd.append('paper_size', paperSize);
      fd.append('orientation', orientation);
      fd.append('order', pageOrder);
      fd.append('margin_mm', marginMm);
      fd.append('spacing_mm', spacingMm);
      fd.append('custom_width_mm', customWidth);
      fd.append('custom_height_mm', customHeight);

      const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
      const res = await fetch(`${API_BASE_URL}/document-management/multi-page-sheet/preview`, {
        method: 'POST',
        body: fd
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to generate preview.');
      
      setPreviewData(data);
    } catch (err) {
      setError('Error generating preview: ' + err.message);
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
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('page_range', pageRange);
      fd.append('pages_per_sheet', pagesPerSheet);
      fd.append('paper_size', paperSize);
      fd.append('orientation', orientation);
      fd.append('order', pageOrder);
      fd.append('margin_mm', marginMm);
      fd.append('spacing_mm', spacingMm);
      fd.append('show_borders', showBorders);
      fd.append('show_crop_marks', showCropMarks);
      fd.append('custom_width_mm', customWidth);
      fd.append('custom_height_mm', customHeight);
      fd.append('output_name', '');

      const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
      const res = await fetch(`${API_BASE_URL}/document-management/multi-page-sheet/generate`, {
        method: 'POST',
        body: fd
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to generate PDF.');
      
      setDownloadUrl(data.download_url);
    } catch (err) {
      setError('Error generating PDF: ' + err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = () => {
    if (downloadUrl) {
      const a = document.createElement('a');
      a.href = apiClient.getFullUrl(downloadUrl);
      a.download = selectedFile.name.replace('.pdf', '_nup.pdf');
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  };

  // Preview Grid Renderer
  const renderPreviewGrid = () => {
    if (!previewData) return null;

    const g = previewData.grid;
    
    const cellW_pct = (previewData.cell_width_pt / previewData.sheet_width_pt) * 100;
    const cellH_pct = (previewData.cell_height_pt / previewData.sheet_height_pt) * 100;
    const marginW_pct = (previewData.margin_pt / previewData.sheet_width_pt) * 100;
    const marginH_pct = (previewData.margin_pt / previewData.sheet_height_pt) * 100;
    const spacingW_pct = (previewData.spacing_pt / previewData.sheet_width_pt) * 100;
    const spacingH_pct = (previewData.spacing_pt / previewData.sheet_height_pt) * 100;

    const cells = [];
    for (let r = 0; r < g.rows; r++) {
      for (let c = 0; c < g.cols; c++) {
        const idx = r * g.cols + c;
        const x_pct = marginW_pct + c * (cellW_pct + spacingW_pct);
        const y_pct = marginH_pct + r * (cellH_pct + spacingH_pct);
        const isFilled = idx < previewData.n_pages;
        
        cells.push(
          <div
            key={idx}
            className={`absolute flex items-center justify-center text-[10px] sm:text-xs rounded border border-dashed transition-colors shadow-sm ${
              isFilled ? 'bg-white border-[#1e2a52]/30 text-[#1e2a52] font-bold' : 'bg-[#1e2a52]/5 border-slate-300 text-slate-400 border-dotted'
            }`}
            style={{
              left: `${x_pct}%`,
              top: `${y_pct}%`,
              width: `${cellW_pct}%`,
              height: `${cellH_pct}%`
            }}
          >
            {isFilled && <span>{idx + 1}</span>}
          </div>
        );
      }
    }

    return (
      <div 
        className="relative bg-white border border-slate-300 shadow-md mx-auto" 
        style={{ 
          width: '100%', 
          maxWidth: '350px', 
          aspectRatio: `${previewData.sheet_width_pt} / ${previewData.sheet_height_pt}` 
        }}
      >
        {cells}
      </div>
    );
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
                <label className="block text-xs font-bold text-slate-700 mb-1.5">Page Range (e.g. 1-3, 5, 7-9)</label>
                <input
                  type="text"
                  placeholder="All pages"
                  value={pageRange}
                  onChange={(e) => setPageRange(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52] outline-none text-sm font-medium bg-white"
                />
              </div>
            </div>

            {/* Layout Settings */}
            <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6">
              <h3 className="text-lg font-bold text-[#1e2a52] mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <LayoutGrid className="w-5 h-5" />
                Layout Settings
              </h3>

              <div className="mb-4">
                <label className="block text-xs font-bold text-slate-700 mb-1.5">Pages per Sheet</label>
                <select
                  value={pagesPerSheet}
                  onChange={(e) => setPagesPerSheet(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] focus:ring-1 focus:ring-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
                >
                  <option value="2">2 pages (2x1)</option>
                  <option value="4">4 pages (2x2)</option>
                  <option value="6">6 pages (3x2)</option>
                  <option value="8">8 pages (4x2)</option>
                  <option value="9">9 pages (3x3)</option>
                  <option value="16">16 pages (4x4)</option>
                </select>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">Paper Size</label>
                  <select
                    value={paperSize}
                    onChange={(e) => setPaperSize(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
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
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
                  >
                    <option value="portrait">Portrait</option>
                    <option value="landscape">Landscape</option>
                    <option value="auto">Auto</option>
                  </select>
                </div>
              </div>

              {paperSize === 'custom' && (
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1.5">Width (mm)</label>
                    <input
                      type="number"
                      value={customWidth}
                      onChange={(e) => setCustomWidth(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1.5">Height (mm)</label>
                    <input
                      type="number"
                      value={customHeight}
                      onChange={(e) => setCustomHeight(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium"
                    />
                  </div>
                </div>
              )}

              <div className="mb-2">
                <label className="block text-xs font-bold text-slate-700 mb-1.5">Page Order</label>
                <select
                  value={pageOrder}
                  onChange={(e) => setPageOrder(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium bg-white cursor-pointer"
                >
                  <option value="ltr">Left to Right</option>
                  <option value="rtl">Right to Left</option>
                  <option value="ttb">Top to Bottom</option>
                </select>
              </div>
            </div>

            {/* Spacing & Options */}
            <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6">
              <h3 className="text-lg font-bold text-[#1e2a52] mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <Settings2 className="w-5 h-5" />
                Spacing & Options
              </h3>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">Margin (mm)</label>
                  <input
                    type="number"
                    value={marginMm}
                    onChange={(e) => setMarginMm(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">Spacing (mm)</label>
                  <input
                    type="number"
                    value={spacingMm}
                    onChange={(e) => setSpacingMm(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:border-[#1e2a52] outline-none text-sm font-medium"
                  />
                </div>
              </div>
              
              <div className="space-y-3 pt-4 border-t border-slate-100">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showBorders}
                    onChange={(e) => setShowBorders(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-[#1e2a52] focus:ring-[#1e2a52]"
                  />
                  <span className="text-sm font-medium text-slate-700 flex items-center gap-2">
                    <Frame className="w-4 h-4 text-slate-400" />
                    Show page borders
                  </span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showCropMarks}
                    onChange={(e) => setShowCropMarks(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-[#1e2a52] focus:ring-[#1e2a52]"
                  />
                  <span className="text-sm font-medium text-slate-700 flex items-center gap-2">
                    <Crop className="w-4 h-4 text-slate-400" />
                    Show crop marks
                  </span>
                </label>
              </div>
            </div>
          </div>

          {/* Right Column: Preview & Actions */}
          <div className="lg:col-span-7">
            <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6 h-full flex flex-col">
              <h3 className="text-lg font-bold text-[#1e2a52] mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
                <Eye className="w-5 h-5" />
                Sheet Preview
              </h3>

              {/* Preview Area */}
              <div className="flex-1 bg-slate-50/50 border border-slate-200 rounded-2xl p-6 mb-4 min-h-[400px] flex flex-col items-center justify-center relative overflow-hidden">
                
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
                    <LayoutGrid className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm font-medium">Upload a PDF and click Preview to see layout</p>
                  </div>
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    {renderPreviewGrid()}
                  </div>
                )}
              </div>

              {previewData && (
                <div className="text-center text-xs font-bold text-slate-500 mb-6 bg-slate-50 py-2 rounded-lg border border-slate-200">
                  {previewData.grid.cols}x{previewData.grid.rows} grid {' | '} 
                  {previewData.n_pages} pages {' | '} 
                  {previewData.grid.n_sheets} sheet(s) {' | '} 
                  {previewData.paper_size.toUpperCase()} {previewData.orientation}
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
                  Generate PDF
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
                    Download Imposed PDF
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