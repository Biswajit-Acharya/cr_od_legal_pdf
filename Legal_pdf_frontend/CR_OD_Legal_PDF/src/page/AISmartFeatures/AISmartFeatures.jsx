/**
 * @file AISmartFeatures.jsx
 * @description AI & Smart Features sub-page for CR OD Legal PDF.
 *
 * Provides 32 AI-powered PDF tools including: summariser, translation,
 * PDF chat (single & multi-doc), OCR, grammar improvement, form filling,
 * AcroForms/XFA support, cloud integrations, and browser-based editing.
 *
 * Exports:
 *  - `AISmartFeatures`     â€” Individual tool card component
 *  - `Header`              â€” Hero section with animated floating file badges
 *  - `PDF_TOOLS`           â€” Array of 32 AI tool definitions
 *  - `AISmartFeaturesPage` â€” Full page component rendered by App.jsx
 */
import React from 'react';
import SlideInText from '../../components/SlideInText';
import ToolWorkspace from '../ToolWorkspace';
import AISummarizerPage from './AISummarizerPage';
import {
  ArrowRight,
  Sparkles,
  Globe,
  FileCode,
  ClipboardCheck,
  Zap,
  Cloud,
  Box,
  MessageSquare,
  MessagesSquare,
  Lightbulb,
  Wand2,
  HelpCircle,
  ListChecks,
  BookOpen,
  Search,
  CheckCircle2,
  PenTool,
  Scan,
  Users,
  Scale,
  FileText,
  Layers,
  Link,
  Download,
  Calendar,
  Share2,
  Package,
  RefreshCw,
  History,
  Monitor,
  Smartphone
} from 'lucide-react';

/* ==========================================================================
   1. AI & SMART FEATURES ICON COMPONENTS (32 TOOLS)
   Har icon component Lucide React ke basic icons ko custom styling ke sath wrap karta hai.
   ========================================================================== */

// 1. AI Summarizer - Summarizes documents using AI
function AiSummarizerIcon({ className = "w-8 h-8" }) { return <Sparkles className={className} />; }

// 2. Translate PDF - Preserves layout while translating
function TranslatePdfIcon({ className = "w-8 h-8" }) { return <Globe className={className} />; }

// 3. PDF to Markdown - Converts PDF content into Markdown format
function PdfToMarkdownIcon({ className = "w-8 h-8" }) { return <FileCode className={className} />; }

// 4. PDF Forms - Interactive form creation and editing
function PdfFormsIcon({ className = "w-8 h-8" }) { return <ClipboardCheck className={className} />; }

// 5. Workflow Automation - Trigger-based custom PDF automation
function WorkflowAutomationIcon({ className = "w-8 h-8" }) { return <Zap className={className} />; }

// 6. Google Drive Integration - Direct connection to Google Drive
function GoogleDriveIntegrationIcon({ className = "w-8 h-8" }) { return <Cloud className={className} />; }

// 7. Dropbox Integration - Sync and manage files with Dropbox
function DropboxIntegrationIcon({ className = "w-8 h-8" }) { return <Box className={className} />; }

// 8. AI Chat with PDF - Interactive Q&A chat for single PDF
function AiChatWithPdfIcon({ className = "w-8 h-8" }) { return <MessageSquare className={className} />; }

// 9. Multi-Document Chat - Cross-reference chat across multiple documents
function MultiDocumentChatIcon({ className = "w-8 h-8" }) { return <MessagesSquare className={className} />; }

// 10. AI Document Insights - Smart analytics and key pattern detection
function AiDocumentInsightsIcon({ className = "w-8 h-8" }) { return <Lightbulb className={className} />; }

// 11. Simplify Document - Converts complex jargon into simple readable text
function SimplifyDocumentIcon({ className = "w-8 h-8" }) { return <Wand2 className={className} />; }

// 12. Answer Document Questions - Direct answers with exact page citations
function AnswerDocumentQuestionsIcon({ className = "w-8 h-8" }) { return <HelpCircle className={className} />; }

// 13. Extract Key Points - Automatically extracts bullet points and action items
function ExtractKeyPointsIcon({ className = "w-8 h-8" }) { return <ListChecks className={className} />; }

// 14. Research Assistant - Deep analysis for research & academic papers
function ResearchAssistantIcon({ className = "w-8 h-8" }) { return <BookOpen className={className} />; }

// 15. AI Semantic Search - Contextual search based on meaning rather than keywords
function AiSemanticSearchIcon({ className = "w-8 h-8" }) { return <Search className={className} />; }

