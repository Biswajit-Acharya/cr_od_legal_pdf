import React, { useState, useRef, useCallback, useEffect } from 'react';

// Component to render individual PDF page thumbnails
const PdfThumbnail = ({ pdfDoc, pageNum, isSelected, onToggle }) => {
    const canvasRef = useRef(null);
    useEffect(() => {
        let renderTask = null;
        if (pdfDoc && canvasRef.current) {
            pdfDoc.getPage(pageNum).then(page => {
                const viewport = page.getViewport({ scale: 0.5 }); // Lower scale for thumbnails
                const canvas = canvasRef.current;
                if (!canvas) return;
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                const ctx = canvas.getContext('2d');
                renderTask = page.render({ canvasContext: ctx, viewport });
            }).catch(e => console.error("Page render error", e));
        }
        return () => {
            if (renderTask) renderTask.cancel();
        };
    }, [pdfDoc, pageNum]);

    return (
        <div 
            onClick={() => onToggle(pageNum)}
            className={`cursor-pointer border-4 rounded-xl p-2 transition-all ${isSelected ? 'border-indigo-600 bg-indigo-50 scale-[1.02] shadow-md' : 'border-transparent bg-white hover:border-indigo-200 shadow-sm hover:shadow-md'}`}
        >
            <canvas ref={canvasRef} className="w-full h-auto border border-slate-200 rounded shadow-sm bg-white" />
            <div className={`text-center mt-2 font-bold text-sm ${isSelected ? 'text-indigo-700' : 'text-slate-600'}`}>Page {pageNum}</div>
            {isSelected && (
                <div className="absolute top-2 right-2 bg-indigo-600 text-white rounded-full p-1 shadow-md">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                    </svg>
                </div>
            )}
        </div>
    );
};

