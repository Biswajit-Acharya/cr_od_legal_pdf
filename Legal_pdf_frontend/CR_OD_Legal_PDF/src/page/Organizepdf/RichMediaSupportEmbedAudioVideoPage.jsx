import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

export default function RichMediaSupportEmbedAudioVideoPage() {
  const [pdfFile, setPdfFile] = useState(null);
  const [mediaFiles, setMediaFiles] = useState([]);
  
  // Placement State
  const [posX, setPosX] = useState(10);
  const [posY, setPosY] = useState(10);
  const [sizeW, setSizeW] = useState(30);
  const [sizeH, setSizeH] = useState(25);
  const [rotation, setRotation] = useState(0);
  const [volume, setVolume] = useState(100);
  
  // Playback State
  const [autoplay, setAutoplay] = useState(false);
  const [loop, setLoop] = useState(false);
  const [muted, setMuted] = useState(false);
  const [controls, setControls] = useState(true);

  // App State
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFlying, setIsFlying] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  
  const pdfInputRef = useRef(null);
  const mediaInputRef = useRef(null);

  const [downloadUrl, setDownloadUrl] = useState(null);
  const [downloadFilename, setDownloadFilename] = useState('');
  
  const [numPages, setNumPages] = useState(null);
  const [pdfDimensions, setPdfDimensions] = useState({ width: 0, height: 0 });
  const [renderScale, setRenderScale] = useState(1);
  const containerRef = useRef(null);

  // Drag logic
  const [dragPos, setDragPos] = useState({ x: 0, y: 0 });
  const [isDraggingMedia, setIsDraggingMedia] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, currentX: 0, currentY: 0 });

  // Sync dragPos to percentages
  useEffect(() => {
    if (pdfDimensions.width > 0 && containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        const scale = containerWidth / pdfDimensions.width;
        
        if (isDraggingMedia) {
            const xPercent = (dragPos.x / containerWidth) * 100;
            const yPercent = (dragPos.y / (pdfDimensions.height * scale)) * 100;
            setPosX(Math.min(Math.max(xPercent, 0), 100).toFixed(1));
            setPosY(Math.min(Math.max(yPercent, 0), 100).toFixed(1));
        }
    }
  }, [dragPos, isDraggingMedia, pdfDimensions]);

  // Sync percentages to dragPos if manual entry
  useEffect(() => {
    if (!isDraggingMedia && pdfDimensions.width > 0 && containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        const scale = containerWidth / pdfDimensions.width;
        setDragPos({
            x: (posX / 100) * containerWidth,
            y: (posY / 100) * (pdfDimensions.height * scale)
        });
    }
  }, [posX, posY, pdfDimensions, isDraggingMedia]);

  const handlePageLoad = (page) => {
    const { originalWidth, originalHeight } = page;
    setPdfDimensions({ width: originalWidth, height: originalHeight });
    
    if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        const scale = containerWidth / originalWidth;
        setRenderScale(scale);
        setDragPos({ x: containerWidth / 2, y: (originalHeight * scale) / 2 });
        setPosX(50);
        setPosY(50);
    }
  };

  const handleMouseDown = (e) => {
    setIsDraggingMedia(true);
    dragRef.current.startX = e.clientX;
    dragRef.current.startY = e.clientY;
    dragRef.current.currentX = dragPos.x;
    dragRef.current.currentY = dragPos.y;
    e.stopPropagation();
    e.preventDefault();
  };

  const handleMouseMove = useCallback((e) => {
    if (!isDraggingMedia) return;
    const dx = e.clientX - dragRef.current.startX;
    const dy = e.clientY - dragRef.current.startY;
    
    let newX = dragRef.current.currentX + dx;
    let newY = dragRef.current.currentY + dy;
    
    if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        newX = Math.max(0, Math.min(newX, rect.width));
        newY = Math.max(0, Math.min(newY, rect.height));
    }
    setDragPos({ x: newX, y: newY });
  }, [isDraggingMedia]);

  const handleMouseUp = useCallback(() => {
    setIsDraggingMedia(false);
  }, []);

  useEffect(() => {
    if (isDraggingMedia) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingMedia, handleMouseMove, handleMouseUp]);

  // Drag and Drop (PDF)
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };
  
  const handleDragLeave = () => setIsDragOver(false);
  
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type === 'application/pdf' || file.name.endsWith('.pdf')) {
          handlePdfChange({ target: { files: [file] } });
      } else {
          handleMediaChange({ target: { files: e.dataTransfer.files } });
      }
    }
  };

  const handlePdfChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (file.type !== 'application/pdf') {
          alert('Please upload a valid PDF file.');
          return;
      }
      setPdfFile(file);
      const blob = new Blob([file], { type: 'application/pdf' });
      setPreviewUrl(URL.createObjectURL(blob));
    }
  };

  const handleMediaChange = (e) => {
      if (e.target.files && e.target.files.length > 0) {
          const newFiles = Array.from(e.target.files);
          setMediaFiles(prev => [...prev, ...newFiles]);
      }
  };

  const removeMedia = (index) => {
      setMediaFiles(prev => prev.filter((_, i) => i !== index));
  };

  const removePdf = () => {
    setPdfFile(null);
    setIsSuccess(false);
    setIsProcessing(false);
    setPreviewUrl(null);
    setMediaFiles([]);
  };

  const resetAll = () => {
    removePdf();
  };

  const setQuickPosition = (x, y) => {
      setPosX(x);
      setPosY(y);
  };

  const processFile = async () => {
    if (!pdfFile || mediaFiles.length === 0) return;
    setIsFlying(true);

    setTimeout(async () => {
        setIsProcessing(true);
        
        try {
            const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

            // Step 1: Create session
            const createRes = await fetch(`${API_BASE_URL}/api/pdf/rich-media/create`, { method: 'POST' });
            if (!createRes.ok) throw new Error('Failed to create session');
            const sessionData = await createRes.json();
            const requestId = sessionData.request_id;

            // Step 2: Upload PDF
            const pdfForm = new FormData();
            pdfForm.append('file', pdfFile);
            pdfForm.append('request_id', requestId);
            const pdfRes = await fetch(`${API_BASE_URL}/api/pdf/rich-media/upload-pdf`, { method: 'POST', body: pdfForm });
            if (!pdfRes.ok) throw new Error('PDF upload failed');

            // Step 3: Upload each media file and add placement
            for (const mediaFile of mediaFiles) {
                const mediaForm = new FormData();
                mediaForm.append('file', mediaFile);
                mediaForm.append('request_id', requestId);
                const mediaRes = await fetch(`${API_BASE_URL}/api/pdf/rich-media/upload-media`, { method: 'POST', body: mediaForm });
                if (!mediaRes.ok) throw new Error(`Media upload failed for ${mediaFile.name}`);
                const mediaData = await mediaRes.json();
                
                // Step 3.5: Auto-generate poster to prevent black box in Adobe Acrobat
                const posterForm = new FormData();
                posterForm.append('request_id', requestId);
                posterForm.append('media_id', mediaData.media.media_id);
                try {
                    await fetch(`${API_BASE_URL}/api/pdf/rich-media/auto-poster`, { method: 'POST', body: posterForm });
                } catch (e) {
                    console.warn("Auto-poster generation failed, proceeding without poster", e);
                }

                // Step 4: Add placement for this media
                const placementForm = new FormData();
                placementForm.append('request_id', requestId);
                placementForm.append('media_id', mediaData.media.media_id);
                placementForm.append('page_index', 0);
                placementForm.append('x', posX);
                placementForm.append('y', posY);
                placementForm.append('width', sizeW);
                placementForm.append('height', sizeH);
                placementForm.append('autoplay', autoplay);
                placementForm.append('loop', loop);
                placementForm.append('muted', muted);
                placementForm.append('show_controls', controls);
                placementForm.append('play_on_click', true);
                
                const placeRes = await fetch(`${API_BASE_URL}/api/pdf/rich-media/add-placement`, { method: 'POST', body: placementForm });
                if (!placeRes.ok) {
                   const errData = await placeRes.json().catch(()=>({}));
                   throw new Error(`Placement failed: ${errData.detail || placeRes.statusText}`);
                }
            }

            // Step 5: Process PDF
            const processForm = new FormData();
            processForm.append('request_id', requestId);
            const processRes = await fetch(`${API_BASE_URL}/api/pdf/rich-media/process`, { method: 'POST', body: processForm });
            if (!processRes.ok) {
                const errData = await processRes.json().catch(()=>({}));
                throw new Error(`Processing failed: ${errData.detail || processRes.statusText}`);
            }
            const processData = await processRes.json();
            
            const filename = processData.filename || 'rich_media.pdf';
            const dl = `${API_BASE_URL}/api/pdf/rich-media/download/${requestId}/${filename}`;
            setDownloadUrl(dl);
            setDownloadFilename(`rich_media_${pdfFile.name}`);

            setIsSuccess(true);
        } catch (err) {
            console.error('Rich media API error:', err);
            alert('Error processing file: ' + err.message);
        } finally {
            setIsProcessing(false);
            setIsFlying(false);
        }
    }, 500);
  };
  
  const handleRealDownload = () => {
    if (downloadUrl) {
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = downloadFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };



  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 min-h-screen flex flex-col items-center font-sans">
      {/* Background Decorative Gradients */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-emerald-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-32 left-1/2 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
      
      <div className="w-full max-w-6xl relative z-10">
        <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
          <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
            Embed Rich Media
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
            Seamlessly embed audio, video, and GIFs directly into your PDF document.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8 justify-center items-start w-full">
          {/* Left Column (Upload and Preview) */}
          <div className="w-full lg:max-w-2xl flex flex-col gap-6 mx-auto lg:mx-0 transition-all duration-500">
            <div className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden flex-1">
              
              {/* Upload Zone */}
              <div
                className={`upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 border-indigo-200 bg-indigo-50/30 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group flex flex-col justify-center min-h-[300px] ${isDragOver ? 'border-indigo-500 bg-indigo-50 scale-[1.01]' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !pdfFile ? pdfInputRef.current?.click() : mediaInputRef.current?.click()}
              >
                <input type="file" accept=".pdf" hidden ref={pdfInputRef} onChange={handlePdfChange} />
                <input type="file" accept="video/*,audio/*,image/gif" multiple hidden ref={mediaInputRef} onChange={handleMediaChange} />
                
                <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                  {!pdfFile ? (
                      <svg className="w-10 h-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                      </svg>
                  ) : (
                      <svg className="w-10 h-10 text-pink-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  )}
                </div>
                <p className="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                  {!pdfFile ? 'Drag & drop a PDF here' : 'Drop Audio/Video files here'}
                </p>
                {!pdfFile && <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse PDF</span></p>}
              </div>

              {/* PDF File List */}
              {pdfFile && (
                <div className="file-list mt-6 space-y-3">
                  <div className="file-item flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-[1px] transition-all group">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                        <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                      </div>
                      <div className="flex flex-col truncate">
                         <span className="font-medium text-slate-700 truncate">{pdfFile.name}</span>
                         <span className="text-xs text-slate-500">{(pdfFile.size / 1024 / 1024).toFixed(2)} MB</span>
                      </div>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); removePdf(); }} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0" title="Remove PDF">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Preview UI */}
              {pdfFile && (
                                <div className="preview-section mt-6 rounded-2xl border border-slate-200 bg-slate-50/50 overflow-hidden relative shadow-inner w-full flex justify-center" ref={containerRef}>
                    <Document file={pdfFile} onLoadSuccess={({numPages}) => setNumPages(numPages)}>
                        <Page 
                            pageNumber={1} 
                            width={containerRef.current?.clientWidth || 400} 
                            onLoadSuccess={handlePageLoad} 
                            renderTextLayer={false} 
                            renderAnnotationLayer={false}
                        />
                    </Document>
                    
                    {/* Draggable Media Overlay */}
                    {mediaFiles.length > 0 && pdfDimensions.width > 0 && (
                        <div 
                            onMouseDown={handleMouseDown}
                            className={`absolute border-2 ${isDraggingMedia ? 'border-indigo-500 bg-indigo-500/20 shadow-lg scale-105' : 'border-indigo-400 border-dashed bg-indigo-400/10'} rounded cursor-move flex flex-col items-center justify-center transition-all`}
                            style={{
                                left: `${dragPos.x}px`,
                                top: `${dragPos.y}px`,
                                width: `${sizeW}%`,
                                height: `${sizeH}%`,
                                transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
                            }}
                        >
                            <span className="text-4xl opacity-70 pointer-events-none">
                                {mediaFiles[mediaFiles.length-1]?.type.includes('video') ? '🎬' : '🎵'}
                            </span>
                            <span className="text-xs font-bold text-indigo-700 bg-white/80 px-2 py-0.5 rounded-full mt-2 pointer-events-none shadow-sm whitespace-nowrap">
                              Drag to position
                            </span>
                        </div>
                    )}
                </div>
              )}
            </div>
          </div>

          {/* Right Column (Media Library & Options) */}
          {pdfFile && !isProcessing && !isSuccess && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden mx-auto lg:mx-0 transition-all duration-500 animate-fade-in-up">
              
              <div className="space-y-6">
                
                {/* Media Library */}
                <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4">
                  <div className="flex items-center justify-between mb-2">
                      <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Media Library</h3>
                      <button onClick={() => mediaInputRef.current?.click()} className="text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-2 py-1 rounded">Add +</button>
                  </div>
                  
                  {mediaFiles.length === 0 ? (
                      <div className="p-4 bg-slate-50 border border-slate-200 border-dashed rounded-xl text-center">
                          <p className="text-sm font-medium text-slate-500">No media uploaded yet.</p>
                      </div>
                  ) : (
                      <div className="space-y-2 max-h-40 overflow-y-auto pr-2">
                          {mediaFiles.map((media, idx) => (
                              <div key={idx} className="flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                                  <div className="flex items-center gap-2 overflow-hidden">
                                      <span className="text-xl">{media.type.includes('video') ? '🎬' : '🎵'}</span>
                                      <div className="flex flex-col truncate">
                                          <span className="text-sm font-semibold text-slate-700 truncate">{media.name}</span>
                                          <span className="text-[10px] text-slate-500">{(media.size / 1024 / 1024).toFixed(2)} MB</span>
                                      </div>
                                  </div>
                                  <button onClick={() => removeMedia(idx)} className="text-slate-400 hover:text-red-500 shrink-0"><svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg></button>
                              </div>
                          ))}
                      </div>
                  )}
                </div>

                {/* Placement Settings */}
                {mediaFiles.length > 0 && (
                    <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4 animate-fade-in-up">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Placement & Sizing</h3>
                        
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-600 mb-1">X Pos (%)</label>
                                <input type="number" value={posX} onChange={e => setPosX(e.target.value)} className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-indigo-500" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-600 mb-1">Y Pos (%)</label>
                                <input type="number" value={posY} onChange={e => setPosY(e.target.value)} className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-indigo-500" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-600 mb-1">Width (%)</label>
                                <input type="number" value={sizeW} onChange={e => setSizeW(e.target.value)} className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-indigo-500" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-600 mb-1">Height (%)</label>
                                <input type="number" value={sizeH} onChange={e => setSizeH(e.target.value)} className="w-full p-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-semibold outline-none focus:border-indigo-500" />
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-slate-600 mb-2">Quick Position</label>
                            <div className="grid grid-cols-3 gap-1">
                                <button onClick={() => setQuickPosition(2,2)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">↖</button>
                                <button onClick={() => setQuickPosition(35,2)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">↑</button>
                                <button onClick={() => setQuickPosition(68,2)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">↗</button>
                                <button onClick={() => setQuickPosition(2,37)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">←</button>
                                <button onClick={() => setQuickPosition(35,37)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">●</button>
                                <button onClick={() => setQuickPosition(68,37)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">→</button>
                                <button onClick={() => setQuickPosition(2,72)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">↙</button>
                                <button onClick={() => setQuickPosition(35,72)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">↓</button>
                                <button onClick={() => setQuickPosition(68,72)} className="p-1.5 bg-slate-50 border border-slate-200 hover:bg-indigo-50 rounded text-slate-500 hover:text-indigo-600">↘</button>
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-slate-600 mb-1">Rotation: {rotation}°</label>
                            <input type="range" min="-180" max="180" value={rotation} onChange={e => setRotation(e.target.value)} className="w-full accent-indigo-600" />
                        </div>
                    </div>
                )}

                {/* Playback Settings */}
                {mediaFiles.length > 0 && (
                    <div className="p-5 bg-white rounded-2xl shadow-sm border border-slate-100 space-y-4 animate-fade-in-up">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Playback Settings</h3>
                        
                        <div className="grid grid-cols-2 gap-3">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={autoplay} onChange={e => setAutoplay(e.target.checked)} className="rounded text-indigo-600" />
                                <span className="text-sm font-semibold text-slate-600">Autoplay</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={loop} onChange={e => setLoop(e.target.checked)} className="rounded text-indigo-600" />
                                <span className="text-sm font-semibold text-slate-600">Loop</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={muted} onChange={e => setMuted(e.target.checked)} className="rounded text-indigo-600" />
                                <span className="text-sm font-semibold text-slate-600">Mute</span>
                            </label>
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" checked={controls} onChange={e => setControls(e.target.checked)} className="rounded text-indigo-600" />
                                <span className="text-sm font-semibold text-slate-600">Controls</span>
                            </label>
                        </div>
                        
                        <div className="pt-2">
                            <label className="block text-xs font-bold text-slate-600 mb-1">Volume: {volume}%</label>
                            <input type="range" min="0" max="100" value={volume} onChange={e => setVolume(e.target.value)} className="w-full accent-indigo-600" />
                        </div>
                    </div>
                )}

                {mediaFiles.length > 0 && (
                    <button 
                        onClick={processFile} 
                        disabled={isFlying}
                        className={`w-full bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-bold py-4 px-8 rounded-xl shadow-xl shadow-indigo-200 transform transition-all duration-500 flex items-center justify-center gap-2 group mt-8 relative overflow-hidden ${isFlying ? 'scale-95 opacity-80 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-[0.98]'}`}
                    >
                        <span className={`transition-all duration-500 ${isFlying ? '-translate-x-4 opacity-0' : ''}`}>Embed Media</span>
                        <svg className={`w-5 h-5 absolute right-1/4 transition-all duration-500 ease-in-out ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150 rotate-45' : 'group-hover:translate-x-1 opacity-0 group-hover:opacity-100'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
                        <svg className={`w-5 h-5 transition-all duration-500 ${isFlying ? 'translate-x-[200px] -translate-y-[100px] opacity-0 scale-150' : 'group-hover:translate-x-1'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                    </button>
                )}
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
                            <div className="speeder-loader-wrapper mb-8">
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
              <h3 className="text-xl font-bold text-slate-800 mb-2">Embedding Media</h3>
              <p className="text-slate-500 text-center text-sm">Please wait... packing your audio and video files into the PDF container.</p>
            </div>
          )}

          {isSuccess && !isProcessing && (
            <div className="w-full lg:max-w-md bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-10 flex flex-col items-center justify-center relative overflow-hidden animate-fade-in-up min-h-[400px]">
              <div className="w-24 h-24 bg-emerald-100 rounded-full flex items-center justify-center mb-6 shadow-inner">
                <svg className="w-12 h-12 text-emerald-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" /></svg>
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-3">PDF Ready!</h3>
              <p className="text-slate-500 text-center mb-8 font-medium">Successfully embedded {mediaFiles.length} media items into your PDF.</p>
              
              <button onClick={handleRealDownload} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-emerald-200 transition-all active:scale-95 flex justify-center items-center gap-2 mb-3">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                Download
              </button>
              <button onClick={resetAll} className="w-full bg-slate-800 hover:bg-slate-900 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-slate-300 transition-all active:scale-95 flex justify-center items-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                Embed more media
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
