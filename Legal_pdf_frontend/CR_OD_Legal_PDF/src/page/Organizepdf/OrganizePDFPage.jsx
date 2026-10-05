import React, { useEffect } from 'react';

export default function OrganizePDFPage() {
  useEffect(() => {
    // Inject page logic script
    const scriptText = `/**
 * ================================================================
 * PAGE    : organizepdf
 * SERVICE : organize_pdf_services
 * ================================================================
 */

'use strict';

var PAGE_CONFIG = {
    endpoint: '/api/organize_pdf_services/organizepdf',
    acceptedTypes: ['application/pdf'],
    maxFileSizeMB: 100,
};

var state = {
    files: [],
    isProcessing: false,
};

function qs(sel) { return document.querySelector(sel); }
function show(el) { if (el) el.style.display = ''; }
function hide(el) { if (el) el.style.display = 'none'; }
function setProgress(pct) {
    const fill = qs('.progress-fill') || qs('#progressFill');
    if (fill) fill.style.width = pct + '%';
}

function initUpload() {
    const zones = document.querySelectorAll('[class*="upload-zone"], [id*="dropZone"], [id*="uploadZone"]');
    const inputs = document.querySelectorAll('input[type="file"]');
    
    if (zones.length === 0 || inputs.length === 0) return;
    
    const zone = zones[0];
    const input = inputs[0];

    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
    });

    input.addEventListener('change', () => {
        if (input.files.length) handleFiles(input.files);
    });
}

function handleFiles(fileList) {
    if (!fileList || fileList.length === 0) return;
    
    for (let i = 0; i < fileList.length; i++) {
        const file = fileList[i];
        state.files.push(file);
    }
    
    renderFileList();
}

function renderFileList() {
    // Show action panel
    const panel = qs('.action-panel, .convert-right, #optionsPanel, .workspace-right');
    if (panel) show(panel);
    
    // Enable buttons
    const btns = document.querySelectorAll('button.btn-primary, button#submitBtn, button[onclick^="handleAction"]');
    btns.forEach(btn => {
        btn.disabled = false;
        btn.style.cursor = 'pointer';
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
    });
    
    // Update Drop Zone text
    const p = qs('[class*="upload-zone"] p.drop-text') || qs('[id*="dropZone"] p.drop-text');
    if (p) p.textContent = state.files.length + ' File(s) selected';
    
    // Render file list if container exists
    const listContainer = qs('[class*="file-list"]') || qs('[id*="fileList"]');
    if (listContainer) {
        listContainer.innerHTML = '';
        state.files.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'file-item flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-[1px] transition-all group';
            item.innerHTML = \`
                <div class="flex items-center gap-3 overflow-hidden">
                    <div class="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                        <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                    </div>
                    <span class="font-medium text-slate-700 truncate">\${file.name}</span>
                </div>
                <button onclick="removeFile(\${index}); event.stopPropagation();" class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0" title="Remove file">
                    <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
            \`;
            listContainer.appendChild(item);
        });
    }
}

window.removeFile = function(index) {
    state.files.splice(index, 1);
    renderFileList();
    if (state.files.length === 0) {
        const btns = document.querySelectorAll('button.btn-primary, button#submitBtn, button[onclick^="handleAction"]');
        btns.forEach(btn => btn.disabled = true);
        const p = qs('[class*="upload-zone"] p.drop-text') || qs('[id*="dropZone"] p.drop-text');
        if (p) p.innerHTML = 'Drag & Drop your PDFs here';
    }
};

window.handleAction = async function() {
    var domInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    var domFiles = domInputs.flatMap(function(i) { return Array.from(i.files || []); });
    
    var filesToProcess = [];
    if (window.PDFTools && window.PDFTools.files && window.PDFTools.files.length > 0) {
        filesToProcess = window.PDFTools.files;
    } else if (state.files && state.files.length > 0) {
        filesToProcess = state.files;
    } else if (domFiles.length > 0) {
        filesToProcess = domFiles;
    }

    if (!filesToProcess || filesToProcess.length === 0) {
        alert('Kripya pehle PDF file upload/select karein!');
        return;
    }
    if (state.isProcessing) return;
    
    state.isProcessing = true;

    const mainUI = qs('#mainUI');
    if (mainUI) hide(mainUI);

    const procUI = qs('#processingUI');
    if (procUI) show(procUI);

    const succUI = qs('#successUI');
    if (succUI) hide(succUI);

    try {
        const formData = new FormData();
        formData.append('file', filesToProcess[0]);

        const res = await fetch('/api/organize_pdf_services/organizepdf', {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) throw new Error('API server error (' + res.status + ')');
        const data = await res.json();

        if (data && data.download_url) {
            const dlBtn = qs('#successUI a') || qs('a[download]');
            if (dlBtn) {
                dlBtn.href = data.download_url;
                dlBtn.setAttribute('download', data.filename || 'organized.pdf');
                dlBtn.removeAttribute('onclick');
            }
            if (procUI) hide(procUI);
            if (succUI) show(succUI);
            showSuccess('Done processing!');
        } else {
            throw new Error(data.message || 'Failed to organize PDF');
        }
    } catch (err) {
        showError('Organize PDF Error: ' + err.message);
        if (procUI) hide(procUI);
        if (mainUI) show(mainUI);
    } finally {
        state.isProcessing = false;
    }
};

window.resetApp = function() {
    state.files = [];
    if (window.PDFTools) {
        window.PDFTools.files = [];
        if (typeof window.PDFTools.renderFiles === 'function') window.PDFTools.renderFiles();
        if (typeof window.PDFTools.renderPreview === 'function') window.PDFTools.renderPreview();
    }
    const mainUI = qs('#mainUI');
    const procUI = qs('#processingUI');
    const succUI = qs('#successUI');
    
    if (mainUI) show(mainUI);
    if (procUI) hide(procUI);
    if (succUI) hide(succUI);
    
    renderFileList();
    
    // Reset button state
    const submitBtn = qs('button.btn-primary') || qs('#submitBtn') || qs('button[id$="Btn"]');
    if (submitBtn) {
        submitBtn.classList.remove('opacity-50', 'cursor-not-allowed', 'scale-95');
        submitBtn.disabled = true;
        const textSpan = submitBtn.querySelector('span');
        if (textSpan) textSpan.classList.remove('-translate-x-4', 'opacity-0');
        const svg1 = submitBtn.querySelectorAll('svg')[0];
        if (svg1) {
            svg1.classList.remove('translate-x-[200px]', '-translate-y-[100px]', 'opacity-0', 'scale-150', 'rotate-45');
        }
        const svg2 = submitBtn.querySelectorAll('svg')[1];
        if (svg2) svg2.classList.remove('hidden');
    }
};

function showSuccess(msg) { console.log('[organizepdf] SUCCESS:', msg); }
function showError(msg)   { console.error('[organizepdf] ERROR:', msg); alert(msg); }

document.addEventListener('DOMContentLoaded', () => {
    initUpload();
});
`;
    
    if (!scriptText.trim()) return;

    const scriptEl = document.createElement('script');
    scriptEl.type = 'text/javascript';
    scriptEl.text = scriptText;
    document.body.appendChild(scriptEl);

    if (window.PDFTools) {
      window.PDFTools.files = [];
      window.PDFTools.init();
    }

    document.dispatchEvent(new Event('DOMContentLoaded'));

    return () => {
      if (scriptEl.parentNode) {
        scriptEl.parentNode.removeChild(scriptEl);
      }
    };
  }, []);

  return (
    <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 min-h-screen flex flex-col items-center">
      {/* Background Decorative Gradients */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-32 left-1/2 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>

      <style dangerouslySetInnerHTML={{ __html: `
/* Retaining minimal global styles for specific interactions */
.upload-zone.dragover { 
  border-color: #6366f1 !important; 
  background-color: #eef2ff !important;
  transform: scale(1.01);
}
.preview-empty {
  color: #94a3b8;
  font-weight: 500;
  text-align: center;
}
/* Style for app.js injected preview */
#pdfPreview .preview-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
  align-items: flex-start;
  width: 100%;
}
#pdfPreview .preview-card img {
  max-width: 120px;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  border: 1px solid #e2e8f0;
}
#pdfPreview .preview-page-num {
  text-align: center;
  display: block;
  font-size: 0.75rem;
  color: #64748b;
  margin-top: 4px;
  font-weight: 600;
}
` }} />
      
      <div className="w-full max-w-6xl relative z-10" dangerouslySetInnerHTML={{ __html: `
<div class="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
    <h1 class="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
        Organize PDF
    </h1>
    <p class="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
        Manage and process your documents with the Organize PDF tool.
    </p>
</div>

<div id="mainUI" class="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-10 relative overflow-hidden transition-all duration-500 max-w-4xl mx-auto w-full">
    <!-- Drop Zone -->
    <div class="upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-14 text-center cursor-pointer transition-all duration-300 border-indigo-200 bg-indigo-50/30 hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group" id="dropZone">
        <input type="file" multiple accept=".pdf" hidden>
        <div class="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
            <svg class="w-10 h-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
        </div>
        <p class="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">Drag & Drop your PDFs here</p>
        <p class="text-sm text-slate-500">or <span class="font-semibold text-indigo-600 group-hover:underline">click to browse</span> files</p>
    </div>
    
    <!-- File List Container -->
    <div class="file-list mt-6 space-y-3" id="fileList"></div>

    <!-- Preview Container (Required by app.js) -->
    <div class="preview-section mt-8 rounded-2xl border border-slate-200 bg-slate-50/50 overflow-hidden min-h-[160px] flex flex-col items-center justify-start p-6 shadow-inner" id="pdfPreview">
        <p class="preview-empty my-auto">Upload PDFs to preview</p>
    </div>

    <!-- Action Button -->
    <div class="text-center mt-8">
        <button class="btn btn-primary bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-bold py-4 px-12 rounded-xl shadow-xl shadow-indigo-200 transform transition-all duration-500 flex items-center justify-center gap-2 group relative overflow-hidden mx-auto hover:scale-[1.02] active:scale-[0.98] w-full sm:w-auto cursor-pointer" id="submitBtn" onclick="handleAction()">
            <span class="transition-all duration-500">Execute Action</span>
            <svg class="w-5 h-5 absolute right-1/4 transition-all duration-500 ease-in-out opacity-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
            <svg class="w-5 h-5 transition-transform group-hover:translate-x-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75" />
            </svg>
        </button>
    </div>
</div>

<!-- Processing UI -->
<div id="processingUI" style="display:none;" class="flex flex-col items-center justify-center p-12 bg-white/70 border border-white shadow-2xl rounded-3xl backdrop-blur-xl min-h-[400px] max-w-4xl mx-auto w-full">
    <div class="speeder-loader-wrapper mb-8">
        <div class="loader">
            <span><span></span><span></span><span></span><span></span></span>
            <div class="base"><span></span><div class="face"></div></div>
        </div>
        <div class="longfazers"><span></span><span></span><span></span><span></span></div>
    </div>
    <h3 class="text-xl font-bold text-[#1e2a52] mb-2">Processing your documents...</h3>
    <p class="text-slate-500 text-center text-sm">Please do not close this window</p>
</div>

<!-- Success UI -->
<div id="successUI" style="display:none;" class="p-10 text-center space-y-6 w-full max-w-4xl mx-auto bg-emerald-50 rounded-3xl border border-emerald-100 shadow-2xl relative overflow-hidden min-h-[400px] flex flex-col justify-center items-center">
    <div class="absolute -right-10 -top-10 w-40 h-40 bg-emerald-200 rounded-full mix-blend-multiply filter blur-3xl opacity-50"></div>
    <div class="absolute -left-10 -bottom-10 w-40 h-40 bg-teal-200 rounded-full mix-blend-multiply filter blur-3xl opacity-50"></div>
    
    <div class="flex flex-col items-center justify-center gap-4 relative z-10 w-full max-w-sm">
        <div class="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-2 shadow-sm border border-emerald-200 animate-bounce">
            <svg class="w-10 h-10" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
        </div>
        <h3 class="text-2xl font-extrabold text-emerald-800">Success!</h3>
        <p class="text-emerald-600 font-medium mb-4">Your processed PDF is ready to download.</p>

        <a href="#" download="Organized.pdf" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-emerald-200 transition-all active:scale-95 flex justify-center items-center gap-2 cursor-pointer relative z-10" onclick="alert('Downloading...')">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
            Download Document
        </a>
        
        <button onclick="resetApp()" class="w-full bg-slate-800 hover:bg-slate-900 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-slate-300 transition-all active:scale-95 flex justify-center items-center gap-2 relative z-10 mt-2">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
            Process more files
        </button>
    </div>
</div>

<div class="result" id="result"></div>
` }} />
    </div>
  );
}