export default function SplitPDFPage() {
    const [files, setFiles] = useState([]);
    
    // Split Modes
    const [splitMode, setSplitMode] = useState('extract'); // 'extract' or 'split_every'
    const [splitEvery, setSplitEvery] = useState(1);
    
    // Preview States
    const [pdfDoc, setPdfDoc] = useState(null);
    const [totalPages, setTotalPages] = useState(0);
    const [selectedPages, setSelectedPages] = useState([]);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);

    // Process States
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [errorMsg, setErrorMsg] = useState(null);
    const [downloadUrl, setDownloadUrl] = useState(null);
    const [isDragOver, setIsDragOver] = useState(false);

    const fileInputRef = useRef(null);

    const handleFiles = (newFiles) => {
        const fileArray = Array.from(newFiles).filter(file => file.type === 'application/pdf');
        if (fileArray.length > 0) {
            // We only support one file at a time for splitting with preview
            setFiles([fileArray[0]]);
        }
    };

    // Load PDF Document when a file is selected
    useEffect(() => {
        if (files.length > 0 && window.pdfjsLib) {
            setIsLoadingPreview(true);
            const file = files[0];
            file.arrayBuffer().then(buf => window.pdfjsLib.getDocument({ data: buf }).promise)
            .then(pdf => {
                setPdfDoc(pdf);
                setTotalPages(pdf.numPages);
                setSelectedPages([]); // Reset selection
                setIsLoadingPreview(false);
            }).catch(err => {
                console.error("PDF load error", err);
                setErrorMsg("Failed to load PDF preview. Make sure it's a valid PDF.");
                setIsLoadingPreview(false);
            });
        } else {
            setPdfDoc(null);
            setTotalPages(0);
        }
    }, [files]);

    const togglePage = (pageNum) => {
        if (splitMode !== 'extract') {
            setSplitMode('extract');
        }
        setSelectedPages(prev => {
            if (prev.includes(pageNum)) {
                return prev.filter(p => p !== pageNum);
            } else {
                return [...prev, pageNum].sort((a, b) => a - b);
            }
        });
    };

    const onDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragOver(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    }, []);

    const onDragOver = useCallback((e) => {
        e.preventDefault();
        setIsDragOver(true);
    }, []);

    const onDragLeave = useCallback((e) => {
        e.preventDefault();
        setIsDragOver(false);
    }, []);

    const removeFile = () => {
        setFiles([]);
    };

    const handleSplit = async () => {
        if (files.length === 0) {
            setErrorMsg("Please select a PDF file.");
            return;
        }

        if (splitMode === 'extract' && selectedPages.length === 0) {
            setErrorMsg("Please select at least one page to extract.");
            return;
        }

        setIsProcessing(true);
        setErrorMsg(null);

        const formData = new FormData();
        formData.append('file', files[0]);

        try {
            const API_BASE_URL = import.meta.env.VITE_API_URL || '';
            let endpoint = '';
            
            if (splitMode === 'extract') {
                const pagesStr = selectedPages.join(',');
                endpoint = `${API_BASE_URL}/api/pdf/extract?pages=${encodeURIComponent(pagesStr)}`;
            } else {
                endpoint = `${API_BASE_URL}/api/pdf/split?split_every=${splitEvery}`;
            }

            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
            });
            
            if (!response.ok) {
                let errMsg = `Error: ${response.status}`;
                try { const e = await response.json(); errMsg = e.detail || errMsg; } catch(_){}
                throw new Error(errMsg);
            }
            
            const data = await response.json();
            if (data.download_url) {
                const fileRes = await fetch(`${API_BASE_URL}${data.download_url}`);
                if (!fileRes.ok) throw new Error('Failed to download result');
                const blob = await fileRes.blob();
                const url = window.URL.createObjectURL(blob);
                setDownloadUrl(url);
                setIsSuccess(true);
            } else {
                throw new Error("No download URL returned.");
            }
        } catch (error) {
            setErrorMsg(error.message || "An error occurred during processing.");
        } finally {
            setIsProcessing(false);
        }
    };

    const resetApp = () => {
        setFiles([]);
        setIsProcessing(false);
        setIsSuccess(false);
        setErrorMsg(null);
        if (downloadUrl) {
            window.URL.revokeObjectURL(downloadUrl);
            setDownloadUrl(null);
        }
    };

    return (
        <div className="min-h-screen p-4 sm:p-8 bg-transparent relative z-20 flex flex-col items-center">
            {/* Background Decorative Gradients */}
            <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
            <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
            <div className="absolute -bottom-32 left-1/2 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>
            
            <div className="w-full max-w-6xl relative z-10">
                <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
                    <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
                        Split & Extract PDF
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
                        Visually select pages to extract into a new PDF, or split the document by page count.
                    </p>
                </div>

                {!isProcessing && !isSuccess && (
                    <div id="mainUI" className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-10 relative overflow-hidden transition-all duration-500 max-w-5xl mx-auto w-full">
                        {errorMsg && (
                            <div className="mb-4 p-4 text-red-700 bg-red-100 rounded-lg font-medium shadow-sm border border-red-200">
                                {errorMsg}
                            </div>
                        )}

                        {files.length === 0 ? (
                            <div 
                                className={`upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-14 text-center cursor-pointer transition-all duration-300 ${isDragOver ? 'border-indigo-500 bg-indigo-100 scale-[1.01]' : 'border-indigo-200 bg-indigo-50/30'} hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group`}
                                onDrop={onDrop}
                                onDragOver={onDragOver}
                                onDragLeave={onDragLeave}
                                onClick={() => fileInputRef.current.click()}
                            >
                                <input 
                                    type="file" 
                                    accept=".pdf" 
                                    className="hidden" 
                                    ref={fileInputRef}
                                    onChange={(e) => {
                                        if(e.target.files.length) handleFiles(e.target.files);
                                    }}
                                />
                                <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                                    <svg className="w-10 h-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"/>
                                    </svg>
                                </div>
                                <p className="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                                    Drag & Drop your PDF here
                                </p>
                                <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse</span> files</p>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-6">
                                {/* Top Controls */}
                                <div className="flex flex-col md:flex-row items-center justify-between gap-4 bg-white/80 p-4 rounded-xl border border-slate-200 shadow-sm">
                                    <div className="flex items-center gap-3 w-full md:w-auto">
                                        <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                                            <svg className="w-6 h-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                                        </div>
                                        <div className="overflow-hidden">
                                            <div className="font-bold text-slate-800 truncate">{files[0].name}</div>
                                            <div className="text-sm text-slate-500 font-medium">{totalPages} Pages Total</div>
                                        </div>
                                    </div>
                                    <button onClick={removeFile} className="w-full md:w-auto px-4 py-2 text-sm font-bold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors border border-red-100">
                                        Change File
                                    </button>
                                </div>

                                {/* Main Workspace: 2 columns */}
                                <div className="flex flex-col lg:flex-row gap-6">
                                    {/* Left: Preview Grid */}
                                    <div className="w-full lg:w-2/3 bg-slate-50/50 rounded-2xl border border-slate-200 p-4 h-[500px] overflow-y-auto">
                                        <h3 className="font-bold text-slate-700 mb-4 sticky top-0 bg-slate-50/90 backdrop-blur pb-2 z-10 border-b border-slate-200">
                                            Select pages to extract ({selectedPages.length} selected)
                                        </h3>
                                        
                                        {isLoadingPreview ? (
                                            <div className="flex flex-col items-center justify-center h-40">
                                                <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                                                <div className="text-slate-500 font-medium">Generating preview...</div>
                                            </div>
                                        ) : (
                                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                                                {Array.from({ length: totalPages }).map((_, i) => (
                                                    <div key={i} className="relative">
                                                        <PdfThumbnail 
                                                            pdfDoc={pdfDoc} 
                                                            pageNum={i + 1} 
                                                            isSelected={selectedPages.includes(i + 1)} 
                                                            onToggle={togglePage} 
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    {/* Right: Options */}
                                    <div className="w-full lg:w-1/3 flex flex-col gap-4">
                                        <div 
                                            onClick={() => setSplitMode('extract')}
                                            className={`p-5 rounded-2xl border-2 transition-all cursor-pointer ${splitMode === 'extract' ? 'border-indigo-600 bg-indigo-50 shadow-md' : 'border-slate-200 bg-white hover:border-indigo-300'}`}
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <h3 className="font-bold text-indigo-900 text-lg">Extract Pages</h3>
                                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${splitMode === 'extract' ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300'}`}>
                                                    {splitMode === 'extract' && <div className="w-2 h-2 bg-white rounded-full"></div>}
                                                </div>
                                            </div>
                                            <p className="text-sm text-slate-600 mb-3">Click on the pages you want to keep. They will be merged into one new PDF.</p>
                                            {selectedPages.length > 0 && (
                                                <div className="text-xs font-bold text-indigo-700 bg-indigo-100 p-2 rounded">
                                                    Selected: {selectedPages.join(', ')}
                                                </div>
                                            )}
                                        </div>

                                        <div 
                                            onClick={() => setSplitMode('split_every')}
                                            className={`p-5 rounded-2xl border-2 transition-all cursor-pointer ${splitMode === 'split_every' ? 'border-indigo-600 bg-indigo-50 shadow-md' : 'border-slate-200 bg-white hover:border-indigo-300'}`}
                                        >
                                            <div className="flex items-center justify-between mb-2">
                                                <h3 className="font-bold text-indigo-900 text-lg">Split into Chunks</h3>
                                                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${splitMode === 'split_every' ? 'border-indigo-600 bg-indigo-600' : 'border-slate-300'}`}>
                                                    {splitMode === 'split_every' && <div className="w-2 h-2 bg-white rounded-full"></div>}
                                                </div>
                                            </div>
                                            <p className="text-sm text-slate-600 mb-3">Split the entire document into multiple files evenly.</p>
                                            
                                            {splitMode === 'split_every' && (
                                                <div className="mt-2" onClick={e => e.stopPropagation()}>
                                                    <label className="block text-xs font-bold text-slate-700 mb-1">Pages per chunk</label>
                                                    <input 
                                                        type="number" 
                                                        min="1" 
                                                        value={splitEvery} 
                                                        onChange={(e) => setSplitEvery(e.target.value)}
                                                        className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:border-indigo-500 font-medium" 
                                                    />
                                                </div>
                                            )}
                                        </div>

                                        <button 
                                            onClick={handleSplit} 
                                            disabled={isProcessing || (splitMode === 'extract' && selectedPages.length === 0)}
                                            className="mt-auto btn btn-primary bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-bold py-4 px-6 rounded-xl shadow-xl shadow-indigo-200 transform transition-all duration-300 flex items-center justify-center gap-2 group relative overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] w-full"
                                        >
                                            <span>{splitMode === 'extract' ? 'Extract Selected' : 'Split Document'}</span>
                                            <svg className="w-5 h-5 transition-transform group-hover:translate-x-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75" />
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {isProcessing && (
                    <div id="processingUI" className="flex flex-col items-center justify-center p-12 bg-white/70 border border-white shadow-2xl rounded-3xl backdrop-blur-xl min-h-[400px] max-w-4xl mx-auto w-full mt-6">
                        <div className="speeder-loader-wrapper mb-8">
                            <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                        </div>
                        <h3 className="text-xl font-bold text-[#1e2a52] mb-2">Processing your document...</h3>
                        <p className="text-slate-500 text-center text-sm">This might take a moment.</p>
                    </div>
                )}

                {isSuccess && (
                    <div id="successUI" className="mt-6 p-10 text-center space-y-6 w-full max-w-4xl mx-auto bg-emerald-50 rounded-3xl border border-emerald-100 shadow-2xl relative overflow-hidden min-h-[400px] flex flex-col justify-center items-center">
                        <div className="absolute -right-10 -top-10 w-40 h-40 bg-emerald-200 rounded-full mix-blend-multiply filter blur-3xl opacity-50"></div>
                        <div className="absolute -left-10 -bottom-10 w-40 h-40 bg-teal-200 rounded-full mix-blend-multiply filter blur-3xl opacity-50"></div>
                        
                        <div className="flex flex-col items-center justify-center gap-4 relative z-10 w-full max-w-sm">
                            <div className="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-2 shadow-sm border border-emerald-200 animate-bounce">
                                <svg className="w-10 h-10" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                            </div>
                            <h3 className="text-2xl font-extrabold text-emerald-800">Success!</h3>
                            <p className="text-emerald-600 font-medium mb-4">Your document is ready to download.</p>

                            <a href={downloadUrl} download={splitMode === 'extract' ? 'Extracted_Pages.pdf' : 'Split_Documents.zip'} className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-emerald-200 transition-all active:scale-95 flex justify-center items-center gap-2 cursor-pointer relative z-10">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                Download Result
                            </a>
                            
                            <button onClick={resetApp} className="w-full bg-slate-800 hover:bg-slate-900 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-slate-300 transition-all active:scale-95 flex justify-center items-center gap-2 relative z-10 mt-2">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                                Process another file
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
