/**
 * @file PDFSignature.jsx
 * @description PDF Signature sub-page for CR OD Legal PDF.
 *
 * Provides 45 digital and electronic signature tools including:
 * e-signature, USB token signing, PKI, cloud signatures, biometric
 * signatures, QR verification, bulk signing, and compliance reports.
 *
 * Exports:
 *  - Named icon wrapper functions (used in PDF_TOOLS data array)
 *  - `PDFSignature`     â€” Individual tool card component
 *  - `Header`           â€” Hero section with animated floating file badges
 *  - `PDF_TOOLS`        â€” Array of 45 signature tool definitions
 *  - `PDFSignaturePage` â€” Full page component rendered by App.jsx
 */
import React from 'react';
import SlideInText from '../../components/SlideInText';
import ToolWorkspace from '../ToolWorkspace';
import PDFSignPage from './PDFSignPage';
import DigitalSignPage from './DigitalSignPage';
import ESignPage from './ESignPage';
import USBTokenSignaturePage from './USBTokenSignaturePage';
import {
  ArrowRight,
  PenTool,
  FileCheck,
  Edit3,
  Usb,
  Key,
  Cloud,
  Globe,
  Repeat,
  Users,
  ListOrdered,
  Download,
  Upload,
  ShieldAlert,
  Layout,
  EyeOff,
  Square,
  Wand2,
  Palette,
  FileCode,
  CheckCircle2,
  History,
  FileSearch,
  Bell,
  Hourglass,
  XCircle,
  UserCheck,
  Files,
  FolderCheck,
  Lock,
  ShieldCheck,
  Timer,
  WifiOff,
  QrCode,
  ScanFace,
  Smartphone,
  Fingerprint,
  FileBadge,
  CheckSquare,
  GitCompare,
  FileSpreadsheet,
  UserCog,
  LayoutDashboard,
  UserPlus,
  MapPin,
  HelpCircle
} from 'lucide-react';

/* ==========================================================================
   1. PDF SIGNATURE ICON COMPONENTS (45 SIGNATURE TOOLS)
   ========================================================================== */