// 16. Grammar Improvement - Fixes grammar, spelling, and typos
function GrammarImprovementIcon({ className = "w-8 h-8" }) { return <CheckCircle2 className={className} />; }

// 17. Writing Enhancement - Improves tone, clarity, and readability
function WritingEnhancementIcon({ className = "w-8 h-8" }) { return <PenTool className={className} />; }

// 18. AI OCR - Converts scanned images to searchable & editable text
function AiOcrIcon({ className = "w-8 h-8" }) { return <Scan className={className} />; }

// 19. Meeting Summary - Summarizes meeting transcripts into action items
function MeetingSummaryIcon({ className = "w-8 h-8" }) { return <Users className={className} />; }

// 20. Contract Summary - Analyzes legal documents, clauses, and risk factors
function ContractSummaryIcon({ className = "w-8 h-8" }) { return <Scale className={className} />; }

// 21. AcroForms Support - Support for standard AcroForm interactive fields
function AcroFormsSupportIcon({ className = "w-8 h-8" }) { return <FileText className={className} />; }

// 22. XFA Forms Support - Support for complex dynamic Adobe XFA form formats
function XfaFormsSupportIcon({ className = "w-8 h-8" }) { return <Layers className={className} />; }

// 23. Link Fillable Fields - Links fields to auto-fill repetitive information
function LinkFillableFieldsIcon({ className = "w-8 h-8" }) { return <Link className={className} />; }

// 24. Export Form Data - Exports form inputs into CSV, JSON, or Excel format
function ExportFormDataIcon({ className = "w-8 h-8" }) { return <Download className={className} />; }

// 25. Add Date Fields - Adds interactive date picker fields to forms
function AddDateFieldsIcon({ className = "w-8 h-8" }) { return <Calendar className={className} />; }

// 26. OneDrive Integration - Microsoft OneDrive cloud integration
function OneDriveIntegrationIcon({ className = "w-8 h-8" }) { return <Cloud className={className} />; }

// 27. SharePoint Integration - Enterprise SharePoint library integration
function SharePointIntegrationIcon({ className = "w-8 h-8" }) { return <Share2 className={className} />; }

// 28. Box Integration - Secure cloud storage access for Box
function BoxIntegrationIcon({ className = "w-8 h-8" }) { return <Package className={className} />; }

// 29. Automatic Cloud Sync - Automatic background sync across cloud providers
function AutomaticCloudSyncIcon({ className = "w-8 h-8" }) { return <RefreshCw className={className} />; }

// 30. Cloud Version History - Document version tracking and restoration
function CloudVersionHistoryIcon({ className = "w-8 h-8" }) { return <History className={className} />; }

// 31. Browser-based Editing - Edit documents directly inside web browser
function BrowserBasedEditingIcon({ className = "w-8 h-8" }) { return <Monitor className={className} />; }

// 32. Continue Editing Anywhere - Cross-device seamless editing sync
function ContinueEditingAnywhereIcon({ className = "w-8 h-8" }) { return <Smartphone className={className} />; }

/* ==========================================================================
   2. HEADER COMPONENT WITH FLOATING BRANDING & DECORATIVE ANIMATIONS
   Header component handles top page branding, main title, subtitle, floating SVG file badges,
   and animated dashed background arcs.
   ========================================================================== */

/**
 * Header Component
 * Renders top hero section with dynamic floating file badges and gradient title.
 */


/* ==========================================================================
   3. AI & SMART FEATURES TOOL CARD COMPONENT
   Component displaying each feature card in the grid.
   Includes slide-in entrance animations, hover expansion, icon badge, and action link.
   ========================================================================== */

/**
 * AISmartFeatures Component
 * Renders individual feature tool card inside grid.
 *
 * @param {Object} props - Component properties
 * @param {Object} props.tool - Tool data object containing name, description, icon, bgColor, and iconColor
 * @param {number} [props.index=0] - Index position used for staggered animation timing and entrance direction
 * @param {Function} [props.onClick] - Click handler function
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
            <SlideInText text="AI & Smart Features" />
          </h1>
          <p className="mt-3 sm:mt-4 text-xs sm:text-sm md:text-base font-semibold text-slate-700 max-w-2xl mx-auto leading-relaxed">
            Leverage artificial intelligence to summarize, translate, analyze, and chat with your PDFs.
          </p>
        </div>
      </div>
    </header>
  );
}

export function AISmartFeatures({ tool, index = 0, onClick }) {
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

/* ==========================================================================
   4. DATA (COLORS AND PDF_TOOLS)
   ========================================================================== */

