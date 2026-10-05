import os
import csv
import logging
from pathlib import Path
from typing import Dict, Any, List

from app.core.paths import Paths
from app.Convert_to_pdf_services.html_to_pdf_service import html_to_pdf_service

logger = logging.getLogger(__name__)

class CsvToPdfService:
    def validate_csv_file(self, path: Path) -> None:
        """Validate that the file is CSV and safe."""
        if not path.exists():
            raise ValueError(f"File not found: {path.name}")
        if path.stat().st_size == 0:
            raise ValueError(f"File '{path.name}' is empty.")
            
        if path.stat().st_size > 50 * 1024 * 1024:
            raise ValueError(f"File '{path.name}' exceeds the 50 MB size limit.")
            
        ext = path.suffix.lower()
        if ext not in [".csv", ".txt"]:
            raise ValueError(f"File '{path.name}' has an unsupported extension. Only .csv is allowed.")

    def preview_csv(self, path: Path, delimiter: str = ',', encoding: str = 'utf-8') -> Dict[str, Any]:
        """Read a snippet of the CSV for previewing and configuration."""
        self.validate_csv_file(path)
        
        sample_rows = []
        columns = []
        try:
            with open(path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.reader(f, delimiter=delimiter)
                try:
                    columns = next(reader)
                except StopIteration:
                    raise ValueError("The CSV file is empty or invalid.")
                
                # ensure unique column names just in case
                unique_cols = []
                for i, col in enumerate(columns):
                    base = col.strip() or f"Column_{i+1}"
                    name = base
                    counter = 1
                    while name in unique_cols:
                        name = f"{base} ({counter})"
                        counter += 1
                    unique_cols.append(name)
                columns = unique_cols

                count = 0
                for row in reader:
                    # Pad row if shorter than columns
                    if len(row) < len(columns):
                        row.extend([""] * (len(columns) - len(row)))
                    # Truncate if longer
                    elif len(row) > len(columns):
                        row = row[:len(columns)]
                    sample_rows.append(row)
                    count += 1
                    if count >= 50:
                        break
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")

        return {
            "columns": columns,
            "sample_data": sample_rows,
            "total_sample": len(sample_rows)
        }

    async def process(
        self,
        request_id: str,
        filename: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process CSV configuration into a PDF."""
        upload_dir = Paths.request_upload(request_id)
        input_path = upload_dir / filename
        self.validate_csv_file(input_path)

        # Config extraction
        delimiter = config.get("delimiter", ",")
        encoding = config.get("encoding", "utf-8")
        has_header = config.get("has_header", True)
        
        # Columns config
        # format: [{"orig": "Col", "new": "My Col", "hidden": False, "align": "left", "width": "auto"}]
        columns_config = config.get("columns", [])
        
        # Row config
        sort_col = config.get("sort_col", None)
        sort_desc = config.get("sort_desc", False)
        search_query = config.get("search_query", "").lower()
        remove_empty = config.get("remove_empty", False)
        
        # Formatting
        null_replacement = config.get("null_replacement", "")

        # Read full data
        all_rows = []
        orig_columns = []
        try:
            with open(input_path, 'r', encoding=encoding, errors='replace') as f:
                reader = csv.reader(f, delimiter=delimiter)
                if has_header:
                    orig_columns = next(reader)
                else:
                    # peek first row
                    first_row = next(reader)
                    orig_columns = [f"Column {i+1}" for i in range(len(first_row))]
                    all_rows.append(first_row)
                    
                for row in reader:
                    all_rows.append(row)
        except Exception as e:
            raise ValueError(f"Failed to read full CSV: {str(e)}")

        # Normalize orig_columns
        unique_cols = []
        for i, col in enumerate(orig_columns):
            base = col.strip() or f"Column_{i+1}"
            name = base
            counter = 1
            while name in unique_cols:
                name = f"{base} ({counter})"
                counter += 1
            unique_cols.append(name)
        orig_columns = unique_cols

        # Re-map columns config if empty
        if not columns_config:
            columns_config = [{"orig": c, "new": c, "hidden": False, "align": "left"} for c in orig_columns]

        # Create mapping of orig index -> config
        col_map = {}
        for idx, col_name in enumerate(orig_columns):
            cfg = next((c for c in columns_config if c["orig"] == col_name), None)
            if cfg and not cfg.get("hidden", False):
                col_map[idx] = cfg

        # Filter and process rows
        filtered_rows = []
        for row in all_rows:
            # Pad
            if len(row) < len(orig_columns):
                row.extend([""] * (len(orig_columns) - len(row)))
                
            # Remove empty
            is_empty = all(not str(cell).strip() for cell in row)
            if remove_empty and is_empty:
                continue
                
            # Build mapped row
            mapped_row = []
            row_text = ""
            for idx in col_map.keys():
                val = str(row[idx]).strip() if idx < len(row) else ""
                if not val and null_replacement:
                    val = null_replacement
                mapped_row.append(val)
                row_text += f"{val.lower()} "
                
            # Search
            if search_query and search_query not in row_text:
                continue
                
            filtered_rows.append(mapped_row)
            
        # Sorting
        if sort_col:
            # find mapped index of sort_col
            sort_idx = -1
            for i, (orig_idx, cfg) in enumerate(col_map.items()):
                if cfg["orig"] == sort_col:
                    sort_idx = i
                    break
            
            if sort_idx != -1:
                # try numeric sort first
                def sort_key(row_val):
                    val = row_val[sort_idx]
                    try:
                        return (0, float(val.replace(',', '')))
                    except ValueError:
                        return (1, val)
                
                filtered_rows.sort(key=sort_key, reverse=sort_desc)

        # Generate HTML
        html_parts = []
        html_parts.append("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; margin: 0; padding: 0px; color: #333; }
                .report-title { font-size: 24px; font-weight: bold; margin-bottom: 5px; color: #111; }
                .report-subtitle { font-size: 14px; color: #666; margin-bottom: 20px; }
                table { width: 100%; border-collapse: collapse; margin-top: 10px; page-break-inside: auto; }
                thead { display: table-header-group; }
                tr { page-break-inside: avoid; page-break-after: auto; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f8fafc; font-weight: bold; color: #334155; }
                tr:nth-child(even) { background-color: #fcfcfc; }
            </style>
        </head>
        <body>
        """)

        report_title = config.get("report_title", "")
        report_subtitle = config.get("report_subtitle", "")
        if report_title:
            html_parts.append(f"<div class='report-title'>{report_title}</div>")
        if report_subtitle:
            html_parts.append(f"<div class='report-subtitle'>{report_subtitle}</div>")

        # Table
        html_parts.append("<table><thead><tr>")
        for orig_idx, cfg in col_map.items():
            align = cfg.get("align", "left")
            width_style = f"width:{cfg['width']};" if cfg.get("width") and cfg.get("width") != "auto" else ""
            html_parts.append(f"<th style='text-align:{align}; {width_style}'>{cfg['new']}</th>")
        html_parts.append("</tr></thead><tbody>")

        for r in filtered_rows:
            html_parts.append("<tr>")
            for i, (orig_idx, cfg) in enumerate(col_map.items()):
                align = cfg.get("align", "left")
                val = r[i]
                # very basic HTML escaping
                val = val.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_parts.append(f"<td style='text-align:{align};'>{val}</td>")
            html_parts.append("</tr>")
            
        html_parts.append("</tbody></table>")
        html_parts.append("</body></html>")
        
        final_html = "\n".join(html_parts)

        # Forward to HtmlToPdfService
        pdf_filename = filename.rsplit('.', 1)[0] + ".pdf"
        
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
            password=config.get("password", ""),
            output_filename=pdf_filename
        )

        # Fix download URL to point to our router endpoint instead of HTML's
        result["download_url"] = f"/api/convert-to-pdf/csv-to-pdf/download/{request_id}/{result['filename']}"
        result["view_url"] = f"/api/convert-to-pdf/csv-to-pdf/view/{request_id}/{result['filename']}"
        
        return result

csv_to_pdf_service = CsvToPdfService()
