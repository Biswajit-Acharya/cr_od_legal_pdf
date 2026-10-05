import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Download,
  Eraser,
  FileText,
  Image as ImageIcon,
  Link,
  MousePointer2,
  PenTool,
  RefreshCw,
  Share2,
  Type,
  Upload,
  X,
} from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
const MAX_UPLOAD_MB = 100;
const METHOD_LABELS = {
  aadhaar_esign: 'Aadhaar eSign',
  draw: 'Draw Signature',
  upload: 'Upload Signature',
  type: 'Typed Signature',
};

export default function ESignPage({ tool, onBack }) {
  const [workflow, setWorkflow] = useState('idle');
  const [capabilities, setCapabilities] = useState(null);
  const [file, setFile] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pageSize, setPageSize] = useState(null);
  const [previewSize, setPreviewSize] = useState(null);
  const [method, setMethod] = useState('');
  const [signatureData, setSignatureData] = useState('');
  const [typedName, setTypedName] = useState('');
  const [uploadedSignatureName, setUploadedSignatureName] = useState('');
  const [placement, setPlacement] = useState({ x: 72, y: 96, width: 180, height: 64 });
  const [scale, setScale] = useState(1.15);
  const [dragState, setDragState] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasDrawn, setHasDrawn] = useState(false);
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [shareResult, setShareResult] = useState(null);
  const [transaction, setTransaction] = useState(null);
  const [identityStatus, setIdentityStatus] = useState('NOT_STARTED');

  const fileInputRef = useRef(null);
  const signatureInputRef = useRef(null);
  const drawCanvasRef = useRef(null);
  const previewRef = useRef(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/pdf/signature/e-sign/capabilities`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Could not load eSign capabilities.')))
      .then((data) => {
        if (!active) return;
        setCapabilities(data);
        if (data.methods?.length) setMethod(data.methods[0]);
      })
      .catch(() => {
        if (!active) return;
        setError('The eSign service is not available right now.');
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const canvas = drawCanvasRef.current;
    if (!canvas || workflow !== 'signature_created' || method !== 'draw') return;
    const ctx = canvas.getContext('2d');
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#0f172a';
  }, [workflow, method]);

  const methods = capabilities?.methods || [];
  const fileSize = file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : '';
  const currentSignaturePreview = method === 'type' ? typedName : signatureData;
  const canContinueFromUpload = Boolean(file);
  const canConfirmSignature = (
    (method === 'draw' && hasDrawn) ||
    (method === 'upload' && Boolean(signatureData)) ||
    (method === 'type' && typedName.trim().length > 0)
  );
  const canPlace = Boolean(currentSignaturePreview);

  const setWorkflowSafe = (next) => {
    setError('');
    setWorkflow(next);
  };

  const handleFile = (incomingFile) => {
    setError('');
    setResult(null);
    setShareResult(null);
    if (!incomingFile) return;
    if (incomingFile.type !== 'application/pdf' && !incomingFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF documents can be uploaded for eSign.');
      return;
    }
    if (incomingFile.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`PDF is too large. Maximum upload size is ${MAX_UPLOAD_MB} MB.`);
      return;
    }
    setFile(incomingFile);
    setNumPages(null);
    setPageNumber(1);
    setPageSize(null);
    setPreviewSize(null);
    setSignatureData('');
    setTypedName('');
    setUploadedSignatureName('');
    setWorkflow('uploaded');
  };

  const handleDrop = (event) => {
    event.preventDefault();
    handleFile(event.dataTransfer.files?.[0]);
  };

  const removeFile = () => {
    setFile(null);
    setNumPages(null);
    setWorkflow('idle');
    setResult(null);
    setShareResult(null);
  };

  const selectMethod = (nextMethod) => {
    setMethod(nextMethod);
    setSignatureData('');
    setTypedName('');
    setUploadedSignatureName('');
    setHasDrawn(false);
    if (nextMethod === 'aadhaar_esign') {
       setWorkflow('identity_verification');
    } else {
       setWorkflow('method_selected');
    }
  };

  const pointerPoint = (event, canvas) => {
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - rect.left) / rect.width) * canvas.width,
      y: ((event.clientY - rect.top) / rect.height) * canvas.height,
    };
  };

  const startDrawing = (event) => {
    const canvas = drawCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const point = pointerPoint(event, canvas);
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
    setIsDrawing(true);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const drawSignature = (event) => {
    if (!isDrawing) return;
    const canvas = drawCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const point = pointerPoint(event, canvas);
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    setHasDrawn(true);
  };

  const stopDrawing = () => setIsDrawing(false);

  const clearCanvas = () => {
    const canvas = drawCanvasRef.current;
    if (!canvas) return;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
    setSignatureData('');
  };

  const confirmSignature = () => {
    if (method === 'draw') {
      const canvas = drawCanvasRef.current;
      if (!canvas || !hasDrawn) {
        setError('Please draw your signature before continuing.');
        return;
      }
      setSignatureData(canvas.toDataURL('image/png'));
    }
    if (method === 'type' && !typedName.trim()) {
      setError('Please enter the signer name before continuing.');
      return;
    }
    setWorkflowSafe('placement');
  };

  const startIdentityVerification = async () => {
    setIsProcessing(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('placement', JSON.stringify({
        page: pageNumber,
        x: Number(placement.x.toFixed(2)),
        y: Number(placement.y.toFixed(2)),
        width: Number(placement.width.toFixed(2)),
        height: Number(placement.height.toFixed(2)),
      }));
      formData.append('user_email', 'user@nexora.example');
      formData.append('user_name', 'Authenticated User');
      formData.append('user_role', 'Signer');

      const response = await fetch(`${API_BASE_URL}/api/pdf/signature/e-sign/initiate`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
         setIdentityStatus('FAILED');
         throw new Error(errorForStatus(response.status, data.detail));
      }
      setTransaction(data);
      setIdentityStatus(data.status);
      setWorkflowSafe('review');
    } catch (err) {
      setError(err.message || 'Identity verification initialization failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSignatureUpload = (event) => {
    const imageFile = event.target.files?.[0];
    if (!imageFile) return;
    if (!['image/png', 'image/jpeg', 'image/jpg', 'image/webp'].includes(imageFile.type)) {
      setError('Signature image must be PNG, JPEG, or WebP.');
      return;
    }
    const reader = new FileReader();
    reader.onload = (loadEvent) => {
      setSignatureData(String(loadEvent.target.result));
      setUploadedSignatureName(imageFile.name);
      setError('');
    };
    reader.readAsDataURL(imageFile);
  };

  const onDocumentLoadSuccess = ({ numPages: loadedPages }) => {
    setNumPages(loadedPages);
  };

  const onPageLoadSuccess = (page) => {
    const viewport = page.getViewport({ scale: 1 });
    setPageSize({ width: viewport.width, height: viewport.height });
  };

  const onPageRenderSuccess = () => {
    if (!previewRef.current) return;
    const rect = previewRef.current.getBoundingClientRect();
    setPreviewSize({ width: rect.width, height: rect.height });
  };

  const pdfToPreview = (value, axis) => {
    if (!pageSize || !previewSize) return value;
    return axis === 'x'
      ? value * (previewSize.width / pageSize.width)
      : value * (previewSize.height / pageSize.height);
  };

  const previewToPdf = (value, axis) => {
    if (!pageSize || !previewSize) return value;
    return axis === 'x'
      ? value * (pageSize.width / previewSize.width)
      : value * (pageSize.height / previewSize.height);
  };

  const placementPreview = {
    x: pdfToPreview(placement.x, 'x'),
    y: pdfToPreview(placement.y, 'y'),
    width: pdfToPreview(placement.width, 'x'),
    height: pdfToPreview(placement.height, 'y'),
  };

  const updatePlacement = (patch) => {
    if (!pageSize) {
      setPlacement((current) => ({ ...current, ...patch }));
      return;
    }
    setPlacement((current) => {
      const next = { ...current, ...patch };
      next.width = Math.max(24, Math.min(next.width, pageSize.width - next.x));
      next.height = Math.max(12, Math.min(next.height, pageSize.height - next.y));
      next.x = Math.max(0, Math.min(next.x, pageSize.width - next.width));
      next.y = Math.max(0, Math.min(next.y, pageSize.height - next.height));
      return next;
    });
  };

  const startPlacementDrag = (event, mode) => {
    event.preventDefault();
    setDragState({
      mode,
      startX: event.clientX,
      startY: event.clientY,
      initial: placement,
    });
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const movePlacement = (event) => {
    if (!dragState) return;
    const dx = previewToPdf(event.clientX - dragState.startX, 'x');
    const dy = previewToPdf(event.clientY - dragState.startY, 'y');
    if (dragState.mode === 'resize') {
      updatePlacement({
        width: dragState.initial.width + dx,
        height: dragState.initial.height + dy,
      });
    } else {
      updatePlacement({
        x: dragState.initial.x + dx,
        y: dragState.initial.y + dy,
      });
    }
  };

  const endPlacementDrag = () => setDragState(null);

  const errorForStatus = (status, detail) => {
    const fallback = {
      400: 'The PDF or signature input could not be accepted.',
      401: 'You are not authorized to complete this eSign request.',
      403: 'This action is not allowed.',
      404: 'The requested eSign resource was not found.',
      413: 'The uploaded file is too large.',
      422: 'Please check the signature method, placement, and required fields.',
      500: 'The server could not finish electronic signing.',
    };
    return detail || fallback[status] || 'The signing request failed.';
  };

  const confirmSign = async () => {
    if (!file || !method || !pageSize) return;
    setIsProcessing(true);
    setWorkflow('signing');
    setError('');
    setShareResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('method', method);
      formData.append('placement', JSON.stringify({
        page: pageNumber,
        x: Number(placement.x.toFixed(2)),
        y: Number(placement.y.toFixed(2)),
        width: Number(placement.width.toFixed(2)),
        height: Number(placement.height.toFixed(2)),
      }));
      formData.append('signature_data', method === 'type' ? '' : signatureData);
      formData.append('signer_name', typedName.trim());

      const response = await fetch(`${API_BASE_URL}/api/pdf/signature/e-sign`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorForStatus(response.status, data.detail));
      setResult(data);
      setWorkflow('completed');
    } catch (err) {
      setError(err.message || 'Network failure while signing the PDF.');
      setWorkflow('review');
    } finally {
      setIsProcessing(false);
    }
  };

  const createShare = async () => {
    if (!result?.filename) return;
    setIsProcessing(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('filename', result.filename);
      formData.append('allow_download', 'true');
      formData.append('allow_print', 'false');
      const response = await fetch(`${API_BASE_URL}/api/pdf/signature/e-sign/share`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorForStatus(response.status, data.detail));
      setShareResult(data);
    } catch (err) {
      setError(err.message || 'Could not create a secure share link.');
    } finally {
      setIsProcessing(false);
    }
  };

  const resetAll = () => {
    setWorkflow('idle');
    setFile(null);
    setNumPages(null);
    setPageNumber(1);
    setPageSize(null);
    setPreviewSize(null);
    setSignatureData('');
    setTypedName('');
    setUploadedSignatureName('');
    setResult(null);
    setShareResult(null);
    setError('');
    setTransaction(null);
    setIdentityStatus('NOT_STARTED');
  };

  const Step = ({ id, label }) => {
    const stepIndex = {
      idle: 1,
      uploaded: 2,
      method_selected: 3,
      signature_created: 3,
      placement: 4,
      review: 5,
      signing: 6,
      completed: 7,
    }[workflow] || 1;
    const done = id < stepIndex || (workflow === 'completed' && id <= 8);
    const active = id === stepIndex || (workflow === 'completed' && id === 8);
    return (
      <div className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${active ? 'bg-blue-50 text-blue-800' : done ? 'bg-emerald-50 text-emerald-800' : 'bg-slate-50 text-slate-500'}`}>
        <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-black ${done ? 'bg-emerald-600 text-white' : active ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>
          {done ? <Check className="h-3.5 w-3.5" /> : id}
        </span>
        <span className="font-bold">{label}</span>
      </div>
    );
  };

  return (
    <div className="flex min-h-screen w-full flex-col bg-slate-50">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between px-4 pb-4 pt-6">
        <button onClick={onBack} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <div className="text-center">
          <h1 className="text-2xl font-black tracking-tight text-slate-900">eSign PDF</h1>
          <p className="text-sm font-medium text-slate-500">Electronic signatures with visible placement and backend verification</p>
        </div>
        <div className="w-[92px]" />
      </div>

      <div className="mx-auto flex w-full max-w-[1440px] flex-col lg:flex-row gap-6 px-4 pb-12 items-start">
        <aside className="w-full lg:w-[360px] shrink-0 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2 text-sm font-black text-slate-800">
              <PenTool className="h-4 w-4 text-blue-600" /> Workflow
            </div>
            <div className="space-y-2">
              <Step id={1} label="Upload Document" />
              <Step id={2} label="Select Method" />
              {method === 'aadhaar_esign' ? (
                 <Step id={3} label="Identity Verification" />
              ) : (
                 <>
                   <Step id={3} label="Create Signature" />
                   <Step id={4} label="Place Signature" />
                 </>
              )}
              <Step id={5} label="Review" />
              <Step id={6} label="Confirm Sign" />
              <Step id={7} label="Verification" />
              <Step id={8} label="Download / Share" />
            </div>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-semibold text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
            </div>
          )}

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 flex items-center gap-2 font-black text-slate-800"><FileText className="h-4 w-4" /> 1. Upload Document</h2>
            {!file ? (
              <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleDrop}
                className="flex min-h-40 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-center"
              >
                <Upload className="mb-3 h-8 w-8 text-slate-400" />
                <p className="text-sm font-bold text-slate-700">Drag and drop a PDF</p>
                <p className="mt-1 text-xs text-slate-500">or browse from your device</p>
                <button onClick={() => fileInputRef.current?.click()} className="mt-4 rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700">
                  Choose PDF
                </button>
                <input ref={fileInputRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(event) => handleFile(event.target.files?.[0])} />
              </div>
            ) : (
              <div className="space-y-3">
                <div className="rounded-xl border border-blue-100 bg-blue-50 p-3">
                  <p className="truncate text-sm font-black text-blue-950" title={file.name}>{file.name}</p>
                  <p className="mt-1 text-xs font-semibold text-blue-700">{fileSize}{numPages ? ` · ${numPages} page${numPages === 1 ? '' : 's'}` : ' · validating PDF...'}</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => setWorkflowSafe('uploaded')} disabled={!canContinueFromUpload} className="flex-1 rounded-xl bg-blue-600 px-3 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50">
                    Continue
                  </button>
                  <button onClick={removeFile} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-600 hover:bg-slate-50">
                    Change
                  </button>
                </div>
              </div>
            )}
          </section>

          {file && workflow !== 'idle' && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 font-black text-slate-800">2. Select Signature Method</h2>
              <div className="grid grid-cols-1 gap-2">
                {methods.map((item) => (
                  <button
                    key={item}
                    onClick={() => selectMethod(item)}
                    className={`flex items-center gap-3 rounded-xl border px-3 py-3 text-left transition ${method === item ? 'border-blue-300 bg-blue-50 text-blue-800' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`}
                  >
                    {item === 'draw' ? <PenTool className="h-4 w-4" /> : item === 'upload' ? <ImageIcon className="h-4 w-4" /> : <Type className="h-4 w-4" />}
                    <span className="text-sm font-black">{METHOD_LABELS[item] || item}</span>
                  </button>
                ))}
              </div>
            </section>
          )}

          {file && workflow !== 'idle' && method && method !== 'aadhaar_esign' && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 font-black text-slate-800">3. Create / Upload Signature</h2>
              {method === 'draw' && (
                <div className="space-y-3">
                  <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                    <canvas
                      ref={drawCanvasRef}
                      width={520}
                      height={180}
                      className="h-36 w-full touch-none cursor-crosshair bg-white"
                      onPointerDown={startDrawing}
                      onPointerMove={drawSignature}
                      onPointerUp={stopDrawing}
                      onPointerLeave={stopDrawing}
                    />
                  </div>
                  <div className="flex gap-2">
                    <button onClick={clearCanvas} className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-600 hover:bg-slate-50">
                      <Eraser className="h-4 w-4" /> Clear
                    </button>
                    <button onClick={confirmSignature} disabled={!canConfirmSignature} className="flex-1 rounded-xl bg-blue-600 px-3 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50">
                      Save Signature
                    </button>
                  </div>
                </div>
              )}
              {method === 'upload' && (
                <div className="space-y-3">
                  <button onClick={() => signatureInputRef.current?.click()} className="flex w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-blue-200 bg-blue-50 px-4 py-5 text-blue-700 hover:bg-blue-100">
                    <ImageIcon className="mb-2 h-6 w-6" />
                    <span className="text-sm font-black">{signatureData ? 'Replace Signature Image' : 'Choose Signature Image'}</span>
                    <span className="text-xs font-semibold">PNG, JPEG, or WebP</span>
                  </button>
                  <input ref={signatureInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleSignatureUpload} />
                  {signatureData && (
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <div className="mb-2 flex items-center justify-between gap-2">
                        <p className="truncate text-xs font-bold text-slate-600">{uploadedSignatureName}</p>
                        <button onClick={() => { setSignatureData(''); setUploadedSignatureName(''); }} className="text-slate-400 hover:text-red-500"><X className="h-4 w-4" /></button>
                      </div>
                      <img src={signatureData} alt="Signature preview" className="mx-auto max-h-24 object-contain" />
                    </div>
                  )}
                  <button onClick={confirmSignature} disabled={!canConfirmSignature} className="w-full rounded-xl bg-blue-600 px-3 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50">
                    Confirm Signature Image
                  </button>
                </div>
              )}
              {method === 'type' && (
                <div className="space-y-3">
                  <input value={typedName} onChange={(event) => setTypedName(event.target.value)} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm font-bold text-slate-800 outline-none focus:border-blue-400" placeholder="Enter your name" />
                  <div className="flex h-28 items-center justify-center rounded-2xl border border-slate-200 bg-slate-50 px-4">
                    <span className="font-serif text-4xl italic text-slate-900">{typedName || 'Your Name'}</span>
                  </div>
                  <button onClick={confirmSignature} disabled={!canConfirmSignature} className="w-full rounded-xl bg-blue-600 px-3 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50">
                    Confirm Typed Signature
                  </button>
                </div>
              )}
            </section>
          )}

          {workflow === 'placement' && method !== 'aadhaar_esign' && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 flex items-center gap-2 font-black text-slate-800"><MousePointer2 className="h-4 w-4" /> 4. Place Signature</h2>
              <div className="space-y-3 text-sm">
                <label className="block">
                  <span className="mb-1 block text-xs font-bold text-slate-500">Page</span>
                  <input type="number" min="1" max={numPages || 1} value={pageNumber} onChange={(event) => setPageNumber(Math.max(1, Math.min(numPages || 1, Number(event.target.value))))} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-bold" />
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <NumberField label="X" value={placement.x} onChange={(value) => updatePlacement({ x: value })} />
                  <NumberField label="Y" value={placement.y} onChange={(value) => updatePlacement({ y: value })} />
                  <NumberField label="Width" value={placement.width} onChange={(value) => updatePlacement({ width: value })} />
                  <NumberField label="Height" value={placement.height} onChange={(value) => updatePlacement({ height: value })} />
                </div>
                <button onClick={() => setWorkflowSafe('review')} disabled={!canPlace || !pageSize} className="w-full rounded-xl bg-slate-900 px-3 py-3 font-black text-white hover:bg-slate-800 disabled:opacity-50">
                  Review Document
                </button>
              </div>
            </section>
          )}

          {workflow === 'identity_verification' && method === 'aadhaar_esign' && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 font-black text-slate-800">Identity Verification</h2>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 mb-4">
                 <p className="text-sm font-semibold text-slate-700 mb-2">Status:</p>
                 <p className="text-sm font-black text-slate-900">{identityStatus === 'NOT_STARTED' ? 'Waiting for verification' : identityStatus}</p>
              </div>
              <button onClick={startIdentityVerification} disabled={isProcessing} className="w-full rounded-xl bg-blue-600 px-3 py-3 font-black text-white hover:bg-blue-700 disabled:opacity-50">
                Start Aadhaar eSign Verification
              </button>
            </section>
          )}

          {workflow === 'review' && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 font-black text-slate-800">5. Review</h2>
              <ReviewRows
                rows={[
                  ['Document', file?.name],
                  ['Pages', numPages || 'Loading'],
                  ['Signature Method', METHOD_LABELS[method]],
                  ...(method === 'aadhaar_esign' ? [
                    ['Signer', 'Authenticated User'],
                    ['Role', 'Signer'],
                    ['Identity Status', identityStatus],
                    ['Document Hash', transaction?.original_hash ? transaction.original_hash.substring(0, 16) + '...' : 'Pending'],
                  ] : []),
                  ['Selected Page', pageNumber],
                  ['Position', `${Math.round(placement.x)}, ${Math.round(placement.y)}`],
                  ['Size', `${Math.round(placement.width)} x ${Math.round(placement.height)}`],
                ]}
              />
              <div className="mt-4 flex gap-2">
                <button onClick={() => setWorkflowSafe(method === 'aadhaar_esign' ? 'identity_verification' : 'placement')} disabled={isProcessing} className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-600 hover:bg-slate-50">
                  Back / Edit
                </button>
                <button onClick={confirmSign} disabled={isProcessing || (method === 'aadhaar_esign' && identityStatus === 'FAILED')} className="flex-1 rounded-xl bg-emerald-600 px-3 py-2 text-sm font-black text-white hover:bg-emerald-700 disabled:opacity-50">
                  Confirm Sign
                </button>
              </div>
            </section>
          )}

          {workflow === 'signing' && (
            <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5 text-blue-800 shadow-sm">
              <RefreshCw className="mb-3 h-6 w-6 animate-spin" />
              <h2 className="font-black">Signing...</h2>
              <p className="text-sm font-semibold">Processing PDF and verifying the output.</p>
            </section>
          )}

          {workflow === 'completed' && result && (
            <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
              <CheckCircle2 className="mb-3 h-10 w-10 text-emerald-600" />
              <h2 className="mb-2 font-black text-emerald-900">Document Verification</h2>
              <VerificationList verification={result.verification} />
              <a href={API_BASE_URL + result.downloadUrl} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-black text-white hover:bg-emerald-700">
                <Download className="h-4 w-4" /> Download Signed PDF
              </a>
              <button onClick={createShare} disabled={isProcessing} className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-white px-4 py-3 text-sm font-black text-emerald-700 hover:bg-emerald-50 disabled:opacity-50">
                <Share2 className="h-4 w-4" /> Create Secure Share Link
              </button>
              {shareResult?.share_url && (
                <div className="mt-3 rounded-xl border border-emerald-200 bg-white p-3 text-xs font-bold text-emerald-800">
                  <div className="mb-1 flex items-center gap-1"><Link className="h-3.5 w-3.5" /> Share URL</div>
                  <code className="break-all">{shareResult.share_url}</code>
                </div>
              )}
              <button onClick={resetAll} className="mt-4 w-full text-xs font-black text-emerald-700 underline underline-offset-4">
                Sign another document
              </button>
            </section>
          )}
        </aside>

        <main className="w-full flex-1 rounded-2xl border border-slate-200 bg-white shadow-sm lg:sticky lg:top-4 flex flex-col" style={{ height: "calc(100vh - 40px)", minHeight: "820px" }}>
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3 shrink-0">
            <div className="flex items-center gap-2 text-sm font-black text-slate-700">
              <FileText className="h-4 w-4" /> Live PDF Preview
            </div>
            {numPages && (
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-2 py-1.5 text-sm font-bold text-slate-700">
                  <button onClick={() => setPageNumber((value) => Math.max(1, value - 1))} disabled={pageNumber <= 1} className="px-2 disabled:opacity-30 hover:text-blue-600 transition-colors">Prev</button>
                  <span className="px-2 border-x border-slate-200">Page {pageNumber} / {numPages}</span>
                  <button onClick={() => setPageNumber((value) => Math.min(numPages, value + 1))} disabled={pageNumber >= numPages} className="px-2 disabled:opacity-30 hover:text-blue-600 transition-colors">Next</button>
                </div>
                <div className="flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-2 py-1.5 text-sm font-bold text-slate-700 hidden sm:flex">
                  <button onClick={() => setScale(s => Math.max(0.5, s - 0.25))} className="px-2 hover:text-blue-600 transition-colors">Zoom -</button>
                  <span className="px-2 border-x border-slate-200 min-w-[3.5rem] text-center">{Math.round(scale * 100)}%</span>
                  <button onClick={() => setScale(s => Math.min(3, s + 0.25))} className="px-2 hover:text-blue-600 transition-colors">Zoom +</button>
                  <button onClick={() => setScale(1)} className="px-2 border-l border-slate-200 ml-1 pl-3 hover:text-blue-600 transition-colors">Fit</button>
                </div>
              </div>
            )}
          </div>

          <div className="flex flex-1 justify-center overflow-auto bg-slate-200/50 p-4 sm:p-8">
            {file ? (
              <div className="relative inline-block self-start shadow-xl">
                <Document file={file} onLoadSuccess={onDocumentLoadSuccess} onLoadError={() => setError('PDF validation failed. Please choose a readable PDF.')} loading={<div className="p-20 text-sm font-bold text-slate-500">Loading PDF...</div>}>
                  <div ref={previewRef} className="relative">
                    <Page pageNumber={pageNumber} scale={scale} onLoadSuccess={onPageLoadSuccess} onRenderSuccess={onPageRenderSuccess} renderAnnotationLayer={false} renderTextLayer={false} className="bg-white" />
                    {workflow !== 'idle' && canPlace && pageSize && (
                      <div
                        onPointerDown={(event) => startPlacementDrag(event, 'move')}
                        onPointerMove={movePlacement}
                        onPointerUp={endPlacementDrag}
                        onPointerCancel={endPlacementDrag}
                        style={{ left: placementPreview.x, top: placementPreview.y, width: placementPreview.width, height: placementPreview.height }}
                        className="absolute z-20 cursor-move rounded border-2 border-blue-500 bg-blue-500/10 shadow-lg"
                      >
                        {method === 'type' ? (
                          <div className="flex h-full w-full items-center justify-center overflow-hidden bg-white/70 px-2 font-serif text-2xl italic text-slate-900">
                            {typedName || 'Your Name'}
                          </div>
                        ) : (
                          <img src={signatureData} alt="Signature placement preview" className="h-full w-full object-contain" />
                        )}
                        <button
                          type="button"
                          onPointerDown={(event) => startPlacementDrag(event, 'resize')}
                          onPointerMove={movePlacement}
                          onPointerUp={endPlacementDrag}
                          className="absolute -bottom-2 -right-2 h-5 w-5 cursor-nwse-resize rounded-full border-2 border-white bg-blue-600 shadow"
                          aria-label="Resize signature"
                        />
                      </div>
                    )}
                  </div>
                </Document>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center text-slate-400">
                <FileText className="mb-4 h-16 w-16 opacity-25" />
                <p className="font-bold">Upload a PDF to begin eSigning</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function NumberField({ label, value, onChange }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-bold text-slate-500">{label}</span>
      <input type="number" value={Math.round(value)} onChange={(event) => onChange(Number(event.target.value || 0))} className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-bold text-slate-700" />
    </label>
  );
}

function ReviewRows({ rows }) {
  return (
    <div className="space-y-2 text-sm">
      {rows.map(([label, value]) => (
        <div key={label} className="flex justify-between gap-3 border-b border-slate-100 pb-2">
          <span className="font-semibold text-slate-500">{label}</span>
          <span className="max-w-[170px] truncate text-right font-black text-slate-800" title={String(value || '')}>{value}</span>
        </div>
      ))}
    </div>
  );
}

function VerificationList({ verification }) {
  const checks = verification?.checks || {};
  const labels = {
    pdf_generated: 'PDF generated successfully',
    output_pdf_readable: 'Output PDF readable',
    signature_embedded: 'Signature embedded',
    page_verified: 'Page verified',
    integrity_hash_generated: 'Integrity hash generated',
    page_count_preserved: 'Original page count preserved',
  };
  return (
    <div className="space-y-2 text-sm">
      {Object.entries(labels).filter(([key]) => key in checks).map(([key, label]) => (
        <div key={key} className="flex items-center gap-2 font-bold text-emerald-800">
          {checks[key] ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4 text-red-500" />}
          <span>{label}</span>
        </div>
      ))}
      {verification?.sha256 && (
        <div className="mt-3 rounded-xl border border-emerald-200 bg-white p-3">
          <p className="mb-1 text-xs font-black uppercase text-emerald-700">SHA-256</p>
          <code className="break-all text-[11px] text-slate-700">{verification.sha256}</code>
        </div>
      )}
    </div>
  );
}
