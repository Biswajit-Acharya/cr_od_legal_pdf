import React, { useState, useEffect } from 'react';
import { ArrowLeft, Clock, Lock, Trash2, Globe, Link, Check, Eye } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

export default function ShareManagementPage({ onBack }) {
  const [shares, setShares] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [copiedToken, setCopiedToken] = useState('');

  useEffect(() => {
    fetchShares();
  }, []);

  const fetchShares = async () => {
    setIsLoading(true);
    setError('');
    
    // In this stateless implementation, we use localStorage to store the management tokens
    // created by this browser session.
    const savedTokens = JSON.parse(localStorage.getItem('pdf_management_tokens') || '[]');
    
    if (savedTokens.length === 0) {
      setShares([]);
      setIsLoading(false);
      return;
    }
    
    try {
      const formData = new FormData();
      formData.append('management_tokens', savedTokens.join(','));
      
      const res = await fetch(`${API_BASE_URL}/api/pdf/security/secure-sharing/manage`, {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to load shares.');
      
      // Match management tokens back to display properly
      // Note: The backend response should ideally return management tokens for us to know which is which, 
      // but for security we might just assume they are ours.
      setShares(data.shares || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRevoke = async (token, managementToken) => {
    if (!window.confirm("Are you sure you want to revoke access to this document? Anyone with the link will immediately lose access.")) return;
    
    try {
      const formData = new FormData();
      formData.append('management_token', managementToken);
      
      const res = await fetch(`${API_BASE_URL}/api/pdf/security/secure-sharing/${token}/revoke`, {
        method: 'POST',
        body: formData
      });
      
      if (!res.ok) {
         const data = await res.json().catch(()=>({}));
         throw new Error(data.detail || 'Failed to revoke share.');
      }
      
      // Refresh list
      fetchShares();
    } catch (err) {
      alert(err.message);
    }
  };

  const copyLink = (token) => {
    const url = `${window.location.origin}/#shared/${token}`;
    navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(''), 2000);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Active':
        return <span className="px-2.5 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold uppercase tracking-wide">Active</span>;
      case 'Expired':
        return <span className="px-2.5 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-bold uppercase tracking-wide">Expired</span>;
      case 'Revoked':
        return <span className="px-2.5 py-1 bg-red-100 text-red-700 rounded-full text-xs font-bold uppercase tracking-wide">Revoked</span>;
      default:
        return <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-full text-xs font-bold uppercase tracking-wide">{status}</span>;
    }
  };

  return (
    <div className="flex-1 flex flex-col w-full relative z-20 min-h-screen bg-slate-50">
      {/* Header */}
      <div className="w-full bg-[#1e2a52] px-4 sm:px-6 md:px-10 py-8 relative text-white">
        <div className="max-w-[1200px] mx-auto">
          <button onClick={onBack} className="inline-flex items-center gap-2 text-blue-200 hover:text-white transition-colors mb-6 text-sm font-semibold">
            <ArrowLeft className="w-4 h-4" /> Back to Tools
          </button>
          
          <h1 className="text-3xl font-extrabold mb-3">Manage Secure Shares</h1>
          <p className="text-blue-100 max-w-2xl text-sm sm:text-base leading-relaxed">
            View, track, and revoke access to all the PDF documents you have securely shared.
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 w-full max-w-[1200px] mx-auto px-4 sm:px-6 md:px-10 py-8 relative -mt-8 z-30">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200/60 overflow-hidden">
          {isLoading ? (
            <div className="p-12 text-center text-slate-500">
              <div className="w-8 h-8 border-4 border-[#1e2a52] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              Loading your shares...
            </div>
          ) : error ? (
            <div className="p-12 text-center text-red-500 bg-red-50">
              {error}
            </div>
          ) : shares.length === 0 ? (
            <div className="p-16 text-center flex flex-col items-center">
              <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center text-blue-600 mb-6">
                <Globe className="w-10 h-10" />
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">No Active Shares Found</h2>
              <p className="text-slate-500 max-w-md">You haven't securely shared any PDF documents yet using this browser, or your local data was cleared.</p>
              <button onClick={() => window.location.hash = '#pdf-security'} className="mt-8 bg-[#1e2a52] hover:bg-[#16203e] text-white px-6 py-3 rounded-full font-bold shadow-md transition-all text-sm">
                Create a Secure Share
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Document</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Security</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Views</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider">Created</th>
                    <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {shares.map(share => (
                    <tr key={share.token} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                            <FileText className="w-5 h-5" />
                          </div>
                          <div>
                            <p className="text-sm font-bold text-slate-800 max-w-[200px] truncate">{share.filename}</p>
                            <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                              {share.token.substring(0,8)}...
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(share.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1.5">
                          {share.has_password && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600"><Lock className="w-3 h-3" /> Password Protected</span>
                          )}
                          {!share.allow_download && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600"><Eye className="w-3 h-3" /> View Only</span>
                          )}
                          {share.expires_at && (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-600">
                              <Clock className="w-3 h-3" /> Expires: {new Date(share.expires_at.replace('Z', '+00:00')).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-slate-700">{share.access_count} views</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                        {new Date(share.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button 
                            onClick={() => copyLink(share.token)}
                            className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                            title="Copy Share Link"
                          >
                            {copiedToken === share.token ? <Check className="w-5 h-5 text-emerald-500" /> : <Link className="w-5 h-5" />}
                          </button>
                          
                          {share.status === 'Active' && (
                            <button 
                              onClick={() => handleRevoke(share.token, share.management_token)}
                              className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              title="Revoke Access"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