/**
 * Curated palette of background pastel colors and matching icon text colors.
 * Cards me cycle hone wale custom color themes:
 * - bg: Badge background SVG color
 * - icon: Lucide icon color class
 */
const colors = [
  { bg: 'bg-[#FFECEC]', icon: 'text-[#EF4444]' }, // Red theme
  { bg: 'bg-[#E3F2FD]', icon: 'text-[#3B82F6]' }, // Blue theme
  { bg: 'bg-[#F3E5F5]', icon: 'text-[#A855F7]' }, // Purple theme
  { bg: 'bg-[#FEF2F2]', icon: 'text-[#DC2626]' }, // Rose theme
  { bg: 'bg-[#FFF3E0]', icon: 'text-[#F97316]' }, // Orange theme
  { bg: 'bg-[#ECFDF5]', icon: 'text-[#10B981]' }, // Green theme
  { bg: 'bg-[#E0F2FE]', icon: 'text-[#0284C7]' }, // Sky theme
  { bg: 'bg-[#FEF3C7]', icon: 'text-[#D97706]' }, // Amber theme
  { bg: 'bg-[#F5F3FF]', icon: 'text-[#7C3AED]' }, // Violet theme
  { bg: 'bg-[#FCE4EC]', icon: 'text-[#EC4899]' }  // Pink theme
];

/**
 * PDF_TOOLS Array
 * List of 32 tool configurations displayed in the main application grid.
 */
