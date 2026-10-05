/**
 * Tool API Configuration
 * Maps tool names to their backend API endpoints.
 * Used by ToolWorkspace to make real backend API calls.
 */

const API_BASE = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || '';

// PDF Security tools -> /api/pdf/security/*
const PDF_SECURITY_ENDPOINTS = {
  'Protect PDF': { endpoint: '/api/pdf/security/protect', method: 'POST', type: 'file+field', fieldName: 'password', fieldLabel: 'Password' },
  'Unlock PDF': { endpoint: '/api/pdf/security/unlock', method: 'POST', type: 'file+field', fieldName: 'password', fieldLabel: 'Password' },
  'Remove JavaScript': { endpoint: '/api/pdf/security/remove-javascript', method: 'POST', type: 'file' },
  'Remove Form Data': { endpoint: '/api/pdf/security/remove-form-data', method: 'POST', type: 'file' },
  'Remove Hidden Data': { endpoint: '/api/pdf/security/remove-hidden-data', method: 'POST', type: 'file' },
  'Restrict Accessibility Copy': { endpoint: '/api/pdf/security/restrict-copy', method: 'POST', type: 'file' },
  'PDF Security Score': { endpoint: '/api/pdf/security/security-score', method: 'POST', type: 'file' },
  'Malware Scan PDF': { endpoint: '/api/pdf/security/malware-scan', method: 'POST', type: 'file' },
  'PDF/A Validation': { endpoint: '/api/pdf/security/pdfa-validation', method: 'POST', type: 'file' },
  'Digital Signature Verification': { endpoint: '/api/pdf/security/digital-signature-verify', method: 'POST', type: 'file' },
  'Document Integrity Verification': { endpoint: '/api/pdf/document-integrity/verify', method: 'POST', type: 'file' },
  'Restrict Page Extraction': { endpoint: '/api/pdf/security/restrict-page-extraction', method: 'POST', type: 'file' },
  'Share Management': { endpoint: '/api/pdf/security/secure-share/list', method: 'GET', type: 'none' },
  'Embedded Media Detection': { endpoint: '/api/pdf/security/embedded-media-detect', method: 'POST', type: 'file' },
  'File Expiration': {
    endpoint: '/api/pdf/security/file-expiration',
    method: 'POST',
    type: 'file+fields',
    fields: [
      { name: 'expiration_type', label: 'Expiration Type', inputType: 'select', default: 'duration', options: [{ label: 'Duration (in seconds)', value: 'duration' }, { label: 'Exact Date', value: 'date' }] },
      { name: 'duration_seconds', label: 'Duration (Seconds) (Leave empty if Date)', inputType: 'number', default: '86400' },
      { name: 'expires_at', label: 'Expiration Date (Leave empty if Duration)', inputType: 'datetime-local' }
    ]
  },
  'Hide Sensitive Information': { endpoint: '/api/pdf/security/hide-sensitive', method: 'POST', type: 'file' },
  'Blackout Areas': { endpoint: '/api/pdf/security/blackout-areas', method: 'POST', type: 'file' },
  'PDF Metadata Protection': { endpoint: '/api/pdf/security/metadata-protection', method: 'POST', type: 'file+fields', fields: [{name:'password',label:'Owner Password (optional)',inputType:'password'}] },
  'PDF Sanitization': { endpoint: '/api/pdf/security/sanitize', method: 'POST', type: 'file' },
  'PDF Security Policy Templates': { endpoint: '/api/pdf/security/policy-templates', method: 'POST', type: 'file' },
  'PDF Version Security Check': { endpoint: '/api/pdf/security/version-check', method: 'POST', type: 'file' },
  'Secure PDF Sharing': {
    endpoint: '/api/pdf/security/secure-sharing',
    method: 'POST',
    type: 'file+fields',
    fields: [
      { name: 'password', label: 'Password Protection (Optional)', inputType: 'password' },
      { name: 'expires_at', label: 'Expiration Date (Optional)', inputType: 'datetime-local' },
      { name: 'allow_download', label: 'Allow Download', inputType: 'checkbox', default: 'true' },
      { name: 'allow_print', label: 'Allow Printing', inputType: 'checkbox', default: 'true' }
    ]
  },
  'Security Audit Report': { endpoint: '/api/pdf/security/audit-report', method: 'POST', type: 'file' },
  'Trusted Certificates': { endpoint: '/api/pdf/security/trusted-certs', method: 'POST', type: 'file' },
  'Unsafe Link Detection': { endpoint: '/api/pdf/security/unsafe-link-detection', method: 'POST', type: 'file' },
  'Watermark Protection': { endpoint: '/api/pdf/security/watermark-protection', method: 'POST', type: 'file' },
  'Atomic Server Timestamping': { endpoint: '/api/pdf/security/atomic-server-timestamping', method: 'POST', type: 'file' },
  'AI Document Classification': { endpoint: '/api/pdf/security/ai-document-classification', method: 'POST', type: 'file' },
  'AI Security Recommendations': { endpoint: '/api/pdf/security/ai-recommendations', method: 'POST', type: 'file' },
  'AI Security Risk Detection': { endpoint: '/api/pdf/security/ai-security-risk-detection', method: 'POST', type: 'file' },
  'AI Sensitive Data Detection': { endpoint: '/api/pdf/security/ai-sensitive-data-detection', method: 'POST', type: 'file' },
  'PDF Forensic Analysis': { endpoint: '/api/pdf/security/forensic-analysis', method: 'POST', type: 'file' },
};

