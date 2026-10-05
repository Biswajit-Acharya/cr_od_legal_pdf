/**
 * @file App.jsx
 * @description Root application component for CR OD Legal PDF.
 *
 * Responsibilities:
 *  - Manages global UI state: active page, search query, direct tool selection.
 *  - Implements client-side SPA routing via `window.history.pushState` (hash-based).
 *  - Provides a unified real-time search across all 15 categories and their sub-tools.
 *  - Renders the correct sub-page component based on `activePage` state.
 *  - Wraps every view inside the shared <GlobalHeader> and <GlobalFooter>.
 *
 * Routing Strategy:
 *  All navigation is done via state (not React Router). When the user clicks a
 *  category card, `activePage` is set to that category's `id` string (e.g. 'organize-pdf').
 *  The browser Back button is handled via the `popstate` event listener so users
 *  can navigate backwards naturally without a full page reload.
 */
import React, { useState, useMemo, useEffect } from 'react';
import SEOHead from './components/SEOHead';

/* -------------------------------------------------------------------------- */
/*  Layout Components                                                          */
/* -------------------------------------------------------------------------- */
import ToolCard, { Header as GlobalHeader, Footer as GlobalFooter, BackgroundWatermark } from './components/crodlegalpdf';

/* -------------------------------------------------------------------------- */
/*  Home Dashboard Data                                                        */
/* -------------------------------------------------------------------------- */
import { PDF_TOOLS } from './data/crodlegalpdf';  // 20 top-level category cards

/* -------------------------------------------------------------------------- */
/*  Tool Workspace (individual tool file upload/processing UI)                 */
/* -------------------------------------------------------------------------- */
import ToolWorkspace from './page/ToolWorkspace';

/* -------------------------------------------------------------------------- */
/*  Sub-page Components & their tool data arrays                              */
/*  Each page exports a <Page> component and its own PDF_TOOLS / TOOLS array. */
/* -------------------------------------------------------------------------- */
import OrganizepdfPage, { OrganizepdfCard, PDF_TOOLS as tools1 } from './page/Organizepdf/Organizepdf';
import { PDFtoConvertPage, PDF_TOOLS as tools2 } from './page/PDFtoConvert/PDFtoConvert';
import { ConvertPDFPage, PDF_TOOLS as tools3 } from './page/ConvertPDF/ConvertPDF';
import { PDFSecurityPage, PDF_TOOLS as tools4 } from './page/PDFSecurity/PDFSecurity';
import DocumentIntegrityVerificationPage from './page/PDFSecurity/DocumentIntegrityVerificationPage';
import PDFSecurityScorePage from './page/PDFSecurity/PDFSecurityScorePage';
import PDFSecurityPolicyTemplatesPage from './page/PDFSecurity/PDFSecurityPolicyTemplatesPage';
import AISecurityRiskDetectionPage from './page/PDFSecurity/AISecurityRiskDetection/AISecurityRiskDetectionPage';
import { PDFSignaturePage, PDF_TOOLS as tools5 } from './page/PDFSignature/PDFSignature';
import { AISmartFeaturesPage, PDF_TOOLS as tools6 } from './page/AISmartFeatures/AISmartFeatures';
import { CompareRedactionPage, PDF_TOOLS as tools7 } from './page/CompareRedaction/CompareRedaction';
import { TeamBusinessPage, TEAM_BUSINESS_TOOLS as tools8 } from './page/TeamBusiness/TeamBusiness';
import { AccessibilityPage, ACCESSIBILITY_TOOLS as tools9 } from './page/Accessibility/Accessibility';
import { DocumentManagementPage, PDF_TOOLS as tools10 } from './page/DocumentManagement/DocumentManagement';
import { ImageProcessingPage, IMAGE_PROCESSING_TOOLS as tools11 } from './page/ImageProcessing/ImageProcessing';
import { PDFReaderPage, PDF_TOOLS as tools12 } from './page/PDFReader/PDFReader';
import { ReviewAnnotationPage, PDF_TOOLS as tools13 } from './page/ReviewAnnotation/ReviewAnnotation';
import { FingerprintAuthenticationBiometricSignaturePage, BIOMETRIC_TOOLS as tools14 } from './page/FingerprintAuthenticationBiometricSignature/FingerprintAuthenticationBiometricSignature';
import { PDFCopyrightProtectionPage, PDF_TOOLS as tools15 } from './page/PDFCopyrightProtection/PDFCopyrightProtection';
import SoftwareAboutUsPage, { SOFTWARE_ABOUT_US_TOOLS as tools16 } from './page/SoftwareAboutUs/SoftwareAboutUs';
import ContactUsPage from './page/ContactUs/ContactUs';
import AgentWidget from './page/AIagent/agent';
import SharedDocumentViewerPage from './page/PDFSecurity/SharedDocumentViewerPage';
import ShareManagementPage from './page/PDFSecurity/ShareManagementPage';