export const PDF_TOOLS = [
  {
    id: 'ai-summarizer',
    name: 'AI Summarizer',
    description: 'Generate concise executive summaries and key takeaways from any document automatically.',
    icon: AiSummarizerIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'translate-pdf',
    name: 'Translate PDF',
    description: 'Instantly translate PDF documents into 100+ languages while preserving layout.',
    icon: TranslatePdfIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'pdf-to-markdown',
    name: 'PDF to Markdown',
    description: 'Convert PDFs to clean, formatted Markdown code ready for note apps and LLMs.',
    icon: PdfToMarkdownIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'pdf-forms',
    name: 'PDF Forms',
    description: 'Create, fill out, and manage interactive PDF forms with smart validation.',
    icon: PdfFormsIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'workflow-automation',
    name: 'Workflow & Automation',
    description: 'Automate repetitive PDF tasks with custom trigger-based automated workflows.',
    icon: WorkflowAutomationIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'google-drive-integration',
    name: 'Google Drive Integration',
    description: 'Connect directly to Google Drive to open, edit, and save PDFs seamlessly.',
    icon: GoogleDriveIntegrationIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'dropbox-integration',
    name: 'Dropbox Integration',
    description: 'Sync and edit PDF files stored in your Dropbox cloud accounts effortlessly.',
    icon: DropboxIntegrationIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'ai-chat-with-pdf',
    name: 'AI Chat with PDF',
    description: 'Have interactive conversations with your PDF documents to ask questions instantly.',
    icon: AiChatWithPdfIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'multi-document-chat',
    name: 'Multi-document Chat',
    description: 'Chat across multiple PDFs simultaneously to cross-reference facts and insights.',
    icon: MultiDocumentChatIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'ai-document-insights',
    name: 'AI Document Insights',
    description: 'Uncover hidden patterns, sentiment, structure, and smart analytics in PDFs.',
    icon: AiDocumentInsightsIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'simplify-document',
    name: 'Simplify Document',
    description: 'Rewrite complex jargon and technical documents into easy-to-read plain language.',
    icon: SimplifyDocumentIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'answer-document-questions',
    name: 'Answer Document Questions',
    description: 'Get precise, instant answers with exact page citations from your document.',
    icon: AnswerDocumentQuestionsIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'extract-key-points',
    name: 'Extract Key Points',
    description: 'Extract bullet points, action items, dates, and core concepts automatically.',
    icon: ExtractKeyPointsIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'research-assistant',
    name: 'Research Assistant',
    description: 'Deep dive into academic papers and legal briefs with AI research assistance.',
    icon: ResearchAssistantIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'ai-semantic-search',
    name: 'AI Semantic Search',
    description: 'Search documents by concept and context rather than just exact keyword matching.',
    icon: AiSemanticSearchIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'grammar-improvement',
    name: 'Grammar Improvement',
    description: 'Detect and fix grammatical errors, typos, and style inconsistencies instantly.',
    icon: GrammarImprovementIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'writing-enhancement',
    name: 'Writing Enhancement',
    description: 'Refine tone, clarity, vocabulary, and readability of your PDF content.',
    icon: WritingEnhancementIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'ai-ocr',
    name: 'AI OCR',
    description: 'Turn scanned image PDFs into searchable, selectable, and editable text using AI.',
    icon: AiOcrIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'meeting-summary',
    name: 'Meeting Summary',
    description: 'Transform meeting notes and transcript PDFs into structured action items.',
    icon: MeetingSummaryIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'contract-summary',
    name: 'Contract Summary',
    description: 'Analyze legal contracts to summarize clauses, obligations, risks, and dates.',
    icon: ContractSummaryIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'acroforms-support',
    name: 'AcroForms Support',
    description: 'Full compatibility with standard AcroForms for interactive form field filling.',
    icon: AcroFormsSupportIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'xfa-forms-support',
    name: 'XFA Forms Support',
    description: 'Process, view, and fill complex dynamic Adobe XFA forms seamlessly.',
    icon: XfaFormsSupportIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  },
  {
    id: 'link-fillable-fields',
    name: 'Link Fillable Fields',
    description: 'Connect form fields together to auto-populate duplicate data across pages.',
    icon: LinkFillableFieldsIcon,
    bgColor: colors[2].bg,
    iconColor: colors[2].icon
  },
  {
    id: 'export-form-data',
    name: 'Export Form Data',
    description: 'Extract filled form responses into CSV, JSON, or Excel spreadsheet formats.',
    icon: ExportFormDataIcon,
    bgColor: colors[3].bg,
    iconColor: colors[3].icon
  },
  {
    id: 'add-date-fields',
    name: 'Add Date Fields',
    description: 'Insert smart auto-updating date pickers and timestamp fields into forms.',
    icon: AddDateFieldsIcon,
    bgColor: colors[4].bg,
    iconColor: colors[4].icon
  },
  {
    id: 'onedrive-integration',
    name: 'OneDrive Integration',
    description: 'Access, edit, and save your PDFs directly inside Microsoft OneDrive.',
    icon: OneDriveIntegrationIcon,
    bgColor: colors[5].bg,
    iconColor: colors[5].icon
  },
  {
    id: 'sharepoint-integration',
    name: 'SharePoint Integration',
    description: 'Enterprise integration with SharePoint document libraries and team sites.',
    icon: SharePointIntegrationIcon,
    bgColor: colors[6].bg,
    iconColor: colors[6].icon
  },
  {
    id: 'box-integration',
    name: 'Box Integration',
    description: 'Securely access and manage PDF documents stored in Box cloud storage.',
    icon: BoxIntegrationIcon,
    bgColor: colors[7].bg,
    iconColor: colors[7].icon
  },
  {
    id: 'automatic-cloud-sync',
    name: 'Automatic Cloud Sync',
    description: 'Keep changes synced across all connected cloud storage platforms automatically.',
    icon: AutomaticCloudSyncIcon,
    bgColor: colors[8].bg,
    iconColor: colors[8].icon
  },
  {
    id: 'cloud-version-history',
    name: 'Cloud Version History',
    description: 'Track document revisions, restore previous versions, and view edit logs.',
    icon: CloudVersionHistoryIcon,
    bgColor: colors[9].bg,
    iconColor: colors[9].icon
  },
  {
    id: 'browser-based-editing',
    name: 'Browser-based Editing',
    description: 'Edit PDFs directly in your web browser with zero installation needed.',
    icon: BrowserBasedEditingIcon,
    bgColor: colors[0].bg,
    iconColor: colors[0].icon
  },
  {
    id: 'continue-editing-anywhere',
    name: 'Continue Editing Anywhere',
    description: 'Pick up where you left off across desktop, tablet, and mobile devices.',
    icon: ContinueEditingAnywhereIcon,
    bgColor: colors[1].bg,
    iconColor: colors[1].icon
  }
];

export function AISmartFeaturesPage({ onBack, searchQuery = "" }) {
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
    if (selectedTool.id === 'ai-summarizer') {
      return <AISummarizerPage tool={selectedTool} onBack={() => { setSelectedTool(null); const parentHash = window.location.hash.split('/')[0]; window.history.pushState({ page: parentHash.replace('#', '') }, '', parentHash); window.scrollTo(0, 0); }} />;
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
              <AISmartFeatures
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
