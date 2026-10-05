import React, { useState, useRef, useEffect } from 'react';
import { pdfjs } from 'react-pdf';

// Define worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

// Keep requests relative in local development (Vite proxies /api to FastAPI)
// and allow deployments to provide an explicit backend base URL.
const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function EditPdfPage() {
  const [file, setFile] = useState(null);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [zoomScale, setZoomScale] = useState(0.5);
  
  const [activeTool, setActiveTool] = useState('select');
  const [hasSelection, setHasSelection] = useState(false);
  const [isTextSelected, setIsTextSelected] = useState(false);
  
  const [thumbnails, setThumbnails] = useState([]);
  
  const [props, setProps] = useState({
    fill: '#000000',
    stroke: '#ef4444',
    strokeWidth: 2,
    opacity: 100,
    fontSize: 20,
    fontFamily: 'helvetica',
    fontWeight: 'normal',
    fontStyle: 'normal',
    underline: false,
    textAlign: 'left'
  });

  const canvasRef = useRef(null);
  const fabricRef = useRef(null);
  const fCanvas = useRef(null);
  const wrapperRef = useRef(null);
  
  const pageEdits = useRef({});
  const history = useRef({});
  const historyPtr = useRef({});
  
  const activeRenderTask = useRef(null);
  
  // Load Fabric.js dynamically
  useEffect(() => {
    if (!window.fabric && !document.getElementById('fabric-js-script')) {
      const fabricScript = document.createElement('script');
      fabricScript.id = 'fabric-js-script';
      fabricScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/fabric.js/5.3.1/fabric.min.js';
      document.head.appendChild(fabricScript);
    }
  }, []);

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange({ target: { files: e.dataTransfer.files } });
    }
  };

  const handleFileChange = async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f || f.type !== 'application/pdf') {
      alert('Please upload a valid PDF file.');
      return;
    }
    
    setFile(f);
    setIsProcessing(true);
    
    try {
      const buf = await f.arrayBuffer();
      const doc = await pdfjs.getDocument({ data: buf }).promise;
      setPdfDoc(doc);
      setTotalPages(doc.numPages);
      setCurrentPage(1);
      
      // Init Edits memory
      pageEdits.current = {};
      history.current = {};
      historyPtr.current = {};
      for(let i=1; i<=doc.numPages; i++) {
          history.current[i] = [];
          historyPtr.current[i] = -1;
      }
      
      generateThumbnails(doc);
    } catch (err) {
      alert("Failed to read PDF.");
      console.error(err);
      setFile(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const generateThumbnails = async (doc) => {
    const thumbs = [];
    const maxThumbs = Math.min(doc.numPages, 10);
    for (let i = 1; i <= maxThumbs; i++) {
        try {
            const page = await doc.getPage(i);
            const viewport = page.getViewport({ scale: 0.2 });
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            await page.render({ canvasContext: ctx, viewport }).promise;
            thumbs.push(canvas.toDataURL());
        } catch(e) {}
    }
    setThumbnails(thumbs);
  };

  useEffect(() => {
    if (pdfDoc && window.fabric && canvasRef.current && fabricRef.current) {
      initFabric();
    }
  }, [pdfDoc, file]);

  const initFabric = () => {
    if (fCanvas.current) {
        fCanvas.current.dispose();
    }
    fCanvas.current = new window.fabric.Canvas(fabricRef.current, {
        preserveObjectStacking: true,
        selectionColor: 'rgba(59, 130, 246, 0.1)', 
        selectionBorderColor: '#3b82f6',
        cornerColor: '#ffffff',
        cornerStrokeColor: '#3b82f6',
        cornerStyle: 'rect',
        transparentCorners: false,
        cornerSize: 8
    });
    
    fCanvas.current.on('selection:created', updateSelectionState);
    fCanvas.current.on('selection:updated', updateSelectionState);
    fCanvas.current.on('selection:cleared', () => { setHasSelection(false); setIsTextSelected(false); });
    fCanvas.current.on('object:modified', () => saveHistoryState());
    fCanvas.current.on('object:added', () => { saveHistoryState(); });
    
    renderPage(currentPage);
  };

  const updateSelectionState = () => {
      if(!fCanvas.current) return;
      const obj = fCanvas.current.getActiveObject();
      if (!obj) { setHasSelection(false); return; }
      setHasSelection(true);
      if (obj.type === 'i-text' || obj.type === 'text') {
          setIsTextSelected(true);
          setProps(prev => ({
              ...prev,
              fill: obj.fill || prev.fill,
              fontSize: obj.fontSize || prev.fontSize,
              fontFamily: obj.fontFamily || prev.fontFamily,
              fontWeight: obj.fontWeight || 'normal',
              fontStyle: obj.fontStyle || 'normal',
              underline: obj.underline || false,
              textAlign: obj.textAlign || 'left'
          }));
      } else {
          setIsTextSelected(false);
          setProps(prev => ({
              ...prev,
              fill: obj.fill || prev.fill,
              stroke: obj.stroke || prev.stroke,
              strokeWidth: obj.strokeWidth || prev.strokeWidth,
              opacity: (obj.opacity || 1) * 100
          }));
      }
  };

  const renderPage = async (num) => {
    if (!pdfDoc || !canvasRef.current || !fCanvas.current) return;
    
    // Save current before switching
    if (currentPage !== num && !isProcessing) {
        pageEdits.current[currentPage] = fCanvas.current.toJSON();
    }
    
    setCurrentPage(num);
    setIsProcessing(true);
    
    try {
      const page = await pdfDoc.getPage(num);
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
      if (activeRenderTask.current) activeRenderTask.current.cancel();

      const baseScale = 1.5;
      const renderViewport = page.getViewport({ scale: baseScale });
      const displayViewport = page.getViewport({ scale: zoomScale });

      canvas.width = renderViewport.width;
      canvas.height = renderViewport.height;
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      
      if (wrapperRef.current) {
          wrapperRef.current.style.width = `${displayViewport.width}px`;
          wrapperRef.current.style.height = `${displayViewport.height}px`;
      }

      activeRenderTask.current = page.render({ canvasContext: ctx, viewport: renderViewport });
      await activeRenderTask.current.promise;
      activeRenderTask.current = null;
      
      fCanvas.current.setWidth(displayViewport.width);
      fCanvas.current.setHeight(displayViewport.height);
      fCanvas.current.setZoom(zoomScale / baseScale);
      fCanvas.current.clear();
      setHasSelection(false);
      
      // Load edits
      if (pageEdits.current[num]) {
          fCanvas.current.loadFromJSON(pageEdits.current[num], () => {
              fCanvas.current.renderAll();
          });
      } else {
          saveHistoryState(true);
      }
    } catch (e) {
      if (e.name !== 'RenderingCancelledException') console.error(e);
    } finally {
      setIsProcessing(false);
    }
  };

  useEffect(() => {
      if (pdfDoc && fCanvas.current) renderPage(currentPage);
  }, [zoomScale]);

  const saveHistoryState = (initial = false) => {
      if (!fCanvas.current || isProcessing) return;
      if (!initial) pageEdits.current[currentPage] = fCanvas.current.toJSON();
      
      const stack = history.current[currentPage];
      let ptr = historyPtr.current[currentPage];
      
      const state = JSON.stringify(fCanvas.current.toJSON());
      if (ptr < stack.length - 1) {
          history.current[currentPage] = stack.slice(0, ptr + 1);
      }
      if (ptr >= 0 && stack[ptr] === state) return;
      
      history.current[currentPage].push(state);
      historyPtr.current[currentPage]++;
  };

  const undo = () => {
      let ptr = historyPtr.current[currentPage];
      if (ptr > 0) {
          historyPtr.current[currentPage]--;
          fCanvas.current.loadFromJSON(history.current[currentPage][historyPtr.current[currentPage]], () => {
              fCanvas.current.renderAll();
              pageEdits.current[currentPage] = fCanvas.current.toJSON();
          });
      }
  };

  const redo = () => {
      let ptr = historyPtr.current[currentPage];
      const stack = history.current[currentPage];
      if (ptr < stack.length - 1) {
          historyPtr.current[currentPage]++;
          fCanvas.current.loadFromJSON(stack[historyPtr.current[currentPage]], () => {
              fCanvas.current.renderAll();
              pageEdits.current[currentPage] = fCanvas.current.toJSON();
          });
      }
  };

  const changeTool = (tool) => {
      setActiveTool(tool);
      if (!fCanvas.current) return;
      
      if (tool === 'select') {
          fCanvas.current.isDrawingMode = false;
          fCanvas.current.selection = true;
      } else if (tool === 'pan') {
          fCanvas.current.isDrawingMode = false;
          fCanvas.current.selection = false;
      } else if (tool === 'draw' || tool === 'highlight') {
          fCanvas.current.isDrawingMode = true;
          fCanvas.current.freeDrawingBrush = new window.fabric.PencilBrush(fCanvas.current);
          if (tool === 'draw') {
              fCanvas.current.freeDrawingBrush.color = props.stroke;
              fCanvas.current.freeDrawingBrush.width = props.strokeWidth * 1.5;
          } else {
              fCanvas.current.freeDrawingBrush.color = 'rgba(250, 204, 21, 0.5)';
              fCanvas.current.freeDrawingBrush.width = 20 * 1.5;
          }
      }
  };

  const updateObj = (key, val) => {
      setProps(p => ({ ...p, [key]: val }));
      if (!fCanvas.current) return;
      
      const obj = fCanvas.current.getActiveObject();
      if (obj) {
          let actualVal = val;
          if (key === 'strokeWidth') actualVal = val * 1.5;
          if (key === 'opacity') actualVal = val / 100;
          
          if (obj.type === 'activeSelection') {
              obj.forEachObject(o => o.set(key, actualVal));
          } else {
              obj.set(key, actualVal);
          }
          fCanvas.current.renderAll();
          saveHistoryState();
      }
      
      if (fCanvas.current.isDrawingMode) {
          if (key === 'stroke') fCanvas.current.freeDrawingBrush.color = val;
          if (key === 'strokeWidth') fCanvas.current.freeDrawingBrush.width = val * 1.5;
      }
  };

  const addText = () => {
      changeTool('select');
      const text = new window.fabric.IText('Double click to edit', {
          left: 50, top: 50, fill: props.fill, fontSize: props.fontSize, fontFamily: props.fontFamily,
          scaleX: 1.5, scaleY: 1.5 
      });
      fCanvas.current.add(text);
      fCanvas.current.setActiveObject(text);
  };
  
  const addImage = (e) => {
      changeTool('select');
      const imgFile = e.target.files[0];
      if(!imgFile) return;
      const reader = new FileReader();
      reader.onload = function(f) {
          window.fabric.Image.fromURL(f.target.result, function(img) {
              img.scaleToWidth(250 * 1.5);
              fCanvas.current.add(img);
              fCanvas.current.setActiveObject(img);
          });
      };
      reader.readAsDataURL(imgFile);
      e.target.value = '';
  };

  const addShape = (type) => {
      changeTool('select');
      const size = 150 * 1.5;
      const opts = { left: 50, top: 50, fill: props.fill, stroke: props.stroke, strokeWidth: props.strokeWidth * 1.5, opacity: props.opacity / 100 };
      let shape;
      if (type === 'rect') shape = new window.fabric.Rect({ ...opts, width: size, height: size });
      else if (type === 'circle') shape = new window.fabric.Circle({ ...opts, radius: size/2 });
      else if (type === 'line') shape = new window.fabric.Line([50, 50, 250*1.5, 50], { stroke: props.stroke, strokeWidth: props.strokeWidth * 1.5, opacity: props.opacity / 100 });
      if (shape) {
          fCanvas.current.add(shape);
          fCanvas.current.setActiveObject(shape);
      }
  };

  const deleteSelected = () => {
      if(!fCanvas.current) return;
      const activeObjects = fCanvas.current.getActiveObjects();
      if (activeObjects.length) {
          fCanvas.current.discardActiveObject();
          activeObjects.forEach(obj => fCanvas.current.remove(obj));
          saveHistoryState();
      }
  };

  const saveDocument = async () => {
      if (fCanvas.current) pageEdits.current[currentPage] = fCanvas.current.toJSON();
      
      const normalizedEdits = {};
      let hasEdits = false;
      
      for (const [pNum, pJson] of Object.entries(pageEdits.current)) {
          if (pJson && pJson.objects && pJson.objects.length > 0) {
              hasEdits = true;
              // Fabric's canvas state must remain untouched. Mutating it here
              // caused every subsequent save attempt to shrink/reposition edits.
              const pageObjects = structuredClone(pJson.objects);
              pageObjects.forEach(obj => {
                  obj.left /= 1.5; obj.top /= 1.5;
                  obj.scaleX = (obj.scaleX || 1) / 1.5; obj.scaleY = (obj.scaleY || 1) / 1.5;
                  if(obj.strokeWidth) obj.strokeWidth /= 1.5;
                  if(obj.radius) obj.radius /= 1.5; 
                  if (obj.path) { obj.path.forEach(cmd => { for (let i = 1; i < cmd.length; i++) cmd[i] /= 1.5; }); }
              });
              normalizedEdits[pNum] = pageObjects;
          }
      }
      
      if (!hasEdits) { alert("No edits detected. Please make some changes before saving."); return; }
      
      setIsProcessing(true);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('edits', JSON.stringify(normalizedEdits));
      
      try {
          const res = await fetch(`${API_BASE_URL}/api/pdf/edit_pdf`, { method: 'POST', body: formData });
          const data = await res.json();
          if (res.ok) {
              const a = document.createElement('a');
              a.href = `${API_BASE_URL}${data.download_url}`;
              a.download = data.filename;
              document.body.appendChild(a); a.click(); document.body.removeChild(a);
          } else { alert(data.detail || 'Error saving PDF'); }
      } catch (err) {
          alert(`Unable to save PDF: ${err.message || 'Network error'}`);
      } finally { setIsProcessing(false); }
  };
  
  const resetAll = () => {
      setFile(null);
      setPdfDoc(null);
      setTotalPages(0);
      setCurrentPage(1);
      setThumbnails([]);
      if (fCanvas.current) {
          fCanvas.current.dispose();
          fCanvas.current = null;
      }
  };

  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 min-h-screen flex flex-col items-center">
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-emerald-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-32 left-1/2 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
      
      <div className="w-full max-w-7xl relative z-10 flex flex-col">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
        
        <div className="page-header text-center mb-10 mt-6 w-full">
            <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">Edit PDF</h1>
            <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">Add text, images, shapes, and freehand drawings directly onto your PDF documents.</p>
        </div>

        <div className={`flex flex-col lg:flex-row gap-8 justify-center items-start w-full ${!file ? 'items-center' : ''}`}>
          {/* Left Column */}
          <div className={`w-full ${file ? 'lg:max-w-[800px]' : 'max-w-3xl'} flex flex-col gap-6 mx-auto transition-all duration-500`}>
            <div className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-8 relative overflow-hidden flex-1 min-h-[500px]">
              
              {!file ? (
                <div 
                    className="upload-zone relative overflow-hidden border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 border-indigo-200 bg-indigo-50/30 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group flex flex-col justify-center min-h-[400px] w-full"
                    onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('border-indigo-400', 'bg-indigo-50'); }}
                    onDragLeave={(e) => { e.preventDefault(); e.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50'); }}
                    onDrop={handleDrop}
                >
                    <input type="file" accept=".pdf" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" onChange={handleFileChange} />
                    <div className="relative z-0 pointer-events-none">
                        <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                            <i className="fas fa-file-pdf text-4xl text-indigo-600"></i>
                        </div>
                        <h2 className="text-2xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">Upload PDF</h2>
                        <p className="text-slate-500 font-medium">Click or drag & drop a PDF here to begin editing</p>
                    </div>
                </div>
              ) : (
                <div className="flex flex-col h-full bg-slate-100 rounded-xl overflow-hidden border border-slate-200" style={{ height: '700px' }}>
                    {/* Top Toolbar */}
                    <div className="flex items-center gap-2 p-3 bg-white border-b border-slate-200 overflow-x-auto shadow-sm z-10">
                        <button className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${activeTool === 'select' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`} onClick={() => changeTool('select')} title="Select"><i className="fas fa-mouse-pointer"></i></button>
                        <button className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${activeTool === 'pan' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`} onClick={() => changeTool('pan')} title="Pan"><i className="fas fa-hand-paper"></i></button>
                        <div className="w-px h-6 bg-slate-300 mx-1"></div>
                        <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors" onClick={addText} title="Add Text"><i className="fas fa-font"></i></button>
                        <div className="relative">
                            <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors" title="Add Image"><i className="fas fa-image"></i></button>
                            <input type="file" accept="image/*" className="absolute inset-0 opacity-0 cursor-pointer" onChange={addImage} />
                        </div>
                        <button className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${activeTool === 'draw' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`} onClick={() => changeTool('draw')} title="Draw"><i className="fas fa-pencil-alt"></i></button>
                        <button className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors ${activeTool === 'highlight' ? 'bg-indigo-100 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`} onClick={() => changeTool('highlight')} title="Highlight"><i className="fas fa-highlighter"></i></button>
                        <div className="w-px h-6 bg-slate-300 mx-1"></div>
                        <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors" onClick={() => addShape('rect')} title="Rectangle"><i className="far fa-square"></i></button>
                        <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors" onClick={() => addShape('circle')} title="Circle"><i className="far fa-circle"></i></button>
                        <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors" onClick={() => addShape('line')} title="Line"><i className="fas fa-minus"></i></button>
                        <div className="flex-1"></div>
                        <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors" onClick={undo} title="Undo"><i className="fas fa-undo"></i></button>
                        <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors" onClick={redo} title="Redo"><i className="fas fa-redo"></i></button>
                        <button className="px-3 py-1.5 rounded-lg text-sm font-semibold text-red-600 hover:bg-red-50 transition-colors ml-2" onClick={deleteSelected} title="Delete"><i className="fas fa-trash"></i></button>
                    </div>
                    
                    {/* Workspace */}
                    <div className="flex-1 flex overflow-hidden relative">
                        {/* Thumbnails */}
                        <div className="w-24 bg-white border-r border-slate-200 overflow-y-auto p-2 flex flex-col gap-2 z-10 shadow-sm shrink-0">
                            {thumbnails.map((src, i) => (
                                <div key={i} onClick={() => renderPage(i+1)} className={`relative w-full aspect-[210/297] bg-white border-2 rounded cursor-pointer overflow-hidden transition-all ${currentPage === i+1 ? 'border-indigo-600 ring-2 ring-indigo-200' : 'border-slate-200 hover:border-slate-300'}`}>
                                    <img src={src} className="w-full h-full object-contain" alt="" />
                                    <span className="absolute bottom-1 right-1 bg-black/60 text-white text-[10px] font-bold px-1 rounded">{i+1}</span>
                                </div>
                            ))}
                        </div>
                        
                        {/* Canvas Area */}
                        <div className="flex-1 bg-slate-200 overflow-auto relative">
                            <div className="w-max min-w-full min-h-full p-4 sm:p-8 flex flex-col justify-center">
                                <div ref={wrapperRef} className="relative bg-white shadow-xl mx-auto transition-all duration-200" style={{ transformOrigin: 'top left' }}>
                                    <canvas ref={canvasRef} className="absolute inset-0 z-0 pointer-events-none" />
                                    <canvas ref={fabricRef} className="absolute inset-0 z-10" />
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    {/* Bottom Toolbar */}
                    <div className="flex items-center justify-between p-2 bg-white border-t border-slate-200 text-sm font-medium text-slate-600 z-10">
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-1">
                                <button onClick={() => renderPage(Math.max(1, currentPage - 1))} className="w-6 h-6 flex items-center justify-center rounded hover:bg-slate-100"><i className="fas fa-chevron-left text-xs"></i></button>
                                <span>Page {currentPage} of {totalPages}</span>
                                <button onClick={() => renderPage(Math.min(totalPages, currentPage + 1))} className="w-6 h-6 flex items-center justify-center rounded hover:bg-slate-100"><i className="fas fa-chevron-right text-xs"></i></button>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button onClick={() => setZoomScale(z => Math.max(0.5, z - 0.2))} className="w-6 h-6 rounded hover:bg-slate-100"><i className="fas fa-minus text-xs"></i></button>
                            <span className="w-12 text-center">{Math.round(zoomScale * 100)}%</span>
                            <button onClick={() => setZoomScale(z => Math.min(3.0, z + 0.2))} className="w-6 h-6 rounded hover:bg-slate-100"><i className="fas fa-plus text-xs"></i></button>
                        </div>
                    </div>
                </div>
              )}

              {/* Loader */}
              {isProcessing && (
                <div className="absolute inset-0 bg-white/60 backdrop-blur-sm z-50 flex flex-col items-center justify-center rounded-3xl">
                    <svg className="animate-spin w-10 h-10 text-indigo-600 mb-4" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path></svg>
                    <span className="font-bold text-slate-700">Processing...</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Right Column (Properties & Actions) */}
          {file && (
            <div className="w-full lg:w-80 flex flex-col gap-4">
              <div className="bg-white/70 backdrop-blur-xl border border-white rounded-3xl p-6 shadow-xl hover:shadow-2xl transition-shadow flex flex-col gap-4">
                <h3 className="font-bold text-slate-900 border-b border-slate-100 pb-2">Properties</h3>
                
                {hasSelection ? (
                    <div className="flex flex-col gap-4 animate-[fadein_0.2s_ease]">
                        {isTextSelected && (
                            <div className="flex flex-col gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-500 mb-1 block">Font Family</label>
                                    <select className="w-full p-2 border border-slate-200 rounded-lg text-sm bg-slate-50" value={props.fontFamily} onChange={(e) => updateObj('fontFamily', e.target.value)}>
                                        <option value="helvetica">Helvetica</option>
                                        <option value="times new roman">Times New Roman</option>
                                        <option value="courier">Courier</option>
                                    </select>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1">
                                        <label className="text-xs font-semibold text-slate-500 mb-1 block">Size</label>
                                        <input type="number" className="w-full p-2 border border-slate-200 rounded-lg text-sm bg-slate-50" value={props.fontSize} onChange={(e) => updateObj('fontSize', parseInt(e.target.value))} />
                                    </div>
                                    <div className="flex items-end gap-1 pb-0.5">
                                        <button className={`w-8 h-8 rounded border ${props.fontWeight === 'bold' ? 'bg-indigo-100 border-indigo-300 text-indigo-700' : 'bg-white border-slate-200 text-slate-600'}`} onClick={() => updateObj('fontWeight', props.fontWeight === 'bold' ? 'normal' : 'bold')}><i className="fas fa-bold text-xs"></i></button>
                                        <button className={`w-8 h-8 rounded border ${props.fontStyle === 'italic' ? 'bg-indigo-100 border-indigo-300 text-indigo-700' : 'bg-white border-slate-200 text-slate-600'}`} onClick={() => updateObj('fontStyle', props.fontStyle === 'italic' ? 'normal' : 'italic')}><i className="fas fa-italic text-xs"></i></button>
                                        <button className={`w-8 h-8 rounded border ${props.underline ? 'bg-indigo-100 border-indigo-300 text-indigo-700' : 'bg-white border-slate-200 text-slate-600'}`} onClick={() => updateObj('underline', !props.underline)}><i className="fas fa-underline text-xs"></i></button>
                                    </div>
                                </div>
                            </div>
                        )}
                        
                        <div className="flex flex-col gap-3 border-t border-slate-100 pt-3">
                            <div className="flex items-center justify-between">
                                <label className="text-xs font-semibold text-slate-500">Color (Fill)</label>
                                <input type="color" className="w-8 h-8 rounded border border-slate-200 cursor-pointer" value={props.fill} onChange={(e) => updateObj('fill', e.target.value)} />
                            </div>
                            {!isTextSelected && (
                                <div className="flex items-center justify-between">
                                    <label className="text-xs font-semibold text-slate-500">Stroke</label>
                                    <div className="flex items-center gap-2">
                                        <input type="color" className="w-8 h-8 rounded border border-slate-200 cursor-pointer" value={props.stroke} onChange={(e) => updateObj('stroke', e.target.value)} />
                                        <input type="number" className="w-14 p-1.5 border border-slate-200 rounded-lg text-xs bg-slate-50 text-center" value={props.strokeWidth} onChange={(e) => updateObj('strokeWidth', parseFloat(e.target.value))} />
                                    </div>
                                </div>
                            )}
                            <div className="flex items-center justify-between mt-2">
                                <label className="text-xs font-semibold text-slate-500">Opacity</label>
                                <input type="range" className="flex-1 ml-4 accent-indigo-600" min="10" max="100" value={props.opacity} onChange={(e) => updateObj('opacity', parseInt(e.target.value))} />
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="text-sm text-slate-400 text-center py-6">
                        Select an object on the canvas to view its properties.
                    </div>
                )}
                
                <button 
                  onClick={saveDocument}
                  disabled={isProcessing}
                  className="w-full bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-700 hover:to-cyan-700 text-white py-4 px-4 rounded-xl font-bold shadow-xl shadow-indigo-200 transition-all flex items-center justify-center gap-2 hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 mt-4"
                >
                  Save Edited PDF
                </button>
                <button onClick={resetAll} disabled={isProcessing} className="w-full px-6 py-3 bg-white border border-slate-200 text-slate-600 font-bold rounded-xl hover:bg-slate-50 transition-colors disabled:opacity-50">
                  Cancel & Reset
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