// PDF Signature tools -> /api/pdf/signature/*
const PDF_SIGNATURE_ENDPOINTS = {
  'Digital Sign': { endpoint: '/api/pdf/signature/digital-sign', method: 'POST', type: 'file' },
  'e-Sign': { endpoint: '/api/pdf/signature/e-sign', method: 'POST', type: 'file+fields', fields: [{name:'signer_name',label:'Signer Name'},{name:'reason',label:'Reason for Signing'}] },
  'PDF Sign': { endpoint: '/api/pdf/signature/pdf-sign', method: 'POST', type: 'file' },
  'Biometric Signature': { endpoint: '/api/pdf/signature/biometric-sign', method: 'POST', type: 'file+field', fieldName: 'signature_image', fieldLabel: 'Signature Image URL' },
  'Cloud Signature': { endpoint: '/api/pdf/signature/cloud-sign', method: 'POST', type: 'file+field', fieldName: 'provider', fieldLabel: 'Cloud Provider' },
  'Visible Signature Designer': { endpoint: '/api/pdf/signature/visible-signature', method: 'POST', type: 'file+fields', fields: [{name:'x',label:'X Position',default:'100'},{name:'y',label:'Y Position',default:'100'},{name:'page',label:'Page Number',default:'1'}] },
  'Invisible Digital Signature': { endpoint: '/api/pdf/signature/invisible-signature', method: 'POST', type: 'file' },
  'Signature Field Creator': { endpoint: '/api/pdf/signature/create-field', method: 'POST', type: 'file+fields', fields: [{name:'field_name',label:'Field Name'},{name:'x',label:'X Position',default:'100'},{name:'y',label:'Y Position',default:'100'},{name:'page',label:'Page Number',default:'1'}] },
  'PKI Signature': { endpoint: '/api/pdf/signature/pki-sign', method: 'POST', type: 'file' },
  'Signature Appearance Templates': { endpoint: '/api/pdf/signature/appearance-templates', method: 'POST', type: 'file' },
  'USB Token Signature': { endpoint: '/api/pdf/signature/usb-token-sign', method: 'POST', type: 'file' },
  'Timestamp Signature': { endpoint: '/api/pdf/signature/timestamp-sign', method: 'POST', type: 'file' },
  'Long-Term Signature Validation (LTV)': { endpoint: '/api/pdf/signature/validate', method: 'POST', type: 'file' },
  'Batch Signature Validation': { endpoint: '/api/pdf/signature/validate', method: 'POST', type: 'file' },
  'Bulk Signature': { endpoint: '/api/pdf/signature/pdf-sign', method: 'POST', type: 'file' },
  'Signature Validation': { endpoint: '/api/pdf/signature/validate', method: 'POST', type: 'file' },
  'Signature Audit Trail': { endpoint: '/api/pdf/signature/audit-trail', method: 'POST', type: 'file' },
  'Signature History': { endpoint: '/api/pdf/signature/history', method: 'POST', type: 'file' },
  'Signature Certificate Viewer': { endpoint: '/api/pdf/signature/certificate-viewer', method: 'POST', type: 'file' },
  'Certificate Import': { endpoint: '/api/pdf/signature/certificate-import', method: 'POST', type: 'file+field', fieldName: 'cert_file', fieldLabel: 'Certificate File' },
  'Certificate Export': { endpoint: '/api/pdf/signature/certificate-export', method: 'POST', type: 'file' },
  'Certificate Revocation Check': { endpoint: '/api/pdf/signature/certificate-revocation', method: 'POST', type: 'file' },
  'Delegated Signing': { endpoint: '/api/pdf/signature/delegated-signing', method: 'POST', type: 'file' },
  'Multi-signer Workflow': { endpoint: '/api/pdf/signature/multi-signer', method: 'POST', type: 'file+field', fieldName: 'signers', fieldLabel: 'Signers (comma-separated)' },
  'Signing Order': { endpoint: '/api/pdf/signature/signing-order', method: 'POST', type: 'file' },
  'Signing Status Dashboard': { endpoint: '/api/pdf/signature/status-dashboard', method: 'POST', type: 'file' },
  'Face Verification Before Signing': { endpoint: '/api/pdf/signature/face-verification', method: 'POST', type: 'file' },
  'OTP Verification Before Signing': { endpoint: '/api/pdf/signature/otp-verification', method: 'POST', type: 'file' },
  'QR Code Signature Verification': { endpoint: '/api/pdf/signature/qr-verify', method: 'POST', type: 'file' },
  'Remote Signature': { endpoint: '/api/pdf/signature/remote-sign', method: 'POST', type: 'file' },
  'Offline Signature Support': { endpoint: '/api/pdf/signature/pdf-sign', method: 'POST', type: 'file' },
  'Signature Location': { endpoint: '/api/pdf/signature/visible-signature', method: 'POST', type: 'file+fields', fields: [{name:'x',label:'X',default:'50'},{name:'y',label:'Y',default:'50'},{name:'page',label:'Page',default:'1'}] },
  'Signature Reason': { endpoint: '/api/pdf/signature/e-sign', method: 'POST', type: 'file+field', fieldName: 'reason', fieldLabel: 'Reason for Signing' },
  'Signature Permission Manager': { endpoint: '/api/pdf/signature/delegated-signing', method: 'POST', type: 'file' },
  'Signature Lock Document': { endpoint: '/api/pdf/signature/lock-document', method: 'POST', type: 'file' },
  'Signature Reminder': { endpoint: '/api/pdf/signature/reminder', method: 'POST', type: 'file' },
  'Signature Expiration': { endpoint: '/api/pdf/signature/expiration', method: 'POST', type: 'file' },
  'Signature Comparison': { endpoint: '/api/pdf/signature/comparison', method: 'POST', type: 'file' },
  'Signature Compliance Check': { endpoint: '/api/pdf/signature/compliance-check', method: 'POST', type: 'file' },
  'Signature Evidence Report': { endpoint: '/api/pdf/signature/evidence-report', method: 'POST', type: 'file' },
  'Reject Signature Request': { endpoint: '/api/pdf/signature/reject', method: 'POST', type: 'file' },
  'Reuse Signature': { endpoint: '/api/pdf/signature/reuse', method: 'POST', type: 'file' },
  'Auto Signature Placement': { endpoint: '/api/pdf/signature/auto-place', method: 'POST', type: 'file' },
  'Witness Signature': { endpoint: '/api/pdf/signature/witness-sign', method: 'POST', type: 'file+field', fieldName: 'witness_name', fieldLabel: 'Witness Name' },
  'Initial Signature': { endpoint: '/api/pdf/signature/initial-sign', method: 'POST', type: 'file+field', fieldName: 'initial_name', fieldLabel: 'Initial' },
};

