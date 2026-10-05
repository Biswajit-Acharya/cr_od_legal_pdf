import React from 'react';
import GenericPDFToolPage from '../../components/GenericPDFToolPage';

export default function PDFtoEditablePDFPage({ onBack }) {
  return (
    <GenericPDFToolPage
      toolName="PDF to Editable PDF"
      toolDesc="Convert a scanned or locked PDF into a fully editable PDF using OCR."
      apiEndpoint="/api/pdf/pdf-to-searchable/process"
      getFormData={(files, formState) => {
        const fd = new FormData();
        fd.append('file', files[0]);
        return fd;
      }}
      outputExt=".pdf"
      onBack={onBack}
    />
  );
}
