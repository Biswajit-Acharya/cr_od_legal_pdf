/**
 * @file PDFCopyrightProtection.jsx
 * @description PDF Copyright Protection sub-page. Provides 32 tools: copyright registration, XMP metadata, watermarking, DRM, ownership certificates, DMCA notices, and content authenticity.
 *
 * Exports:
 *  - PDFCopyrightProtectionPage, PDFCopyrightCard (card), Header, PDF_TOOLS
 */
import React from 'react';
import SlideInText from '../../components/SlideInText';
import ToolWorkspace from '../ToolWorkspace';
import AIContentSimilarityCheckPage from './AIContentSimilarityCheckPage';
import AuthorVerificationPage from './AuthorVerificationPage';
import BlockchainCopyrightRegistrationPage from './BlockchainCopyrightRegistrationPage';
import ContentOwnershipValidationPage from './ContentOwnershipValidationPage';
import CopyrightAuditTrailPage from './CopyrightAuditTrailPage';
import CopyrightClaimReportPage from './CopyrightClaimReportPage';
import CopyrightEvidenceReportPage from './CopyrightEvidenceReportPage';
import CopyrightExpirationTrackingPage from './CopyrightExpirationTrackingPage';
import CopyrightHistoryPage from './CopyrightHistoryPage';
import CopyrightHolderManagementPage from './CopyrightHolderManagementPage';
import CopyrightInformationEditorPage from './CopyrightInformationEditorPage';
import CopyrightInfringementDetectionPage from './CopyrightInfringementDetectionPage';
import CopyrightMetadataManagementPage from './CopyrightMetadataManagementPage';
import CopyrightNoticePage from './CopyrightNoticePage';
import CopyrightPolicyTemplatesPage from './CopyrightPolicyTemplatesPage';
import CopyrightRegistrationPage from './CopyrightRegistrationPage';
import CopyrightRenewalReminderPage from './CopyrightRenewalReminderPage';
import CopyrightRevocationRecordPage from './CopyrightRevocationRecordPage';
import CopyrightTransferManagementPage from './CopyrightTransferManagementPage';
import CopyrightWatermarkPage from './CopyrightWatermarkPage';
import DigitalCopyrightSealPage from './DigitalCopyrightSealPage';
import DocumentOwnershipVerificationPage from './DocumentOwnershipVerificationPage';
import DocumentProvenanceTrackingPage from './DocumentProvenanceTrackingPage';
import DuplicateContentDetectionPage from './DuplicateContentDetectionPage';
import InvisibleCopyrightWatermarkPage from './InvisibleCopyrightWatermarkPage';
import LicenseManagementPage from './LicenseManagementPage';
import LicenseVerificationPage from './LicenseVerificationPage';
import OwnershipCertificatePage from './OwnershipCertificatePage';
import PublisherInformationPage from './PublisherInformationPage';
import UsageRightsManagementPage from './UsageRightsManagementPage';
import BlockchainOwnershipVerificationPage from './BlockchainOwnershipVerificationPage';
/**
 * @file PDFCopyrightProtection.jsx
 * @module components/PDFCopyrightProtection
 * @description Master component library for the PDF Copyright Protection interface.
 * Provides 32 custom SVG tool icon components, an animated hero Header section,
 * and a responsive tool card component with SVG stroke animation effects.
 *
 * @author DeepMind Pair Programming Suite
 * @version 6.1.0
 */
import { ArrowRight } from 'lucide-react';

import {
  Award,
  FileEdit,
  Database,
  Info,
  Stamp,
  EyeOff,
  ShieldAlert,
  FileText,
  UserCheck,
  Building2,
  Users,
  Key,
  CheckCircle,
  Sliders,
  LayoutTemplate,
  Shield,
  FileBarChart,
  AlertTriangle,
  Copy,
  Cpu,
  CheckSquare,
  FolderCheck,
  History,
  Clock,
  Repeat,
  Calendar,
  Bell,
  FileMinus,
  GitCommit,
  Link,
  Globe,
  ClipboardCheck
} from 'lucide-react';

/* ==========================================================================
   SECTION 1: PDF COPYRIGHT PROTECTION TOOL ICON WRAPPER COMPONENTS (32 ITEMS)
   ========================================================================== */