// AI Smart Features -> /api/ai/*
const AI_SMART_FEATURES_ENDPOINTS = {
  'AI Chat with PDF': { endpoint: '/api/ai/chat-with-pdf', method: 'POST', type: 'file+field', fieldName: 'message', fieldLabel: 'Ask a question about this PDF' },
  'AI Summarizer': { endpoint: '/api/ai/summarize', method: 'POST', type: 'file' },
  'AI OCR': { endpoint: '/api/ai/ocr', method: 'POST', type: 'file' },
  'AI Semantic Search': { endpoint: '/api/ai/semantic-search', method: 'POST', type: 'file+field', fieldName: 'query', fieldLabel: 'Search Query' },
  'AI Document Insights': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'Contract Summary': { endpoint: '/api/ai/contract-summary', method: 'POST', type: 'file' },
  'Meeting Summary': { endpoint: '/api/ai/meeting-summary', method: 'POST', type: 'file' },
  'Research Assistant': { endpoint: '/api/ai/research-assistant', method: 'POST', type: 'file+field', fieldName: 'query', fieldLabel: 'Research Query' },
  'Extract Key Points': { endpoint: '/api/ai/extract-key-points', method: 'POST', type: 'file' },
  'Answer Document Questions': { endpoint: '/api/ai/answer-questions', method: 'POST', type: 'file+field', fieldName: 'question', fieldLabel: 'Your Question' },
  'Translate PDF': { endpoint: '/api/ai/translate', method: 'POST', type: 'file+field', fieldName: 'target_language', fieldLabel: 'Target Language (e.g., Spanish, French)' },
  'Simplify Document': { endpoint: '/api/ai/simplify', method: 'POST', type: 'file' },
  'Grammar Improvement': { endpoint: '/api/ai/grammar-check', method: 'POST', type: 'file' },
  'Writing Enhancement': { endpoint: '/api/ai/writing-enhancement', method: 'POST', type: 'file' },
  'Multi-document Chat': { endpoint: '/api/ai/multi-doc-chat', method: 'POST', type: 'multi-file+field', fieldName: 'message', fieldLabel: 'Ask about these documents' },
  'Workflow & Automation': { endpoint: '/api/ai/workflow-automation', method: 'POST', type: 'file' },
  'PDF to Markdown': { endpoint: '/convert-from-pdf/pdf-to-markdown', method: 'POST', type: 'file' },
  'PDF Forms': { endpoint: '/api/pdf/security/remove-form-data', method: 'POST', type: 'file' },
  'AcroForms Support': { endpoint: '/api/pdf/security/remove-form-data', method: 'POST', type: 'file' },
  'XFA Forms Support': { endpoint: '/api/pdf/security/remove-form-data', method: 'POST', type: 'file' },
  'Add Date Fields': { endpoint: '/api/pdf/security/remove-form-data', method: 'POST', type: 'file' },
  'Link Fillable Fields': { endpoint: '/api/pdf/security/remove-form-data', method: 'POST', type: 'file' },
  'Export Form Data': { endpoint: '/api/pdf/security/remove-form-data', method: 'POST', type: 'file' },
  'Cloud Version History': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'Automatic Cloud Sync': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'Continue Editing Anywhere': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'Browser-based Editing': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'Google Drive Integration': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'Dropbox Integration': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'OneDrive Integration': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'Box Integration': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
  'SharePoint Integration': { endpoint: '/api/ai/document-insights', method: 'POST', type: 'file' },
};

