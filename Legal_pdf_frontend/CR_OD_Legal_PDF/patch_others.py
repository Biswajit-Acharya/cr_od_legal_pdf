import os
import re

directories = ['src/page/OrganizePDF', 'src/page/PDFSignature', 'src/page/PDFSecurity', 'src/page/AISmartFeatures', 'src/page/Accessibility', 'src/page/AccessibilityCompliance']

for d in directories:
    if not os.path.exists(d): continue
    for root, dirs, files in os.walk(d):
        for file in files:
            if not file.endswith('.jsx'): continue
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If the page already has a specific accept or is an image tool, skip
            if 'accept="image' in content or 'accept=".png' in content:
                continue
                
            # If it's a generic file input without accept, add accept=".pdf"
            if 'accept=".pdf"' not in content:
                content = re.sub(
                    r'<input\s+ref=\{inputRef\}\s+type="file"\s+className="hidden"\s+onChange=',
                    r'<input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange=',
                    content
                )
                content = re.sub(
                    r'<input\s+ref=\{inputRef\}\s+type="file"\s+onChange=',
                    r'<input ref={inputRef} type="file" accept=".pdf" onChange=',
                    content
                )
                
                # Update addFile validation for .pdf if it exists and doesn't have validation
                validation_code = """    const f = Array.from(newFiles)[0];
    if (!f) return;
    
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Invalid file type. Please upload a valid PDF file.');
      return;
    }"""
                # A lot of components use addFile(e.target.files) or addFiles(e.target.files)
                # This regex targets the first 'const f = Array.from(newFiles)[0]; if (!f) return;'
                if 'setError' in content and 'const f = Array.from' in content and 'fileExt' not in content:
                     content = re.sub(
                        r'const f = Array\.from\(newFiles\)\[0\];\s*if \(\!f\) return;',
                        validation_code,
                        content
                    )
                
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

print("Done patching other features!")
