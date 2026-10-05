import React from 'react';
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Info,
  Shield,
  Link,
  AlertCircle
} from 'lucide-react';

const UnsafeLinkDetectionResult = ({ result }) => {
  if (!result || !result.links) return null;

  const { stats, links, total_links, scanned_at } = result;

  const getRiskIcon = (level) => {
    switch (level) {
      case 'CRITICAL': return <XCircle className="text-red-500 w-5 h-5" />;
      case 'HIGH': return <AlertCircle className="text-red-400 w-5 h-5" />;
      case 'MEDIUM': return <AlertTriangle className="text-orange-500 w-5 h-5" />;
      case 'LOW': return <Info className="text-yellow-500 w-5 h-5" />;
      case 'INFO': return <CheckCircle className="text-emerald-500 w-5 h-5" />;
      default: return <CheckCircle className="text-emerald-500 w-5 h-5" />;
    }
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'CRITICAL': return 'bg-red-100 text-red-800 border-red-200';
      case 'HIGH': return 'bg-red-50 text-red-700 border-red-100';
      case 'MEDIUM': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'LOW': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'INFO': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      default: return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <Shield className="text-indigo-600 w-6 h-6" />
            <h3 className="text-lg font-semibold text-slate-800">Scan Summary</h3>
          </div>
          <span className="text-sm text-slate-500">
            {new Date(scanned_at || Date.now()).toLocaleString()}
          </span>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 p-6">
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 text-center">
            <div className="text-2xl font-bold text-slate-700">{total_links}</div>
            <div className="text-xs font-medium text-slate-500 mt-1 uppercase">Total Links</div>
          </div>
          <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-100 text-center">
            <div className="text-2xl font-bold text-emerald-600">{stats.safe}</div>
            <div className="text-xs font-medium text-emerald-600 mt-1 uppercase">Safe / Info</div>
          </div>
          <div className="bg-yellow-50 rounded-xl p-4 border border-yellow-100 text-center">
            <div className="text-2xl font-bold text-yellow-600">{stats.suspicious}</div>
            <div className="text-xs font-medium text-yellow-600 mt-1 uppercase">Suspicious</div>
          </div>
          <div className="bg-orange-50 rounded-xl p-4 border border-orange-100 text-center">
            <div className="text-2xl font-bold text-orange-600">{stats.high_risk}</div>
            <div className="text-xs font-medium text-orange-600 mt-1 uppercase">High Risk</div>
          </div>
          <div className="bg-red-50 rounded-xl p-4 border border-red-100 text-center">
            <div className="text-2xl font-bold text-red-600">{stats.dangerous_scheme + stats.invalid}</div>
            <div className="text-xs font-medium text-red-600 mt-1 uppercase">Dangerous / Invalid</div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-slate-800">Analyzed URLs</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50/50 text-slate-500 uppercase text-xs font-semibold">
              <tr>
                <th className="px-6 py-4">Risk</th>
                <th className="px-6 py-4">URL</th>
                <th className="px-6 py-4">Score</th>
                <th className="px-6 py-4">Pages</th>
                <th className="px-6 py-4">Findings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {links.length === 0 ? (
                <tr>
                  <td colSpan="5" className="px-6 py-8 text-center text-slate-500">
                    No URLs found in this document.
                  </td>
                </tr>
              ) : (
                links.sort((a, b) => b.risk_score - a.risk_score).map((link, idx) => (
                  <tr key={idx} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        {getRiskIcon(link.risk_level)}
                        <span className={"text-xs font-bold px-2 py-0.5 rounded-full border " + getRiskColor(link.risk_level)}>
                          {link.risk_level}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 max-w-xs truncate" title={link.original_url}>
                      <div className="flex items-center space-x-2">
                        <Link className="text-slate-400 shrink-0 w-4 h-4" />
                        <span className="font-mono text-slate-700 truncate">{link.original_url}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-bold text-slate-700">
                      {link.risk_score}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {link.page_numbers.map(p => (
                          <span key={p} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">Pg {p}</span>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {link.findings.length === 0 ? (
                        <span className="text-emerald-600 text-xs font-medium">No suspicious indicators</span>
                      ) : (
                        <ul className="space-y-1">
                          {link.findings.map((f, i) => (
                            <li key={i} className="text-xs text-slate-600 flex items-start">
                              <span className="text-slate-400 mr-1.5">•</span>
                              <span title={f.evidence}>{f.description}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default UnsafeLinkDetectionResult;
