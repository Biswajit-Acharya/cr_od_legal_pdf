/**
 * @file PDFSecurity.jsx
 * @description PDF Security sub-page. Provides 32 security tools: password protection, unlock, digital signatures, watermark, malware scan, metadata protection, PDF/A validation, and AI risk analysis.
 *
 * Exports:
 *  - PDFSecurityPage, PDFSecurity (card), Header, PDF_TOOLS, plus named icon exports
 */
import React from 'react';
import SlideInText from '../../components/SlideInText';
import ToolWorkspace from '../ToolWorkspace';
import ProtectPDFPage from './ProtectPDFPage';
import DigitalSignatureVerificationPage from './DigitalSignatureVerificationPage';
import DocumentIntegrityVerificationPage from './DocumentIntegrityVerificationPage';
import PDFSecurityScorePage from './PDFSecurityScorePage';
import PDFSecurityPolicyTemplatesPage from './PDFSecurityPolicyTemplatesPage';
import WatermarkProtectionPage from './WatermarkProtectionPage';
import MalwareScanPDFPage from './MalwareScanPDF/MalwareScanPDFPage';
import AISecurityRiskDetectionPage from './AISecurityRiskDetection/AISecurityRiskDetectionPage';
import AISensitiveDataDetectionPage from './AISensitiveDataDetection/AISensitiveDataDetectionPage';
import AIDocumentClassificationPage from './AIDocumentClassification/AIDocumentClassificationPage';
import PDFMetadataProtectionPage from './PDFMetadataProtection/PDFMetadataProtectionPage';
import RemoveJavaScriptPage from './RemoveJavaScript/RemoveJavaScriptPage';
import AtomicServerTimestampingPage from './AtomicServerTimestampingPage';
import PDFSanitizationPage from './PDFSanitization/PDFSanitizationPage';
import RestrictPageExtractionPage from './RestrictPageExtraction/RestrictPageExtractionPage';
import RestrictAccessibilityCopyPage from './RestrictAccessibilityCopy/RestrictAccessibilityCopyPage';
import TrustedCertificatesPage from './TrustedCertificates/TrustedCertificatesPage';
import UnsafeLinkDetectionPage from './UnsafeLinkDetection/UnsafeLinkDetectionPage';
import PDFForensicAnalysisPage from './PDFForensicAnalysis/PDFForensicAnalysisPage';
import EmbeddedMediaDetectionPage from './EmbeddedMediaDetection/EmbeddedMediaDetectionPage';
import PDFVersionSecurityCheckPage from './PDFVersionSecurityCheck/PDFVersionSecurityCheckPage';
import {
  ArrowRight,
  Lock,
  Unlock,
  FileCheck,
  ShieldCheck,
  ShieldAlert,
  Stamp,
  Share2,
  Clock,
  Paperclip,
  Bug,
  Link2Off,
  Award,
  FileCode,
  Bot,
  Sparkles,
  FileSearch,
  Cpu,
  History,
  FileText,
  Wrench,
  Search,
  Film,
  AlertCircle,
  Ban,
  Layers,
  Code2,
  EyeOff,
  CheckSquare,
  Shield,
  FileCheck2,
  Square,
  Eye
} from 'lucide-react';


/* ==========================================================================
   1. PDF SECURITY ICON COMPONENTS (32 SECURITY TOOLS)
   ========================================================================== */