/* -------------------------------------------------------------------------- */
/*  SUB_TOOLS_MAP                                                              */
/*  Maps each top-level category `id` to its flat array of individual tools.  */
/*  Used by the global search to deep-search across all sub-tool titles.      */
/* -------------------------------------------------------------------------- */
const SUB_TOOLS_MAP = {
  'organize-pdf': tools1 || [],
  'convert-to-pdf': tools2 || [],
  'convert-from-pdf': tools3 || [],
  'pdf-security': tools4 || [],
  'pdf-signature': tools5 || [],
  'pdf-ai-tools': tools6 || [],
  'compare-redaction': tools7 || [],
  'team-business': tools8 || [],
  'accessibility': tools9 || [],
  'document-management': tools10 || [],
  'image-processing': tools11 || [],
  'pdf-reader': tools12 || [],
  'review-annotation': tools13 || [],
  'fingerprint-auth-signature': tools14 || [],
  'pdf-copyright-protection': tools15 || [],
  'software-about-us': tools16 || [],
  'Contact-Us': [],
  'AI-Agent': [],
};

/**
 * App
 * Root component that owns global state and renders the correct view.
 *
 * State:
 *  @state {string}      activePage         - Currently visible page id (default: 'home')
 *  @state {string}      searchQuery        - Live search string typed in the header
 *  @state {Object|null} selectedDirectTool - A specific sub-tool opened from search results;
 *                                            renders ToolWorkspace when non-null
 *
 * @returns {JSX.Element} Full-page layout with header, dynamic content area, and footer
 */
