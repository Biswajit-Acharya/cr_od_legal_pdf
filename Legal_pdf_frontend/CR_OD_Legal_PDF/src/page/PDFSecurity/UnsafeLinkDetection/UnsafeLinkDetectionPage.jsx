import React from 'react';
import ToolWorkspace from '../../ToolWorkspace';
import UnsafeLinkDetectionResult from './UnsafeLinkDetectionResult';

const UnsafeLinkDetectionPage = () => {
  return (
    <ToolWorkspace
      toolName="Unsafe Link Detection"
      title="Unsafe Link Detection"
      description="Extract and heuristically analyze all hyperlinks in a PDF to identify suspicious or potentially malicious URLs."
      icon={null}
      accept=".pdf"
      RenderResult={UnsafeLinkDetectionResult}
    />
  );
};

export default UnsafeLinkDetectionPage;