// Accessibility tools -> /api/accessibility/*
const ACCESSIBILITY_ENDPOINTS = {
  'WCAG Compliance Checker': { endpoint: '/api/accessibility/wcag-checker/scan', method: 'POST', type: 'file', customUpload: true },
  'PDF/UA Compliance': { endpoint: '/api/accessibility/pdfua-check', method: 'POST', type: 'file' },
  'Accessibility Checker': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Accessibility Compliance Dashboard': { endpoint: '/api/accessibility/compliance-dashboard', method: 'POST', type: 'file' },
  'Accessibility Fix Suggestions AI': { endpoint: '/api/accessibility/fix-suggestions', method: 'POST', type: 'file' },
  'Accessibility Report Export': { endpoint: '/api/accessibility/export-report', method: 'POST', type: 'file' },
  'Accessibility Support': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Tagged PDF Support': { endpoint: '/api/accessibility/tagged-pdf-support', method: 'POST', type: 'file' },
  'Screen Reader Support': { endpoint: '/api/accessibility/screen-reader-support', method: 'POST', type: 'file' },
  'Read Aloud': { endpoint: '/api/accessibility/read-aloud', method: 'POST', type: 'file' },
  'Reading Order Editor': { endpoint: '/api/accessibility/reading-order', method: 'POST', type: 'file' },
  'Reading Ruler': { endpoint: '/api/accessibility/read-aloud', method: 'POST', type: 'file' },
  'Keyboard Navigation': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Keyboard Shortcut Customization': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Skip Navigation Links': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Voice Navigation': { endpoint: '/api/accessibility/read-aloud', method: 'POST', type: 'file' },
  'Speech to Text Input': { endpoint: '/api/accessibility/read-aloud', method: 'POST', type: 'file' },
  'Color Contrast Validation': { endpoint: '/api/accessibility/color-contrast', method: 'POST', type: 'file' },
  'High Contrast Mode': { endpoint: '/api/accessibility/color-contrast', method: 'POST', type: 'file' },
  'Text Reflow': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Adjustable Letter Spacing': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Adjustable Line Spacing': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Custom Font Size Controls': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Dyslexia Reading Mode': { endpoint: '/api/accessibility/read-aloud', method: 'POST', type: 'file' },
  'Focus Mode': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Alternative Text (Alt Text)': { endpoint: '/api/accessibility/alt-text', method: 'POST', type: 'file' },
  'Heading Structure Validation': { endpoint: '/api/accessibility/heading-structure', method: 'POST', type: 'file' },
  'Accessible Forms': { endpoint: '/api/accessibility/accessible-forms', method: 'POST', type: 'file' },
  'Accessible Table Validation': { endpoint: '/api/accessibility/accessible-tables', method: 'POST', type: 'file' },
  'Captions & Transcript Support': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Sign Language Video Support': { endpoint: '/api/accessibility/checker', method: 'POST', type: 'file' },
  'Language Detection & Document Language Tagging': { endpoint: '/api/accessibility/language-detection', method: 'POST', type: 'file' },
};

