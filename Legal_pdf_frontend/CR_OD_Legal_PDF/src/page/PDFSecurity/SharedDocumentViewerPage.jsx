import React, { useState, useEffect } from 'react';
import { ArrowLeft, Lock, FileText, Download, AlertTriangle, EyeOff } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

export default function SharedDocumentViewerPage({ onBack }) {
  const [token, setToken] = useState('');
  const [status, setStatus] = useState('loading'); // loading, password_required, valid, error
  const [errorDetails, setErrorDetails] = useState('');
  const [password, setPassword] = useState('');
  const [shareData, setShareData] = useState(null);
  
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfBlob, setPdfBlob] = useState(null);

  useEffect(() => {
    const parts = window.location.hash.replace('#', '').split('/');
    if (parts.length > 1 && parts[0] === 'shared') {
      const t = parts[1];
      setToken(t);
      validateShare(t);
    } else {
      setStatus('error');
      setErrorDetails('Invalid share link format.');
    }
  }, []);

  const validateShare = async (t) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/pdf/security/secure-sharing/${t}/validate`);
      const data = await res.json();
      
      if (!res.ok) {
        if (res.status === 403) {
           setStatus('error');
           setErrorDetails(data.detail || 'Access denied.');
           return;
        }
        throw new Error(data.detail || 'Failed to validate share link.');
      }
      
      setShareData(data);
      if (data.has_password) {
        setStatus('password_required');
      } else {
        loadDocument(t, null);
      }
    } catch (err) {
      setStatus('error');
      setErrorDetails(err.message || 'The share link is invalid or no longer exists.');
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (!password) return;
    
    try {
      const formData = new FormData();
      formData.append('password', password);
      
      const res = await fetch(`${API_BASE_URL}/api/pdf/security/secure-sharing/${token}/verify`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Incorrect password.');
      }
      
      loadDocument(token, password);
    } catch (err) {
      alert(err.message);
    }
  };

  const loadDocument = async (t, pwd) => {
    setStatus('loading_doc');
    try {
      let url = `${API_BASE_URL}/api/pdf/security/secure-sharing/${t}/access`;
      if (pwd) {
        url += `?password=${encodeURIComponent(pwd)}`;
      }
      
      const res = await fetch(url);
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to load document.');
      }
      
      const blob = await res.blob();
      setPdfBlob(window.URL.createObjectURL(blob));
      setStatus('valid');
    } catch (err) {
      setStatus('error');
      setErrorDetails(err.message);
    }
  };

  const handleDownload = () => {
    if (!pdfBlob || !shareData?.allow_download) return;
    const a = document.createElement('a');
    a.href = pdfBlob;
    a.download = shareData.filename || 'shared_document.pdf';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };
  
  // Prevent right click and printing if not allowed
  useEffect(() => {
    const handleContextMenu = (e) => e.preventDefault();
    const handleKeyDown = (e) => {
      // Prevent Ctrl+P (Print), Ctrl+S (Save), etc if not allowed
      if (!shareData?.allow_print && e.ctrlKey && e.key === 'p') e.preventDefault();
      if (!shareData?.allow_download && e.ctrlKey && e.key === 's') e.preventDefault();
    };

    if (status === 'valid') {
      document.addEventListener('contextmenu', handleContextMenu);
      document.addEventListener('keydown', handleKeyDown);
    }
    
    return () => {
      document.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [status, shareData]);

  if (status === 'loading' || status === 'loading_doc') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] bg-[#f8faf7]">
        <div className="w-12 h-12 border-4 border-[#1e2a52] border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-sm font-bold text-[#1e2a52] animate-pulse">
          {status === 'loading' ? 'Validating secure link...' : 'Loading secure document...'}
        </p>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] bg-[#f8faf7] px-4">
        <div className="bg-white p-8 rounded-2xl shadow-lg border border-red-100 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-800 mb-2">Access Denied</h2>
          <p className="text-slate-600 mb-6">{errorDetails}</p>
          <button onClick={() => window.location.hash = '#home'} className="bg-[#1e2a52] text-white px-6 py-2.5 rounded-full font-bold hover:bg-[#16203e] transition-all text-sm w-full">
            Return to Home
          </button>
        </div>
      </div>
    );
  }

  if (status === 'password_required') {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] bg-[#f8faf7] px-4">
        <div className="bg-white p-8 rounded-2xl shadow-lg border border-slate-200 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Lock className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-800 mb-2">Protected Document</h2>
          <p className="text-sm text-slate-500 mb-6">This shared document is protected by a password.</p>
          
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <input 
              type="password" 
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Enter password..."
              className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-center"
              required
            />
            <button type="submit" className="bg-[#1e2a52] text-white px-6 py-3 rounded-xl font-bold hover:bg-[#16203e] transition-all text-sm w-full shadow-md">
              Unlock Document
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col w-full relative z-20 min-h-screen bg-slate-900">
      {/* Header */}
      <div className="w-full bg-slate-800 border-b border-slate-700 px-4 sm:px-6 py-3 flex items-center justify-between text-white sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <button onClick={() => window.location.hash = '#home'} className="p-2 hover:bg-slate-700 rounded-full transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500/20 p-2 rounded-lg text-emerald-400">
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold truncate max-w-[200px] sm:max-w-md">{shareData?.filename}</h1>
              <p className="text-xs text-slate-400">Secure PDF Share</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {!shareData?.allow_print && (
             <span className="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-400 bg-slate-700/50 px-3 py-1.5 rounded-full">
               <EyeOff className="w-3.5 h-3.5" /> Print Disabled
             </span>
          )}
          {shareData?.allow_download && (
            <button onClick={handleDownload} className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-full font-bold transition-all text-xs sm:text-sm shadow-md">
              <Download className="w-4 h-4" /> <span className="hidden sm:inline">Download</span>
            </button>
          )}
        </div>
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 overflow-auto flex justify-center bg-slate-900 p-4 sm:p-8" 
           style={{ 
             userSelect: shareData?.allow_download ? 'auto' : 'none',
             WebkitUserSelect: shareData?.allow_download ? 'auto' : 'none'
           }}>
        {pdfBlob && (
          <Document
            file={pdfBlob}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            loading={<div className="text-white">Loading PDF...</div>}
            className="flex flex-col items-center gap-4"
          >
            {Array.from(new Array(numPages), (el, index) => (
              <Page 
                key={`page_${index + 1}`} 
                pageNumber={index + 1} 
                className="shadow-2xl !bg-white overflow-hidden max-w-full"
                renderTextLayer={shareData?.allow_download}
                renderAnnotationLayer={shareData?.allow_download}
                width={Math.min(window.innerWidth - 32, 1000)}
              />
            ))}
          </Document>
        )}
      </div>
    </div>
  );
}