export function PdfSignIcon({ className = "w-8 h-8" }) { return <PenTool className={className} />; }
export function DigitalSignIcon({ className = "w-8 h-8" }) { return <FileCheck className={className} />; }
export function ESignIcon({ className = "w-8 h-8" }) { return <Edit3 className={className} />; }
export function UsbTokenSignatureIcon({ className = "w-8 h-8" }) { return <Usb className={className} />; }
export function PkiSignatureIcon({ className = "w-8 h-8" }) { return <Key className={className} />; }
export function CloudSignatureIcon({ className = "w-8 h-8" }) { return <Cloud className={className} />; }
export function RemoteSignatureIcon({ className = "w-8 h-8" }) { return <Globe className={className} />; }
export function ReuseSignatureIcon({ className = "w-8 h-8" }) { return <Repeat className={className} />; }
export function MultiSignerWorkflowIcon({ className = "w-8 h-8" }) { return <Users className={className} />; }
export function SigningOrderIcon({ className = "w-8 h-8" }) { return <ListOrdered className={className} />; }
export function CertificateImportIcon({ className = "w-8 h-8" }) { return <Download className={className} />; }
export function CertificateExportIcon({ className = "w-8 h-8" }) { return <Upload className={className} />; }
export function CertificateRevocationCheckIcon({ className = "w-8 h-8" }) { return <ShieldAlert className={className} />; }
export function VisibleSignatureDesignerIcon({ className = "w-8 h-8" }) { return <Layout className={className} />; }
export function InvisibleDigitalSignatureIcon({ className = "w-8 h-8" }) { return <EyeOff className={className} />; }
export function SignatureFieldCreatorIcon({ className = "w-8 h-8" }) { return <Square className={className} />; }
export function AutoSignaturePlacementIcon({ className = "w-8 h-8" }) { return <Wand2 className={className} />; }
export function SignatureAppearanceTemplatesIcon({ className = "w-8 h-8" }) { return <Palette className={className} />; }
export function InitialSignatureIcon({ className = "w-8 h-8" }) { return <FileCode className={className} />; }
export function SignatureValidationIcon({ className = "w-8 h-8" }) { return <CheckCircle2 className={className} />; }
export function SignatureHistoryIcon({ className = "w-8 h-8" }) { return <History className={className} />; }
export function SignatureAuditTrailIcon({ className = "w-8 h-8" }) { return <FileSearch className={className} />; }
export function SignatureReminderIcon({ className = "w-8 h-8" }) { return <Bell className={className} />; }
export function SignatureExpirationIcon({ className = "w-8 h-8" }) { return <Hourglass className={className} />; }
export function RejectSignatureRequestIcon({ className = "w-8 h-8" }) { return <XCircle className={className} />; }
export function DelegatedSigningIcon({ className = "w-8 h-8" }) { return <UserCheck className={className} />; }
export function BulkSignatureIcon({ className = "w-8 h-8" }) { return <Files className={className} />; }
export function BatchSignatureValidationIcon({ className = "w-8 h-8" }) { return <FolderCheck className={className} />; }
export function SignatureLockDocumentIcon({ className = "w-8 h-8" }) { return <Lock className={className} />; }
export function LtvValidationIcon({ className = "w-8 h-8" }) { return <ShieldCheck className={className} />; }
export function TimestampSignatureIcon({ className = "w-8 h-8" }) { return <Timer className={className} />; }
export function OfflineSignatureSupportIcon({ className = "w-8 h-8" }) { return <WifiOff className={className} />; }
export function QrCodeSignatureVerificationIcon({ className = "w-8 h-8" }) { return <QrCode className={className} />; }
export function FaceVerificationIcon({ className = "w-8 h-8" }) { return <ScanFace className={className} />; }
export function OtpVerificationIcon({ className = "w-8 h-8" }) { return <Smartphone className={className} />; }
export function BiometricSignatureIcon({ className = "w-8 h-8" }) { return <Fingerprint className={className} />; }
export function CertificateViewerIcon({ className = "w-8 h-8" }) { return <FileBadge className={className} />; }
export function SignatureComplianceCheckIcon({ className = "w-8 h-8" }) { return <CheckSquare className={className} />; }
export function SignatureComparisonIcon({ className = "w-8 h-8" }) { return <GitCompare className={className} />; }
export function SignatureEvidenceReportIcon({ className = "w-8 h-8" }) { return <FileSpreadsheet className={className} />; }
export function SignaturePermissionManagerIcon({ className = "w-8 h-8" }) { return <UserCog className={className} />; }
export function SigningStatusDashboardIcon({ className = "w-8 h-8" }) { return <LayoutDashboard className={className} />; }
export function WitnessSignatureIcon({ className = "w-8 h-8" }) { return <UserPlus className={className} />; }
export function SignatureLocationIcon({ className = "w-8 h-8" }) { return <MapPin className={className} />; }
export function SignatureReasonIcon({ className = "w-8 h-8" }) { return <HelpCircle className={className} />; }