export function ProtectPdfIcon({ className = "w-8 h-8" }) { return <Lock className={className} />; }
export function UnlockPdfIcon({ className = "w-8 h-8" }) { return <Unlock className={className} />; }
export function DigitalSignatureIcon({ className = "w-8 h-8" }) { return <FileCheck className={className} />; }
export function SecurityAuditIcon({ className = "w-8 h-8" }) { return <ShieldCheck className={className} />; }
export function DocumentIntegrityIcon({ className = "w-8 h-8" }) { return <ShieldAlert className={className} />; }
export function WatermarkProtectionIcon({ className = "w-8 h-8" }) { return <Stamp className={className} />; }
export function SecureSharingIcon({ className = "w-8 h-8" }) { return <Share2 className={className} />; }
export function FileExpirationIcon({ className = "w-8 h-8" }) { return <Clock className={className} />; }
export function EmbeddedFileDetectionIcon({ className = "w-8 h-8" }) { return <Paperclip className={className} />; }
export function MalwareScanIcon({ className = "w-8 h-8" }) { return <Bug className={className} />; }
export function UnsafeLinkDetectionIcon({ className = "w-8 h-8" }) { return <Link2Off className={className} />; }
export function PdfSecurityScoreIcon({ className = "w-8 h-8" }) { return <Award className={className} />; }
export function SecurityPolicyIcon({ className = "w-8 h-8" }) { return <FileCode className={className} />; }
export function AiSecurityRiskIcon({ className = "w-8 h-8" }) { return <Bot className={className} />; }
export function AiSensitiveDataIcon({ className = "w-8 h-8" }) { return <Sparkles className={className} />; }
export function AiClassificationIcon({ className = "w-8 h-8" }) { return <FileSearch className={className} />; }
export function AiRecommendationsIcon({ className = "w-8 h-8" }) { return <Cpu className={className} />; }
export function AtomicTimestampingIcon({ className = "w-8 h-8" }) { return <History className={className} />; }
export function MetadataProtectionIcon({ className = "w-8 h-8" }) { return <FileText className={className} />; }
export function PdfSanitizationIcon({ className = "w-8 h-8" }) { return <Wrench className={className} />; }
export function PdfForensicsIcon({ className = "w-8 h-8" }) { return <Search className={className} />; }
export function EmbeddedMediaIcon({ className = "w-8 h-8" }) { return <Film className={className} />; }
export function VersionSecurityCheckIcon({ className = "w-8 h-8" }) { return <AlertCircle className={className} />; }
export function RestrictAccessibilityCopyIcon({ className = "w-8 h-8" }) { return <Ban className={className} />; }
export function RestrictPageExtractionIcon({ className = "w-8 h-8" }) { return <Layers className={className} />; }
export function RemoveJavascriptIcon({ className = "w-8 h-8" }) { return <Code2 className={className} />; }
export function RemoveHiddenDataIcon({ className = "w-8 h-8" }) { return <EyeOff className={className} />; }
export function RemoveFormDataIcon({ className = "w-8 h-8" }) { return <CheckSquare className={className} />; }
export function TrustedCertificatesIcon({ className = "w-8 h-8" }) { return <Shield className={className} />; }
export function PdfAValidationIcon({ className = "w-8 h-8" }) { return <FileCheck2 className={className} />; }
export function BlackoutAreasIcon({ className = "w-8 h-8" }) { return <Square className={className} />; }
export function HideSensitiveInformationIcon({ className = "w-8 h-8" }) { return <Eye className={className} />; }

/**
 * Curated palette of background pastel colors and matching icon text colors
 * assigned cyclically across the tool cards.
 */
const colors = [
  { bg: 'bg-[#FFECEC]', icon: 'text-[#EF4444]' },
  { bg: 'bg-[#E3F2FD]', icon: 'text-[#3B82F6]' },
  { bg: 'bg-[#F3E5F5]', icon: 'text-[#A855F7]' },
  { bg: 'bg-[#FEF2F2]', icon: 'text-[#DC2626]' },
  { bg: 'bg-[#FFF3E0]', icon: 'text-[#F97316]' },
  { bg: 'bg-[#ECFDF5]', icon: 'text-[#10B981]' },
  { bg: 'bg-[#E0F2FE]', icon: 'text-[#0284C7]' },
  { bg: 'bg-[#FEF3C7]', icon: 'text-[#D97706]' },
  { bg: 'bg-[#F5F3FF]', icon: 'text-[#7C3AED]' },
  { bg: 'bg-[#FCE4EC]', icon: 'text-[#EC4899]' }
];

