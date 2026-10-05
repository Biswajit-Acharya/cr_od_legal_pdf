import os

with open(r'c:\Users\achar\Downloads\Legal_pdf_fullstack\Legal_pdf_fullstack\Legal_pdf_frontend\CR_OD_Legal_PDF\src\page\ToolWorkspace.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we don't render raw JSON for Remove JavaScript
content = content.replace(
    "{apiResult && !downloadUrl && !apiResult.share_url && (",
    "{apiResult && !downloadUrl && !apiResult.share_url && toolName !== 'Remove JavaScript' && ("
)
content = content.replace(
    "{apiResult && !apiResult.share_url && (",
    "{apiResult && !apiResult.share_url && toolName !== 'Remove JavaScript' && ("
)

# Define the custom UI to inject for Remove JavaScript
custom_ui = '''
                  {apiResult && toolName === 'Remove JavaScript' && (
                    <div className="text-left bg-white border border-slate-200 rounded-2xl p-6 mt-4 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
                      
                      {/* Success / Error Header */}
                      {apiResult.javascript_count === 0 || apiResult.javascript_detected === false ? (
                        <div className="flex flex-col items-center text-center space-y-3 mb-6">
                          <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center">
                            <CheckCircle2 className="w-7 h-7 text-emerald-600" />
                          </div>
                          <h2 className="text-xl font-bold text-slate-900">? No JavaScript Detected</h2>
                          <p className="text-slate-600 text-sm">No embedded PDF JavaScript was found in this document.</p>
                        </div>
                      ) : (
                        (!apiResult.verification_passed || (apiResult.removed_count || 0) < (apiResult.javascript_count || 0)) ? (
                          <div className="flex flex-col items-center text-center space-y-3 mb-6">
                            <div className="w-14 h-14 bg-amber-100 rounded-full flex items-center justify-center">
                              <AlertCircle className="w-7 h-7 text-amber-600" />
                            </div>
                            <h2 className="text-xl font-bold text-amber-900">? JavaScript Removal Requires Attention</h2>
                            <p className="text-amber-800 text-sm">JavaScript was detected, but the cleaned PDF could not be fully verified.</p>
                          </div>
                        ) : (
                          <div className="flex flex-col items-center text-center space-y-3 mb-6">
                            <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center">
                              <CheckCircle2 className="w-7 h-7 text-emerald-600" />
                            </div>
                            <h2 className="text-xl font-bold text-slate-900">? JavaScript Removed Successfully</h2>
                            <p className="text-slate-600 text-sm">Your PDF has been cleaned and independently verified.</p>
                            <p className="text-slate-500 text-xs font-mono bg-slate-50 px-3 py-1 rounded mt-2">{apiResult.original_filename || files[0]?.name}</p>
                          </div>
                        )
                      )}

                      {/* Security Analysis Table */}
                      <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden mb-6">
                        <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                          <h3 className="font-bold text-slate-800 text-sm">SECURITY ANALYSIS</h3>
                        </div>
                        <div className="divide-y divide-slate-100 text-sm">
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">JavaScript Detected</span>
                            <span className="font-bold text-slate-900">{apiResult.javascript_count || 0}</span>
                          </div>
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">JavaScript Removed</span>
                            <span className="font-bold text-slate-900">{apiResult.removed_count || 0}</span>
                          </div>
                          {(apiResult.javascript_count || 0) > 0 && (
                            <div className="flex justify-between items-center px-4 py-3">
                              <span className="text-slate-600 font-medium">Remaining JavaScript</span>
                              <span className={ont-bold }>
                                {Math.max(0, (apiResult.javascript_count || 0) - (apiResult.removed_count || 0))}
                              </span>
                            </div>
                          )}
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Verification</span>
                            <span className={ont-bold flex items-center }>
                              {apiResult.verification_passed ? '? Passed' : '? Failed'}
                            </span>
                          </div>
                          {(apiResult.javascript_count || 0) > 0 && (
                            <div className="flex justify-between items-center px-4 py-3">
                              <span className="text-slate-600 font-medium">Pages Preserved</span>
                              <span className={ont-bold flex items-center }>
                                {apiResult.pages_preserved ? '? Yes' : '? No'}
                              </span>
                            </div>
                          )}
                          <div className="flex justify-between items-center px-4 py-3">
                            <span className="text-slate-600 font-medium">Digital Signature</span>
                            <span className={ont-bold }>
                              {apiResult.digital_signature_detected ? 'Detected' : 'Not Detected'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Detected Locations */}
                      {(apiResult.javascript_count || 0) > 0 && apiResult.javascript_locations?.length > 0 && (
                        <div className="bg-slate-50 border border-slate-200 rounded-xl overflow-hidden mb-6">
                          <div className="bg-slate-100 border-b border-slate-200 px-4 py-3">
                            <h3 className="font-bold text-slate-800 text-sm uppercase">Detected JavaScript</h3>
                          </div>
                          <div className="px-4 py-3">
                            <ul className="space-y-1">
                              {apiResult.javascript_locations.map((loc, idx) => (
                                <li key={idx} className="flex items-center text-slate-700 text-sm">
                                  <span className="mr-2 text-slate-400">•</span>
                                  {loc}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}

                      {/* Verification Message */}
                      {(apiResult.javascript_count || 0) > 0 && apiResult.verification_passed && (apiResult.removed_count || 0) >= (apiResult.javascript_count || 0) && (
                        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start space-x-3 mb-6">
                          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-emerald-900 font-bold text-sm mb-0.5">? Verification Passed</h4>
                            <p className="text-emerald-700 text-xs">
                              The sanitized PDF was scanned again after removal. No embedded JavaScript remains in the cleaned PDF.
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Signature Warning */}
                      {apiResult.digital_signature_detected && (
                        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start space-x-3 mb-6">
                          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-amber-900 font-bold text-sm mb-0.5">? Digital Signature Detected</h4>
                            <p className="text-amber-800 text-xs">
                              Modifying a signed PDF may affect the validity of its existing digital signature. Re-verification may be required.
                            </p>
                          </div>
                        </div>
                      )}

                    </div>
                  )}
'''

content = content.replace(
    "{apiResult && !apiResult.share_url && toolName !== 'Remove JavaScript' && (",
    "{apiResult && !apiResult.share_url && toolName !== 'Remove JavaScript' && (" + custom_ui
)

with open(r'c:\Users\achar\Downloads\Legal_pdf_fullstack\Legal_pdf_fullstack\Legal_pdf_frontend\CR_OD_Legal_PDF\src\page\ToolWorkspace.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