export default function App() {
  const [activePage, setActivePage] = useState(() => {
    const hash = window.location.hash.replace('#', '').split('/')[0];
    if (hash === 'shared') return 'shared';
    if (hash === 'manage-shares') return 'manage-shares';
    return hash && SUB_TOOLS_MAP[hash] ? hash : 'home';
  });          // Currently active sub-page id
  const [searchQuery, setSearchQuery] = useState('');            // Controlled search input value
  const [selectedDirectTool, setSelectedDirectTool] = useState(null); // Sub-tool selected from search

  // Normalised query string used for all filter comparisons
  const query = searchQuery.trim().toLowerCase();

  /* ------------------------------------------------------------------------ */
  /*  Memoised Search Results                                                  */
  /* ------------------------------------------------------------------------ */

  /**
   * filteredMainTools
   * Filters the 20 top-level category cards whose name contains the search query.
   * Returns the full list when query is empty (no active search).
   */
  const filteredMainTools = useMemo(() => {
    if (!query) return PDF_TOOLS;
    return PDF_TOOLS.filter(parent => {
      const parentName = (parent.name || parent.title || '').toLowerCase();
      return parentName.includes(query);
    });
  }, [query]);

  /**
   * filteredSubTools
   * Deep-searches every sub-tool across all 15 categories.
   * Attaches `parentId` and a composite `uniqueKey` to each match so the
   * correct sub-page can be navigated to on click.
   * Returns an empty array when query is empty to avoid rendering the
   * "Matching Specific Tools" section on the home screen.
   */
  const filteredSubTools = useMemo(() => {
    if (!query) return [];
    const results = [];
    Object.entries(SUB_TOOLS_MAP).forEach(([parentId, subTools]) => {
      subTools.forEach((child, idx) => {
        const title = (child.title || child.name || '').toLowerCase();
        if (title.includes(query)) {
          results.push({
            ...child,
            parentId,                                      // Parent category id for navigation
            uniqueKey: `${parentId}-${child.id || idx}`   // Stable React list key
          });
        }
      });
    });
    return results;
  }, [query]);

  /* ------------------------------------------------------------------------ */
  /*  Event Handlers                                                           */
  /* ------------------------------------------------------------------------ */

  /**
   * handleSearchChange
   * Called whenever the search input value changes.
   * Pushes a `#search` history entry on the *first* character typed so the
   * browser Back button dismisses the search results instead of leaving the app.
   *
   * @param {string} val - New search string value from the input
   */
  const handleSearchChange = (val) => {
    // Only push a new history entry when transitioning from empty → non-empty
    if (val !== '' && searchQuery === '') {
      window.history.pushState({ searchOpen: true }, '', '#search');
    }
    setSearchQuery(val);
  };

  /**
   * handleDirectToolSelect
   * Called when a user clicks a specific sub-tool card from the search results.
   * Opens that tool directly in <ToolWorkspace> and pushes a history entry
   * so the Back button can dismiss the workspace view.
   *
   * @param {Object} tool - The selected tool data object from a sub-tools array
   */
  const handleDirectToolSelect = (tool) => {
    window.history.pushState({ toolOpen: true }, '', '#tool');
    setSelectedDirectTool(tool);
  };

  /**
   * handleToolClick
   * Called when a top-level category card is clicked from the home grid or search results.
   * Resolves the target page id and navigates cleanly.
   *
   * @param {Object} tool - Tool data object
   */
  const handleToolClick = (tool) => {
    const pageId = tool.parentId || tool.id;
    if (pageId) {
      if (SUB_TOOLS_MAP[pageId]) {
        navigateToPage(pageId);
      } else {
        handleDirectToolSelect(tool);
      }
    }
  };

  /**
   * navigateToPage
   * Switches activePage to the given id, resets search/tool states,
   * pushes a history entry, and scrolls to top.
   *
   * @param {string} pageId - The page id to navigate to
   */
  const navigateToPage = (pageId) => {
    setSearchQuery('');
    setSelectedDirectTool(null);
    if (pageId !== activePage) {
      window.history.pushState({ page: pageId }, '', '#' + pageId);
      setActivePage(pageId);
    }
    window.scrollTo(0, 0);
  };

  /**
   * handlePageBack
   * Guaranteed back navigation from any sub-page directly to Home Dashboard.
   */
  const handlePageBack = () => {
    setSelectedDirectTool(null);
    setSearchQuery('');
    setActivePage('home');
    window.history.pushState({ page: 'home' }, '', '#home');
    window.scrollTo(0, 0);
  };

  /* ------------------------------------------------------------------------ */
  /*  Scroll & State Sync Effect                                              */
  /* ------------------------------------------------------------------------ */
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [activePage, selectedDirectTool, searchQuery]);

  /* ------------------------------------------------------------------------ */
  /*  Browser Back / Forward Button Handler                                   */
  /* ------------------------------------------------------------------------ */
  useEffect(() => {
    const handlePopState = (e) => {
      setSelectedDirectTool(null);
      setSearchQuery('');
      let targetPage = 'home';
      const hash = window.location.hash;
      if (hash) {
          const parts = hash.split('/');
          targetPage = parts[0].replace('#', '');
      } else if (e.state && e.state.page) {
          targetPage = e.state.page;
      }
      setActivePage(targetPage);
      window.scrollTo(0, 0);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  /* ------------------------------------------------------------------------ */
  /*  Security Protection: Disable Copy (Ctrl+C) & Cut (Ctrl+X)               */
  /* ------------------------------------------------------------------------ */
  useEffect(() => {
    // Disable clipboard Copy event (Ctrl+C / Right-click Copy)
    const handleCopy = (e) => {
      e.preventDefault();
    };

    // Disable clipboard Cut event (Ctrl+X / Right-click Cut)
    const handleCut = (e) => {
      e.preventDefault();
    };

    // Disable keyboard shortcuts Ctrl+C / Cmd+C and Ctrl+X / Cmd+X
    const handleKeyDown = (e) => {
      const key = (e.key || '').toLowerCase();
      if ((e.ctrlKey || e.metaKey) && (key === 'c' || key === 'x')) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    document.addEventListener('copy', handleCopy);
    document.addEventListener('cut', handleCut);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('copy', handleCopy);
      document.removeEventListener('cut', handleCut);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  /* ------------------------------------------------------------------------ */
  /*  Render                                                                   */
  /* ------------------------------------------------------------------------ */
  return (
    <div className="min-h-screen flex flex-col font-sans selection:bg-slate-900 selection:text-white bg-[#f2f6ee] overflow-x-hidden w-full max-w-full">
      <SEOHead activePage={activePage} tool={selectedDirectTool} />

      {/* ------------------------------------------------------------------ */}
      {/* GLOBAL HEADER — contains logo, page title, and the search bar      */}
      {/* ------------------------------------------------------------------ */}
      <GlobalHeader searchQuery={searchQuery} onSearchChange={handleSearchChange} />

      {/* ------------------------------------------------------------------ */}
      {/* MAIN CONTENT AREA — conditionally renders one of:                  */}
      {/*   a) ToolWorkspace  — when a specific sub-tool is selected          */}
      {/*   b) Search results — when search query is non-empty                */}
      {/*   c) A sub-page     — when a category card has been clicked         */}
      {/*   d) Home dashboard  — default view with all 20 category cards      */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 flex flex-col w-full relative z-0 min-h-[500px]">
        {/* Background Watermark strictly in background behind cards */}
        <BackgroundWatermark />

        {/* ── a) Tool Workspace ─────────────────────────────────────────── */}
        {selectedDirectTool ? (
          selectedDirectTool.id === 'document-integrity-verification' ? (
            <DocumentIntegrityVerificationPage tool={selectedDirectTool} onBack={() => {
              if (window.history.state?.toolOpen) {
                window.history.back();
              } else {
                setSelectedDirectTool(null);
              }
            }} />
          ) : selectedDirectTool.id === 'pdf-security-score' ? (
            <PDFSecurityScorePage tool={selectedDirectTool} onBack={() => {
              if (window.history.state?.toolOpen) {
                window.history.back();
              } else {
                setSelectedDirectTool(null);
              }
            }} />
          ) : selectedDirectTool.id === 'pdf-security-policy-templates' ? (
            <PDFSecurityPolicyTemplatesPage tool={selectedDirectTool} onBack={() => {
              if (window.history.state?.toolOpen) {
                window.history.back();
              } else {
                setSelectedDirectTool(null);
              }
            }} />
          ) : (
            <ToolWorkspace tool={selectedDirectTool} onBack={() => {
              if (window.history.state?.toolOpen) {
                window.history.back();
              } else {
                setSelectedDirectTool(null);
              }
            }} />
          )

          /* ── b) Search Results ─────────────────────────────────────────── */
        ) : query !== '' ? (
          <div className="w-full max-w-[1720px] mx-auto px-4 sm:px-6 md:px-10 py-4 overflow-x-hidden flex-1 flex flex-col">
            <main className="flex-1 pt-4 pb-4">
              <div className="mb-6 space-y-8">

                {/* Category matches — top-level cards whose name matches query */}
                {filteredMainTools.length > 0 && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-800 mb-4 px-1 flex items-center gap-2">
                      <span>Matching Categories</span>
                      <span className="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full">{filteredMainTools.length}</span>
                    </h2>
                    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-6 md:gap-8">
                      {filteredMainTools.map((tool, idx) => (
                        // Clear search and navigate to the matched category
                        <ToolCard key={tool.id} tool={tool} index={idx} onClick={(t) => { setSearchQuery(''); handleToolClick(t); }} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Sub-tool matches — individual tools whose title matches query */}
                {filteredSubTools.length > 0 && (
                  <div>
                    <h2 className="text-lg font-bold text-slate-800 mb-4 px-1 flex items-center gap-2">
                      <span>Matching Specific Tools</span>
                      <span className="bg-purple-100 text-purple-700 text-xs px-2 py-0.5 rounded-full">{filteredSubTools.length}</span>
                    </h2>
                    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-6 md:gap-8">
                      {filteredSubTools.map((tool, idx) => (
                        // Open the tool directly in ToolWorkspace
                        <OrganizepdfCard key={tool.uniqueKey} tool={tool} index={idx} onClick={(t) => { handleDirectToolSelect(t); }} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty state — shown when no category or sub-tool matches the query */}
                {filteredMainTools.length === 0 && filteredSubTools.length === 0 && (
                  <div className="text-center py-16 bg-white rounded-2xl border border-slate-200/80 shadow-sm text-slate-500">
                    <p className="text-base font-semibold text-slate-700">No tools found matching "{searchQuery}"</p>
                    <p className="text-xs text-slate-400 mt-1">Try searching with a different term or keyword.</p>
                  </div>
                )}
              </div>
            </main>
          </div>

          /* ── c) Sub-page views — one per category id ───────────────────── */
        ) : activePage === 'organize-pdf' ? (
          <OrganizepdfPage onBack={handlePageBack} />
        ) : activePage === 'convert-to-pdf' ? (
          <PDFtoConvertPage onBack={handlePageBack} />
        ) : activePage === 'convert-from-pdf' ? (
          <ConvertPDFPage onBack={handlePageBack} />
        ) : activePage === 'pdf-security' ? (
          <PDFSecurityPage onBack={handlePageBack} />
        ) : activePage === 'pdf-signature' ? (
          <PDFSignaturePage onBack={handlePageBack} />
        ) : activePage === 'pdf-ai-tools' ? (
          <AISmartFeaturesPage onBack={handlePageBack} />
        ) : activePage === 'compare-redaction' ? (
          <CompareRedactionPage onBack={handlePageBack} />
        ) : activePage === 'team-business' ? (
          <TeamBusinessPage onBack={handlePageBack} />
        ) : activePage === 'accessibility' ? (
          <AccessibilityPage onBack={handlePageBack} />
        ) : activePage === 'document-management' ? (
          <DocumentManagementPage onBack={handlePageBack} />
        ) : activePage === 'image-processing' ? (
          <ImageProcessingPage onBack={handlePageBack} />
        ) : activePage === 'pdf-reader' ? (
          <PDFReaderPage onBack={handlePageBack} />
        ) : activePage === 'review-annotation' ? (
          <ReviewAnnotationPage onBack={handlePageBack} />
        ) : activePage === 'fingerprint-auth-signature' ? (
          <FingerprintAuthenticationBiometricSignaturePage onBack={handlePageBack} />
        ) : activePage === 'pdf-copyright-protection' ? (
          <PDFCopyrightProtectionPage onBack={handlePageBack} />
        ) : activePage === 'software-about-us' ? (
          <SoftwareAboutUsPage onBack={handlePageBack} />
        ) : activePage === 'Contact-Us' ? (
          <ContactUsPage onBack={handlePageBack} />
        ) : activePage === 'shared' ? (
          <SharedDocumentViewerPage onBack={handlePageBack} />
        ) : activePage === 'manage-shares' ? (
          <ShareManagementPage onBack={handlePageBack} />
        // ) : activePage === 'AI-Agent' ? (
        //   <AIAgentPage onBack={handlePageBack} />
          /* ── d) Home Dashboard — default view ─────────────────────────── */
        ) : (
          <div className="w-full max-w-[1720px] mx-auto px-4 sm:px-6 md:px-10 py-4 overflow-x-hidden flex-1 flex flex-col relative z-0">
            <main className="flex-1 pt-4 pb-4 relative z-10">
              {/* Responsive grid: 2 cols on mobile → 3 on lg → 4 on xl */}
              <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-6 md:gap-8">
                {PDF_TOOLS.map((tool, idx) => (
                  <ToolCard
                    key={tool.id}
                    tool={tool}
                    index={idx}
                    onClick={handleToolClick}
                  />
                ))}
              </div>
            </main>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* GLOBAL FOOTER — links, stats, social icons, copyright              */}
      {/* ------------------------------------------------------------------ */}
      <AgentWidget onNavigateToCategory={navigateToPage} onNavigateToTool={handleDirectToolSelect} />
      <GlobalFooter />
    </div>
  );
}

