import React, { useState, useRef, useCallback } from 'react';
import { uploadFiles, getFullUrl } from '../../api/apiClient';

export default function MergePDFPage() {
    const [files, setFiles] = useState([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [errorMsg, setErrorMsg] = useState(null);
    const [downloadUrl, setDownloadUrl] = useState(null);
    const [isDragOver, setIsDragOver] = useState(false);

    const fileInputRef = useRef(null);

    const handleFiles = (newFiles) => {
        const fileArray = Array.from(newFiles).filter(file => file.type === 'application/pdf');
        if (fileArray.length > 0) {
            setFiles(prev => [...prev, ...fileArray]);
        }
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

    const removeFile = (indexToRemove) => {
        setFiles(prev => prev.filter((_, idx) => idx !== indexToRemove));
    };

    const handleMerge = async () => {
        if (files.length < 2) {
            setErrorMsg("Please select at least 2 PDF files to merge.");
            return;
        }

        setIsProcessing(true);
        setErrorMsg(null);

        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file); // API expects 'files' list
        });

        try {
            const data = await uploadFiles('/api/pdf/merge', formData, false);
            if (data && data.download_url) {
                const fullDownloadUrl = getFullUrl(data.download_url);
                const fileRes = await fetch(fullDownloadUrl);
                if (!fileRes.ok) throw new Error('Failed to download merged document from server.');
                const blob = await fileRes.blob();
                const url = window.URL.createObjectURL(blob);
                setDownloadUrl(url);
                setIsSuccess(true);
            } else {
                throw new Error("No download URL returned from server.");
            }
        } catch (error) {
            setErrorMsg(error.message || "An error occurred during merging.");
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
            
            <div className="w-full max-w-4xl relative z-10">
                <div className="text-center max-w-2xl mx-auto mt-8 mb-8 px-4">
                    <h1 className="text-2xl sm:text-4xl font-black text-[#1e2a52] leading-tight mb-3">
                        Merge PDFs
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed">
                        Combine multiple PDF files into a single, seamless document in seconds.
                    </p>
                </div>

                {!isProcessing && !isSuccess && (
                    <div id="mainUI" className="bg-white/70 backdrop-blur-xl border border-white shadow-2xl rounded-3xl p-6 sm:p-10 relative overflow-hidden transition-all duration-500 max-w-4xl mx-auto w-full">
                        {errorMsg && (
                            <div className="mb-4 p-4 text-red-700 bg-red-100 rounded-lg">
                                {errorMsg}
                            </div>
                        )}

                        <div 
                            className={`upload-zone relative border-2 border-dashed rounded-2xl p-8 sm:p-14 text-center cursor-pointer transition-all duration-300 ${isDragOver ? 'border-indigo-500 bg-indigo-100 scale-[1.01]' : 'border-indigo-200 bg-indigo-50/30'} hover:border-indigo-400 hover:bg-indigo-50 hover:shadow-inner group`}
                            onDrop={onDrop}
                            onDragOver={onDragOver}
                            onDragLeave={onDragLeave}
                            onClick={() => fileInputRef.current.click()}
                        >
                            <input 
                                type="file" 
                                multiple 
                                accept=".pdf" 
                                className="hidden" 
                                ref={fileInputRef}
                                onChange={(e) => {
                                    if(e.target.files.length) handleFiles(e.target.files);
                                }}
                            />
                            <div className="w-20 h-20 bg-white shadow-md rounded-2xl flex items-center justify-center mx-auto mb-6 transition-transform group-hover:scale-110 group-hover:-translate-y-1">
                                <svg className="w-10 h-10 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                            </div>
                            <p className="drop-text text-xl font-bold text-slate-800 mb-2 transition-colors group-hover:text-indigo-900">
                                {files.length > 0 ? `${files.length} File(s) selected` : 'Drag & Drop your PDFs here'}
                            </p>
                            <p className="text-sm text-slate-500">or <span className="font-semibold text-indigo-600 group-hover:underline">click to browse</span> files</p>
                        </div>
                        
                        {files.length > 0 && (
                            <div className="file-list mt-6 space-y-3">
                                {files.map((file, idx) => (
                                    <div key={idx} className="file-item flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm hover:shadow-md hover:-translate-y-[1px] transition-all group">
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg shrink-0">
                                                <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg>
                                            </div>
                                            <span className="font-medium text-slate-700 truncate">{file.name}</span>
                                        </div>
                                        <button onClick={(e) => { e.stopPropagation(); removeFile(idx); }} className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors cursor-pointer shrink-0" title="Remove file">
                                            <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="text-center mt-8">
                            <button 
                                onClick={handleMerge} 
                                disabled={files.length < 2 || isProcessing}
                                className="btn btn-primary bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700 text-white font-bold py-4 px-12 rounded-xl shadow-xl shadow-indigo-200 transform transition-all duration-500 flex items-center justify-center gap-2 group relative overflow-hidden mx-auto disabled:opacity-50 disabled:cursor-not-allowed hover:scale-[1.02] active:scale-[0.98] w-full sm:w-auto"
                            >
                                <span className="transition-all duration-500">Merge Files Now</span>
                                <svg className="w-5 h-5 transition-transform group-hover:translate-x-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12h15m0 0l-6.75-6.75M19.5 12l-6.75 6.75" />
                                </svg>
                            </button>
                        </div>
                    </div>
                )}

                {isProcessing && (
                    <div id="processingUI" className="flex flex-col items-center justify-center p-8 sm:p-12 bg-white/70 border border-white shadow-2xl rounded-3xl backdrop-blur-xl min-h-[400px] max-w-4xl mx-auto w-full mt-6">
                        <div className="speeder-loader-wrapper mb-6">
                            <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                        </div>
                        <h3 className="text-xl font-bold text-[#1e2a52] mb-2 text-center">Merging your documents...</h3>
                        <p className="text-slate-600 text-center text-sm max-w-md mb-2">
                            Please wait. If the free backend was sleeping, it may take up to 50 seconds to wake up.
                        </p>
                        <p className="text-xs text-slate-400 text-center mb-6">A timeout will automatically trigger if the server does not respond.</p>
                        <button
                            onClick={() => setIsProcessing(false)}
                            className="text-xs text-red-500 hover:text-red-700 underline font-medium cursor-pointer"
                        >
                            Cancel and go back
                        </button>
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
                            <p className="text-emerald-600 font-medium mb-4">Your merged PDF is ready to download.</p>

                            <a href={downloadUrl} download="Merged_Document.pdf" className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-emerald-200 transition-all active:scale-95 flex justify-center items-center gap-2 cursor-pointer relative z-10">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                Download Merged PDF
                            </a>
                            
                            <button onClick={resetApp} className="w-full bg-slate-800 hover:bg-slate-900 text-white font-bold py-4 px-8 rounded-xl shadow-lg shadow-slate-300 transition-all active:scale-95 flex justify-center items-center gap-2 relative z-10 mt-2">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" /></svg>
                                Merge more files
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
