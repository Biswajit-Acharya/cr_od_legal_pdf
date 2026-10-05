import React, { useState, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ArrowLeft } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

// Setup pdf.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

// Signature Drawing Pad Component
const SignaturePad = ({ onSave, onClear }) => {
  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.strokeStyle = '#000000';
    }
  }, []);

  const getCoordinates = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    if (e.touches && e.touches.length > 0) {
      return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const startDrawing = (e) => {
    const { x, y } = getCoordinates(e);
    const ctx = canvasRef.current.getContext('2d');
    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
  };

  const draw = (e) => {
    if (!isDrawing) return;
    const { x, y } = getCoordinates(e);
    const ctx = canvasRef.current.getContext('2d');
    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    if (isDrawing) {
      setIsDrawing(false);
      onSave(canvasRef.current.toDataURL('image/png'));
    }
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    onClear();
  };

  return (
    <div className="flex flex-col items-center gap-3 w-full">
      <div className="border-2 border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm w-full relative">
        <canvas
          ref={canvasRef}
          width={320}
          height={160}
          className="w-full h-[160px] cursor-crosshair touch-none"
          onMouseDown={startDrawing}
          onMouseMove={draw}
          onMouseUp={stopDrawing}
          onMouseLeave={stopDrawing}
          onTouchStart={startDrawing}
          onTouchMove={draw}
          onTouchEnd={stopDrawing}
        />
        <div className="absolute bottom-2 left-2 pointer-events-none opacity-20 flex gap-2 items-center">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
            <span className="font-bold text-xs uppercase tracking-wider">Draw Signature</span>
        </div>
      </div>
      <button type="button" onClick={clearCanvas} className="text-sm font-semibold text-slate-500 hover:text-slate-700 underline underline-offset-2 transition-colors">
        Clear Canvas
      </button>
    </div>
  );
};