/* ==========================================================================
   2. PDF TOOLS CONFIGURATION DATA
   ========================================================================== */

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
    id: 'pdf-sign',
    name: 'PDF Sign',
    description: 'Sign PDF documents with your handwritten, typed, or drawn electronic signature.',
    icon: PdfSignIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'digital-sign',
    name: 'Digital Sign',
    description: 'Apply cryptographically secure digital signatures backed by PKI certificates.',
    icon: DigitalSignIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'e-sign',
    name: 'e-Sign',
    description: 'Legally binding electronic signatures for quick online document approvals.',
    icon: ESignIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'usb-token-signature',
    name: 'USB Token Signature',
    description: 'Sign documents using hardware USB tokens and cryptographic security dongles.',
    icon: UsbTokenSignatureIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'pki-signature',
    name: 'PKI Signature',
    description: 'Public Key Infrastructure signatures ensuring maximum integrity and legal validity.',
    icon: PkiSignatureIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'cloud-signature',
    name: 'Cloud Signature',
    description: 'Access and sign documents via secure cloud HSM digital signature providers.',
    icon: CloudSignatureIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'remote-signature',
    name: 'Remote Signature',
    description: 'Authorize document signatures remotely from any browser or mobile device.',
    icon: RemoteSignatureIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'reuse-signature',
    name: 'Reuse Signature',
    description: 'Save and reuse your pre-approved signature assets for faster signing workflows.',
    icon: ReuseSignatureIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'multi-signer-workflow',
    name: 'Multi-signer Workflow',
    description: 'Coordinate multi-party signing processes with real-time status tracking.',
    icon: MultiSignerWorkflowIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'signing-order',
    name: 'Signing Order',
    description: 'Set sequential or parallel routing rules for multiple document signers.',
    icon: SigningOrderIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'certificate-import',
    name: 'Certificate Import',
    description: 'Import PFX, P12, or PEM digital certificate files into your secure vault.',
    icon: CertificateImportIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'certificate-export',
    name: 'Certificate Export',
    description: 'Export public key certificates for recipient verification and key exchange.',
    icon: CertificateExportIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'certificate-revocation-check',
    name: 'Certificate Revocation Check',
    description: 'Verify certificate validity against real-time CRL and OCSP responder lists.',
    icon: CertificateRevocationCheckIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'visible-signature-designer',
    name: 'Visible Signature Designer',
    description: 'Customize signature visual stamps with logos, dates, titles, and text.',
    icon: VisibleSignatureDesignerIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'invisible-digital-signature',
    name: 'Invisible Digital Signature',
    description: 'Cryptographically seal documents without displaying visual signature marks.',
    icon: InvisibleDigitalSignatureIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'signature-field-creator',
    name: 'Signature Field Creator',
    description: 'Add interactive signature, initial, and date fields anywhere in PDFs.',
    icon: SignatureFieldCreatorIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'auto-signature-placement',
    name: 'Auto Signature Placement',
    description: 'Automatically detect anchor tags and place signature blocks instantly.',
    icon: AutoSignaturePlacementIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'signature-appearance-templates',
    name: 'Signature Appearance Templates',
    description: 'Select and manage professional styling templates for signature stamps.',
    icon: SignatureAppearanceTemplatesIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'initial-signature',
    name: 'Initial Signature',
    description: 'Add initial marks across all pages of long contracts for page consent.',
    icon: InitialSignatureIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'signature-validation',
    name: 'Signature Validation',
    description: 'Verify the cryptographic authenticity and integrity of signed PDFs.',
    icon: SignatureValidationIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'signature-history',
    name: 'Signature History',
    description: 'View complete historical logs of all signed documents and signers.',
    icon: SignatureHistoryIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'signature-audit-trail',
    name: 'Signature Audit Trail',
    description: 'Generate tamper-evident audit logs with IP addresses, timestamps, and IDs.',
    icon: SignatureAuditTrailIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'signature-reminder',
    name: 'Signature Reminder',
    description: 'Automate email and notification reminders for pending document signers.',
    icon: SignatureReminderIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'signature-expiration',
    name: 'Signature Expiration',
    description: 'Set custom expiration deadlines on pending signature request links.',
    icon: SignatureExpirationIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'reject-signature-request',
    name: 'Reject Signature Request',
    description: 'Decline signing requests with mandatory rejection reason notes.',
    icon: RejectSignatureRequestIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'delegated-signing',
    name: 'Delegated Signing',
    description: 'Reassign signing authority to authorized proxy representatives.',
    icon: DelegatedSigningIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'bulk-signature',
    name: 'Bulk Signature',
    description: 'Sign hundreds of PDF documents simultaneously with a single action.',
    icon: BulkSignatureIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'batch-signature-validation',
    name: 'Batch Signature Validation',
    description: 'Validate signatures across entire folders of PDF files in batch mode.',
    icon: BatchSignatureValidationIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'signature-lock-document',
    name: 'Signature Lock Document',
    description: 'Lock document editing and formatting permanently after final signature.',
    icon: SignatureLockDocumentIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'long-term-signature-validation',
    name: 'Long-Term Signature Validation (LTV)',
    description: 'Embed revocation state data for long-term validation over decades.',
    icon: LtvValidationIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'timestamp-signature',
    name: 'Timestamp Signature',
    description: 'Add RFC 3161 compliant trusted time-stamps from certified TSAs.',
    icon: TimestampSignatureIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'offline-signature-support',
    name: 'Offline Signature Support',
    description: 'Sign documents without an active internet connection using local keys.',
    icon: OfflineSignatureSupportIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'qr-code-signature-verification',
    name: 'QR Code Signature Verification',
    description: 'Embed scannable QR codes for instant offline verification of signed prints.',
    icon: QrCodeSignatureVerificationIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'face-verification-before-signing',
    name: 'Face Verification Before Signing',
    description: 'Require biometric facial scanning authentication before releasing signature.',
    icon: FaceVerificationIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'otp-verification-before-signing',
    name: 'OTP Verification Before Signing',
    description: 'Send multi-factor SMS or Email OTP codes to verify signer identity.',
    icon: OtpVerificationIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'biometric-signature',
    name: 'Biometric Signature',
    description: 'Capture pen speed, pressure, and biometric parameters during signing.',
    icon: BiometricSignatureIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'signature-certificate-viewer',
    name: 'Signature Certificate Viewer',
    description: 'Inspect detailed X.509 certificate chains, key usage, and issuer info.',
    icon: CertificateViewerIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'signature-compliance-check',
    name: 'Signature Compliance Check',
    description: 'Verify compliance with eIDAS, HIPAA, 21 CFR Part 11, and ESIGN standards.',
    icon: SignatureComplianceCheckIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'signature-comparison',
    name: 'Signature Comparison',
    description: 'Compare signature changes and revisions across document versions.',
    icon: SignatureComparisonIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'signature-evidence-report',
    name: 'Signature Evidence Report',
    description: 'Download comprehensive legal evidence packages for court admissibility.',
    icon: SignatureEvidenceReportIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'signature-permission-manager',
    name: 'Signature Permission Manager',
    description: 'Configure role-based signing rights and administrative permissions.',
    icon: SignaturePermissionManagerIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'signing-status-dashboard',
    name: 'Signing Status Dashboard',
    description: 'Monitor real-time status of sent, signed, and pending requests.',
    icon: SigningStatusDashboardIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'witness-signature',
    name: 'Witness Signature',
    description: 'Add neutral third-party witness signature fields to legal contracts.',
    icon: WitnessSignatureIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'signature-location',
    name: 'Signature Location',
    description: 'Record geotagged physical location coordinates at time of signature.',
    icon: SignatureLocationIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'signature-reason',
    name: 'Signature Reason',
    description: 'Attach custom legally binding intent and signing reason statements.',
    icon: SignatureReasonIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  }
];