export const PDF_TOOLS = [
  {
    id: 'protect-pdf',
    name: 'Protect PDF',
    description: 'Encrypt PDF files with strong password protection and permission controls.',
    icon: ProtectPdfIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'unlock-pdf',
    name: 'Unlock PDF',
    description: 'Remove passwords and unlock restricted PDF permissions securely.',
    icon: UnlockPdfIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'digital-signature-verification',
    name: 'Digital Signature Verification',
    description: 'Verify authenticity, integrity, and signer certificates of signed PDFs.',
    icon: DigitalSignatureIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'security-audit-report',
    name: 'Security Audit Report',
    description: 'Generate comprehensive PDF security compliance and vulnerability reports.',
    icon: SecurityAuditIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'document-integrity-verification',
    name: 'Document Integrity Verification',
    description: 'Validate cryptographic hashes to ensure document has not been tampered with.',
    icon: DocumentIntegrityIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'watermark-protection',
    name: 'Watermark Protection',
    description: 'Add custom text, image, or dynamic anti-leak security watermarks.',
    icon: WatermarkProtectionIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'secure-pdf-sharing',
    name: 'Secure PDF Sharing',
    description: 'Share encrypted, view-only PDFs with restricted download and access controls.',
    icon: SecureSharingIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'file-expiration',
    name: 'File Expiration',
    description: 'Set self-destruct timers and access expiry dates on shared PDF files.',
    icon: FileExpirationIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'embedded-file-detection',
    name: 'Embedded File Detection',
    description: 'Scan and inspect hidden attachments or embedded files inside PDFs.',
    icon: EmbeddedFileDetectionIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'malware-scan-pdf',
    name: 'Malware Scan PDF',
    description: 'Scan PDFs for malicious scripts, exploits, and hidden payload viruses.',
    icon: MalwareScanIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'unsafe-link-detection',
    name: 'Unsafe Link Detection',
    description: 'Identify phishing URLs, suspicious hyperlinks, and tracking web links.',
    icon: UnsafeLinkDetectionIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'pdf-security-score',
    name: 'PDF Security Score',
    description: 'Calculate overall document security rating based on encryption and vulnerabilities.',
    icon: PdfSecurityScoreIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'pdf-security-policy-templates',
    name: 'PDF Security Policy Templates',
    description: 'Apply enterprise security policies and compliance rule presets.',
    icon: SecurityPolicyIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'ai-security-risk-detection',
    name: 'AI Security Risk Detection',
    description: 'AI-driven analysis to detect potential security threats and data breaches.',
    icon: AiSecurityRiskIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'ai-sensitive-data-detection',
    name: 'AI Sensitive Data Detection',
    description: 'Automatically detect PII, SSN, credit cards, and confidential data.',
    icon: AiSensitiveDataIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'ai-document-classification',
    name: 'AI Document Classification',
    description: 'Categorize document confidentiality levels automatically using AI.',
    icon: AiClassificationIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'ai-security-recommendations',
    name: 'AI Security Recommendations',
    description: 'Get smart AI suggestions to harden document privacy and safety.',
    icon: AiRecommendationsIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'atomic-server-timestamping',
    name: 'Atomic Server Timestamping',
    description: 'Apply RFC 3161 compliant cryptographic server timestamps to PDFs.',
    icon: AtomicTimestampingIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'pdf-metadata-protection',
    name: 'PDF Metadata Protection',
    description: 'Strip or sanitize hidden EXIF, author details, and creation metadata.',
    icon: MetadataProtectionIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'pdf-sanitization',
    name: 'PDF Sanitization',
    description: 'Deep clean hidden structures, comments, bookmarks, and revision logs.',
    icon: PdfSanitizationIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'pdf-forensic-analysis',
    name: 'PDF Forensic Analysis',
    description: 'Perform detailed forensic inspection of PDF structure and revision history.',
    icon: PdfForensicsIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'embedded-media-detection',
    name: 'Embedded Media Detection',
    description: 'Detect and extract embedded audio, video, and rich media objects.',
    icon: EmbeddedMediaIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'pdf-version-security-check',
    name: 'PDF Version Security Check',
    description: 'Analyze PDF format version risks and specification compliance.',
    icon: VersionSecurityCheckIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'restrict-accessibility-copy',
    name: 'Restrict Accessibility Copy',
    description: 'Prevent unauthorized copying of text, images, and content.',
    icon: RestrictAccessibilityCopyIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'restrict-page-extraction',
    name: 'Restrict Page Extraction',
    description: 'Lock page extraction, splitting, and merging actions on PDF.',
    icon: RestrictPageExtractionIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'remove-javascript',
    name: 'Remove JavaScript',
    description: 'Strip dangerous embedded JavaScript actions and auto-executing scripts.',
    icon: RemoveJavascriptIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'remove-hidden-data',
    name: 'Remove Hidden Data',
    description: 'Clean invisible layers, annotations, and hidden document metadata.',
    icon: RemoveHiddenDataIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'remove-form-data',
    name: 'Remove Form Data',
    description: 'Purge form fields, user input history, and interactive form elements.',
    icon: RemoveFormDataIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'trusted-certificates',
    name: 'Trusted Certificates',
    description: 'Manage and validate digital certificate chains and CA roots.',
    icon: TrustedCertificatesIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'pdf-a-validation',
    name: 'PDF/A Validation',
    description: 'Check strict PDF/A archivability and long-term compliance standards.',
    icon: PdfAValidationIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'blackout-areas',
    name: 'Blackout Areas',
    description: 'Redact sensitive document areas with permanent blackout boxes.',
    icon: BlackoutAreasIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'hide-sensitive-information',
    name: 'Hide Sensitive Information',
    description: 'Obfuscate sensitive content, text phrases, and confidential data.',
    icon: HideSensitiveInformationIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  }
];

