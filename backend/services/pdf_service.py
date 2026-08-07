import os
import markdown
import re
import base64
import mimetypes
from jinja2 import Template
from weasyprint import HTML
from config import settings


class PDFService:
    # Beautiful CSS template for printing manuals
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{{ title }}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700&display=swap');
            
            @page {
                size: A4;
                margin: 20mm;
                @bottom-right {
                    content: counter(page) " / " counter(pages);
                    font-family: 'Noto Sans JP', sans-serif;
                    font-size: 8pt;
                    color: #718096;
                }
                @bottom-left {
                    content: "{{ title }}";
                    font-family: 'Noto Sans JP', sans-serif;
                    font-size: 8pt;
                    color: #718096;
                }
            }

            body {
                font-family: 'Noto Sans JP', 'Helvetica Neue', Arial, sans-serif;
                color: #2D3748;
                line-height: 1.6;
                font-size: 11pt;
            }

            h1, h2, h3, h4 {
                color: #1A365D;
                font-weight: 700;
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                page-break-after: avoid;
                break-after: avoid;
            }

            h1 {
                font-size: 24pt;
                border-bottom: 3px solid #3182CE;
                padding-bottom: 8px;
                margin-top: 0;
            }

            h2 {
                font-size: 18pt;
                border-bottom: 1px solid #E2E8F0;
                padding-bottom: 6px;
            }

            h3 {
                font-size: 14pt;
            }

            /* Step Block - Prevents entire procedure step from splitting across page boundary */
            .step-block {
                page-break-inside: avoid;
                break-inside: avoid;
                margin-bottom: 1.5em;
            }

            p {
                margin-top: 0;
                margin-bottom: 1em;
            }

            /* Lists */
            ol, ul {
                margin-top: 0;
                margin-bottom: 1em;
                padding-left: 20px;
                page-break-inside: avoid;
                break-inside: avoid;
            }

            li {
                margin-bottom: 0.5em;
                page-break-inside: avoid;
                break-inside: avoid;
            }

            /* Code blocks */
            code {
                font-family: monospace;
                background-color: #EDF2F7;
                padding: 2px 4px;
                border-radius: 4px;
                font-size: 9.5pt;
            }

            pre {
                background-color: #F7FAFC;
                border: 1px solid #E2E8F0;
                padding: 12px;
                border-radius: 6px;
                overflow: auto;
                page-break-inside: avoid;
                break-inside: avoid;
            }

            pre code {
                background-color: transparent;
                padding: 0;
            }

            /* Blockquotes */
            blockquote {
                margin: 0 0 1em 0;
                padding: 10px 20px;
                background-color: #EBF8FF;
                border-left: 4px solid #3182CE;
                color: #2B6CB0;
                page-break-inside: avoid;
                break-inside: avoid;
            }

            /* Images - Auto-resized to fit within A4 page height alongside text */
            .image-container {
                text-align: left;
                margin: 12px 0;
                page-break-inside: avoid;
                break-inside: avoid;
            }

            img {
                max-width: 100%;
                max-height: 105mm;
                object-fit: contain;
                height: auto;
                border-radius: 6px;
                box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
                border: 1px solid #E2E8F0;
                page-break-inside: avoid;
                break-inside: avoid;
            }


            /* Forced Page Break */
            .page-break {
                page-break-before: always !important;
                break-before: page !important;
                height: 0;
                margin: 0;
                border: none;
                clear: both;
            }

            /* Tables */
            table {
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 1.5em;
                page-break-inside: avoid;
                break-inside: avoid;
            }

            tr {
                page-break-inside: avoid;
                break-inside: avoid;
            }


            th, td {
                border: 1px solid #CBD5E0;
                padding: 8px 12px;
                text-align: left;
            }

            th {
                background-color: #EDF2F7;
                font-weight: 700;
            }

            tr:nth-child(even) {
                background-color: #F7FAFC;
            }

            /* Layout utilities */
            .manual-meta {
                font-size: 9pt;
                color: #718096;
                margin-bottom: 30px;
                border-bottom: 1px solid #E2E8F0;
                padding-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <h1>{{ title }}</h1>
        <div class="manual-meta">
            作成日時: {{ created_at }}
        </div>
        <div class="manual-content">
            {{ content }}
        </div>
    </body>
    </html>
    """

    @staticmethod
    def _convert_image_paths_to_absolute(markdown_content: str) -> str:
        """
        Converts relative image paths like 'images/foo.png' or '/media/images/foo.png'
        to local absolute paths file:///app/media/... for WeasyPrint rendering.
        """
        def replace_path(match):
            img_alt = match.group(1)
            img_path = match.group(2)
            
            filename = os.path.basename(img_path)
            absolute_path = f"file://{settings.MEDIA_DIR}/images/{filename}"
            return f"![{img_alt}]({absolute_path})"

        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        return re.sub(pattern, replace_path, markdown_content)

    @staticmethod
    def _embed_images_as_base64(markdown_content: str) -> str:
        """
        Embeds local image files into Markdown as Base64 data URIs
        so the exported HTML contains self-contained standalone images.
        """
        def replace_to_base64(match):
            img_alt = match.group(1)
            img_path = match.group(2)
            
            filename = os.path.basename(img_path)
            abs_path = os.path.join(settings.MEDIA_DIR, "images", filename)
            
            if os.path.exists(abs_path):
                try:
                    mime_type, _ = mimetypes.guess_type(abs_path)
                    if not mime_type:
                        mime_type = "image/png"
                    with open(abs_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                    base64_url = f"data:{mime_type};base64,{encoded_string}"
                    return f"![{img_alt}]({base64_url})"
                except Exception as e:
                    print(f"Error encoding image to base64: {e}")
            
            return match.group(0)

        pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        return re.sub(pattern, replace_to_base64, markdown_content)

    @classmethod
    def generate_html(cls, title: str, markdown_content: str, created_at_str: str, embed_base64: bool = True) -> str:
        """
        Converts Markdown to a full HTML document using the custom template.
        If embed_base64 is True, local images are embedded directly as Data URIs.
        """
        if embed_base64:
            markdown_content = cls._embed_images_as_base64(markdown_content)

        # Convert custom pagebreak tags (<!-- pagebreak --> or [pagebreak]) to HTML div
        markdown_content = re.sub(
            r'<!--\s*pagebreak\s*-->|\[pagebreak\]',
            '<div class="page-break"></div>',
            markdown_content,
            flags=re.IGNORECASE
        )

        # Convert markdown to html (with table and other extensions)
        html_body = markdown.markdown(
            markdown_content,
            extensions=['extra', 'codehilite', 'toc']
        )
        
        # Wrap images in container divs for styling
        html_body = re.sub(
            r'<img ([^>]+)>',
            r'<div class="image-container"><img \1></div>',
            html_body
        )

        # Wrap h2/h3 sections into step-blocks to prevent page break splitting
        pattern = r'(<h[23][^>]*>.*?</h[23]>)'
        parts = re.split(pattern, html_body, flags=re.DOTALL)
        
        wrapped_parts = []
        if parts[0].strip():
            wrapped_parts.append(parts[0])
            
        for i in range(1, len(parts), 2):
            heading = parts[i]
            body_content = parts[i+1] if (i+1) < len(parts) else ""
            wrapped_parts.append(f'<div class="step-block">{heading}{body_content}</div>')
            
        if len(parts) > 1:
            html_body = "".join(wrapped_parts)

        template = Template(cls.HTML_TEMPLATE)
        return template.render(
            title=title,
            content=html_body,
            created_at=created_at_str
        )


    @classmethod
    def generate_pdf(cls, title: str, markdown_content: str, created_at_str: str, output_path: str):
        """
        Generates a PDF file from Markdown content.
        """
        # WeasyPrint requires local file:/// paths for local images
        processed_markdown = cls._convert_image_paths_to_absolute(markdown_content)
        html_content = cls.generate_html(title, processed_markdown, created_at_str, embed_base64=False)
        HTML(string=html_content).write_pdf(output_path)
