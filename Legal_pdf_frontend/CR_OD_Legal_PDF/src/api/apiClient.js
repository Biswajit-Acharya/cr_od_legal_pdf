// Centralized API Client for Legal PDF Fullstack
// All requests use relative URLs — Vite proxy forwards to backend automatically.
// Backend can run on ANY port — just set VITE_BACKEND_URL in .env

const getCleanApiBase = () => {
    // When running in the browser on Vercel, use relative URLs ('')
    // Vercel rewrites in vercel.json will proxy all /api requests to Render server-side
    // This completely eliminates any browser CORS preflight blocking!
    if (typeof window !== 'undefined' && window.location && (window.location.hostname.includes('vercel.app') || window.location.hostname.includes('localhost') || window.location.hostname === '127.0.0.1')) {
        return '';
    }
    let url = (import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '').trim();
    if (url.includes('crodlegalpdf.onrender.com')) {
        url = 'https://cr-od-legal-pdf-backend.onrender.com';
    }
    return url.replace(/\/+$/, '');
};

export const API_BASE_URL = getCleanApiBase();
const DEFAULT_TIMEOUT_MS = 90000; // 90 seconds (allows for Render cold start ~50s)

/**
 * Helper to handle file uploads properly.
 * @param {string} endpoint - The API endpoint (e.g., '/api/pdf/merge' or '/document-management/batch-export')
 * @param {FormData} formData - The payload containing files and other form fields
 * @param {boolean} expectFileResponse - If true, resolves to Blob. If false, resolves to JSON.
 * @param {number} timeoutMs - Max wait time in ms before aborting
 */
export const uploadFiles = async (endpoint, formData, expectFileResponse = false, timeoutMs = DEFAULT_TIMEOUT_MS) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            body: formData,
            signal: controller.signal,
        });

        if (!response.ok) {
            let errorMsg = `Server Error: ${response.status} ${response.statusText}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
                }
            } catch (e) { }
            throw new Error(errorMsg);
        }

        if (expectFileResponse) {
            return await response.blob();
        }
        return await response.json();
    } catch (error) {
        if (error.name === 'AbortError') {
            const timeoutError = new Error('Request timed out. The server might be waking up or taking too long. Please try again in 30 seconds.');
            console.error(`API Timeout on ${endpoint}:`, timeoutError);
            throw timeoutError;
        }
        console.error(`API Error on ${endpoint}:`, error);
        throw error;
    } finally {
        clearTimeout(timeoutId);
    }
};

/**
 * Helper to download a processed file.
 * @param {string} url - The URL to download from (relative path)
 * @param {string} filename - The suggested filename for the downloaded file
 * @param {number} timeoutMs - Max wait time in ms before aborting
 */
export const downloadFile = async (url, filename, timeoutMs = 60000) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(`${API_BASE_URL}${url}`, {
            method: 'GET',
            signal: controller.signal,
        });

        if (!response.ok) {
            throw new Error(`Download failed: ${response.status} ${response.statusText}`);
        }

        const blob = await response.blob();
        const objectUrl = window.URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = objectUrl;
        a.download = filename || 'downloaded_file.pdf';
        document.body.appendChild(a);
        a.click();

        window.URL.revokeObjectURL(objectUrl);
        document.body.removeChild(a);
    } catch (error) {
        if (error.name === 'AbortError') {
            const timeoutError = new Error('Download timed out. Please try again.');
            console.error(`Download Timeout on ${url}:`, timeoutError);
            throw timeoutError;
        }
        console.error(`Download Error on ${url}:`, error);
        throw error;
    } finally {
        clearTimeout(timeoutId);
    }
};

/**
 * Helper to get URL for download links.
 * Returns relative paths as-is (Vite proxy handles forwarding in dev).
 * @param {string} path - Relative path starting with /
 * @returns {string} URL safe for <a href>
 */
export const getFullUrl = (path) => {
    if (!path || path.startsWith('http') || path === '#' || path === '#mock-download' || path === '#mock-zip-download') return path;
    return `${API_BASE_URL}${path}`;
};

export default {
    uploadFiles,
    downloadFile,
    getFullUrl,
    API_BASE_URL,
};