const PDFTools = {
    files: [],
    maxFiles: 20,
    maxSize: 100 * 1024 * 1024,

    init() {
        if (typeof pdfjsLib !== 'undefined') {
            const ext = pdfjsLib.version >= '4' ? 'mjs' : 'js';
            pdfjsLib.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.${ext}`;
        }

        document.querySelectorAll('.upload-zone').forEach(zone => {
            const input = zone.querySelector('input[type="file"]');
            if (!input) return; // custom upload zone – handled by page script
            if (zone.dataset.managedBy === 'custom') return; // explicitly opt-out

            zone.addEventListener('click', (e) => {
                if (e.target.tagName !== 'INPUT' && !e.target.closest('.remove-btn')) {
                    input.click();
                }
            });

            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                zone.classList.add('dragover');
            });

            zone.addEventListener('dragleave', () => {
                zone.classList.remove('dragover');
            });

            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('dragover');
                this.addFiles(e.dataTransfer.files);
            });

            input.addEventListener('change', (e) => {
                this.addFiles(e.target.files);
                e.target.value = '';
            });
        });
    },

    addFiles(fileList) {
        for (const file of fileList) {
            if (this.files.length >= this.maxFiles) {
                this.toast('Maximum 20 files allowed', 'error');
                break;
            }
            if (file.size > this.maxSize) {
                this.toast(`${file.name} exceeds 100MB`, 'error');
                continue;
            }
            if (!file.name.toLowerCase().endsWith('.pdf')) {
                this.toast(`${file.name} is not a PDF`, 'error');
                continue;
            }
            if (!this.files.find(f => f.name === file.name && f.size === file.size)) {
                this.files.push(file);
            }
        }
        this.renderFiles();
        this.renderPreview();
    },

    removeFile(index) {
        this.files.splice(index, 1);
        this.renderFiles();
        this.renderPreview();
    },

    renderFiles() {
        const list = document.getElementById('fileList');
        if (!list) return;

        if (this.files.length === 0) {
            list.innerHTML = '';
            return;
        }

        list.innerHTML = this.files.map((f, i) => `
            <div class="file-item">
                <span class="name">${f.name}</span>
                <span class="size">${this.formatSize(f.size)}</span>
                <button class="remove-btn" onclick="event.stopPropagation(); PDFTools.removeFile(${i})">&times;</button>
            </div>
        `).join('');
    },

    async renderPreview() {
        const container = document.getElementById('pdfPreview');
        if (!container) return;

        if (this.files.length === 0) {
            container.innerHTML = '<p class="preview-empty">Upload a PDF to see preview</p>';
            return;
        }

        if (typeof pdfjsLib === 'undefined') {
            container.innerHTML = '<p class="preview-error">PDF.js not loaded.</p>';
            return;
        }

        container.innerHTML = '<div class="preview-loading"><div class="preview-spinner"></div><span>Loading pages...</span></div>';

        try {
            const file = this.files[0];
            const arrayBuffer = await file.arrayBuffer();
            const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

            let html = `<div class="preview-header"><span class="preview-title">${file.name}</span><span class="preview-count">${pdf.numPages} page${pdf.numPages > 1 ? 's' : ''}</span></div>`;
            html += '<div class="preview-grid">';

            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const viewport = page.getViewport({ scale: 1.5 });

                const canvas = document.createElement('canvas');
                canvas.width = viewport.width;
                canvas.height = viewport.height;

                const ctx = canvas.getContext('2d');
                await page.render({ canvasContext: ctx, viewport }).promise;

                html += `
                    <div class="preview-card" data-page-index="${i-1}" data-rotation="0" id="preview-card-${i-1}">
                        <div class="preview-card-inner">
                            <img src="${canvas.toDataURL('image/png')}" alt="Page ${i}" id="preview-img-${i-1}" style="transition: transform 0.3s ease;">
                            ${window.location.pathname === '/rotate' ? `
                            <div class="rotate-overlay" onclick="handleIndividualRotate(${i-1}, event)" style="position:absolute; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.4); display:none; align-items:center; justify-content:center; cursor:pointer; z-index:10; border-radius:4px;">
                                <svg style="width:40px;height:40px;color:white;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
                                </svg>
                            </div>` : ''}
                            <div class="preview-card-footer">
                                <span class="preview-page-num">${i}</span>
                            </div>
                        </div>
                    </div>`;
            }

            html += '</div>';
            container.innerHTML = html;

        } catch (err) {
            container.innerHTML = `<p class="preview-error">Preview failed: ${err.message}</p>`;
        }
    },

    formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },

    async upload(url, formData, btnEl) {
        btnEl.classList.add('loading');
        btnEl.disabled = true;
        
        const procUI = document.getElementById('processingUI');
        if (procUI) {
            btnEl.style.display = 'none';
            procUI.style.display = 'flex';
        }

        try {
            const res = await fetch(url, { method: 'POST', body: formData });
            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || data.message || 'Request failed');
            }

            return data;
        } catch (err) {
            this.toast(err.message, 'error');
            if (procUI) {
                procUI.style.display = 'none';
                btnEl.style.display = '';
            }
            throw err;
        } finally {
            btnEl.classList.remove('loading');
            btnEl.disabled = false;
        }
    },

    showResult(containerId, data, downloadUrl) {
        const procUI = document.getElementById('processingUI');
        if (procUI) procUI.style.display = 'none';
        
        const el = document.getElementById(containerId);
        if (!el) return;

        el.classList.add('show');

        if (data.success) {
            let previewHtml = '';
            if (data.filename && data.filename.toLowerCase().endsWith('.pdf')) {
                previewHtml = `
                    <div style="margin: 20px 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #f8fafc; padding: 10px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">
                        <p style="margin: 0 0 10px 0; font-size: 0.9rem; color: #64748b; font-weight: 600; display: flex; align-items: center; gap: 5px;">
                            <svg xmlns="http://www.w3.org/2000/svg" style="width:16px;height:16px" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                            Preview Result
                        </p>
                        <iframe src="${downloadUrl}#toolbar=0&navpanes=0&scrollbar=0" width="100%" height="450px" style="border: 1px solid #cbd5e1; border-radius: 4px; background: white;"></iframe>
                    </div>`;
            }

            el.innerHTML = `
                <div class="result-card success">
                    <div class="result-header success">&#10003; Success</div>
                    <div class="result-info">${data.message}</div>
                    ${previewHtml}
                    <a href="${downloadUrl}" class="download-btn" download style="margin-bottom: 10px;">&#8615; Download File</a>
                    <button class="btn btn-secondary" style="width: 100%; border: 1px solid #cbd5e1; background: white; color: #475569;" onclick="location.reload()">Process Another File</button>
                </div>`;
            setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 100);
        } else {
            el.innerHTML = `
                <div class="result-card error">
                    <div class="result-header error">&#10007; Error</div>
                    <div class="result-info">${data.message || data.detail || 'Operation failed'}</div>
                </div>`;
            setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 100);
        }
    },

    toast(msg, type = 'error') {
        const el = document.getElementById('toast');
        if (!el) return;
        el.textContent = msg;
        el.className = `toast ${type}`;
        setTimeout(() => { el.className = 'toast hidden'; }, 3500);
    }
};

window.PDFTools = PDFTools;
document.addEventListener('DOMContentLoaded', () => PDFTools.init());