/** @typedef {Object} IconProps @property {string} [className="w-8 h-8"] - Tailwind CSS sizing & styling classes */

/** @param {IconProps} props @returns {JSX.Element} 1. Copyright Registration Icon */
function CopyrightRegistrationIcon({ className = "w-8 h-8" }) { return <Award className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 2. Copyright Information Editor Icon */
function CopyrightInformationEditorIcon({ className = "w-8 h-8" }) { return <FileEdit className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 3. Copyright Metadata Management Icon */
function CopyrightMetadataManagementIcon({ className = "w-8 h-8" }) { return <Database className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 4. Copyright Notice Icon */
function CopyrightNoticeIcon({ className = "w-8 h-8" }) { return <Info className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 5. Copyright Watermark Icon */
function CopyrightWatermarkIcon({ className = "w-8 h-8" }) { return <Stamp className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 6. Invisible Copyright Watermark Icon */
function InvisibleCopyrightWatermarkIcon({ className = "w-8 h-8" }) { return <EyeOff className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 7. Digital Copyright Seal Icon */
function DigitalCopyrightSealIcon({ className = "w-8 h-8" }) { return <ShieldAlert className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 8. Ownership Certificate Icon */
function OwnershipCertificateIcon({ className = "w-8 h-8" }) { return <FileText className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 9. Author Verification Icon */
function AuthorVerificationIcon({ className = "w-8 h-8" }) { return <UserCheck className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 10. Publisher Information Icon */
function PublisherInformationIcon({ className = "w-8 h-8" }) { return <Building2 className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 11. Copyright Holder Management Icon */
function CopyrightHolderManagementIcon({ className = "w-8 h-8" }) { return <Users className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 12. License Management Icon */
function LicenseManagementIcon({ className = "w-8 h-8" }) { return <Key className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 13. License Verification Icon */
function LicenseVerificationIcon({ className = "w-8 h-8" }) { return <CheckCircle className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 14. Usage Rights Management Icon */
function UsageRightsManagementIcon({ className = "w-8 h-8" }) { return <Sliders className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 15. Copyright Policy Templates Icon */
function CopyrightPolicyTemplatesIcon({ className = "w-8 h-8" }) { return <LayoutTemplate className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 16. Document Ownership Verification Icon */
function DocumentOwnershipVerificationIcon({ className = "w-8 h-8" }) { return <Shield className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 17. Copyright Claim Report Icon */
function CopyrightClaimReportIcon({ className = "w-8 h-8" }) { return <FileBarChart className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 18. Copyright Infringement Detection Icon */
function CopyrightInfringementDetectionIcon({ className = "w-8 h-8" }) { return <AlertTriangle className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 19. Duplicate Content Detection Icon */
function DuplicateContentDetectionIcon({ className = "w-8 h-8" }) { return <Copy className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 20. AI Content Similarity Check Icon */
function AiContentSimilarityCheckIcon({ className = "w-8 h-8" }) { return <Cpu className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 21. Content Ownership Validation Icon */
function ContentOwnershipValidationIcon({ className = "w-8 h-8" }) { return <CheckSquare className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 22. Copyright Evidence Report Icon */
function CopyrightEvidenceReportIcon({ className = "w-8 h-8" }) { return <FolderCheck className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 23. Copyright Audit Trail Icon */
function CopyrightAuditTrailIcon({ className = "w-8 h-8" }) { return <History className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 24. Copyright History Icon */
function CopyrightHistoryIcon({ className = "w-8 h-8" }) { return <Clock className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 25. Copyright Transfer Management Icon */
function CopyrightTransferManagementIcon({ className = "w-8 h-8" }) { return <Repeat className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 26. Copyright Expiration Tracking Icon */
function CopyrightExpirationTrackingIcon({ className = "w-8 h-8" }) { return <Calendar className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 27. Copyright Renewal Reminder Icon */
function CopyrightRenewalReminderIcon({ className = "w-8 h-8" }) { return <Bell className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 28. Copyright Revocation Record Icon */
function CopyrightRevocationRecordIcon({ className = "w-8 h-8" }) { return <FileMinus className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 29. Document Provenance Tracking Icon */
function DocumentProvenanceTrackingIcon({ className = "w-8 h-8" }) { return <GitCommit className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 30. Blockchain Copyright Registration Icon */
function BlockchainCopyrightRegistrationIcon({ className = "w-8 h-8" }) { return <Link className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 31. Blockchain Ownership Verification Icon */
function BlockchainOwnershipVerificationIcon({ className = "w-8 h-8" }) { return <Globe className={className} />; }

/** @param {IconProps} props @returns {JSX.Element} 32. Copyright Compliance Report Icon */
function CopyrightComplianceReportIcon({ className = "w-8 h-8" }) { return <ClipboardCheck className={className} />; }

/* ==========================================================================
   SECTION 2: DATA CONFIGURATION (COLORS & TOOLS)
   ========================================================================== */

/**
 * Curated palette of 10 pastel background colors and matching vibrant icon colors.
 * Used sequentially to provide visual variety across tool grid cards.
 *
 * @type {Array<{bg: string, icon: string}>}
 */
const colors = [
  { bg: 'bg-[#FFECEC]', icon: 'text-[#EF4444]' }, // 0. Red Theme
  { bg: 'bg-[#E3F2FD]', icon: 'text-[#3B82F6]' }, // 1. Blue Theme
  { bg: 'bg-[#F3E5F5]', icon: 'text-[#A855F7]' }, // 2. Purple Theme
  { bg: 'bg-[#FEF2F2]', icon: 'text-[#DC2626]' }, // 3. Rose Theme
  { bg: 'bg-[#FFF3E0]', icon: 'text-[#F97316]' }, // 4. Orange Theme
  { bg: 'bg-[#ECFDF5]', icon: 'text-[#10B981]' }, // 5. Green Theme
  { bg: 'bg-[#E0F2FE]', icon: 'text-[#0284C7]' }, // 6. Sky Theme
  { bg: 'bg-[#FEF3C7]', icon: 'text-[#D97706]' }, // 7. Amber Theme
  { bg: 'bg-[#F5F3FF]', icon: 'text-[#7C3AED]' }, // 8. Violet Theme
  { bg: 'bg-[#FCE4EC]', icon: 'text-[#EC4899]' }  // 9. Pink Theme
];

/**
 * PDF_TOOLS Configuration Dataset
 * Array of 32 PDF Copyright Protection tool objects displayed in the main application grid.
 *
 * @type {Array<{id: string, name: string, description: string, icon: React.ComponentType, bgColor: string, iconColor: string}>}
 */
export const PDF_TOOLS = [
  {
    id: 'copyright-registration',
    name: 'Copyright Registration',
    description: 'Register official copyright claims and file ownership credentials for PDF documents.',
    icon: CopyrightRegistrationIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'copyright-information-editor',
    name: 'Copyright Information Editor',
    description: 'Edit and manage copyright metadata, legal notices, and author details within PDF files.',
    icon: CopyrightInformationEditorIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'copyright-metadata-management',
    name: 'Copyright Metadata Management',
    description: 'Inject, audit, and organize XMP copyright schema metadata in document headers.',
    icon: CopyrightMetadataManagementIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'copyright-notice',
    name: 'Copyright Notice',
    description: 'Embed legal copyright notice banners and ownership declarations across all pages.',
    icon: CopyrightNoticeIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'copyright-watermark',
    name: 'Copyright Watermark',
    description: 'Apply visible text or graphic copyright watermarks with opacity and angle controls.',
    icon: CopyrightWatermarkIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'invisible-copyright-watermark',
    name: 'Invisible Copyright Watermark',
    description: 'Embed covert, steganographic digital watermarks to track unauthorized distribution.',
    icon: InvisibleCopyrightWatermarkIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'digital-copyright-seal',
    name: 'Digital Copyright Seal',
    description: 'Apply cryptographically sealed digital copyright badges to prevent tampering.',
    icon: DigitalCopyrightSealIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'ownership-certificate',
    name: 'Ownership Certificate',
    description: 'Generate downloadable and verifiable digital certificates of document ownership.',
    icon: OwnershipCertificateIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'author-verification',
    name: 'Author Verification',
    description: 'Verify author identities, public keys, and cryptographic signatures in PDFs.',
    icon: AuthorVerificationIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'publisher-information',
    name: 'Publisher Information',
    description: 'Attach verified publisher metadata, ISBN tags, and distribution rights info.',
    icon: PublisherInformationIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'copyright-holder-management',
    name: 'Copyright Holder Management',
    description: 'Manage primary and co-copyright holders, entity shares, and contact records.',
    icon: CopyrightHolderManagementIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'license-management',
    name: 'License Management',
    description: 'Assign Creative Commons or custom commercial license terms to PDF documents.',
    icon: LicenseManagementIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'license-verification',
    name: 'License Verification',
    description: 'Validate document usage licenses, expiration dates, and authorization keys.',
    icon: LicenseVerificationIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'usage-rights-management',
    name: 'Usage Rights Management',
    description: 'Configure print, copy, modification, and redistribution permissions for users.',
    icon: UsageRightsManagementIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'copyright-policy-templates',
    name: 'Copyright Policy Templates',
    description: 'Apply standardized copyright policy templates and legal terms in one click.',
    icon: CopyrightPolicyTemplatesIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'document-ownership-verification',
    name: 'Document Ownership Verification',
    description: 'Perform automated checks to verify original document ownership and authenticity.',
    icon: DocumentOwnershipVerificationIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'copyright-claim-report',
    name: 'Copyright Claim Report',
    description: 'Generate comprehensive copyright claim dossiers and formal legal reports.',
    icon: CopyrightClaimReportIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'copyright-infringement-detection',
    name: 'Copyright Infringement Detection',
    description: 'Scan web and repository databases for unauthorized uses of your PDF content.',
    icon: CopyrightInfringementDetectionIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'duplicate-content-detection',
    name: 'Duplicate Content Detection',
    description: 'Detect identical content blocks, copied passages, and uncredited excerpts.',
    icon: DuplicateContentDetectionIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'ai-content-similarity-check',
    name: 'AI Content Similarity Check',
    description: 'Utilize AI models to calculate textual and visual similarity against target files.',
    icon: AiContentSimilarityCheckIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'content-ownership-validation',
    name: 'Content Ownership Validation',
    description: 'Validate original content creation timestamp and cryptographic hash proofs.',
    icon: ContentOwnershipValidationIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'copyright-evidence-report',
    name: 'Copyright Evidence Report',
    description: 'Compile tamper-proof evidence packages for copyright dispute resolutions.',
    icon: CopyrightEvidenceReportIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'copyright-audit-trail',
    name: 'Copyright Audit Trail',
    description: 'Track complete immutable audit logs of copyright metadata edits and transfers.',
    icon: CopyrightAuditTrailIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'copyright-history',
    name: 'Copyright History',
    description: 'Review chronological version history of copyright claims and licensing updates.',
    icon: CopyrightHistoryIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'copyright-transfer-management',
    name: 'Copyright Transfer Management',
    description: 'Manage legal assignment, transfer, and licensing handoffs between parties.',
    icon: CopyrightTransferManagementIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'copyright-expiration-tracking',
    name: 'Copyright Expiration Tracking',
    description: 'Monitor copyright protection terms, public domain transitions, and dates.',
    icon: CopyrightExpirationTrackingIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'copyright-renewal-reminder',
    name: 'Copyright Renewal Reminder',
    description: 'Receive automated notifications and alerts for upcoming copyright renewals.',
    icon: CopyrightRenewalReminderIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'copyright-revocation-record',
    name: 'Copyright Revocation Record',
    description: 'Log and publish official copyright revocation and license termination records.',
    icon: CopyrightRevocationRecordIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'document-provenance-tracking',
    name: 'Document Provenance Tracking',
    description: 'Trace complete origin lineage, derivative works, and editing history of PDFs.',
    icon: DocumentProvenanceTrackingIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'blockchain-copyright-registration',
    name: 'Blockchain Copyright Registration',
    description: 'Timestamp and register document hashes on decentralized blockchain ledgers.',
    icon: BlockchainCopyrightRegistrationIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'blockchain-ownership-verification',
    name: 'Blockchain Ownership Verification',
    description: 'Verify immutable blockchain ownership receipts and smart contract records.',
    icon: BlockchainOwnershipVerificationIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'copyright-compliance-report',
    name: 'Copyright Compliance Report',
    description: 'Audit documents against international copyright standards and DMCA policies.',
    icon: CopyrightComplianceReportIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  }
];

/* ==========================================================================
   SECTION 3: ANIMATED HERO HEADER COMPONENT
   ========================================================================== */

/**
 * Header Component
 * Renders the top hero branding section featuring animated background floating file badges,
 * dashed SVG curve paths, glowing particle indicators, and gradient typography.
 * Fully responsive: badge positions and scaling are optimized for both mobile screens and desktop viewports.
 *
 * @component
 * @returns {JSX.Element} Rendered hero header section
 */


/* ==========================================================================
   SECTION 4: MAIN TOOL CARD COMPONENT
   ========================================================================== */

/**
 * PDFCopyrightProtection Tool Card Component
 * Renders individual interactive feature card with responsive dimensions, custom SVG badge,
 * hover elevation scale, and stroke draw animation.
 *
 * @component
 * @param {Object} props Component properties
 * @param {Object} props.tool Tool configuration object (id, name, description, icon, bgColor, iconColor)
 * @param {number} [props.index=0] Staggered animation index multiplier
 * @param {Function} [props.onClick] Interactive click event handler
 * @returns {JSX.Element} Rendered tool card element
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
            <SlideInText text="PDF Copyright Protection" />
          </h1>
          <p className="mt-3 sm:mt-4 text-xs sm:text-sm md:text-base font-semibold text-slate-700 max-w-2xl mx-auto leading-relaxed">
            Watermark, lock permissions, add copyright notices, and protect intellectual property.
          </p>
        </div>
      </div>
    </header>
  );
}

export function PDFCopyrightProtection({ tool, index = 0, onClick }) {
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
          ) : typeof IconComponent === 'function' ? (
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

export function PDFCopyrightProtectionPage({ onBack, searchQuery = "" }) {
    const [selectedTool, setSelectedTool] = React.useState(null);

  React.useEffect(() => {
    if (selectedTool) {
      window.history.pushState({ toolOpen: true }, '');
      window.scrollTo(0, 0);
    }
  }, [selectedTool]);

  React.useEffect(() => {
    const handlePopState = () => {
      setSelectedTool(null);
      window.scrollTo(0, 0);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  if (selectedTool) {
    const handleBack = () => { setSelectedTool(null); window.scrollTo(0, 0); };
    if (selectedTool.id === 'ai-content-similarity-check') {
      return <AIContentSimilarityCheckPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'author-verification') {
      return <AuthorVerificationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'blockchain-copyright-registration') {
      return <BlockchainCopyrightRegistrationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'blockchain-ownership-verification') {
      return <BlockchainOwnershipVerificationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'content-ownership-validation') {
      return <ContentOwnershipValidationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-audit-trail') {
      return <CopyrightAuditTrailPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-claim-report') {
      return <CopyrightClaimReportPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-evidence-report') {
      return <CopyrightEvidenceReportPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-expiration-tracking') {
      return <CopyrightExpirationTrackingPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-history') {
      return <CopyrightHistoryPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-holder-management') {
      return <CopyrightHolderManagementPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-information-editor') {
      return <CopyrightInformationEditorPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-infringement-detection') {
      return <CopyrightInfringementDetectionPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-metadata-management') {
      return <CopyrightMetadataManagementPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-notice') {
      return <CopyrightNoticePage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-policy-templates') {
      return <CopyrightPolicyTemplatesPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-registration') {
      return <CopyrightRegistrationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-renewal-reminder') {
      return <CopyrightRenewalReminderPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-revocation-record') {
      return <CopyrightRevocationRecordPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-transfer-management') {
      return <CopyrightTransferManagementPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'copyright-watermark') {
      return <CopyrightWatermarkPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'digital-copyright-seal') {
      return <DigitalCopyrightSealPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'document-ownership-verification') {
      return <DocumentOwnershipVerificationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'document-provenance-tracking') {
      return <DocumentProvenanceTrackingPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'duplicate-content-detection') {
      return <DuplicateContentDetectionPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'invisible-copyright-watermark') {
      return <InvisibleCopyrightWatermarkPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'license-management') {
      return <LicenseManagementPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'license-verification') {
      return <LicenseVerificationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'ownership-certificate') {
      return <OwnershipCertificatePage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'publisher-information') {
      return <PublisherInformationPage tool={selectedTool} onBack={handleBack} />;
    }
    if (selectedTool.id === 'usage-rights-management') {
      return <UsageRightsManagementPage tool={selectedTool} onBack={handleBack} />;
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
              <PDFCopyrightProtection
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