/* ==========================================================================
   3. HEADER COMPONENT WITH FLOATING BRANDING & DECORATIVE ANIMATIONS
   ========================================================================== */

/**
 * Header Component
 * Renders top section with brand logos, page heading ("PDF Signature"), 
 * floating document icons, and decorative background dashed arc.
 */


/* ==========================================================================
   4. ORGANIZEPDF TOOL CARD COMPONENT
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
            <SlideInText text="PDF Signatures & Forms" />
          </h1>
          <p className="mt-3 sm:mt-4 text-xs sm:text-sm md:text-base font-semibold text-slate-700 max-w-2xl mx-auto leading-relaxed">
            Sign PDFs electronically, create digital signatures, and fill out interactive PDF forms.
          </p>
        </div>
      </div>
    </header>
  );
}

export function PDFSignature({ tool, index = 0, onClick }) {
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

/**
 * PDFSignaturePage
 * Top-level page component for the PDF Signature category.
 * Manages which specific tool is open in the ToolWorkspace.
 *
 * State:
 *  @state {Object|null} selectedTool - The currently open sub-tool, or null if showing the grid
 *
 * History management:
 *  - Pushes `{ toolOpen: true }` entry when a tool is selected, so the
 *    browser Back button dismisses the workspace instead of leaving the page.
 *  - The `popstate` listener resets `selectedTool` to null on Back navigation.
 *
 * @component
 * @param {Function} props.onBack               - Callback to navigate back to the home dashboard
 * @param {string}   [props.searchQuery=""]     - Optional search filter passed down to filter the tool grid
 * @returns {JSX.Element} Hero header + responsive tool card grid (or ToolWorkspace if a tool is open)
 */
export function PDFSignaturePage({ onBack, searchQuery = "" }) {
  const [selectedTool, setSelectedTool] = React.useState(() => {
    const hashParts = window.location.hash.replace('#', '').split('/');
    if (hashParts.length > 1) {
      const toolId = hashParts[1];
      return PDF_TOOLS.find(t => t.id === toolId) || null;
    }
    return null;
  }); // Currently open tool in workspace

  // Push a history entry when a tool opens so Back closes it (not the whole page)
  React.useEffect(() => {
    if (selectedTool) {
      window.history.pushState({ toolOpen: true }, '', `${window.location.hash.split('/')[0]}/${selectedTool.id}`);
      window.scrollTo(0, 0);
    }
  }, [selectedTool]);

  // Listen for browser Back navigation and close the tool workspace
  React.useEffect(() => {
    const handlePopState = () => {
      setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState); // Cleanup on unmount
  }, []);

  // Show ToolWorkspace when a tool card is clicked
  if (selectedTool) {
    const handleBack = () => {
      setSelectedTool(null);
      const parentHash = window.location.hash.split('/')[0];
      window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash);
      window.scrollTo(0, 0);
    };

    if (selectedTool.id === 'pdf-sign') {
      return <PDFSignPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'digital-sign') {
      return <DigitalSignPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'e-sign') {
      return <ESignPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'usb-token-signature') {
      return <USBTokenSignaturePage tool={selectedTool} onBack={handleBack} />;
    }
    return <ToolWorkspace tool={selectedTool} onBack={handleBack} />;
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
              <PDFSignature
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
