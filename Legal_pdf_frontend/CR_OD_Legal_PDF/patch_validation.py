import os
import re

directory = 'src/page/PDFtoConvert'

# Map component names to extensions and accept strings
extensions_map = {
    'BMPtoPDFPage.jsx': ('.bmp', 'image/bmp'),
    'CADDWGDXFtoPDFPage.jsx': ('.dwg, .dxf', '.dwg,.dxf'),
    'CSVtoPDFPage.jsx': ('.csv', 'text/csv'),
    'EmailEMLtoPDFPage.jsx': ('.eml', 'message/rfc822'),
    'EPUBtoPDFPage.jsx': ('.epub', 'application/epub+zip'),
    'ExceltoPDFPage.jsx': ('.xls, .xlsx', '.xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    'GIFtoPDFPage.jsx': ('.gif', 'image/gif'),
    'HEICtoPDFPage.jsx': ('.heic', 'image/heic'),
    'HTMLtoPDFPage.jsx': ('.html, .htm', 'text/html'),
    'IllustratorAItoPDFPage.jsx': ('.ai', 'application/postscript'),
    'JPGtoPDFPage.jsx': ('.jpg, .jpeg', 'image/jpeg'),
    'JSONtoPDFPage.jsx': ('.json', 'application/json'),
    'MarkdownMDtoPDFPage.jsx': ('.md', 'text/markdown'),
    'MOBItoPDFPage.jsx': ('.mobi', 'application/x-mobipocket-ebook'),
    'ODPtoPDFPage.jsx': ('.odp', 'application/vnd.oasis.opendocument.presentation'),
    'ODStoPDFPage.jsx': ('.ods', 'application/vnd.oasis.opendocument.spreadsheet'),
    'ODTtoPDFPage.jsx': ('.odt', 'application/vnd.oasis.opendocument.text'),
    'OutlookMSGtoPDFPage.jsx': ('.msg', 'application/vnd.ms-outlook'),
    'PhotoshopPSDtoPDFPage.jsx': ('.psd', 'image/vnd.adobe.photoshop'),
    'PNGtoPDFPage.jsx': ('.png', 'image/png'),
    'PowerPointtoPDFPage.jsx': ('.ppt, .pptx', '.ppt,.pptx,application/vnd.ms-powerpoint,application/vnd.openxmlformats-officedocument.presentationml.presentation'),
    'PublishertoPDFPage.jsx': ('.pub', 'application/x-mspublisher'),
    'RAWImagetoPDFPage.jsx': ('.raw, .cr2, .nef, .arw', 'image/x-adobe-dng,image/x-canon-cr2,image/x-nikon-nef,image/x-sony-arw,.raw,.cr2,.nef,.arw'),
    'RTFtoPDFPage.jsx': ('.rtf', 'application/rtf'),
    'SVGtoPDFPage.jsx': ('.svg', 'image/svg+xml'),
    'TexttoPDFPage.jsx': ('.txt', 'text/plain'),
    'TIFFtoPDFPage.jsx': ('.tiff, .tif', 'image/tiff'),
    'VisiotoPDFPage.jsx': ('.vsd, .vsdx', 'application/vnd.visio,.vsd,.vsdx'),
    'WebPtoPDFPage.jsx': ('.webp', 'image/webp'),
    'WordtoPDFPage.jsx': ('.doc, .docx', '.doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
    'XMLtoPDFPage.jsx': ('.xml', 'application/xml,text/xml'),
    'XPStoPDFPage.jsx': ('.xps', 'application/vnd.ms-xpsdocument'),
    'ZIPtoPDFPage.jsx': ('.zip', 'application/zip')
}

for filename, (exts_str, accept_str) in extensions_map.items():
    filepath = os.path.join(directory, filename)
    if not os.path.exists(filepath): continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    exts_list = [e.strip() for e in exts_str.split(',')]
    exts_js_array = str(exts_list)
    
    # Update input accept attribute
    content = re.sub(
        r'<input\s+ref=\{inputRef\}\s+type="file"\s+className="hidden"\s+onChange=\{handleFileChange\}\s*/>',
        f'<input ref={{inputRef}} type="file" className="hidden" accept="{accept_str}" onChange={{handleFileChange}} />',
        content
    )
    
    # Update addFile validation
    validation_code = f"""    const f = Array.from(newFiles)[0];
    if (!f) return;
    
    const fileExt = '.' + f.name.split('.').pop().toLowerCase();
    const allowedExts = {exts_js_array};
    if (!allowedExts.includes(fileExt)) {{
      setError(`Invalid file type. Please upload a valid ${{allowedExts.join(', ')}} file.`);
      return;
    }}"""
    
    content = re.sub(
        r'const f = Array\.from\(newFiles\)\[0\];\s*if \(\!f\) return;',
        validation_code,
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done patching frontend validation!")
