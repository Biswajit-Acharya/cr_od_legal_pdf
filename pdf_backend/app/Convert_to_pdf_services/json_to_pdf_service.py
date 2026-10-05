import json
import logging
from typing import Dict, Any, List

from app.core.paths import Paths
from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service

logger = logging.getLogger(__name__)

class JsonToPdfService:
    def validate_and_parse(self, content: str) -> Dict[str, Any]:
        """Validate JSON and detect optimal rendering mode."""
        if not content.strip():
            raise ValueError("Empty JSON provided.")
            
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # Provide useful error
            raise ValueError(f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}")
            
        # Detect recommended mode
        recommended_mode = "tree"
        if isinstance(data, list):
            if all(isinstance(i, dict) for i in data):
                recommended_mode = "table"
                
        return {
            "parsed": data,
            "recommended_mode": recommended_mode
        }

    def _render_table(self, data: Any) -> str:
        """Render JSON as a tabular HTML."""
        if not isinstance(data, list) or not data:
            return "<p>Data is not a valid non-empty array for Table mode.</p>"
            
        # Extract unique keys for headers
        keys = []
        for row in data:
            if isinstance(row, dict):
                for k in row.keys():
                    if k not in keys:
                        keys.append(k)
                        
        if not keys:
            return "<p>No tabular keys found.</p>"

        html = ["<table class='json-table'>", "<thead><tr>"]
        for k in keys:
            html.append(f"<th>{self._escape(str(k))}</th>")
        html.append("</tr></thead><tbody>")
        
        for row in data:
            html.append("<tr>")
            if isinstance(row, dict):
                for k in keys:
                    val = row.get(k, "")
                    # If nested object/array inside a table cell, stringify it
                    if isinstance(val, (dict, list)):
                        val = json.dumps(val)
                    elif val is None:
                        val = "null"
                    elif isinstance(val, bool):
                        val = "true" if val else "false"
                    html.append(f"<td>{self._escape(str(val))}</td>")
            else:
                # If the row itself is just a primitive in a list
                html.append(f"<td colspan='{len(keys)}'>{self._escape(str(row))}</td>")
            html.append("</tr>")
            
        html.append("</tbody></table>")
        return "".join(html)

    def _render_tree(self, data: Any) -> str:
        """Render JSON as a hierarchical tree."""
        return f"<div class='json-tree'>{self._render_tree_recursive(data)}</div>"
        
    def _render_tree_recursive(self, data: Any) -> str:
        if isinstance(data, dict):
            if not data:
                return "{}"
            html = ["<ul>"]
            for k, v in data.items():
                html.append(f"<li><strong>{self._escape(str(k))}:</strong> {self._render_tree_recursive(v)}</li>")
            html.append("</ul>")
            return "".join(html)
        elif isinstance(data, list):
            if not data:
                return "[]"
            html = ["<ul>"]
            for i, v in enumerate(data):
                html.append(f"<li><em>[{i}]</em> {self._render_tree_recursive(v)}</li>")
            html.append("</ul>")
            return "".join(html)
        elif data is None:
            return "<span class='val-null'>null</span>"
        elif isinstance(data, bool):
            return f"<span class='val-bool'>{'true' if data else 'false'}</span>"
        elif isinstance(data, (int, float)):
            return f"<span class='val-num'>{data}</span>"
        else:
            return f"<span class='val-str'>\"{self._escape(str(data))}\"</span>"

    def _render_kv(self, data: Any) -> str:
        """Render JSON in a flat Key-Value format layout."""
        # We can reuse the tree rendering but style it as key-value lines
        return f"<div class='json-kv'>{self._render_tree_recursive(data)}</div>"

    def _render_raw(self, content: str) -> str:
        """Render raw JSON text."""
        # Re-parse and dump for pretty printing
        try:
            data = json.loads(content)
            pretty = json.dumps(data, indent=4, ensure_ascii=False)
        except:
            pretty = content
        return f"<pre class='json-raw'><code>{self._escape(pretty)}</code></pre>"
        
    def _escape(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    async def process(
        self,
        request_id: str,
        filename: str,
        content: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        mode = config.get("mode", "raw")
        
        # Validation
        if not content.strip():
            raise ValueError("No JSON content provided.")
            
        try:
            parsed_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e.msg} at line {e.lineno}, column {e.colno}")
            
        # Determine HTML body based on mode
        if mode == "table":
            body_html = self._render_table(parsed_data)
        elif mode == "tree":
            body_html = self._render_tree(parsed_data)
        elif mode == "key-value":
            body_html = self._render_kv(parsed_data)
        else:
            body_html = self._render_raw(content)

        # Generate HTML Wrapper
        html_parts = []
        html_parts.append("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 13px; margin: 0; padding: 0px; color: #333; }
                .report-title { font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #111; }
                
                /* Table Mode */
                table.json-table { width: 100%; border-collapse: collapse; margin-top: 10px; page-break-inside: auto; }
                table.json-table thead { display: table-header-group; }
                table.json-table tr { page-break-inside: avoid; page-break-after: auto; }
                table.json-table th, table.json-table td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
                table.json-table th { background-color: #f8fafc; font-weight: bold; color: #334155; }
                table.json-table tr:nth-child(even) { background-color: #fcfcfc; }
                
                /* Tree / KV Mode */
                .json-tree ul, .json-kv ul { list-style-type: none; padding-left: 20px; margin: 4px 0; }
                .json-tree > ul, .json-kv > ul { padding-left: 0; }
                .json-tree li, .json-kv li { padding: 3px 0; line-height: 1.5; page-break-inside: avoid; }
                .val-str { color: #15803d; }
                .val-num { color: #0284c7; }
                .val-bool { color: #a16207; font-weight: bold; }
                .val-null { color: #94a3b8; font-style: italic; }
                
                .json-kv li { border-bottom: 1px solid #f1f5f9; }
                .json-kv > ul > li { border-bottom: 1px solid #e2e8f0; margin-bottom: 5px; }
                
                /* Raw Mode */
                .json-raw { 
                    font-family: 'Courier New', Courier, monospace; 
                    background: #f8fafc; 
                    padding: 15px; 
                    border-radius: 6px; 
                    border: 1px solid #e2e8f0; 
                    white-space: pre-wrap; 
                    word-wrap: break-word;
                    font-size: 12px;
                }
            </style>
        </head>
        <body>
        """)

        report_title = config.get("pdf_title", "")
        if report_title:
            html_parts.append(f"<div class='report-title'>{self._escape(report_title)}</div>")
            
        html_parts.append(body_html)
        html_parts.append("</body></html>")
        
        final_html = "\n".join(html_parts)

        # Forward to HtmlToPdfService
        pdf_filename = filename
        if pdf_filename.lower().endswith(".json"):
            pdf_filename = pdf_filename[:-5] + ".pdf"
        elif not pdf_filename.lower().endswith(".pdf"):
            pdf_filename += ".pdf"
            
        result = await html_to_pdf_service.process(
            request_id=request_id,
            input_type="html",
            content=final_html,
            page_size=config.get("page_size", "A4"),
            orientation=config.get("orientation", "portrait"),
            margin_preset=config.get("margin_preset", "normal"),
            custom_margin_top="", custom_margin_right="", custom_margin_bottom="", custom_margin_left="",
            custom_page_width="", custom_page_height="", custom_page_unit="px",
            print_background=True,
            header_text=config.get("header_text", ""),
            footer_text=config.get("footer_text", ""),
            page_numbers=config.get("page_numbers", True),
            title=config.get("pdf_title", ""),
            author=config.get("pdf_author", ""),
            subject=config.get("pdf_subject", ""),
            keywords="",
            password="", # JSON converter doesn't strictly request password but can be passed
            output_filename=pdf_filename
        )

        # Override download URL for json-to-pdf routes
        result["download_url"] = f"/api/convert-to-pdf/json-to-pdf/download/{request_id}/{result['filename']}"
        result["view_url"] = f"/api/convert-to-pdf/json-to-pdf/view/{request_id}/{result['filename']}"
        
        return result

json_to_pdf_service = JsonToPdfService()