/* ==========================================================================
   2. HEADER COMPONENT WITH FLOATING BRANDING & DECORATIVE ANIMATIONS
   ========================================================================== */

/**
 * Header Component
 * Renders top section with brand logos, page heading ("Convert to PDF"), 
 * floating document icons, and decorative background dashed arc.
 */


/* ==========================================================================
   3. ORGANIZEPDF TOOL CARD COMPONENT
   ========================================================================== */

/**
 * Organizepdf Component
 * Renders individual PDF conversion tool card with hover border animation, document badge, and description.
 *
 * @param {Object} props - Component properties
 * @param {Object} props.tool - Tool data object (name, description, icon, bgColor, iconColor)
 * @param {number} [props.index=0] - Card array index used for staggered row slide animations
 * @param {Function} [props.onClick] - Click event handler callback
 */
/* ==========================================================================
   2. HEADER COMPONENT
   ========================================================================== */

export function Header() {
  /** Reusable floating PDF-style document badge icon inside header */
  const FileIcon = ({ bg, icon = null, rotate = 0, size = 34, floatClass = 'animate-float-1' }) => {
    const w = size;
    const h = size * 1.22;
    return (
      <div className={floatClass}>
        <div
          style={{ transform: `rotate(${rotate}deg)`, width: w, height: h, filter: 'drop-shadow(0 6px 12px rgba(0,0,0,0.15))' }}
          className="hover:scale-115 transition-transform duration-300 cursor-default flex-shrink-0 scale-[0.50] sm:scale-100 origin-center"
        >
          <svg width={w} height={h} viewBox="-7 -7 70 82" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M4 0h36l16 16v48a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V4a4 4 0 0 1 4-4z"
              fill="white"
              stroke="white"
              strokeWidth="12"
              strokeLinejoin="round"
            />
            <path d="M4 0h36l16 16v48a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V4a4 4 0 0 1 4-4z" fill={bg} />
            <path d="M40 0l16 16H44a4 4 0 0 1-4-4V0z" fill="rgba(0,0,0,0.2)" />
            {icon}
          </svg>
        </div>
      </div>
    );
  };

  return (
    <header className="w-full relative pt-1 sm:pt-2 pb-2 sm:pb-3 mb-2 sm:mb-3 select-none">

      {/* Animated background floating dots along the arc */}
      <div className="absolute hidden sm:block left-[13%] top-[32%] w-3 h-3 rounded-full bg-blue-500 shadow pointer-events-none z-10 animate-float-3" />
      <div className="absolute hidden sm:block left-[35%] top-[62%] w-2.5 h-2.5 rounded-full bg-blue-400 shadow-sm pointer-events-none z-10 animate-float-1" />
      <div className="absolute hidden sm:block right-[34%] top-[20%] w-3 h-3 rounded-full bg-emerald-400 shadow pointer-events-none z-10 animate-float-5" />
      <div className="absolute hidden sm:block right-[19%] top-[58%] w-2.5 h-2.5 rounded-full bg-red-400 shadow-sm pointer-events-none z-10 animate-float-2" />
      <div className="absolute hidden sm:block right-[37%] top-[74%] w-2 h-2 rounded-full bg-orange-400 shadow-sm pointer-events-none z-10 animate-float-4" />

      {/* Floating file badges around header */}
      <div className="absolute flex left-0 sm:left-4 md:left-[17%]" style={{ top: '45%', zIndex: 15 }}>
        <FileIcon bg="#9333EA" rotate={-13} size={32} floatClass="animate-float-1"
          icon={
            <>
              <circle cx="18" cy="30" r="3.5" fill="rgba(255,255,255,0.7)" />
              <path d="M6 48 L18 35 L27 43 L36 33 L50 47 L50 54 L6 54Z" fill="rgba(255,255,255,0.55)" />
            </>
          }
        />
      </div>

      <div className="absolute flex left-6 sm:left-20 md:left-[26%]" style={{ top: '4%', zIndex: 15 }}>
        <FileIcon bg="#2563EB" rotate={7} size={38} floatClass="animate-float-2"
          icon={
            <text x="28" y="50" textAnchor="middle" fontFamily="Arial Black,sans-serif" fontWeight="900" fontSize="20" fill="white" opacity="0.95">AI</text>
          }
        />
      </div>

      <div className="absolute flex right-6 sm:right-20 md:right-[26%]" style={{ top: '4%', zIndex: 15 }}>
        <FileIcon bg="#16A34A" rotate={-7} size={38} floatClass="animate-float-4"
          icon={
            <text x="28" y="50" textAnchor="middle" fontFamily="Arial Black,sans-serif" fontWeight="900" fontSize="20" fill="white" opacity="0.95">X</text>
          }
        />
      </div>

      <div className="absolute flex right-0 sm:right-4 md:right-[20%]" style={{ top: '42%', zIndex: 15 }}>
        <FileIcon bg="#EA580C" rotate={9} size={32} floatClass="animate-float-5"
          icon={
            <text x="28" y="50" textAnchor="middle" fontFamily="Arial Black,sans-serif" fontWeight="900" fontSize="20" fill="white" opacity="0.95">P</text>
          }
        />
      </div>

      <div className="absolute hidden lg:flex" style={{ right: '15%', top: '56%', zIndex: 15 }}>
        <FileIcon bg="#64748B" rotate={-5} size={30} floatClass="animate-float-6"
          icon={
            <text x="28" y="50" textAnchor="middle" fontFamily="Arial Black,sans-serif" fontWeight="900" fontSize="12" fill="white" letterSpacing="0.5">ZIP</text>
          }
        />
      </div>

      {/* Main header row: Title and Tagline */}
      <div className="flex items-center justify-center w-full relative z-20">
        <div className="flex-1 text-center flex flex-col items-center justify-center min-w-0 pt-1 sm:pt-2 md:pt-3 px-2">
          <h1 className="text-xl sm:text-3xl md:text-4xl lg:text-5xl font-black text-[#1e2a52] tracking-tight leading-tight break-words pb-1">
            <SlideInText text="PDF Security & Protection" />
          </h1>
          <p className="mt-3 sm:mt-4 text-xs sm:text-sm md:text-base font-semibold text-slate-700 max-w-2xl mx-auto leading-relaxed">
            Protect your PDFs with passwords, encryption, redaction, and digital security tools.
          </p>
        </div>
      </div>
    </header>
  );
}