// Biometric Auth tools -> /api/biometric/*
const BIOMETRIC_ENDPOINTS = {
  'Add Fingerprint': { endpoint: '/api/biometric/add-fingerprint', method: 'POST', type: 'file+field', fieldName: 'fingerprint_data', fieldLabel: 'Fingerprint Data' },
  'Verify Fingerprint': { endpoint: '/api/biometric/verify-fingerprint', method: 'POST', type: 'file+field', fieldName: 'fingerprint_data', fieldLabel: 'Fingerprint Data' },
  'Update Fingerprint': { endpoint: '/api/biometric/update-fingerprint', method: 'POST', type: 'file+field', fieldName: 'fingerprint_data', fieldLabel: 'New Fingerprint Data' },
  'Replace Fingerprint': { endpoint: '/api/biometric/replace-fingerprint', method: 'POST', type: 'file+fields', fields: [{name:'old_fingerprint',label:'Old Fingerprint'},{name:'new_fingerprint',label:'New Fingerprint'}] },
  'Remove Fingerprint': { endpoint: '/api/biometric/remove-fingerprint', method: 'POST', type: 'file' },
  'Fingerprint Matching': { endpoint: '/api/biometric/match-fingerprint', method: 'POST', type: 'file+field', fieldName: 'fingerprint_data', fieldLabel: 'Fingerprint to Match' },
  'Add Face Signature': { endpoint: '/api/biometric/add-face-signature', method: 'POST', type: 'file' },
  'Verify Face Signature': { endpoint: '/api/biometric/verify-face-signature', method: 'POST', type: 'file' },
  'Remove Face Signature': { endpoint: '/api/biometric/remove-face-signature', method: 'POST', type: 'file' },
  'Add Handwritten Biometric Signature': { endpoint: '/api/biometric/add-handwritten-signature', method: 'POST', type: 'file' },
  'Verify Handwritten Signature': { endpoint: '/api/biometric/verify-handwritten-signature', method: 'POST', type: 'file' },
  'Remove Handwritten Biometric Signature': { endpoint: '/api/biometric/remove-handwritten-signature', method: 'POST', type: 'file' },
  'Add Iris Signature': { endpoint: '/api/biometric/add-iris-signature', method: 'POST', type: 'file+field', fieldName: 'iris_data', fieldLabel: 'Iris Data' },
  'Verify Iris Signature': { endpoint: '/api/biometric/verify-iris-signature', method: 'POST', type: 'file+field', fieldName: 'iris_data', fieldLabel: 'Iris Data' },
  'Remove Iris Signature': { endpoint: '/api/biometric/remove-iris-signature', method: 'POST', type: 'file' },
  'Add Palm Signature': { endpoint: '/api/biometric/add-palm-signature', method: 'POST', type: 'file+field', fieldName: 'palm_data', fieldLabel: 'Palm Data' },
  'Verify Palm Signature': { endpoint: '/api/biometric/verify-palm-signature', method: 'POST', type: 'file+field', fieldName: 'palm_data', fieldLabel: 'Palm Data' },
  'Remove Palm Signature': { endpoint: '/api/biometric/remove-palm-signature', method: 'POST', type: 'file' },
  'Add Voice Signature': { endpoint: '/api/biometric/add-voice-signature', method: 'POST', type: 'file+field', fieldName: 'voice_data', fieldLabel: 'Voice Data' },
  'Verify Voice Signature': { endpoint: '/api/biometric/verify-voice-signature', method: 'POST', type: 'file+field', fieldName: 'voice_data', fieldLabel: 'Voice Data' },
  'Remove Voice Signature': { endpoint: '/api/biometric/remove-voice-signature', method: 'POST', type: 'file' },
  'Biometric Signature Validation': { endpoint: '/api/biometric/validation', method: 'POST', type: 'file' },
  'Biometric Signature Timestamp': { endpoint: '/api/biometric/timestamp', method: 'POST', type: 'file' },
  'Biometric Signature Revocation': { endpoint: '/api/biometric/remove-fingerprint', method: 'POST', type: 'file' },
  'Biometric Signature Audit Trail': { endpoint: '/api/biometric/audit-trail', method: 'POST', type: 'file' },
  'Biometric Signature Backup': { endpoint: '/api/biometric/backup', method: 'POST', type: 'file' },
  'Biometric Signature Certificate Binding': { endpoint: '/api/biometric/validation', method: 'POST', type: 'file' },
  'Biometric Signature Encryption': { endpoint: '/api/biometric/lock', method: 'POST', type: 'file+field', fieldName: 'passcode', fieldLabel: 'Encryption Passcode' },
  'Biometric Signature Expiration': { endpoint: '/api/biometric/timestamp', method: 'POST', type: 'file' },
  'Biometric Signature History': { endpoint: '/api/biometric/history', method: 'POST', type: 'file' },
  'Export Biometric Signature': { endpoint: '/api/biometric/export', method: 'POST', type: 'file' },
  'Import Biometric Signature': { endpoint: '/api/biometric/import', method: 'POST', type: 'file' },
  'Extract Biometric Signature': { endpoint: '/api/biometric/extract', method: 'POST', type: 'file' },
  'Lock Biometric Signature': { endpoint: '/api/biometric/lock', method: 'POST', type: 'file+field', fieldName: 'passcode', fieldLabel: 'Passcode' },
  'Unlock Biometric Signature': { endpoint: '/api/biometric/unlock', method: 'POST', type: 'file+field', fieldName: 'passcode', fieldLabel: 'Passcode' },
  'Multi-Biometric Signature': { endpoint: '/api/biometric/add-fingerprint', method: 'POST', type: 'file' },
  'Clone Biometric Signature (Admin)': { endpoint: '/api/biometric/export', method: 'POST', type: 'file' },
  'Replace Biometric Signature': { endpoint: '/api/biometric/replace-fingerprint', method: 'POST', type: 'file+fields', fields: [{name:'old_fingerprint',label:'Old'},{name:'new_fingerprint',label:'New'}] },
  'Restore Biometric Signature': { endpoint: '/api/biometric/restore', method: 'POST', type: 'file' },
  'Reuse Biometric Signature': { endpoint: '/api/biometric/add-fingerprint', method: 'POST', type: 'file' },
};

// Merge all endpoints into one lookup
const TOOL_API_CONFIG = {
  ...PDF_SECURITY_ENDPOINTS,
  ...PDF_SIGNATURE_ENDPOINTS,
  ...AI_SMART_FEATURES_ENDPOINTS,
  ...ACCESSIBILITY_ENDPOINTS,
  ...BIOMETRIC_ENDPOINTS,
};

/**
 * Get the API configuration for a tool by its name.
 * @param {string} toolName - The tool's display name
 * @returns {object|null} - { endpoint, method, type, ... } or null if not found
 */
export function getToolApiConfig(toolName) {
  return TOOL_API_CONFIG[toolName] || null;
}

export { PDF_SECURITY_ENDPOINTS, PDF_SIGNATURE_ENDPOINTS, AI_SMART_FEATURES_ENDPOINTS, ACCESSIBILITY_ENDPOINTS, BIOMETRIC_ENDPOINTS };
export default TOOL_API_CONFIG;