export default function WatermarkProtectionPage({ tool, onBack }) {
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  
  // React-PDF states
  const [previewFile, setPreviewFile] = useState(null);
  const [pdfDimensions, setPdfDimensions] = useState({ width: 0, height: 0 });
  const [renderScale, setRenderScale] = useState(1);
  const containerRef = useRef(null);

  // Settings
  const [watermarkType, setWatermarkType] = useState('text'); // text, image, signature
  const [position, setPosition] = useState('custom'); // centered, custom
  const [opacity, setOpacity] = useState(80);
  const [rotation, setRotation] = useState(0);

  // Drag State
  const [dragPos, setDragPos] = useState({ x: 50, y: 50 });
  const [isDraggingWM, setIsDraggingWM] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, currentX: 50, currentY: 50 });

  // Text Settings
  const [text, setText] = useState('CONFIDENTIAL');
  const [fontFamily, setFontFamily] = useState('Helvetica');
  const [fontSize, setFontSize] = useState(60);
  const [fontColor, setFontColor] = useState('#FF0000');
  const [styleBold, setStyleBold] = useState(false);
  const [styleItalic, setStyleItalic] = useState(false);

  // Image / Signature File Settings
  const [imageBytes, setImageBytes] = useState(null);
  const [imageType, setImageType] = useState('png'); // png or jpeg
  const [scale, setScale] = useState(1.0);
  const [sigMode, setSigMode] = useState('draw'); // draw, upload
  const [sigCanvasData, setSigCanvasData] = useState(null);

  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const sigUploadRef = useRef(null);

  // Backend Result
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [downloadFilename, setDownloadFilename] = useState('');

  const toolName = tool?.name || 'Watermark Protection';
  const toolDesc = tool?.description || 'Protect document ownership and stop unauthorized reuse with dynamic watermarks.';

  useEffect(() => {
    if (files.length > 0) {
      const reader = new FileReader();
      reader.onload = (e) => setPreviewFile(e.target.result);
      reader.readAsDataURL(files[0]);
    } else {
      setPreviewFile(null);
    }
  }, [files]);

  useEffect(() => {
    // Reset drag position to center when document changes or position mode changes
    if (position === 'centered' && pdfDimensions.width) {
      setDragPos({ x: (pdfDimensions.width * renderScale) / 2, y: (pdfDimensions.height * renderScale) / 2 });
    }
  }, [position, pdfDimensions, renderScale]);

  const handlePageLoad = (page) => {
    const { originalWidth, originalHeight } = page;
    setPdfDimensions({ width: originalWidth, height: originalHeight });
    
    // Calculate render scale based on container width
    if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        const s = containerWidth / originalWidth;
        setRenderScale(s);
        if (position === 'centered') {
            setDragPos({ x: containerWidth / 2, y: (originalHeight * s) / 2 });
        } else {
            setDragPos({ x: containerWidth / 2, y: (originalHeight * s) / 2 });
        }
    }
  };

  // Drag Handlers
  const handleWmMouseDown = (e) => {
    if (position === 'centered') {
        setPosition('custom'); // Auto switch to custom if they drag
    }
    setIsDraggingWM(true);
    dragRef.current.startX = e.clientX;
    dragRef.current.startY = e.clientY;
    dragRef.current.currentX = dragPos.x;
    dragRef.current.currentY = dragPos.y;
    e.stopPropagation();
    e.preventDefault();
  };

  const handleWmMouseMove = (e) => {
    if (!isDraggingWM) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    
    let newX = dragRef.current.currentX + dx;
    let newY = dragRef.current.currentY + dy;
    
    // Constrain to container bounds
    if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        newX = Math.max(0, Math.min(newX, rect.width));
        newY = Math.max(0, Math.min(newY, rect.height));
    }

    setDragPos({ x: newX, y: newY });
  };

  const handleWmMouseUp = () => {
    setIsDraggingWM(false);
  };

  useEffect(() => {
    if (isDraggingWM) {
      window.addEventListener('mousemove', handleWmMouseMove);
      window.addEventListener('mouseup', handleWmMouseUp);
    } else {
      window.removeEventListener('mousemove', handleWmMouseMove);
      window.removeEventListener('mouseup', handleWmMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleWmMouseMove);
      window.removeEventListener('mouseup', handleWmMouseUp);
    };
  }, [isDraggingWM]);

  // File Handlers
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };
  
  const handleDragLeave = () => setIsDragOver(false);
  
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const validFiles = Array.from(e.dataTransfer.files).filter(f => f.type === 'application/pdf');
      if (validFiles.length > 0) setFiles(prev => [...prev, ...validFiles]);
    }
  };

  const removeFile = (indexToRemove) => {
    setFiles(files.filter((_, index) => index !== indexToRemove));
    if (files.length - 1 === 0) {
      setIsSuccess(false);
      setIsProcessing(false);
      setPreviewFile(null);
    }
  };

  const handleImageUpload = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setImageType(file.type);
      const reader = new FileReader();
      reader.onload = (ev) => setImageBytes(ev.target.result);
      reader.readAsArrayBuffer(file);
    }
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setIsFlying(true);
    
    setTimeout(async () => {
      setIsProcessing(true);
      
      try {
        const file = files[0]; // Process first file for now in this UI
        const formData = new FormData();
        formData.append('file', file);
        
        let backendType = watermarkType;
        if (watermarkType === 'signature') backendType = 'image';
        
        formData.append('watermark_type', backendType);
        formData.append('position', position);
        formData.append('opacity', opacity);
        formData.append('rotation', rotation);
        formData.append('pages', 'all');
        
        // Pass X/Y coordinates if custom placement
        if (position === 'custom' && pdfDimensions.width) {
            const pdfX = dragPos.x / renderScale;
            const pdfY = dragPos.y / renderScale; // PyMuPDF origin is top-left, matching the screen coordinates!
            formData.append('pos_x', pdfX);
            formData.append('pos_y', pdfY);
        }

        if (watermarkType === 'text') {
            formData.append('text', text);
            formData.append('font_size', fontSize);
            formData.append('font_color', fontColor);
        } else {
            let blobToUpload = null;
            if (watermarkType === 'image' && imageBytes) {
                blobToUpload = new Blob([imageBytes], { type: imageType });
            } else if (watermarkType === 'signature') {
                if (sigMode === 'draw' && sigCanvasData) {
                    const res = await fetch(sigCanvasData);
                    blobToUpload = await res.blob();
                } else if (sigMode === 'upload' && imageBytes) {
                    blobToUpload = new Blob([imageBytes], { type: imageType });
                }
            }
            if (blobToUpload) {
                formData.append('image_file', blobToUpload, 'watermark.png');
                formData.append('scale', scale * 100);
            } else {
                throw new Error('Please select an image or draw a signature.');
            }
        }

        const response = await fetch(`${API_BASE_URL}/api/pdf/security/watermark`, {
            method: 'POST',
            body: formData,
        });
        
        if (!response.ok) {
            const errData = await response.json().catch(() => null);
            throw new Error(errData?.detail || 'Watermark failed on the server.');
        }

        const data = await response.json();
        if (data.download_url) {
            setDownloadUrl(`${API_BASE_URL}${data.download_url}`);
            setDownloadFilename(data.output_file || `watermarked_${file.name}`);
        }
        
        setIsSuccess(true);
      } catch (err) {
        console.error(err);
        alert(err.message || "Error generating watermark.");
      } finally {
        setIsProcessing(false);
        setIsFlying(false);
      }
    }, 500);
  };

  const resetAll = () => {
    setFiles([]);
    setIsSuccess(false);
    setPreviewFile(null);
    setDownloadUrl(null);
  };

  // Dynamic preview styling
  let previewWMStyle = {
    position: 'absolute',
    left: `${dragPos.x}px`,
    top: `${dragPos.y}px`,
    transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
    opacity: opacity / 100,
    cursor: isDraggingWM ? 'grabbing' : 'grab',
    zIndex: 10,
    userSelect: 'none'
  };

  let previewContent = null;
  if (watermarkType === 'text') {
    previewWMStyle = {
        ...previewWMStyle,
        color: fontColor,
        fontSize: `${fontSize * renderScale}px`,
        fontFamily: fontFamily.toLowerCase().includes('times') ? 'serif' : fontFamily.toLowerCase().includes('courier') ? 'monospace' : 'sans-serif',
        fontWeight: styleBold ? 'bold' : 'normal',
        fontStyle: styleItalic ? 'italic' : 'normal',
        whiteSpace: 'nowrap'
    };
    previewContent = <div style={previewWMStyle} onMouseDown={handleWmMouseDown}>{text || 'TEXT'}</div>;
  } else if (watermarkType === 'image' || watermarkType === 'signature') {
      let imgSrc = null;
      if (watermarkType === 'image' && imageBytes) {
          const blob = new Blob([imageBytes], { type: imageType });
          imgSrc = URL.createObjectURL(blob);
      } else if (watermarkType === 'signature') {
          if (sigMode === 'draw' && sigCanvasData) imgSrc = sigCanvasData;
          else if (sigMode === 'upload' && imageBytes) {
              const blob = new Blob([imageBytes], { type: imageType });
              imgSrc = URL.createObjectURL(blob);
          }
      }
      
      if (imgSrc) {
          const imgWidth = 200 * scale * renderScale; // Mock default width calculation
          previewContent = <div style={previewWMStyle} onMouseDown={handleWmMouseDown}><img src={imgSrc} style={{width: `${imgWidth}px`, pointerEvents: 'none'}} alt="WM" /></div>
      } else {
          previewContent = <div style={{...previewWMStyle, padding: '10px', border: '2px dashed #999', backgroundColor: 'rgba(255,255,255,0.5)'}} onMouseDown={handleWmMouseDown}>[No Image]</div>;
      }
  }

  return (
    <div className="flex-1 flex flex-col w-full relative z-20 min-h-screen bg-transparent p-4 sm:p-8">
      <div className="w-full max-w-[1200px] mx-auto px-4 pb-4 relative z-30 flex-none text-left">
        <button onClick={onBack} className="inline-flex items-center gap-2 bg-white text-[#1e2a52] font-bold px-4 py-2 rounded-full shadow-md border border-slate-200 hover:shadow-lg hover:scale-105 transition-all cursor-pointer text-xs sm:text-sm">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
      </div>

      <div className="w-full max-w-6xl mx-auto relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-2 mb-8 px-4">
          <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">{toolName}</h1>
          <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">{toolDesc}</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 justify-center items-start w-full">
          {/* Left Column (Upload and Preview) */}
          <div className="w-full lg:max-w-2xl flex flex-col gap-6 mx-auto lg:mx-0 transition-all duration-500">
            <div className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden flex-1">
              {!previewFile && (
                  <div
                    className={`upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 border-indigo-200 bg-indigo-50/30 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group flex flex-col justify-center min-h-[300px] ${isDragOver ? 'border-indigo-500 bg-indigo-50 scale-[1.01]' : ''}`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <input type="file" accept=".pdf" hidden ref={fileInputRef} onChange={handleFileChange} />
                    <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                      <svg className="w-10 h-10 text-indigo-600" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                    </div>
                    <p className="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                      Drag & drop a PDF here
                    </p>
                    <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse</span></p>
                  </div>
              )}

              {files.length > 0 && (
                <div className="file-list mb-6 space-y-3">
                  {files.map((file, index) => (
                    <div key={index} className="file-item flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm">
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                          </svg>
                        </div>
                        <span className="font-medium text-slate-700 truncate">{file.name}</span>
                      </div>
                      <button onClick={() => removeFile(index)} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* LIVE PDF PREVIEW */}
              {previewFile && (
                <div className="w-full flex flex-col items-center">
                    <p className="text-xs text-slate-500 mb-2 font-bold uppercase">Drag the watermark to position it</p>
                    <div 
                        className="relative border border-slate-300 shadow-sm overflow-hidden bg-white" 
                        ref={containerRef}
                        style={{ width: '100%', maxWidth: '100%' }}
                    >
                        <Document file={previewFile} loading="Loading PDF...">
                            <Page 
                                pageNumber={1} 
                                width={containerRef.current ? containerRef.current.clientWidth : undefined} 
                                onLoadSuccess={handlePageLoad}
                                renderTextLayer={false}
                                renderAnnotationLayer={false}
                            />
                        </Document>
                        {previewContent}
                    </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column (Options) */}
          {files.length > 0 && !isProcessing && !isSuccess && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden mx-auto lg:mx-0 transition-all duration-500 animate-fade-in-up">
              
              {/* Tabs */}
              <div className="flex gap-1 p-1 bg-slate-100/80 backdrop-blur-sm rounded-xl mb-6 overflow-x-auto">
                {['text', 'image', 'signature'].map((tab) => (
                  <button key={tab} onClick={() => setWatermarkType(tab)} className={`flex-1 py-2.5 px-3 text-sm font-bold rounded-lg transition-all capitalize ${watermarkType === tab ? 'text-[#1e2a52] bg-white shadow-sm border border-indigo-100' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}>
                    {tab}
                  </button>
                ))}
              </div>

              <div className="space-y-6">
                
                {/* Global Settings */}
                <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Location & Appearance</h3>
                  
                  <div className="flex items-center gap-4 border p-1 rounded-xl bg-slate-50">
                    <button onClick={() => setPosition('centered')} className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${position === 'centered' ? 'bg-white shadow border border-slate-200 text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}>Centered</button>
                    <button onClick={() => setPosition('custom')} className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${position === 'custom' ? 'bg-white shadow border border-slate-200 text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}>Custom</button>
                  </div>
                  
                  {position === 'custom' && (
                      <p className="text-xs text-indigo-600 font-bold text-center">You can directly drag the watermark on the preview!</p>
                  )}

                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm font-semibold text-slate-600">Opacity: {opacity}%</label>
                    </div>
                    <input type="range" min="10" max="100" value={opacity} onChange={(e) => setOpacity(e.target.value)} className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#1e2a52]" />
                  </div>

                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm font-semibold text-slate-600">Rotation: {rotation}°</label>
                    </div>
                    <input type="range" min="0" max="360" value={rotation} onChange={(e) => setRotation(e.target.value)} className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#1e2a52]" />
                  </div>
                </div>

                {/* Specific Settings Based on Tab */}
                {watermarkType === 'text' && (
                  <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Text Settings</h3>
                    
                    <div>
                      <label className="block text-sm font-semibold text-slate-600 mb-2">Watermark Text</label>
                      <textarea value={text} onChange={(e) => setText(e.target.value)} rows="2" className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold focus:ring-2 focus:ring-indigo-100 focus:border-[#1e2a52] outline-none transition-all resize-none" placeholder="Enter watermark text..."></textarea>
                    </div>

                    <div className="flex gap-3">
                      <div className="flex-[2]">
                        <label className="block text-xs font-semibold text-slate-500 mb-1">Font Family</label>
                        <select value={fontFamily} onChange={(e) => setFontFamily(e.target.value)} className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-100 focus:border-[#1e2a52] outline-none transition-all">
                          <option value="Helvetica">Helvetica</option>
                          <option value="Times">Times</option>
                          <option value="Courier">Courier</option>
                        </select>
                      </div>
                      <div className="flex-1">
                        <label className="block text-xs font-semibold text-slate-500 mb-1">Size</label>
                        <input type="number" value={fontSize} onChange={(e) => setFontSize(e.target.value)} className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-100 focus:border-[#1e2a52] outline-none transition-all" />
                      </div>
                    </div>

                    <div className="flex gap-3 items-center">
                      <div className="flex gap-2 border border-slate-200 rounded-xl p-1 bg-slate-50">
                        <button onClick={() => setStyleBold(!styleBold)} className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg transition-colors ${styleBold ? 'bg-white shadow text-slate-800' : 'text-slate-400 hover:text-slate-600'}`}>B</button>
                        <button onClick={() => setStyleItalic(!styleItalic)} className={`w-10 h-10 rounded-lg flex items-center justify-center font-serif italic text-lg transition-colors ${styleItalic ? 'bg-white shadow text-slate-800' : 'text-slate-400 hover:text-slate-600'}`}>I</button>
                      </div>
                      <div className="flex-1">
                        <input type="color" value={fontColor} onChange={(e) => setFontColor(e.target.value)} className="w-full h-12 p-1 bg-slate-50 border border-slate-200 rounded-xl cursor-pointer" />
                      </div>
                    </div>
                  </div>
                )}

                {watermarkType === 'image' && (
                  <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Image Settings</h3>
                    
                    <div>
                      <label className="block text-sm font-semibold text-slate-600 mb-2">Upload Image / Logo (PNG, JPG)</label>
                      <input type="file" ref={imageInputRef} accept=".png,.jpg,.jpeg" onChange={handleImageUpload} className="hidden" />
                      <button onClick={() => imageInputRef.current?.click()} className="w-full py-4 border-2 border-dashed border-slate-300 rounded-xl text-slate-500 font-semibold hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-600 transition-all flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                        Select Image
                      </button>
                      {imageBytes && <p className="text-xs text-emerald-600 font-bold mt-2 text-center">✓ Image selected successfully</p>}
                    </div>

                    <div>
                      <label className="block text-sm font-semibold text-slate-600 mb-2">Scale (e.g., 0.5 for 50%)</label>
                      <input type="number" step="0.1" min="0.1" max="5.0" value={scale} onChange={(e) => setScale(e.target.value)} className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-100 focus:border-[#1e2a52] outline-none transition-all" />
                    </div>
                  </div>
                )}

                {watermarkType === 'signature' && (
                  <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Signature Settings</h3>
                    
                    <div className="flex gap-2 border p-1 rounded-xl bg-slate-50">
                      <button onClick={() => setSigMode('draw')} className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${sigMode === 'draw' ? 'bg-white shadow border border-slate-200 text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}>Draw</button>
                      <button onClick={() => setSigMode('upload')} className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${sigMode === 'upload' ? 'bg-white shadow border border-slate-200 text-slate-800' : 'text-slate-500 hover:text-slate-700'}`}>Upload</button>
                    </div>

                    {sigMode === 'draw' && (
                      <SignaturePad onSave={setSigCanvasData} onClear={() => setSigCanvasData(null)} />
                    )}

                    {sigMode === 'upload' && (
                      <div>
                        <label className="block text-sm font-semibold text-slate-600 mb-2">Upload Signature (PNG with transparency)</label>
                        <input type="file" ref={sigUploadRef} accept=".png,.jpg,.jpeg" onChange={handleImageUpload} className="hidden" />
                        <button onClick={() => sigUploadRef.current?.click()} className="w-full py-4 border-2 border-dashed border-slate-300 rounded-xl text-slate-500 font-semibold hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-600 transition-all flex items-center justify-center gap-2">
                          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                          Select File
                        </button>
                        {imageBytes && <p className="text-xs text-emerald-600 font-bold mt-2 text-center">✓ File selected successfully</p>}
                      </div>
                    )}

                    <div>
                      <label className="block text-sm font-semibold text-slate-600 mb-2">Scale (e.g., 0.5 for 50%)</label>
                      <input type="number" step="0.1" min="0.1" max="5.0" value={scale} onChange={(e) => setScale(e.target.value)} className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-medium focus:ring-2 focus:ring-indigo-100 focus:border-[#1e2a52] outline-none transition-all" />
                    </div>
                  </div>
                )}

                <button 
                  onClick={handleProcess} 
                  disabled={isFlying}
                  className={`w-full bg-[#1e2a52] hover:bg-[#2a3a6a] text-white font-bold py-4 px-8 rounded-xl shadow-xl transform transition-all duration-500 flex items-center justify-center gap-2 group mt-8 relative overflow-hidden ${isFlying ? 'scale-95 opacity-80' : 'hover:scale-[1.02] active:scale-[0.98]'}`}
                >
                  <span className={`transition-all duration-500 ${isFlying ? '-translate-x-4 opacity-0' : ''}`}>Secure Document</span>
                  <svg 
                    className={`w-5 h-5 absolute right-1/4 transition-all duration-500 ease-in-out ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150 rotate-45' : 'group-hover:translate-x-1 opacity-0 group-hover:opacity-100'}`} 
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                  <svg 
                    className={`w-5 h-5 transition-all duration-500 ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150' : 'group-hover:translate-x-1'}`} 
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              <h3 className="text-xl font-bold text-slate-800 mb-2">Processing Document</h3>
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mt-4"></div>
              <p className="text-slate-500 text-center text-sm mt-4">Applying secure watermarks...</p>
            </div>
          )}

          {isSuccess && !isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <svg className="w-12 h-12 text-emerald-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-3">Secured!</h3>
              {downloadUrl && (
                <a href={downloadUrl} download={downloadFilename} className="w-full text-center bg-[#1e2a52] hover:bg-[#2a3a6a] text-white font-bold py-4 px-8 rounded-xl shadow-lg transition-all active:scale-95 flex justify-center items-center gap-2 mb-3">
                  Download PDF
                </a>
              )}
              <button onClick={resetAll} className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-4 px-8 rounded-xl shadow-sm transition-all active:scale-95 flex justify-center items-center gap-2">
                Watermark more files
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
