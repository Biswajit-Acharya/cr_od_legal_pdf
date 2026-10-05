import React, { useState, useEffect } from 'react';
import { Shield, FileText, Lock, CheckCircle, Download, Upload, AlertCircle, Eye, EyeOff } from 'lucide-react';

const API_BASE = 'http://localhost:8002/api/pdf';

export default function PDFSecurityPolicyTemplatesPage({ tool, onBack }) {
  const [file, setFile] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('STANDARD_PROTECTION');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  useEffect(() => {
    // Fetch available templates
    fetch(`${API_BASE}/security/security-policy-templates`)
      .then(res => res.json())
      .then(data => {
        setTemplates(data.templates || []);
      })
      .catch(err => {
        console.error('Error fetching templates:', err);
        // Fallback to hardcoded list if fetch fails
        setTemplates([
          { id: 'STANDARD_PROTECTION', name: 'Standard Protection', description: 'Prevents editing and high-res printing. Allows standard printing, copying, and commenting.' },
          { id: 'CONFIDENTIAL', name: 'Confidential', description: 'Highly restricted. Prevents all printing, copying, and editing. Requires password to open if provided.' },
          { id: 'READ_ONLY', name: 'Read Only', description: 'Prevents all modifications, copying, and printing.' },
          { id: 'NO_PRINTING', name: 'No Printing', description: 'Prevents printing but allows other interactions.' },
          { id: 'NO_COPYING', name: 'No Copying', description: 'Prevents text/image extraction.' },
          { id: 'MAXIMUM_PROTECTION', name: 'Maximum Protection', description: 'Maximum restrictions.' },
        ]);
      });
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      setSuccess(false);
      setDownloadUrl(null);
    }
  };

  const handleApplyPolicy = async () => {
    if (!file) {
      setError('Please select a PDF file first.');
      return;
    }
    if (password && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (!password) {
      setError('A password is required to apply security policies.');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('template_id', selectedTemplate);
    if (password) formData.append('password', password);
    if (confirmPassword) formData.append('confirm_password', confirmPassword);

    try {
      const response = await fetch(`${API_BASE}/security/security-policy-templates/apply`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        throw new Error(data.error || data.detail || 'Failed to apply security policy.');
      }
      
      // The backend returns a relative URL like `/api/pdf/download/...`
      // We prepend the host to make it absolute if needed, or just use it directly if proxied.
      // Since API_BASE is absolute, we'll construct the full URL.
      const baseUrl = API_BASE.replace('/api/pdf', '');
      const fullDownloadUrl = data.download_url.startsWith('http') 
        ? data.download_url 
        : `${baseUrl}${data.download_url}`;
        
      setDownloadUrl(fullDownloadUrl);
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Failed to apply security policy.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center space-x-4 mb-6">
        <button 
          onClick={onBack}
          className="p-2 hover:bg-slate-100 rounded-full transition-colors"
        >
          <svg className="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
        </button>
        <div>
          <h2 className="text-2xl font-bold text-slate-800">{tool?.title || 'Security Policy Templates'}</h2>
          <p className="text-slate-500 text-sm mt-1">{tool?.description || 'Apply predefined security policies to your PDF.'}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Left Column - Input */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center">
              <Upload className="w-5 h-5 mr-2 text-indigo-500" />
              1. Upload PDF
            </h3>
            <label className="block w-full border-2 border-dashed border-slate-300 rounded-xl p-8 text-center cursor-pointer hover:border-indigo-500 hover:bg-indigo-50/50 transition-colors">
              <input type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
              <div className="space-y-2">
                <div className="mx-auto w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center">
                  <FileText className="w-6 h-6" />
                </div>
                <div className="text-slate-700 font-medium">
                  {file ? file.name : "Click to select a PDF"}
                </div>
                <p className="text-slate-500 text-xs">
                  {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : "Up to 50MB"}
                </p>
              </div>
            </label>
          </div>

          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center">
              <Lock className="w-5 h-5 mr-2 text-indigo-500" />
              2. Security Password
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Owner Password</label>
                <div className="relative">
                  <input 
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 pr-10"
                    placeholder="Required for permissions"
                  />
                  <button 
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Confirm Password</label>
                <div className="relative">
                  <input 
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 pr-10"
                    placeholder="Confirm password"
                  />
                  <button 
                    className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Templates & Action */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center">
              <Shield className="w-5 h-5 mr-2 text-indigo-500" />
              3. Select Policy Template
            </h3>
            
            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
              {templates.map(t => (
                <label 
                  key={t.id} 
                  className={`block p-4 rounded-xl border-2 cursor-pointer transition-all ${selectedTemplate === t.id ? 'border-indigo-600 bg-indigo-50/50' : 'border-slate-100 hover:border-slate-200 bg-slate-50'}`}
                >
                  <div className="flex items-start">
                    <input 
                      type="radio" 
                      name="template" 
                      value={t.id} 
                      checked={selectedTemplate === t.id}
                      onChange={(e) => setSelectedTemplate(e.target.value)}
                      className="mt-1 mr-3 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div>
                      <div className="font-semibold text-slate-800">{t.name}</div>
                      <div className="text-xs text-slate-500 mt-1">{t.description}</div>
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <button
            onClick={handleApplyPolicy}
            disabled={loading || !file}
            className={`w-full py-4 rounded-xl text-white font-bold text-lg flex justify-center items-center transition-all shadow-lg ${
              loading || !file 
                ? 'bg-slate-400 cursor-not-allowed shadow-none' 
                : 'bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 hover:shadow-indigo-500/25'
            }`}
          >
            {loading ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                Applying Policy...
              </span>
            ) : (
              <span className="flex items-center">
                <Lock className="w-5 h-5 mr-2" />
                Apply Security Policy
              </span>
            )}
          </button>

          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start animate-in slide-in-from-top-2">
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 mr-3 shrink-0" />
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          {success && downloadUrl && (
            <div className="p-6 bg-emerald-50 border border-emerald-200 rounded-xl flex flex-col items-center justify-center space-y-4 animate-in slide-in-from-bottom-4">
              <div className="w-12 h-12 bg-emerald-100 rounded-full flex items-center justify-center">
                <CheckCircle className="w-6 h-6 text-emerald-600" />
              </div>
              <div className="text-center">
                <h4 className="text-lg font-bold text-emerald-800">Policy Applied Successfully!</h4>
                <p className="text-sm text-emerald-600 mt-1">The PDF has been encrypted with the selected template.</p>
              </div>
              <a 
                href={downloadUrl}
                download={`secured_${file?.name || 'document.pdf'}`}
                className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition-colors flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Secured PDF
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}