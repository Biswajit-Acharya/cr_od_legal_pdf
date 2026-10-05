import React, { useState, useRef } from 'react';
import { Upload, FileText, ArrowLeft, AlertCircle, CheckCircle2, Download, ShieldCheck, ShieldAlert, Key, FileBadge, Check, X, Search, FileSignature } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function DigitalSignPage({ tool, onBack }) {
  // Global Workflow State
  const [step, setStep] = useState(1); // 1: PDF, 2: Cert, 3: Config, 4: Review, 5: Done
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');

  // 1. PDF State
  const [file, setFile] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfScale, setPdfScale] = useState(1);

  // 2. Certificate State
  const [certFile, setCertFile] = useState(null);
  const [certPassword, setCertPassword] = useState('');
  const [certInfo, setCertInfo] = useState(null); // Metadata from backend

  // 3. Configuration State
  const [isVisible, setIsVisible] = useState(true);
  const [reason, setReason] = useState('Document Approval');
  const [location, setLocation] = useState('');
  
  // Signature Box Position (Visible only)
  const [box, setBox] = useState({ x: 100, y: 100, width: 200, height: 60 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const signingRequestRef = useRef(false);

  // 5. Success/Validation State
  const [downloadUrl, setDownloadUrl] = useState('');
  const [validationReport, setValidationReport] = useState(null);

  // === Handlers ===

  const handlePdfUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError('');
    }
  };

  const handleCertUpload = (e) => {
    if (e.target.files && e.target.files[0]) {
      setCertFile(e.target.files[0]);
      setError('');
    }
  };

  const loadCertificate = async () => {
    if (!certFile) {
      setError("Please select a certificate file.");
      return;
    }
    setError('');
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('file', certFile);
      formData.append('password', certPassword);

      const response = await fetch(`${API_BASE_URL}/api/pdf/signature/digital/parse-cert`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to load certificate");
      
      setCertInfo(data);
      setStep(3); // Move to config
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSign = async () => {
    if (signingRequestRef.current || isProcessing) return;
    if (!file || !certFile || !certInfo) {
      setError('Please upload a PDF and load a digital certificate before signing.');
      return;
    }
    signingRequestRef.current = true;
    setError('');
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('cert_file', certFile);
      formData.append('password', certPassword);
      
      const config = {
        visible: isVisible,
        reason: reason,
        location: location,
        page: pageNumber,
        x: box.x,
        y: box.y,
        width: box.width,
        height: box.height
      };
      formData.append('config', JSON.stringify(config));

      const response = await fetch(`${API_BASE_URL}/api/pdf/signature/digital/sign`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to sign document");
      
      setDownloadUrl(data.downloadUrl);
      setStep(5); // Move to success
    } catch (err) {
      setError(err.message);
    } finally {
      signingRequestRef.current = false;
      setIsProcessing(false);
    }
  };

  const validateSignature = async () => {
    if (!downloadUrl) return;
    setIsProcessing(true);
    setError('');
    try {
      // In a real scenario, we'd fetch the signed file or just validate it directly if it's stored.
      // Since it's stored on the backend, we can just fetch it as a blob and re-upload, or build an endpoint to validate by ID.
      // We will re-download it as a blob and upload it to `/validate`
      const dlRes = await fetch(`${API_BASE_URL}${downloadUrl}`);
      const blob = await dlRes.blob();
      
      const formData = new FormData();
      formData.append('file', blob, 'signed_doc.pdf');

      const response = await fetch(`${API_BASE_URL}/api/pdf/signature/digital/validate`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to validate document");
      
      setValidationReport(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  // Drag Handlers for visible box
  const handleMouseDown = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left - box.x,
      y: e.clientY - rect.top - box.y
    });
    setIsDragging(true);
    e.preventDefault();
  };

  const handleMouseMove = (e) => {
    if (!isDragging || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    let newX = e.clientX - rect.left - dragOffset.x;
    let newY = e.clientY - rect.top - dragOffset.y;
    
    // Bounds check
    newX = Math.max(0, Math.min(newX, rect.width - box.width));
    newY = Math.max(0, Math.min(newY, rect.height - box.height));
    
    setBox({ ...box, x: newX, y: newY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div className="flex-1 flex flex-col w-full min-h-screen bg-slate-50" onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
      {/* Header */}
      <div className="w-full max-w-[1400px] mx-auto px-4 pt-6 pb-4">
        <div className="flex justify-between items-center mb-4">
          <button onClick={onBack} className="inline-flex items-center gap-2 bg-white text-slate-700 font-semibold px-4 py-2 rounded-xl shadow-sm border border-slate-200 hover:bg-slate-50">
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <h1 className="text-2xl font-black text-slate-800 tracking-tight">Digital Signature</h1>
          <div className="w-[100px]"></div> {/* Spacer */}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-2">
          <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
            <p className="text-sm font-medium text-slate-700 mb-3">
              Apply a cryptographically secure digital signature to a PDF using a digital certificate.
            </p>
            <div className="text-xs space-y-2">
              <div className="flex gap-2">
                <span className="font-bold text-slate-800 min-w-[130px]">Electronic Signature:</span>
                <span className="text-slate-600">Draw/type/upload signature appearance.</span>
              </div>
              <div className="flex gap-2">
                <span className="font-bold text-slate-800 min-w-[130px]">Digital Signature:</span>
                <span className="text-slate-600">Certificate-based cryptographic signature that verifies document integrity and signer/certificate information.</span>
              </div>
            </div>
          </div>
          
          <div className="bg-blue-50 p-4 rounded-2xl border border-blue-100">
            <h3 className="text-sm font-bold text-blue-900 mb-2">Purpose</h3>
            <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-blue-800 list-disc list-inside">
              <li>Digitally sign PDF documents</li>
              <li>Verify document authenticity</li>
              <li>Protect document integrity</li>
              <li>Verify certificate/signer information</li>
              <li>Detect changes after signing</li>
              <li>Support secure business approvals</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="w-full max-w-[1400px] mx-auto px-4 pb-12 grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left Panel - Workflow Steps */}
        <div className="lg:col-span-1 space-y-4">
          
          {/* Step 1: PDF */}
          <div className={`bg-white p-5 rounded-2xl shadow-sm border ${step === 1 ? 'border-blue-400 ring-2 ring-blue-50' : 'border-slate-200'} transition-all`}>
            <h2 className="font-bold text-slate-800 flex items-center justify-between mb-3">
              <span className="flex items-center gap-2"><FileText className="w-4 h-4"/> 1. Document</span>
              {file && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
            </h2>
            {step === 1 && (
              <>
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                  <Upload className="w-6 h-6 text-slate-400 mb-2" />
                  <span className="text-sm font-medium text-slate-600">Upload PDF to sign</span>
                  <input type="file" accept=".pdf" className="hidden" onChange={handlePdfUpload} />
                </label>
                {file && (
                  <button onClick={() => setStep(2)} className="w-full mt-3 py-2 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700">Next Step &rarr;</button>
                )}
              </>
            )}
            {step > 1 && file && (
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 flex justify-between items-center cursor-pointer hover:bg-slate-100" onClick={() => setStep(1)}>
                <span className="text-sm font-semibold text-slate-700 truncate">{file.name}</span>
              </div>
            )}
          </div>

          {/* Step 2: Certificate */}
          {(step >= 2) && (
            <div className={`bg-white p-5 rounded-2xl shadow-sm border ${step === 2 ? 'border-blue-400 ring-2 ring-blue-50' : 'border-slate-200'} transition-all`}>
              <h2 className="font-bold text-slate-800 flex items-center justify-between mb-3">
                <span className="flex items-center gap-2"><Key className="w-4 h-4"/> 2. Digital Certificate</span>
                {certInfo && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
              </h2>
              
              {step === 2 && (
                <div className="space-y-4">
                  <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                    <span className="text-sm font-medium text-slate-600">{certFile ? certFile.name : 'Choose .P12 / .PFX'}</span>
                    <input type="file" accept=".p12,.pfx" className="hidden" onChange={handleCertUpload} />
                  </label>
                  <input type="password" value={certPassword} onChange={e => setCertPassword(e.target.value)} placeholder="Certificate Password" className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl font-medium focus:ring-2 focus:ring-blue-500 focus:outline-none" />
                  
                  {error && <div className="text-xs text-red-600 bg-red-50 p-3 rounded-xl flex items-start gap-2"><AlertCircle className="w-4 h-4 shrink-0 mt-0.5"/> {error}</div>}
                  
                  <button onClick={loadCertificate} disabled={isProcessing || !certFile} className="w-full py-2 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50">
                    {isProcessing ? 'Loading...' : 'Load Certificate'}
                  </button>
                </div>
              )}

              {step > 2 && certInfo && (
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 cursor-pointer hover:bg-slate-100" onClick={() => setStep(2)}>
                  <div className="flex items-center gap-2 mb-2">
                    <FileBadge className="w-4 h-4 text-blue-600"/>
                    <span className="text-sm font-bold text-slate-800 truncate">{certInfo.signer_name}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 flex justify-between border-t border-slate-200 pt-1 mt-1">
                    <span>{certInfo.algorithm}</span>
                    <span className={certInfo.is_expired ? 'text-red-500 font-bold' : 'text-emerald-500 font-bold'}>{certInfo.status}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Signature Configuration */}
          {(step >= 3) && (
            <div className={`bg-white p-5 rounded-2xl shadow-sm border ${step === 3 ? 'border-blue-400 ring-2 ring-blue-50' : 'border-slate-200'} transition-all`}>
              <h2 className="font-bold text-slate-800 flex items-center justify-between mb-3">
                <span className="flex items-center gap-2"><FileSignature className="w-4 h-4"/> 3. Configuration</span>
              </h2>
              
              {step === 3 && (
                <div className="space-y-4 text-sm">
                  <div className="flex gap-2 p-1 bg-slate-100 rounded-xl">
                    <button onClick={() => setIsVisible(true)} className={`flex-1 py-1.5 rounded-lg font-bold ${isVisible ? 'bg-white shadow text-blue-600' : 'text-slate-500'}`}>Visible</button>
                    <button onClick={() => setIsVisible(false)} className={`flex-1 py-1.5 rounded-lg font-bold ${!isVisible ? 'bg-white shadow text-blue-600' : 'text-slate-500'}`}>Invisible</button>
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-500">Reason</label>
                    <input type="text" value={reason} onChange={e=>setReason(e.target.value)} className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-blue-400" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-500">Location</label>
                    <input type="text" value={location} onChange={e=>setLocation(e.target.value)} className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-blue-400" placeholder="e.g. Bhubaneswar" />
                  </div>

                  <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg">
                    <p className="text-xs font-semibold text-blue-800">Hash Algorithm: <span className="font-bold">SHA-256</span></p>
                    <p className="text-xs text-blue-600 mt-1">Cryptographically secure</p>
                  </div>

                  {isVisible && (
                    <div className="text-xs text-amber-600 bg-amber-50 p-2 rounded-lg">
                      Adjust the signature box on the PDF preview before continuing.
                    </div>
                  )}

                  <button onClick={() => setStep(4)} className="w-full py-2 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700">Review & Sign &rarr;</button>
                </div>
              )}

              {step > 3 && (
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 cursor-pointer hover:bg-slate-100" onClick={() => setStep(3)}>
                  <p className="text-sm font-semibold text-slate-700">{isVisible ? 'Visible Signature' : 'Invisible Signature'}</p>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Review */}
          {step === 4 && (
            <div className="bg-slate-900 p-5 rounded-2xl shadow-sm text-white">
              <h2 className="font-bold mb-4 flex items-center gap-2"><ShieldCheck className="w-4 h-4"/> 4. Review & Apply</h2>
              
              <div className="space-y-2 text-xs mb-6 text-slate-300">
                <div className="flex justify-between border-b border-slate-800 pb-1">
                  <span>Signer:</span> <span className="font-bold text-white truncate max-w-[150px]">{certInfo.signer_name}</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-1">
                  <span>Type:</span> <span className="font-bold text-white">{isVisible ? 'Visible' : 'Invisible'}</span>
                </div>
                <div className="flex justify-between pb-1">
                  <span>Algorithm:</span> <span className="font-bold text-white">RSA / SHA-256</span>
                </div>
              </div>

              {error && <div className="mb-4 text-xs text-red-400 bg-red-950/50 p-3 rounded-xl border border-red-900 flex items-start gap-2"><AlertCircle className="w-4 h-4 shrink-0 mt-0.5"/> {error}</div>}

              <button onClick={handleSign} disabled={isProcessing || !file || !certFile || !certInfo} className="w-full py-3 bg-emerald-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-emerald-500 disabled:opacity-50 transition-colors shadow-sm">
                {isProcessing ? 'Signing PDF...' : 'Sign Document'}
              </button>
            </div>
          )}

        </div>

        {/* Right Panel - Viewer / Validation */}
        <div className="lg:col-span-3">
          
          {step < 5 ? (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col h-[800px] overflow-hidden">
              <div className="p-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center text-sm font-medium">
                <span className="text-slate-600 flex items-center gap-2"><Search className="w-4 h-4"/> Document Preview</span>
                {numPages && (
                  <div className="flex items-center gap-3 bg-white px-3 py-1 rounded-lg border border-slate-200 shadow-sm">
                    <button onClick={()=>setPageNumber(p=>Math.max(1, p-1))} disabled={pageNumber<=1} className="text-slate-500">&larr;</button>
                    <span className="font-bold text-slate-700">Page {pageNumber} <span className="text-slate-400 font-normal">of {numPages}</span></span>
                    <button onClick={()=>setPageNumber(p=>Math.min(numPages, p+1))} disabled={pageNumber>=numPages} className="text-slate-500">&rarr;</button>
                  </div>
                )}
              </div>
              
              <div className="flex-1 overflow-auto p-8 bg-slate-200/50 flex justify-center relative">
                {file ? (
                  <div ref={containerRef} className="relative shadow-xl inline-block">
                    <Document file={file} onLoadSuccess={({numPages}) => setNumPages(numPages)} loading={<div className="p-20 text-slate-500">Loading PDF...</div>}>
                      <Page pageNumber={pageNumber} scale={pdfScale} renderAnnotationLayer={false} renderTextLayer={false} className="bg-white" />
                    </Document>
                    
                    {/* Visual Signature Box overlay */}
                    {step >= 3 && isVisible && (
                      <div 
                        style={{ left: box.x, top: box.y, width: box.width, height: box.height }}
                        className={`absolute border-2 cursor-move bg-blue-500/10 transition-colors ${isDragging ? 'border-blue-600' : 'border-blue-400 hover:border-blue-500'}`}
                        onMouseDown={handleMouseDown}
                      >
                        <div className="w-full h-full p-1 flex flex-col text-[8px] sm:text-[10px] leading-tight text-blue-900 overflow-hidden pointer-events-none">
                          <span className="font-bold border-b border-blue-900/20 mb-0.5">Digitally Signed By</span>
                          <span className="font-black truncate text-xs">{certInfo?.signer_name || 'Signer'}</span>
                          <span className="truncate opacity-80">{reason}</span>
                          <span className="truncate opacity-80">{new Date().toLocaleDateString()}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400">
                    <FileText className="w-16 h-16 opacity-20 mb-4" />
                    <p className="font-medium">Upload a PDF to view</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            // Success & Validation Screen
            <div className="space-y-6">
              <div className="bg-emerald-50 border border-emerald-200 p-8 rounded-3xl text-center shadow-sm">
                <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
                <h2 className="text-2xl font-black text-emerald-900 mb-2">PDF Digitally Signed Successfully</h2>
                <p className="text-emerald-700 font-medium mb-8">Your document has been secured with a cryptographic digital signature.</p>
                
                <div className="flex gap-4 justify-center">
                  <a href={API_BASE_URL + downloadUrl} className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-600 text-white font-bold rounded-xl hover:bg-emerald-700 transition-colors shadow-md">
                    <Download className="w-5 h-5"/> Download Signed PDF
                  </a>
                  <button onClick={validateSignature} disabled={isProcessing} className="inline-flex items-center gap-2 px-6 py-3 bg-white border-2 border-emerald-600 text-emerald-700 font-bold rounded-xl hover:bg-emerald-50 transition-colors disabled:opacity-50 shadow-sm">
                    <ShieldCheck className="w-5 h-5"/> {isProcessing ? 'Validating...' : 'Validate Signature'}
                  </button>
                </div>
              </div>

              {validationReport && (
                <div className="bg-white border border-slate-200 rounded-3xl shadow-sm overflow-hidden">
                  <div className="p-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                    <h3 className="text-lg font-black text-slate-800 flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-blue-600"/> Validation Report
                    </h3>
                    <div className={`px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${validationReport.overall_valid ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                      {validationReport.overall_valid ? <><Check className="w-3 h-3"/> VALID</> : <><X className="w-3 h-3"/> INVALID</>}
                    </div>
                  </div>
                  
                  <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-6">
                      
                      <div>
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Integrity & Signature</h4>
                        <div className="space-y-3">
                          <div className="flex justify-between items-center p-3 rounded-xl border border-slate-100 bg-slate-50">
                            <span className="text-sm font-semibold text-slate-700">Signature Status</span>
                            {validationReport.signature_valid ? <span className="text-emerald-600 font-bold text-sm flex items-center gap-1"><CheckCircle2 className="w-4 h-4"/> Valid</span> : <span className="text-red-600 font-bold text-sm flex items-center gap-1"><ShieldAlert className="w-4 h-4"/> Invalid</span>}
                          </div>
                          <div className="flex justify-between items-center p-3 rounded-xl border border-slate-100 bg-slate-50">
                            <span className="text-sm font-semibold text-slate-700">Document Integrity</span>
                            {validationReport.document_integrity_valid ? <span className="text-emerald-600 font-bold text-sm flex items-center gap-1"><CheckCircle2 className="w-4 h-4"/> Untampered</span> : <span className="text-red-600 font-bold text-sm flex items-center gap-1"><ShieldAlert className="w-4 h-4"/> Modified</span>}
                          </div>
                        </div>
                      </div>

                      <div>
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Certificate Details</h4>
                        <div className="space-y-3">
                          <div className="flex justify-between items-center p-3 rounded-xl border border-slate-100 bg-slate-50">
                            <span className="text-sm font-semibold text-slate-700">Certificate Status</span>
                            {validationReport.certificate_valid && !validationReport.certificate_expired ? <span className="text-emerald-600 font-bold text-sm flex items-center gap-1"><CheckCircle2 className="w-4 h-4"/> Valid</span> : <span className="text-red-600 font-bold text-sm flex items-center gap-1"><ShieldAlert className="w-4 h-4"/> Invalid/Expired</span>}
                          </div>
                        </div>
                      </div>
                      
                    </div>
                    
                    <div className="bg-slate-50 rounded-2xl p-5 border border-slate-100 space-y-4 text-sm">
                      <h4 className="font-bold text-slate-800 mb-2">Signing Information</h4>
                      
                      <div className="grid grid-cols-3 gap-2 border-b border-slate-200 pb-3">
                        <span className="text-slate-500 font-medium">Signer</span>
                        <span className="col-span-2 font-bold text-slate-800 truncate">{validationReport.signer_name}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 border-b border-slate-200 pb-3">
                        <span className="text-slate-500 font-medium">Issuer</span>
                        <span className="col-span-2 font-bold text-slate-800 truncate">{validationReport.issuer}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 border-b border-slate-200 pb-3">
                        <span className="text-slate-500 font-medium">Algorithm</span>
                        <span className="col-span-2 font-bold text-slate-800">{validationReport.algorithm}</span>
                      </div>
                      <div className="grid grid-cols-3 gap-2 border-b border-slate-200 pb-3">
                        <span className="text-slate-500 font-medium">Timestamp</span>
                        <span className="col-span-2 font-bold text-slate-800">{validationReport.signing_time}</span>
                      </div>
                      {validationReport.modification_detected && (
                        <div className="bg-red-50 text-red-700 p-3 rounded-xl font-medium flex items-start gap-2 text-xs border border-red-100">
                          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5"/>
                          Warning: Document modification detected after signing. The document integrity is compromised.
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              <div className="text-center pt-4">
                <button onClick={() => { setStep(1); setFile(null); setCertFile(null); setCertInfo(null); setDownloadUrl(''); setValidationReport(null); setCertPassword(''); }} className="text-sm font-bold text-slate-500 hover:text-slate-800 underline underline-offset-4">
                  Sign Another Document
                </button>
              </div>
            </div>
          )}
          
        </div>
      </div>
    </div>
  );
}
