import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, ArrowLeft, X, AlertCircle, PenTool, Image as ImageIcon, Type, CheckCircle2, Download, Calendar, Clock, List, LayoutList, Eye, Trash2 } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function PDFSignPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [error, setError] = useState('');
  const [downloadUrl, setDownloadUrl] = useState('');

  // Mode: 'edit', 'review'
  const [mode, setMode] = useState('edit');

  // Elements State: array of { id, type, page, x, y, width, height, data }
  const [elements, setElements] = useState([]);
  const [activeElementId, setActiveElementId] = useState(null);

  // Modal State for adding Sig/Initials
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState('signature'); // 'signature', 'initial'
  const [signInputType, setSignInputType] = useState('draw'); // 'draw', 'type', 'upload'
  const [typedText, setTypedText] = useState('');
  const [modalImage, setModalImage] = useState(null);

  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const containerRef = useRef(null);
  
  // Drag State
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [pdfScale, setPdfScale] = useState(1.0);

  const onDocumentLoadSuccess = ({ numPages }) => setNumPages(numPages);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setElements([]);
      setMode('edit');
      setIsDone(false);
    }
  };

  const generateId = () => Math.random().toString(36).substr(2, 9);

  const addElement = (type, data, width = 150, height = 50) => {
    const newEl = {
      id: generateId(),
      type,
      page: pageNumber,
      x: 50,
      y: 50,
      width,
      height,
      data
    };
    setElements([...elements, newEl]);
    setActiveElementId(newEl.id);
  };

  const handleAddDate = () => addElement('date', new Date().toLocaleDateString(), 120, 30);
  const handleAddTime = () => addElement('time', new Date().toLocaleTimeString(), 100, 30);

  // Drawing Logic
  const startDrawing = (e) => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
    setIsDrawing(true);
  };
  const draw = (e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 2;
    ctx.stroke();
  };
  const stopDrawing = () => setIsDrawing(false);
  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  const handleModalSave = () => {
    let b64 = null;
    if (signInputType === 'draw' && canvasRef.current) {
      b64 = canvasRef.current.toDataURL('image/png');
    } else if (signInputType === 'type') {
      const canvas = document.createElement('canvas');
      canvas.width = 400; canvas.height = 150;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.font = 'italic 60px serif';
      ctx.fillStyle = '#000';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(typedText || 'Signature', 200, 75);
      b64 = canvas.toDataURL('image/png');
    } else if (signInputType === 'upload' && modalImage) {
      b64 = modalImage;
    }

    if (b64) {
      addElement(modalType, b64, modalType === 'initial' ? 80 : 150, 50);
      setShowModal(false);
      setTypedText('');
      setModalImage(null);
    }
  };

  const handleUploadImage = (e) => {
    const imgFile = e.target.files[0];
    if (imgFile) {
      const reader = new FileReader();
      reader.onload = (event) => setModalImage(event.target.result);
      reader.readAsDataURL(imgFile);
    }
  };

  // Drag Logic
  const handleMouseDown = (e, id) => {
    e.preventDefault();
    setActiveElementId(id);
    const rect = e.currentTarget.getBoundingClientRect();
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setIsDragging(true);
  };
  
  const handleMouseMove = (e) => {
    if (!isDragging || !activeElementId || !containerRef.current) return;
    const parentRect = containerRef.current.getBoundingClientRect();
    const el = elements.find(e => e.id === activeElementId);
    if (!el) return;

    let newX = e.clientX - parentRect.left - dragOffset.x;
    let newY = e.clientY - parentRect.top - dragOffset.y;
    newX = Math.max(0, Math.min(newX, parentRect.width - el.width));
    newY = Math.max(0, Math.min(newY, parentRect.height - el.height));
    
    setElements(elements.map(item => item.id === activeElementId ? { ...item, x: newX, y: newY } : item));
  };
  const handleMouseUp = () => setIsDragging(false);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragOffset, elements, activeElementId]);

  const removeElement = (id) => {
    setElements(elements.filter(e => e.id !== id));
    if (activeElementId === id) setActiveElementId(null);
  };

  const updateActiveSize = (field, value) => {
    if (!activeElementId) return;
    setElements(elements.map(e => e.id === activeElementId ? { ...e, [field]: value } : e));
  };

  const handleSign = async () => {
    if (!file || elements.length === 0) return;
    setIsProcessing(true);
    setError('');
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('signatures', JSON.stringify(elements));

      const response = await fetch(`${API_BASE_URL}/api/pdf/signature/sign`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        let msg = `Error ${response.status}`;
        try { const d = await response.json(); msg = d.detail || msg; } catch(e){}
        throw new Error(msg);
      }
      const data = await response.json();
      setDownloadUrl(data.downloadUrl);
      setIsDone(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const activeEl = elements.find(e => e.id === activeElementId);

  return (
    <div className="flex-1 flex flex-col w-full relative z-20 min-h-screen bg-slate-50">
      {/* Header */}
      <div className="w-full max-w-[1400px] mx-auto px-4 pt-6 pb-4 flex justify-between items-center">
        <button onClick={onBack} className="inline-flex items-center gap-2 bg-white text-slate-700 font-semibold px-4 py-2 rounded-xl shadow-sm border border-slate-200 hover:bg-slate-50">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <h1 className="text-2xl font-black text-slate-800 tracking-tight">PDF Sign Workspace</h1>
        <div className="w-[100px]"></div> {/* Spacer */}
      </div>

      <div className="w-full max-w-[1400px] mx-auto px-4 pb-12 grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left Panel - Tools & Elements */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
            <h2 className="font-bold text-slate-800 mb-3 flex items-center gap-2"><FileText className="w-4 h-4"/> Document</h2>
            {!file ? (
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                <Upload className="w-6 h-6 text-slate-400 mb-2" />
                <span className="text-sm font-medium text-slate-600">Upload PDF to sign</span>
                <input type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
              </label>
            ) : (
              <div className="space-y-3">
                <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
                  <p className="text-sm font-semibold text-blue-900 truncate" title={file.name}>{file.name}</p>
                  <p className="text-xs text-blue-600 mt-1">{numPages ? `${numPages} Pages` : 'Loading...'}</p>
                </div>
                <button onClick={() => setFile(null)} className="text-xs font-semibold text-slate-500 hover:text-red-500 w-full text-left">
                  Replace Document
                </button>
              </div>
            )}
          </div>

          {file && !isDone && mode === 'edit' && (
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><PenTool className="w-4 h-4"/> Sign Tools</h2>
              
              <div className="grid grid-cols-2 gap-2 mb-6">
                <button onClick={() => { setModalType('signature'); setShowModal(true); }} className="flex flex-col items-center justify-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl hover:bg-blue-50 hover:border-blue-200 transition-colors">
                  <PenTool className="w-5 h-5 text-blue-600"/>
                  <span className="text-xs font-semibold text-slate-700">Signature</span>
                </button>
                <button onClick={() => { setModalType('initial'); setShowModal(true); }} className="flex flex-col items-center justify-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl hover:bg-blue-50 hover:border-blue-200 transition-colors">
                  <Type className="w-5 h-5 text-blue-600"/>
                  <span className="text-xs font-semibold text-slate-700">Initials</span>
                </button>
                <button onClick={handleAddDate} className="flex flex-col items-center justify-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl hover:bg-blue-50 hover:border-blue-200 transition-colors">
                  <Calendar className="w-5 h-5 text-blue-600"/>
                  <span className="text-xs font-semibold text-slate-700">Date</span>
                </button>
                <button onClick={handleAddTime} className="flex flex-col items-center justify-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl hover:bg-blue-50 hover:border-blue-200 transition-colors">
                  <Clock className="w-5 h-5 text-blue-600"/>
                  <span className="text-xs font-semibold text-slate-700">Time</span>
                </button>
              </div>

              {activeEl && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 mb-6">
                  <h3 className="text-xs font-bold text-slate-600 mb-2 uppercase">Size Options</h3>
                  <div className="space-y-2 text-xs">
                    <div>
                      <label className="block text-slate-500 mb-1">Width: {activeEl.width}px</label>
                      <input type="range" min="30" max="400" value={activeEl.width} onChange={e=>updateActiveSize('width', Number(e.target.value))} className="w-full" />
                    </div>
                    <div>
                      <label className="block text-slate-500 mb-1">Height: {activeEl.height}px</label>
                      <input type="range" min="15" max="200" value={activeEl.height} onChange={e=>updateActiveSize('height', Number(e.target.value))} className="w-full" />
                    </div>
                  </div>
                </div>
              )}

              <h2 className="font-bold text-slate-800 mb-3 flex items-center gap-2"><LayoutList className="w-4 h-4"/> Added Elements</h2>
              <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                {elements.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No elements added yet.</p>
                ) : (
                  elements.map(el => (
                    <div key={el.id} onClick={() => { setPageNumber(el.page); setActiveElementId(el.id); }} className={`flex items-center justify-between p-2 rounded-lg cursor-pointer border ${activeElementId === el.id ? 'bg-blue-50 border-blue-200' : 'bg-slate-50 border-transparent hover:bg-slate-100'}`}>
                      <div>
                        <p className="text-xs font-semibold text-slate-700 capitalize">{el.type}</p>
                        <p className="text-[10px] text-slate-500">Page {el.page}</p>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); removeElement(el.id); }} className="text-slate-400 hover:text-red-500 p-1"><Trash2 className="w-3 h-3"/></button>
                    </div>
                  ))
                )}
              </div>

              <div className="mt-6 pt-4 border-t border-slate-200">
                <button onClick={() => setMode('review')} disabled={elements.length === 0} className="w-full py-3 bg-slate-900 text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-slate-800 disabled:opacity-50">
                  <Eye className="w-4 h-4"/> Review Document
                </button>
              </div>
            </div>
          )}

          {file && mode === 'review' && !isDone && (
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
              <h2 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-emerald-500"/> Review & Sign</h2>
              
              <div className="space-y-3 mb-6 text-sm">
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Document</span>
                  <span className="font-medium text-slate-800 truncate max-w-[120px]">{file.name}</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Total Elements</span>
                  <span className="font-bold text-blue-600">{elements.length}</span>
                </div>
                <div className="flex justify-between border-b border-slate-100 pb-2">
                  <span className="text-slate-500">Signatures</span>
                  <span className="font-medium text-slate-800">{elements.filter(e=>e.type==='signature').length}</span>
                </div>
                <div className="flex justify-between pb-2">
                  <span className="text-slate-500">Initials</span>
                  <span className="font-medium text-slate-800">{elements.filter(e=>e.type==='initial').length}</span>
                </div>
              </div>

              {error && <div className="mb-4 text-xs text-red-600 bg-red-50 p-3 rounded-xl border border-red-100 flex items-start gap-2"><AlertCircle className="w-4 h-4 shrink-0 mt-0.5"/> {error}</div>}

              <button onClick={handleSign} disabled={isProcessing} className="w-full py-3 bg-emerald-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-emerald-700 disabled:opacity-50 transition-colors shadow-sm mb-3">
                {isProcessing ? <span className="animate-pulse">Processing PDF...</span> : 'Confirm & Sign PDF'}
              </button>
              <button onClick={() => setMode('edit')} disabled={isProcessing} className="w-full py-2 bg-white text-slate-600 border border-slate-200 rounded-xl font-bold text-sm hover:bg-slate-50 disabled:opacity-50">
                Back to Edit
              </button>
            </div>
          )}

          {isDone && (
            <div className="bg-emerald-50 p-6 rounded-2xl border border-emerald-200 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
              <h3 className="font-bold text-emerald-800 text-lg mb-2">PDF Signed Successfully</h3>
              <p className="text-xs text-emerald-600 mb-6">Your legally binding document is ready.</p>
              <a href={API_BASE_URL + downloadUrl} className="inline-flex items-center gap-2 w-full justify-center px-4 py-3 bg-emerald-600 text-white font-bold rounded-xl shadow-sm hover:bg-emerald-700 transition-colors">
                <Download className="w-5 h-5"/> Download Signed PDF
              </a>
              <button onClick={() => { setFile(null); setElements([]); setMode('edit'); setIsDone(false); }} className="mt-4 text-xs font-bold text-emerald-700 hover:underline">
                Sign another document
              </button>
            </div>
          )}
        </div>

        {/* Right Panel - PDF Viewer */}
        <div className="lg:col-span-3 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[800px]">
          <div className="p-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center text-sm font-medium">
            <span className="text-slate-600 flex items-center gap-2"><Eye className="w-4 h-4"/> {mode === 'review' ? 'Previewing Document' : 'Workspace'}</span>
            {numPages && (
              <div className="flex items-center gap-3 bg-white px-3 py-1.5 rounded-lg border border-slate-200 shadow-sm">
                <button onClick={()=>setPageNumber(p=>Math.max(1, p-1))} disabled={pageNumber<=1} className="text-slate-500 hover:text-slate-800 disabled:opacity-30">&larr;</button>
                <span className="font-bold text-slate-700">Page {pageNumber} <span className="text-slate-400 font-normal">of {numPages}</span></span>
                <button onClick={()=>setPageNumber(p=>Math.min(numPages, p+1))} disabled={pageNumber>=numPages} className="text-slate-500 hover:text-slate-800 disabled:opacity-30">&rarr;</button>
              </div>
            )}
          </div>
          
          <div className="flex-1 overflow-auto p-8 bg-slate-200/50 flex justify-center relative">
            {file ? (
              <div ref={containerRef} className="relative shadow-xl inline-block transition-transform duration-200">
                <Document file={file} onLoadSuccess={onDocumentLoadSuccess} loading={<div className="p-20 text-slate-500 animate-pulse font-medium">Loading Document...</div>}>
                  <Page pageNumber={pageNumber} scale={pdfScale} renderAnnotationLayer={false} renderTextLayer={false} className="bg-white" />
                </Document>
                
                {/* Render Elements for Current Page */}
                {!isDone && elements.filter(e => e.page === pageNumber).map(el => (
                  <div 
                    key={el.id}
                    style={{ left: el.x, top: el.y, width: el.width, height: el.height }}
                    className={`absolute border-2 cursor-move rounded transition-colors group ${activeElementId === el.id ? 'border-blue-500 bg-blue-500/10 shadow-lg z-10' : 'border-transparent hover:border-slate-300 hover:bg-slate-100/50'}`}
                    onMouseDown={(e) => handleMouseDown(e, el.id)}
                  >
                    {el.type === 'signature' || el.type === 'initial' ? (
                      <img src={el.data} alt={el.type} className="w-full h-full object-contain pointer-events-none" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center font-bold text-slate-800 select-none pointer-events-none text-center leading-tight" style={{fontSize: `${el.height * 0.5}px`}}>
                        {el.data}
                      </div>
                    )}
                    {activeElementId === el.id && (
                      <div className="absolute -top-7 left-0 bg-blue-600 text-white text-[10px] px-2 py-1 rounded shadow-md whitespace-nowrap pointer-events-none font-bold">
                        Drag to move
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-4">
                <FileText className="w-16 h-16 opacity-20" />
                <p className="font-medium">Upload a PDF to begin signing</p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Signature Creation Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h3 className="font-bold text-slate-800 capitalize">Create {modalType}</h3>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-700 bg-white p-1 rounded-full shadow-sm"><X className="w-4 h-4"/></button>
            </div>
            
            <div className="p-6">
              <div className="flex bg-slate-100 p-1 rounded-xl mb-6">
                <button onClick={() => setSignInputType('draw')} className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-bold rounded-lg transition-all ${signInputType === 'draw' ? 'bg-white shadow text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}><PenTool className="w-3.5 h-3.5"/> Draw</button>
                <button onClick={() => setSignInputType('type')} className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-bold rounded-lg transition-all ${signInputType === 'type' ? 'bg-white shadow text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}><Type className="w-3.5 h-3.5"/> Type</button>
                <button onClick={() => setSignInputType('upload')} className={`flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-bold rounded-lg transition-all ${signInputType === 'upload' ? 'bg-white shadow text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}><ImageIcon className="w-3.5 h-3.5"/> Image</button>
              </div>

              {signInputType === 'draw' && (
                <div className="space-y-3">
                  <div className="bg-slate-50 border-2 border-slate-200 rounded-2xl overflow-hidden touch-none">
                    <canvas ref={canvasRef} width={400} height={160} className="w-full cursor-crosshair" onMouseDown={startDrawing} onMouseMove={draw} onMouseUp={stopDrawing} onMouseLeave={stopDrawing} />
                  </div>
                  <button onClick={clearCanvas} className="w-full text-xs font-bold text-slate-500 hover:text-slate-800">Clear Canvas</button>
                </div>
              )}

              {signInputType === 'type' && (
                <div className="space-y-4">
                  <input type="text" value={typedText} onChange={e => setTypedText(e.target.value)} className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl font-medium focus:ring-2 focus:ring-blue-500 focus:outline-none" placeholder={`Type your ${modalType}`} />
                  <div className="h-32 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-center">
                    <span className="font-serif italic text-4xl text-slate-800">{typedText || modalType}</span>
                  </div>
                </div>
              )}

              {signInputType === 'upload' && (
                <div className="space-y-4">
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-blue-200 bg-blue-50/50 rounded-2xl cursor-pointer hover:bg-blue-50 transition-colors">
                    <Upload className="w-6 h-6 text-blue-500 mb-2" />
                    <span className="text-sm font-semibold text-blue-700">Choose Image</span>
                    <input type="file" accept="image/*" onChange={handleUploadImage} className="hidden" />
                  </label>
                  {modalImage && (
                    <div className="h-32 bg-slate-50 border border-slate-200 rounded-xl p-2 flex items-center justify-center">
                      <img src={modalImage} className="max-h-full object-contain" alt="Preview"/>
                    </div>
                  )}
                </div>
              )}
            </div>
            
            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
              <button onClick={() => setShowModal(false)} className="px-5 py-2.5 text-sm font-bold text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50">Cancel</button>
              <button onClick={handleModalSave} className="px-5 py-2.5 text-sm font-bold text-white bg-blue-600 rounded-xl shadow-sm hover:bg-blue-700">Apply {modalType}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
