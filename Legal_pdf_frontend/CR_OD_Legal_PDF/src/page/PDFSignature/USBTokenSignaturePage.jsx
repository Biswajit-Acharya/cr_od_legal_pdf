import React, { useEffect, useState, useRef } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  Download,
  FileText,
  Key,
  ShieldCheck,
  Usb,
  RefreshCw,
  Upload,
} from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
const MAX_UPLOAD_MB = 100;

export default function UsbTokenSignaturePage({ onBack }) {
  const [workflow, setWorkflow] = useState('idle'); // idle, token_detected, certificate_selected, signing, completed
  const [file, setFile] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [error, setError] = useState('');
  
  const [tokenStatus, setTokenStatus] = useState(null);
  const [certificates, setCertificates] = useState([]);
  const [selectedCert, setSelectedCert] = useState(null);
  const [pin, setPin] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  
  const fileInputRef = useRef(null);

  const handleFile = (incomingFile) => {
    setError('');
    setResult(null);
    if (!incomingFile) return;
    if (incomingFile.type !== 'application/pdf' && !incomingFile.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF documents can be uploaded.');
      return;
    }
    if (incomingFile.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`PDF is too large. Maximum upload size is ${MAX_UPLOAD_MB} MB.`);
      return;
    }
    setFile(incomingFile);
    setWorkflow('file_uploaded');
  };

  const handleDrop = (event) => {
    event.preventDefault();
    handleFile(event.dataTransfer.files?.[0]);
  };

  const checkToken = async () => {
    setIsProcessing(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/usb-token/status`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to detect token.');
      
      setTokenStatus(data);
      if (data.connected) {
        await loadCertificates();
      } else {
        setError(data.error || 'Token not detected.');
      }
    } catch (err) {
      setError(err.message || 'Error communicating with USB token middleware.');
    } finally {
      setIsProcessing(false);
    }
  };

  const loadCertificates = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/pdf/usb-token/certificates`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Failed to load certificates.');
      
      if (data.success && data.certificates) {
        setCertificates(data.certificates);
        setWorkflow('token_detected');
      } else {
        setError(data.error || 'Could not load certificates from token.');
      }
    } catch (err) {
      setError(err.message || 'Error reading certificates.');
    }
  };

  const selectCertificate = async (cert) => {
    setIsProcessing(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('serial_number', cert.serial_number);
      
      const response = await fetch(`${API_BASE_URL}/api/pdf/usb-token/validate-certificate`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Certificate validation failed.');
      
      if (data.valid) {
        setSelectedCert(cert);
        setWorkflow('certificate_selected');
      } else {
        setError(data.error || 'Certificate is not valid for signing.');
      }
    } catch (err) {
      setError(err.message || 'Error validating certificate.');
    } finally {
      setIsProcessing(false);
    }
  };

  const performSigning = async () => {
    if (!pin) {
      setError('Please enter the token PIN.');
      return;
    }
    setIsProcessing(true);
    setError('');
    setWorkflow('signing');
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('pin', pin);
      formData.append('cert_serial', selectedCert.serial_number);
      
      const response = await fetch(`${API_BASE_URL}/api/pdf/usb-token/sign`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Cryptographic signing failed.');
      
      setResult(data);
      setWorkflow('completed');
    } catch (err) {
      setError(err.message || 'Signing failed. Token may have been disconnected or PIN is incorrect.');
      setWorkflow('certificate_selected');
    } finally {
      setIsProcessing(false);
      setPin(''); // Clear PIN immediately
    }
  };

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  return (
    <div className="flex min-h-screen w-full flex-col bg-slate-50">
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between px-4 pb-4 pt-6">
        <button onClick={onBack} className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <div className="text-center">
          <h1 className="text-2xl font-black tracking-tight text-slate-900">USB Token Signature (PKCS#11)</h1>
          <p className="text-sm font-medium text-slate-500">Hardware-backed cryptographic signing</p>
        </div>
        <div className="w-[92px]" />
      </div>

      <div className="mx-auto flex w-full max-w-[1440px] flex-col lg:flex-row gap-6 px-4 pb-12 items-start">
        <aside className="w-full lg:w-[420px] shrink-0 space-y-4">
          
          {error && (
            <div className="flex items-start gap-2 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm font-semibold text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
            </div>
          )}

          {/* 1. PDF Upload */}
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-3 flex items-center gap-2 font-black text-slate-800"><FileText className="h-4 w-4" /> 1. Document</h2>
            {!file ? (
              <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleDrop}
                className="flex min-h-32 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-4 text-center"
              >
                <Upload className="mb-3 h-6 w-6 text-slate-400" />
                <p className="text-sm font-bold text-slate-700">Drag and drop a PDF</p>
                <button onClick={() => fileInputRef.current?.click()} className="mt-3 rounded-xl bg-slate-800 px-4 py-2 text-sm font-bold text-white hover:bg-slate-900">
                  Choose PDF
                </button>
                <input ref={fileInputRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />
              </div>
            ) : (
              <div className="rounded-xl border border-blue-100 bg-blue-50 p-3 flex justify-between items-center">
                <div className="truncate">
                  <p className="truncate text-sm font-black text-blue-950" title={file.name}>{file.name}</p>
                  <p className="mt-1 text-xs font-semibold text-blue-700">{(file.size / (1024*1024)).toFixed(2)} MB</p>
                </div>
                {workflow !== 'signing' && workflow !== 'completed' && (
                  <button onClick={() => setFile(null)} className="text-xs font-bold text-blue-600 underline">Remove</button>
                )}
              </div>
            )}
          </section>

          {/* 2. Token Detection */}
          {file && (workflow === 'file_uploaded' || workflow === 'token_detected' || workflow === 'certificate_selected') && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex justify-between items-center mb-3">
                 <h2 className="flex items-center gap-2 font-black text-slate-800"><Usb className="h-4 w-4" /> 2. USB Token</h2>
                 <button onClick={checkToken} disabled={isProcessing} className="text-blue-600 hover:text-blue-800"><RefreshCw className={`h-4 w-4 ${isProcessing ? 'animate-spin' : ''}`} /></button>
              </div>
              
              {!tokenStatus?.connected ? (
                 <div className="text-center py-4 bg-slate-50 rounded-xl border border-slate-100">
                    <p className="text-sm font-bold text-slate-600 mb-2">Connect your DSC USB Token</p>
                    <button onClick={checkToken} disabled={isProcessing} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700">
                      Detect Token
                    </button>
                 </div>
              ) : (
                 <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-3 space-y-1">
                   <div className="flex justify-between text-xs">
                     <span className="font-semibold text-emerald-700">Token</span>
                     <span className="font-bold text-emerald-900">{tokenStatus.token_name}</span>
                   </div>
                   <div className="flex justify-between text-xs">
                     <span className="font-semibold text-emerald-700">Manufacturer</span>
                     <span className="font-bold text-emerald-900">{tokenStatus.manufacturer}</span>
                   </div>
                   <div className="flex justify-between text-xs">
                     <span className="font-semibold text-emerald-700">Serial</span>
                     <span className="font-bold text-emerald-900">{tokenStatus.serial_number}</span>
                   </div>
                 </div>
              )}
            </section>
          )}

          {/* 3. Certificate Selection */}
          {tokenStatus?.connected && (workflow === 'token_detected' || workflow === 'certificate_selected') && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 flex items-center gap-2 font-black text-slate-800"><ShieldCheck className="h-4 w-4" /> 3. Select Certificate</h2>
              
              {!selectedCert ? (
                <div className="space-y-2">
                  {certificates.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">No certificates found on token.</p>
                  ) : (
                    certificates.map((cert) => (
                      <button 
                        key={cert.serial_number}
                        onClick={() => selectCertificate(cert)}
                        disabled={isProcessing || cert.status !== 'valid'}
                        className={`w-full text-left p-3 rounded-xl border text-sm transition-colors ${cert.status === 'valid' ? 'border-slate-200 hover:border-blue-300 hover:bg-blue-50' : 'border-red-100 bg-red-50 opacity-60'}`}
                      >
                        <p className="font-black text-slate-800 truncate">{cert.owner.split(',')[0]}</p>
                        <p className="text-xs text-slate-500 mt-1">Issuer: {cert.issuer.split(',')[0]}</p>
                        <p className="text-xs text-slate-500">Valid until: {new Date(cert.validity_end).toLocaleDateString()}</p>
                      </button>
                    ))
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-3">
                  <div className="flex justify-between items-start mb-2">
                    <p className="font-black text-blue-900">{selectedCert.owner.split(',')[0]}</p>
                    <button onClick={() => setSelectedCert(null)} className="text-xs font-bold text-blue-600 underline">Change</button>
                  </div>
                  <p className="text-xs text-blue-700">Serial: {selectedCert.serial_number}</p>
                  <p className="text-xs text-blue-700">Valid till: {new Date(selectedCert.validity_end).toLocaleDateString()}</p>
                </div>
              )}
            </section>
          )}

          {/* 4. PIN & Sign */}
          {selectedCert && (workflow === 'certificate_selected' || workflow === 'signing') && (
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-3 flex items-center gap-2 font-black text-slate-800"><Key className="h-4 w-4" /> 4. Token Authentication</h2>
              
              {workflow === 'signing' ? (
                 <div className="flex flex-col items-center justify-center py-6 text-blue-600">
                    <RefreshCw className="h-8 w-8 animate-spin mb-3" />
                    <p className="font-bold text-sm">Performing Cryptographic Signature...</p>
                    <p className="text-xs mt-1 text-slate-500 text-center">Please do not remove your USB Token</p>
                 </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-600 mb-1">Enter Token PIN</label>
                    <input 
                      type="password" 
                      value={pin}
                      onChange={(e) => setPin(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-bold text-slate-800 outline-none focus:border-blue-500"
                      placeholder="••••••••"
                    />
                    <p className="text-[10px] text-slate-400 mt-1">PIN is sent securely to the local token and is never stored.</p>
                  </div>
                  <button 
                    onClick={performSigning} 
                    disabled={!pin || isProcessing}
                    className="w-full rounded-xl bg-slate-900 px-4 py-3 text-sm font-black text-white hover:bg-slate-800 disabled:opacity-50"
                  >
                    Sign Document
                  </button>
                </div>
              )}
            </section>
          )}

          {/* 5. Completed / Result */}
          {workflow === 'completed' && result && (
            <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
              <CheckCircle2 className="mb-3 h-10 w-10 text-emerald-600" />
              <h2 className="mb-2 font-black text-emerald-900">Signed Successfully</h2>
              <div className="space-y-2 text-sm text-emerald-800 font-semibold mb-4">
                 <p>✓ Hardware cryptographic signature embedded</p>
                 <p>✓ PDF byte-range integrity preserved</p>
                 <p>✓ Token session closed</p>
              </div>
              <a href={API_BASE_URL + result.downloadUrl} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-black text-white hover:bg-emerald-700">
                <Download className="h-4 w-4" /> Download Signed PDF
              </a>
              <button onClick={() => {
                setWorkflow('idle');
                setFile(null);
                setTokenStatus(null);
                setSelectedCert(null);
                setCertificates([]);
                setResult(null);
              }} className="mt-3 w-full text-xs font-bold text-emerald-700 underline underline-offset-4">
                Sign Another Document
              </button>
            </section>
          )}

        </aside>

        <main className="w-full flex-1 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col min-h-[600px]">
          <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3 shrink-0">
            <div className="flex items-center gap-2 text-sm font-black text-slate-700">
              <FileText className="h-4 w-4" /> PDF Preview
            </div>
          </div>
          <div className="flex flex-1 justify-center overflow-auto bg-slate-200/50 p-4">
            {file ? (
              <Document file={file} onLoadSuccess={onDocumentLoadSuccess} loading="Loading PDF...">
                <Page pageNumber={pageNumber} renderAnnotationLayer={false} renderTextLayer={false} width={600} />
              </Document>
            ) : (
              <div className="flex flex-col items-center justify-center text-slate-400">
                <FileText className="mb-4 h-16 w-16 opacity-25" />
                <p className="font-bold">Upload a PDF to view</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
