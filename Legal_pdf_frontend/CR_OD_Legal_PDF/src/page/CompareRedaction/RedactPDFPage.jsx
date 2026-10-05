import React, { useState, useRef, useEffect } from 'react';
import { Upload } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function RedactPdfPage() {
    // ── State: Upload ──────────────────────────────────────────────
    const [fileCurrent, setFileCurrent] = useState(null);
    const [dragActive, setDragActive] = useState(false);
    
    // ── State: Workspace & Session ─────────────────────────────────
    const [currentSessionId, setCurrentSessionId] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [currentZoom, setCurrentZoom] = useState(1.0);
    const [currentTool, setCurrentTool] = useState('select'); // 'select' | 'draw'
    const [pageDimensions, setPageDimensions] = useState({});
    
    // ── State: Redaction Candidates ────────────────────────────────
    const [candidates, setCandidates] = useState([]);
    const [selectedFillColor, setSelectedFillColor] = useState('#000000');
    const [overlayLabel, setOverlayLabel] = useState('');
    const [redactionReason, setRedactionReason] = useState('Personal Information');
    
    // ── State: Security Options ────────────────────────────────────
    const [chkCleanMeta, setChkCleanMeta] = useState(true);
    const [chkCleanAnnot, setChkCleanAnnot] = useState(false);
    const [chkCleanEmb, setChkCleanEmb] = useState(true);
    const [chkCleanHidden, setChkCleanHidden] = useState(true);
    
    // ── State: Drawing ─────────────────────────────────────────────
    const [isDrawing, setIsDrawing] = useState(false);
    const [drawStart, setDrawStart] = useState({ x: 0, y: 0 });
    const [tempBox, setTempBox] = useState(null);
    const overlayRef = useRef(null);
    
    // ── State: UI / Process ────────────────────────────────────────
    const [errorMsg, setErrorMsg] = useState(null);
    const [isInitializing, setIsInitializing] = useState(false);
    const [isRedacting, setIsRedacting] = useState(false);
    const [progressText, setProgressText] = useState('');
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [resultData, setResultData] = useState(null);

    // ── Upload Handlers ────────────────────────────────────────────
    const handleFileChange = (e) => {
        if (e.target.files.length) handleFileSelect(e.target.files[0]);
    };
    const handleDrop = (e) => {
        e.preventDefault(); e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files[0]);
    };
    const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(true); };
    const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setDragActive(false); };

    const handleFileSelect = (f) => {
        if (!f.name.toLowerCase().endsWith('.pdf')) { alert('Please select a valid PDF file.'); return; }
        setFileCurrent(f);
        initSession(f);
    };

    // ── API: Initialize ────────────────────────────────────────────
    const initSession = async (f) => {
        setIsInitializing(true);
        setProgressText('Initializing Redaction Workspace...');
        setErrorMsg(null);
        setResultData(null);
        setCurrentSessionId(null);
        
        const fd = new FormData();
        fd.append('file', f);

        try {
            const res = await fetch(`${API_BASE_URL}/api/pdf/redact/initialize`, { method: 'POST', body: fd });
            if (!res.ok) {
                let msg = 'Failed to initialize session';
                try { const d = await res.json(); msg = d.detail || msg; } catch(_) {}
                throw new Error(msg);
            }
            const data = await res.json();
            if (!data.success) throw new Error(data.message || 'Initialization failed');

            setCurrentSessionId(data.session_id);
            setTotalPages(data.page_count || 1);
            setCurrentPage(1);
            setCandidates([]);
            
            const pd = {};
            (data.pages || []).forEach(p => { pd[p.page] = { width: p.width, height: p.height }; });
            setPageDimensions(pd);
            
            setTimeout(() => {
                const ws = document.getElementById('react-workspace');
                if (ws) ws.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        } catch(e) {
            setErrorMsg('Error: ' + e.message);
        } finally {
            setIsInitializing(false);
        }
    };

    // ── API: Automated Tools ───────────────────────────────────────
    const runApiTool = async (endpoint, payloadExt, successCb) => {
        try {
            const res = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: currentSessionId, ...payloadExt }),
            });
            const data = await res.json();
            
            if (!res.ok) {
                alert('Error: ' + (data.detail || data.message || 'Failed to process request'));
                return;
            }
            
            const items = data.candidates || data.matches || [];
            if (data.success && items.length) {
                const toAdd = items.map(c => ({...c, selected: true, id: c.id || `auto_${Date.now()}_${Math.random()}`}));
                setCandidates(prev => [...prev, ...toAdd]);
                successCb(toAdd.length);
            } else {
                alert('No matches found.');
            }
        } catch(e) {
            alert('Error: ' + e.message);
        }
    };

    const openSearchPrompt = () => {
        const query = prompt('Enter exact text or phrase to search and redact:');
        if (!query || !query.trim()) return;
        runApiTool('/api/pdf/redact/search', { query: query.trim() }, (cnt) => alert(`Found and added ${cnt} occurrence(s) for "${query}".`));
    };
    const runPatternDetection = () => runApiTool('/api/pdf/redact/detect-patterns', {}, (cnt) => alert(`Auto-detected ${cnt} sensitive pattern item(s).`));
    const runSensitiveScan = () => runApiTool('/api/pdf/redact/detect-sensitive', {}, (cnt) => alert(`Sensitive Data Scanner found ${cnt} candidate item(s). Please review the list on the right.`));
    
    const openPageRangePrompt = () => {
        const expr = prompt('Enter page numbers/ranges to redact completely (e.g. 1, 3, 5-7):');
        if (!expr) return;
        const parts = expr.split(',');
        const newCands = [];
        parts.forEach(p => {
            if (p.includes('-')) {
                const [s, e] = p.split('-').map(v => parseInt(v.trim(), 10));
                if (!isNaN(s) && !isNaN(e)) {
                    for (let i = Math.min(s, e); i <= Math.max(s, e); i++) {
                        if (i >= 1 && i <= totalPages) newCands.push(createFullPageCand(i));
                    }
                }
            } else {
                const pnum = parseInt(p.trim(), 10);
                if (!isNaN(pnum) && pnum >= 1 && pnum <= totalPages) newCands.push(createFullPageCand(pnum));
            }
        });
        setCandidates(prev => [...prev, ...newCands]);
    };

    const createFullPageCand = (pnum) => {
        const dim = pageDimensions[pnum] || { width: 595, height: 842 };
        return {
            id: `full_page_${pnum}_${Date.now()}_${Math.random()}`,
            page: pnum,
            bbox: [0, 0, dim.width, dim.height],
            text: `Full Page ${pnum}`,
            category: 'MANUAL',
            category_label: 'Full Page',
            selected: true,
        };
    };

    // ── Drawing Events ─────────────────────────────────────────────
    const handleMouseDown = (e) => {
        if (currentTool !== 'draw' || !overlayRef.current) return;
        const rect = overlayRef.current.getBoundingClientRect();
        setIsDrawing(true);
        setDrawStart({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };

    const handleMouseMove = (e) => {
        if (!isDrawing || currentTool !== 'draw' || !overlayRef.current) return;
        const rect = overlayRef.current.getBoundingClientRect();
        const currX = e.clientX - rect.left;
        const currY = e.clientY - rect.top;

        const x0 = Math.min(drawStart.x, currX);
        const y0 = Math.min(drawStart.y, currY);
        const w = Math.abs(currX - drawStart.x);
        const h = Math.abs(currY - drawStart.y);

        setTempBox({ x: x0, y: y0, w, h });
    };

    const handleMouseUp = (e) => {
        if (!isDrawing || currentTool !== 'draw') return;
        setIsDrawing(false);
        if (!tempBox || !overlayRef.current) return;

        const { x, y, w, h } = tempBox;
        setTempBox(null);

        if (w < 8 || h < 8) return; 

        const rect = overlayRef.current.getBoundingClientRect();
        const pageDim = pageDimensions[currentPage] || { width: 595, height: 842 };
        const scaleX = pageDim.width / rect.width;
        const scaleY = pageDim.height / rect.height;

        const pdfBbox = [
            x * scaleX,
            y * scaleY,
            (x + w) * scaleX,
            (y + h) * scaleY,
        ];

        const newCand = {
            id: `manual_${Date.now()}_${Math.random()}`,
            page: currentPage,
            bbox: pdfBbox,
            text: 'Manual Selected Area',
            category: 'MANUAL',
            category_label: 'Manual Area',
            selected: true,
        };

        setCandidates(prev => [...prev, newCand]);
    };

    // ── Actions ────────────────────────────────────────────────────
    const toggleCandidate = (idx) => {
        setCandidates(prev => prev.map((c, i) => i === idx ? { ...c, selected: !c.selected } : c));
    };
    const removeCandidate = (idx) => {
        setCandidates(prev => prev.filter((_, i) => i !== idx));
    };
    const selectAllCandidates = (status) => {
        setCandidates(prev => prev.map(c => ({ ...c, selected: status })));
    };
    const clearAllRedactions = () => {
        if (window.confirm('Clear all redaction targets?')) setCandidates([]);
    };
    const focusCandidate = (c) => {
        if (c && c.page && currentPage !== c.page) setCurrentPage(c.page);
    };
    const formatBytes = (bytes) => (bytes / 1048576).toFixed(2);

    const executeRedaction = async () => {
        setShowConfirmModal(false);
        const selected = candidates.filter(c => c.selected);
        if (!selected.length) return;

        setIsRedacting(true);
        setProgressText('Applying True Permanent Redaction & Wiping Pixels...');
        setErrorMsg(null);

        const payload = {
            session_id: currentSessionId,
            redactions: selected,
            fill_color: selectedFillColor,
            label: overlayLabel.trim(),
            security_options: {
                clean_metadata: chkCleanMeta,
                clean_annotations: chkCleanAnnot,
                clean_embedded_files: chkCleanEmb,
                clean_hidden_content: chkCleanHidden,
            }
        };

        try {
            const res = await fetch(`${API_BASE_URL}/api/pdf/redact/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!res.ok) {
                let msg = 'Redaction failed';
                try { const d = await res.json(); msg = d.detail || msg; } catch(_) {}
                throw new Error(msg);
            }
            const data = await res.json();
            if (!data.success) throw new Error(data.message || 'Redaction failed');

            setResultData(data);
            setCurrentSessionId(null); // Close workspace
            
            setTimeout(() => {
                const resCard = document.getElementById('react-res-card');
                if (resCard) resCard.scrollIntoView({ behavior: 'smooth' });
            }, 100);
        } catch(e) {
            setErrorMsg('Redaction Error: ' + e.message);
        } finally {
            setIsRedacting(false);
        }
    };

    return (
        <div className="react-wrapper-redact_pdf">
            <style dangerouslySetInnerHTML={{ __html: `
                .wrap { max-width: 1200px; margin: 0 auto; padding: 0 1rem; }
                
                /* Upload Zone */
                /* Removed old uzone styles as we are using tailwind now */

                /* Progress & Error */
                .prog { text-align: center; padding: 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 16px; }
                .spinner { display: inline-block; width: 28px; height: 28px; border: 3px solid rgba(37,99,235,.2); border-radius: 50%; border-top-color: #2563eb; animation: spin 1s linear infinite; margin-bottom: 6px; }
                @keyframes spin { to { transform: rotate(360deg); } }
                
                /* Speeder Loader Overrides for Smoother Animation */
                .speeder-loader-wrapper .loader { animation-duration: 1.2s; animation-timing-function: ease-in-out; }
                .speeder-loader-wrapper .loader > span > span:nth-child(1) { animation-duration: 0.6s; }
                .speeder-loader-wrapper .loader > span > span:nth-child(2) { animation-duration: 1.2s; }
                .speeder-loader-wrapper .loader > span > span:nth-child(3) { animation-duration: 1.2s; }
                .speeder-loader-wrapper .loader > span > span:nth-child(4) { animation-duration: 2.5s; }
                .speeder-loader-wrapper .longfazers span:nth-child(1) { animation-duration: 1.2s; }
                .speeder-loader-wrapper .longfazers span:nth-child(2) { animation-duration: 1.6s; }
                .speeder-loader-wrapper .longfazers span:nth-child(3) { animation-duration: 1.2s; }
                .speeder-loader-wrapper .longfazers span:nth-child(4) { animation-duration: 1.0s; }

                /* Toolbar */
                .toolbar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; background: #1e293b; color: #fff; padding: 10px 16px; border-radius: 10px 10px 0 0; }
                .tool-group { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
                .tbtn { padding: 6px 12px; font-size: .8rem; font-weight: 700; border: 1px solid #475569; border-radius: 6px; background: #334155; color: #f8fafc; cursor: pointer; transition: all .15s; display: inline-flex; align-items: center; gap: 4px; }
                .tbtn:hover { background: #475569; border-color: #94a3b8; }
                .tbtn.active { background: #2563eb; border-color: #3b82f6; color: #fff; }
                .tbtn.danger { background: #dc2626; border-color: #ef4444; }
                .tbtn.danger:hover { background: #b91c1c; }

                /* Workspace Main Grid */
                .ws-grid { display: grid; grid-template-columns: 1fr 380px; gap: 16px; background: #f1f5f9; padding: 16px; border: 1px solid #cbd5e1; border-top: none; border-radius: 0 0 10px 10px; }
                @media (max-width: 960px) { .ws-grid { grid-template-columns: 1fr; } }

                /* Viewer Box & Canvas Overlay */
                .viewer-box { text-align: center; background: #cbd5e1; border: 1px solid #94a3b8; border-radius: 8px; padding: 16px; overflow: auto; max-height: 700px; position: relative; user-select: none; }
                .canvas-container { display: inline-block; position: relative; box-shadow: 0 4px 16px rgba(0,0,0,0.15); border-radius: 4px; background: #fff; transition: transform 0.2s ease-in-out; transform-origin: top center; }
                .canvas-container img { display: block; max-width: 100%; height: auto; border-radius: 4px; }
                .overlay-layer { position: absolute; top: 0; left: 0; width: 100%; height: 100%; cursor: crosshair; }
                .redact-box { position: absolute; border: 2px solid #ef4444; background: rgba(239, 68, 68, 0.35); border-radius: 2px; box-sizing: border-box; }
                .redact-box.active { border: 2px solid #2563eb; background: rgba(37, 99, 235, 0.4); z-index: 10; }
                .redact-box .del-btn { position: absolute; top: -10px; right: -10px; width: 18px; height: 18px; background: #dc2626; color: #fff; border-radius: 50%; font-size: 11px; font-weight: bold; line-height: 18px; text-align: center; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.3); }

                /* Right Control Panel */
                .cpanel { display: flex; flex-direction: column; gap: 14px; }
                .cbox { background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; }
                .ctitle { font-size: .88rem; font-weight: 800; color: #0f172a; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }

                /* Candidate List */
                .cand-list { max-height: 220px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px; }
                .citem { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 6px 8px; border-bottom: 1px solid #f1f5f9; font-size: .8rem; cursor: pointer; border-radius: 4px; }
                .citem:hover { background: #f8fafc; }
                .citem.active { background: #eff6ff; border-left: 3px solid #2563eb; }
                .ctag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: .68rem; text-transform: uppercase; }
                .ctag.EMAIL { background: #dbeafe; color: #1e40af; }
                .ctag.PHONE { background: #dcfce7; color: #15803d; }
                .ctag.AADHAAR { background: #fef9c3; color: #a16207; }
                .ctag.PAN { background: #ffedd5; color: #c2410c; }
                .ctag.PERSON { background: #fae8ff; color: #86198f; }
                .ctag.MANUAL { background: #fee2e2; color: #b91c1c; }
                .ctag.SEARCH_MATCH { background: #e0e7ff; color: #4338ca; }

                /* Appearance Form */
                .form-row { margin-bottom: 10px; }
                .form-row label { display: block; font-size: .8rem; font-weight: 700; color: #334155; margin-bottom: 4px; }
                .form-row select, .form-row input[type="text"] { width: 100%; padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: .82rem; box-sizing: border-box; }
                .color-picker-grid { display: flex; gap: 8px; }
                .color-dot { width: 26px; height: 26px; border-radius: 50%; cursor: pointer; border: 2px solid #cbd5e1; transition: transform .15s; }
                .color-dot:hover { transform: scale(1.1); }
                .color-dot.active { border-color: #2563eb; transform: scale(1.15); box-shadow: 0 0 0 2px rgba(37,99,235,0.3); }

                /* Apply Button */
                .btn-apply { width: 100%; padding: 12px 18px; font-size: 1.05rem; font-weight: 800; background: #dc2626; color: #fff; border: none; border-radius: 8px; cursor: pointer; transition: background .15s; display: flex; align-items: center; justify-content: center; gap: 8px; }
                .btn-apply:hover { background: #b91c1c; }
                .btn-apply:disabled { background: #94a3b8; cursor: not-allowed; }

                /* Modal */
                .modal-backdrop { display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15,23,42,0.6); z-index: 100; align-items: center; justify-content: center; }
                .modal-card { background: #fff; border-radius: 12px; width: 90%; max-width: 480px; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); text-align: center; }
                .modal-card h3 { font-size: 1.25rem; font-weight: 800; color: #991b1b; margin-top: 0; margin-bottom: 8px; }
                .modal-card p { font-size: .88rem; color: #475569; margin-bottom: 20px; line-height: 1.4; }
                .modal-btns { display: flex; gap: 10px; justify-content: center; }
                .mbtn { padding: 9px 18px; font-size: .9rem; font-weight: 700; border-radius: 6px; cursor: pointer; border: none; }
                .mbtn.cancel { background: #e2e8f0; color: #334155; }
                .mbtn.cancel:hover { background: #cbd5e1; }
                .mbtn.confirm { background: #dc2626; color: #fff; }
                .mbtn.confirm:hover { background: #b91c1c; }

                /* Result Card */
                .res-card { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 16px; text-align: center; margin-top: 16px; }
            `}} />

            <div className="wrap">
                <div className="w-full max-w-3xl mx-auto px-4 sm:px-6 pb-6">
                    <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
                        <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
                            Secure PDF Redaction
                        </h1>
                        <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
                            Permanently wipe sensitive information, PII, and financial data from your PDF documents with irreversible redaction.
                        </p>
                    </div>
                    <div className="bg-white rounded-3xl border border-slate-200/80 shadow-[0_8px_30px_rgba(0,0,0,0.04)] p-6 sm:p-10 mb-6">
                        {/* File Upload Area */}
                        <input type="file" id="pdfFileInput" accept=".pdf,application/pdf" className="hidden" onChange={handleFileChange} />
                        <label 
                            htmlFor="pdfFileInput" 
                            className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all block ${dragActive ? 'border-[#1e2a52] bg-[#e8f0e2]' : 'border-[#1e2a52]/30 bg-[#f8faf7] hover:border-[#1e2a52] hover:bg-[#eff4ea]'}`}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onDrop={handleDrop}
                        >
                            <div className="w-16 h-16 bg-[#1e2a52]/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                <Upload className="w-8 h-8 text-[#1e2a52]" />
                            </div>
                            <p className="text-base sm:text-lg font-bold text-[#1e2a52] mb-1">
                                Drop file here or click to browse
                            </p>
                            <p className="text-xs sm:text-sm text-slate-500 mb-2">
                                Accepted: <span className="font-semibold text-[#1e2a52]">PDF files (.pdf)</span>
                            </p>
                            {fileCurrent && <div className="text-sm font-bold text-[#16a34a] break-all">{fileCurrent.name} ({formatBytes(fileCurrent.size)} MB)</div>}
                        </label>
                    </div>
                </div>

                <div className="card">

                    {/* Progress Box */}
                    {(isInitializing || isRedacting) && (
                        <div className="flex flex-col items-center justify-center p-6 bg-[#f8faf7] border border-slate-200/80 rounded-2xl overflow-hidden relative min-h-[160px] mt-4 mb-4">
                            <div className="speeder-loader-wrapper">
                                <div className="loader">
                                    <span>
                                        <span></span><span></span><span></span><span></span>
                                    </span>
                                    <div className="base">
                                        <span></span>
                                        <div className="face"></div>
                                    </div>
                                </div>
                                <div className="longfazers">
                                    <span></span><span></span><span></span><span></span>
                                </div>
                            </div>
                            <p className="text-sm font-bold text-[#1e2a52] mt-4 animate-pulse">
                                {progressText || 'Processing... Please wait!'}
                            </p>
                            {isRedacting && (
                                <p className="text-xs text-slate-500 mt-1 text-center max-w-sm">Applying permanent redaction and sanitizing document.</p>
                            )}
                        </div>
                    )}

                    {/* Error Box */}
                    {errorMsg && (
                        <div style={{background:'#fef2f2', border:'1px solid #fecaca', color:'#b91c1c', padding:'12px', borderRadius:'8px', marginTop:'16px', textAlign:'center', fontWeight:700}}>
                            {errorMsg}
                        </div>
                    )}

                    {/* Result Card */}
                    {resultData && (
                        <div className="res-card" id="react-res-card">
                            <h2 style={{margin:'0 0 8px 0', fontSize:'1.3rem', color:'#15803d'}}>✅ Permanent Redaction Complete</h2>
                            <p style={{margin:'0 0 12px 0', color:'#334155', fontSize:'.9rem'}}>Successfully applied {resultData.total_redactions} true permanent redaction(s) across {resultData.pages_processed} page(s).</p>
                            
                            <div style={{display:'inline-block', background: resultData.verification?.verification_passed ? '#dcfce7' : '#fef2f2', border: `1px solid ${resultData.verification?.verification_passed ? '#86efac' : '#fecaca'}`, color: resultData.verification?.verification_passed ? '#166534' : '#991b1b', padding:'8px 16px', borderRadius:'20px', fontSize:'.85rem', fontWeight:800, marginBottom:'16px'}}>
                                {resultData.verification?.verification_passed 
                                    ? '🔍 Post-Redaction Empirical Verification: PASSED (0 Extractable Matches Found)'
                                    : `⚠️ Verification Alert: ${resultData.verification?.message}`}
                            </div>
                            <div>
                                <a href={`${API_BASE_URL}${resultData.download_url}`} className="btn-apply" style={{display:'inline-flex', width:'auto', padding:'10px 24px', textDecoration:'none', background:'#16a34a'}}>
                                    ⬇️ Download Redacted PDF
                                </a>
                            </div>
                        </div>
                    )}

                    {/* Workspace Section */}
                    {currentSessionId && (
                        <div className="workspace show" id="react-workspace" style={{marginTop: '16px'}}>
                            {/* Toolbar */}
                            <div className="toolbar">
                                <div className="tool-group">
                                    <button className={`tbtn ${currentTool === 'select' ? 'active' : ''}`} onClick={() => setCurrentTool('select')}>👆 Select</button>
                                    <button className={`tbtn ${currentTool === 'draw' ? 'active' : ''}`} onClick={() => setCurrentTool('draw')}>📦 Redact Area</button>
                                    <button className="tbtn" onClick={openSearchPrompt}>🔍 Search Text</button>
                                    <button className="tbtn" onClick={runPatternDetection}>⚡ Auto Regex Patterns</button>
                                    <button className="tbtn" onClick={runSensitiveScan}>🤖 Auto Sensitive Scan</button>
                                    <button className="tbtn" onClick={openPageRangePrompt}>📄 Redact Page Range</button>
                                    <button className="tbtn danger" onClick={clearAllRedactions}>🧹 Clear All</button>
                                </div>
                                <div className="tool-group">
                                    <button className="tbtn" onClick={() => setCurrentZoom(z => Math.max(0.5, z - 0.2))}>🔍 -</button>
                                    <button className="tbtn" onClick={() => setCurrentZoom(z => Math.min(2.5, z + 0.2))}>🔍 +</button>
                                    <button className="tbtn" onClick={() => setCurrentZoom(1.0)}>🔄 Reset</button>
                                    <button className="tbtn" onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>&larr; Prev</button>
                                    <span style={{fontSize:'.82rem', fontWeight:800}}>Page {currentPage} / {totalPages}</span>
                                    <button className="tbtn" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}>Next &rarr;</button>
                                </div>
                            </div>

                            {/* Workspace Main Grid */}
                            <div className="ws-grid">
                                {/* Viewer Box */}
                                <div className="viewer-box">
                                    <div className="canvas-container" style={{transform: `scale(${currentZoom})`}}>
                                        <img src={`${API_BASE_URL}/api/pdf/redact/render-page/${currentSessionId}/${currentPage}?dpi=150`} alt="PDF Page" style={{pointerEvents: 'none'}} />
                                        <div 
                                            className="overlay-layer" 
                                            ref={overlayRef}
                                            onMouseDown={handleMouseDown}
                                            onMouseMove={handleMouseMove}
                                            onMouseUp={handleMouseUp}
                                            onMouseLeave={handleMouseUp}
                                        >
                                            {/* Render temporary drawing box */}
                                            {tempBox && (
                                                <div className="redact-box active" style={{ left: tempBox.x, top: tempBox.y, width: tempBox.w, height: tempBox.h }} />
                                            )}
                                            
                                            {/* Render existing redaction boxes for current page */}
                                            {candidates.filter(c => c.page === currentPage && c.selected).map(cand => {
                                                const dim = pageDimensions[currentPage] || { width: 595, height: 842 };
                                                const [x0, y0, x1, y1] = cand.bbox;
                                                const left = (x0 / dim.width) * 100;
                                                const top = (y0 / dim.height) * 100;
                                                const width = ((x1 - x0) / dim.width) * 100;
                                                const height = ((y1 - y0) / dim.height) * 100;
                                                
                                                return (
                                                    <div key={cand.id} className="redact-box" style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}>
                                                        <div className="del-btn" onClick={(e) => { e.stopPropagation(); removeCandidate(candidates.findIndex(c => c.id === cand.id)); }}>×</div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>

                                {/* Right Control Panel */}
                                <div className="cpanel">
                                    {/* Candidates List */}
                                    <div className="cbox">
                                        <div className="ctitle">
                                            <span>Redaction Regions ({candidates.length})</span>
                                            <div>
                                                <button className="tbtn" style={{padding:'2px 6px', fontSize:'0.7rem', marginRight: '4px'}} onClick={() => selectAllCandidates(true)}>Select All</button>
                                                <button className="tbtn" style={{padding:'2px 6px', fontSize:'0.7rem'}} onClick={() => selectAllCandidates(false)}>Deselect</button>
                                            </div>
                                        </div>
                                        <div className="cand-list">
                                            {candidates.length === 0 ? (
                                                <div style={{textAlign:'center', padding:'16px', color:'#64748b', fontSize:'.8rem'}}>No redactions added yet. Use "Redact Area", "Search Text", or "Auto Regex" above.</div>
                                            ) : (
                                                candidates.map((c, idx) => (
                                                    <div key={c.id} className={`citem ${c.page === currentPage ? 'active' : ''}`} onClick={() => focusCandidate(c)}>
                                                        <div style={{display:'flex', alignItems:'center', gap:'6px', overflow:'hidden'}}>
                                                            <input type="checkbox" checked={c.selected} onChange={() => {}} onClick={(e) => { e.stopPropagation(); toggleCandidate(idx); }} />
                                                            <span className={`ctag ${c.category}`}>{c.category_label || c.category}</span>
                                                            <span style={{fontWeight:700, color:'#1e293b'}}>P.{c.page}:</span>
                                                            <span style={{textOverflow:'ellipsis', overflow:'hidden', whiteSpace:'nowrap', maxWidth:'140px'}} title={c.text}>{c.text}</span>
                                                        </div>
                                                        <span style={{color:'#ef4444', fontWeight:'bold', cursor:'pointer'}} onClick={(e) => { e.stopPropagation(); removeCandidate(idx); }}>&times;</span>
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </div>

                                    {/* Redaction Appearance & Label */}
                                    <div className="cbox">
                                        <div className="ctitle">Redaction Appearance</div>
                                        
                                        <div className="form-row">
                                            <label>Fill Color:</label>
                                            <div className="color-picker-grid">
                                                {['#000000', '#ffffff', '#ef4444', '#3b82f6', '#64748b'].map(color => (
                                                    <div 
                                                        key={color} 
                                                        className={`color-dot ${selectedFillColor === color ? 'active' : ''}`} 
                                                        style={{background: color}} 
                                                        onClick={() => setSelectedFillColor(color)}
                                                    />
                                                ))}
                                            </div>
                                        </div>

                                        <div className="form-row">
                                            <label htmlFor="optOverlayLabel">Overlay Label Text (Optional):</label>
                                            <input type="text" id="optOverlayLabel" value={overlayLabel} onChange={e => setOverlayLabel(e.target.value)} placeholder="e.g. REDACTED or CONFIDENTIAL" />
                                        </div>

                                        <div className="form-row">
                                            <label htmlFor="optReason">Redaction Reason:</label>
                                            <select id="optReason" value={redactionReason} onChange={e => setRedactionReason(e.target.value)}>
                                                <option value="Personal Information">Personal Information (PII)</option>
                                                <option value="Financial Information">Financial Data</option>
                                                <option value="Confidential Information">Business Confidential</option>
                                                <option value="Legal Privilege">Legal Privilege</option>
                                                <option value="Security Information">Security / Credentials</option>
                                                <option value="Other">Other</option>
                                            </select>
                                        </div>
                                    </div>

                                    {/* Security Sanitization Controls */}
                                    <div className="cbox">
                                        <div className="ctitle">Security Sanitization Options</div>
                                        <div style={{display:'flex', flexDirection:'column', gap:'6px', fontSize:'.8rem', color:'#334155'}}>
                                            <label style={{display:'flex', alignItems:'center', gap:'6px'}}><input type="checkbox" checked={chkCleanMeta} onChange={e => setChkCleanMeta(e.target.checked)} /> Wipe Document Metadata (Author, Title, Dates)</label>
                                            <label style={{display:'flex', alignItems:'center', gap:'6px'}}><input type="checkbox" checked={chkCleanAnnot} onChange={e => setChkCleanAnnot(e.target.checked)} /> Remove All Annotations &amp; Comments</label>
                                            <label style={{display:'flex', alignItems:'center', gap:'6px'}}><input type="checkbox" checked={chkCleanEmb} onChange={e => setChkCleanEmb(e.target.checked)} /> Remove Embedded Files &amp; Attachments</label>
                                            <label style={{display:'flex', alignItems:'center', gap:'6px'}}><input type="checkbox" checked={chkCleanHidden} onChange={e => setChkCleanHidden(e.target.checked)} /> Cleanup Hidden Content &amp; Layers</label>
                                        </div>
                                    </div>

                                    {/* Apply Redactions Button */}
                                    <button className="btn-apply" disabled={candidates.filter(c => c.selected).length === 0} onClick={() => setShowConfirmModal(true)}>
                                        🔒 Apply Permanent Redactions
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="modal-backdrop">
                    <div className="modal-card">
                        <h3>⚠️ Permanent Redaction Warning</h3>
                        <p>You are about to apply <strong>true permanent redaction</strong>. The selected sensitive text, image regions, and underlying document streams will be permanently wiped from the PDF file. <strong>This action cannot be undone.</strong></p>
                        <div className="modal-btns">
                            <button className="mbtn cancel" onClick={() => setShowConfirmModal(false)}>Cancel</button>
                            <button className="mbtn confirm" onClick={executeRedaction}>Apply Permanent Redactions</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