export function PDFSecurity({ tool, index = 0, onClick }) {
  if (!tool) return null;
  const IconComponent = tool.icon;
  const isElement = React.isValidElement(tool.icon);
  const toolName = tool.name || tool.title || 'PDF Tool';
  const toolBg = tool.bgColor || tool.bg || '#FFECEC';
  const toolIconColor = tool.iconColor || tool.color || 'text-blue-600';

  const rowIndex = Math.floor(index / 2);
  const delayMs = rowIndex * 120;
  const slideAnimation = rowIndex % 2 === 0 ? 'animate-card-slide-left' : 'animate-card-slide-right';

  const fillHex = (typeof toolBg === 'string' ? toolBg.match(/#[A-Fa-f0-9]{6}/)?.[0] : null) || '#E0F2FE';

  return (
    <div
      onClick={() => onClick?.(tool)}
      style={{ animationDelay: `${delayMs}ms` }}
      className={`${slideAnimation} bg-white rounded-[16px] sm:rounded-[22px] p-2.5 sm:p-4 border border-slate-200/80 shadow-[0_4px_20px_rgba(0,0,0,0.03)] hover:shadow-[0_12px_28px_rgba(37,99,235,0.15)] hover:-translate-y-1 transition-all duration-300 ease-out cursor-pointer flex items-center gap-2 sm:gap-4 group select-none relative overflow-hidden h-[98px] sm:h-[112px] z-10 hover:z-30`}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.(tool);
        }
      }}
    >
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 overflow-visible">
        <rect
          x="1.5"
          y="1.5"
          width="calc(100% - 3px)"
          height="calc(100% - 3px)"
          rx="18"
          fill="none"
          stroke="#2563EB"
          strokeWidth="2"
          pathLength="100"
          className="animate-draw-line"
        />
      </svg>

      <div className="w-8 h-10 sm:w-13 sm:h-15 shrink-0 relative flex items-center justify-center group-hover:scale-108 transition-transform duration-200 filter drop-shadow-[0_4px_10px_rgba(0,0,0,0.06)] mt-0.5">
        <svg className="absolute inset-0 w-full h-full" viewBox="-4 -4 56 66" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M4 0h30l14 14v40a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V4a4 4 0 0 1 4-4z"
            fill="white"
            stroke="white"
            strokeWidth="8"
            strokeLinejoin="round"
          />
          <path d="M4 0h30l14 14v40a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4V4a4 4 0 0 1 4-4z" fill={fillHex} />
          <path d="M34 0l14 14H38a4 4 0 0 1-4-4V0z" fill="rgba(0,0,0,0.18)" />
        </svg>
        <div className={`relative z-10 ${toolIconColor}`}>
          {isElement ? (
            tool.icon
          ) : typeof IconComponent === 'function' || typeof IconComponent === 'object' ? (
            <IconComponent className="w-5 h-5 sm:w-7 sm:h-7" />
          ) : null}
        </div>
      </div>

      <div className="flex flex-col text-left min-w-0 relative z-0 flex-1">
        <h3 className="text-[11.5px] sm:text-base font-bold text-slate-900 line-clamp-2 leading-tight group-hover:text-blue-600 transition-colors">
          {toolName}
        </h3>
        <p className="text-[10px] sm:text-xs text-slate-500 font-normal leading-tight line-clamp-2 mt-0.5 sm:mt-1">
          {tool.description}
        </p>

        <div className="max-h-0 opacity-0 group-hover:max-h-8 group-hover:opacity-100 group-hover:mt-1.5 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] overflow-hidden flex items-center gap-1.5 text-xs sm:text-sm font-bold text-blue-600">
          <span>Use Feature</span>
          <ArrowRight className="w-3.5 h-3.5 sm:w-4 sm:h-4 group-hover:translate-x-1.5 transition-transform duration-200" />
        </div>
      </div>
    </div>
  );
}

export function PDFSecurityPage({ onBack, searchQuery = "" }) {
    const [selectedTool, setSelectedTool] = React.useState(() => {
    const hashParts = window.location.hash.replace('#', '').split('/');
    if (hashParts.length > 1) {
      const toolId = hashParts[1];
      return PDF_TOOLS.find(t => t.id === toolId) || null;
    }
    return null;
  });

  React.useEffect(() => {
    if (selectedTool) {
      window.history.pushState({ toolOpen: true }, '', `${window.location.hash.split('/')[0]}/${selectedTool.id}`);
      window.scrollTo(0, 0);
    }
  }, [selectedTool]);

  React.useEffect(() => {
    const handlePopState = () => {
      setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  if (selectedTool) {
    if (selectedTool.id === 'protect-pdf') {
      return <ProtectPDFPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'pdf-metadata-protection') {
      return <PDFMetadataProtectionPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'atomic-server-timestamping') {
      return <AtomicServerTimestampingPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'pdf-sanitization') {
      return <PDFSanitizationPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'pdf-forensic-analysis') {
      return <PDFForensicAnalysisPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'embedded-media-detection') {
      return <EmbeddedMediaDetectionPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'pdf-version-security-check') {
      return <PDFVersionSecurityCheckPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'restrict-accessibility-copy') {
      return <RestrictAccessibilityCopyPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'trusted-certificates') {
      return <TrustedCertificatesPage tool={selectedTool} onBack={() => setSelectedTool(null)} />;
    }
    if (selectedTool.id === 'remove-javascript') {
      return <RemoveJavaScriptPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'digital-signature-verification') {
      return <DigitalSignatureVerificationPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'document-integrity-verification') {
      return <DocumentIntegrityVerificationPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'pdf-security-score') {
      return <PDFSecurityScorePage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'pdf-security-policy-templates') {
      return <PDFSecurityPolicyTemplatesPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'watermark-protection') {
      return <WatermarkProtectionPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'malware-scan-pdf') {
      return <MalwareScanPDFPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'unsafe-link-detection') {
      return <UnsafeLinkDetectionPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
        if (selectedTool.id === 'ai-security-risk-detection') {
      return <AISecurityRiskDetectionPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'ai-sensitive-data-detection') {
      return <AISensitiveDataDetectionPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'ai-document-classification') {
      return <AIDocumentClassificationPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'restrict-page-extraction') {
      return <RestrictPageExtractionPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    if (selectedTool.id === 'ai-security-recommendations') {
      return <AISecurityRiskDetectionPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
    }
    return <ToolWorkspace tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
  }

    return (
    <div className="flex-1 flex flex-col w-full relative pt-11 sm:pt-4">
      {onBack && (
        <button onClick={onBack} 
          className="absolute top-1.5 left-3 sm:top-5 sm:left-6 md:left-10 z-50 text-[#1e2a52] hover:text-blue-950 font-bold flex items-center gap-1.5 sm:gap-2 bg-white/90 px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-full shadow-sm backdrop-blur-md border border-slate-200/90 transition-all hover:shadow-md hover:scale-105 cursor-pointer text-xs sm:text-sm"
        >
          <svg className="w-4 h-4 text-[#1e2a52]" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
          </svg>
          <span>Back</span>
        </button>
      )}
      <Header />
      <div className="flex-1 flex flex-col w-full max-w-[1720px] mx-auto px-4 sm:px-6 md:px-10 py-4 overflow-x-hidden">
        <main className="flex-1 pt-1 pb-4">
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-2.5 gap-y-3 sm:gap-6 md:gap-8">
            {PDF_TOOLS.filter(tool => {
              const q = (searchQuery || "").trim().toLowerCase();
              if (!q) return true;
              const name = (tool.name || tool.title || "").toLowerCase(); return name.includes(q);
            }).map((tool, idx) => (
              <PDFSecurity
                key={tool.id}
                tool={tool}
                index={idx}
                onClick={(t) => setSelectedTool(t)}
              />
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}

