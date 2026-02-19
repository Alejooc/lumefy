from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime
import os
import requests
from reportlab.lib.utils import ImageReader

class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        # Corporate Colors
        self.primary_color = colors.HexColor("#1677ff")  # Corporate Blue
        self.secondary_color = colors.HexColor("#595959") # Dark Grey
        self.accent_color = colors.HexColor("#0D47A1")   # Deep Blue
        self.light_bg = colors.HexColor("#f5f5f5")       # Light Grey
        
        # Paths
        self.base_assets_path = r"c:\Angular\lumefy\frontend_mantis\src"

        self.title_style = ParagraphStyle(
            'HeaderTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=self.primary_color,
            spaceAfter=2,
            fontName='Helvetica-Bold'
        )
        
        self.subtitle_style = ParagraphStyle(
            'HeaderSubtitle',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.secondary_color,
            leading=11
        )

        self.label_style = ParagraphStyle(
            'Label',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica-Bold',
            textColor=colors.black
        )

        self.value_style = ParagraphStyle(
            'Value',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.black
        )

        self.invoice_num_style = ParagraphStyle(
            'InvoiceNum',
            parent=self.styles['Heading2'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            alignment=TA_RIGHT
        )

    def _get_logo_image(self, url, width=120, height=50):
        """
        Retrieves logo image from URL (http) or local path.
        Returns an Image object or None.
        """
        try:
            img_data = None
            
            # 1. Handle Remote URL
            if url and (url.startswith("http://") or url.startswith("https://")):
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        img_data = BytesIO(response.content)
                except:
                    pass # Fallback to None
            
            # 2. Handle Local Path (assets/...)
            elif url and "assets/" in url:
                # Remove leading slash or definition issues
                clean_path = url.replace("/", "\\")
                if clean_path.startswith("\\"): clean_path = clean_path[1:]
                
                # Construct absolute path: c:\Angular\...\src\assets\images...
                full_path = os.path.join(self.base_assets_path, clean_path)
                
                if os.path.exists(full_path):
                    img_data = full_path

            if img_data:
                img = Image(img_data)
                
                # Resize keeping aspect ratio
                img_width = img.drawWidth
                img_height = img.drawHeight
                
                aspect = img_height / float(img_width)
                
                # Fit to box
                if img_width > width:
                    img.drawWidth = width
                    img.drawHeight = width * aspect
                elif img_height > height:
                    img.drawHeight = height
                    img.drawWidth = height / aspect
                    
                return img

        except Exception as e:
            print(f"Error loading logo: {e}")
            return None
        
        return None

    def _add_header(self, doc, elements, company=None, doc_type="DOCUMENTO", doc_id=""):
        # 1. Prepare Data
        company_name = company.name if company else "Lumefy SaaS"
        address = company.address if company and company.address else "Calle 123 #45-67"
        tax_id = company.tax_id if company and company.tax_id else "NIT: 900.123.456-7"
        phone = company.phone if company and company.phone else "+57 300 123 4567"
        website = company.website if company and company.website else "www.lumefy.io"
        logo_url = company.logo_url if company else "assets/images/logo-dark.svg" # Default fallback
        # SVG fallback not supported by ReportLab efficiently without svglib, assume png/jpg or text
        # If SVG, we might skip or try. For now, let's assume if it fails it fails gracefully.

        # 2. Logo
        logo_img = self._get_logo_image(logo_url)
        
        left_content = []
        if logo_img:
            left_content.append(logo_img)
            left_content.append(Spacer(1, 5))
        else:
            left_content.append(Paragraph(company_name.upper(), self.title_style))
            
        left_content.append(Paragraph(address, self.subtitle_style))
        left_content.append(Paragraph(f"NIT: {tax_id}", self.subtitle_style))
        left_content.append(Paragraph(f"{phone} | {website}", self.subtitle_style))

        right_content = [
            Paragraph(doc_type.upper(), ParagraphStyle('DT', parent=self.styles['Heading2'], alignment=TA_RIGHT, fontSize=16, textColor=self.primary_color)),
            Paragraph(f"#{doc_id}", self.invoice_num_style),
            Spacer(1, 5),
            Paragraph(f"<b>FECHA:</b> {datetime.now().strftime('%d/%m/%Y')}", ParagraphStyle('FD', parent=self.value_style, alignment=TA_RIGHT)),
        ]

        # 3. Create Table
        data = [[left_content, right_content]]
        t = Table(data, colWidths=[doc.width*0.6, doc.width*0.4])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        
        elements.append(t)
        
        # 4. Divider Line
        elements.append(Spacer(1, 15))
        elements.append(Table([['']], colWidths=[doc.width], rowHeights=[2], style=TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), self.primary_color)
        ])))
        elements.append(Spacer(1, 15))

    def generate_invoice(self, sale, company=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []

        # 1. Header
        self._add_header(doc, elements, company, "FACTURA DE VENTA", str(sale.id).split('-')[0].upper())

        # 2. Client & Details Info (Side by Side)
        client_name = sale.client.name.upper() if sale.client else 'CONSUMIDOR FINAL'
        client_address = getattr(sale.client, 'address', '---')
        client_phone = getattr(sale.client, 'phone', '---')
        client_email = getattr(sale.client, 'email', '---')
        
        # Info Box Style
        info_data = [
            [
                [
                    Paragraph("FACTURAR A:", self.label_style),
                    Paragraph(client_name, ParagraphStyle('CN', parent=self.value_style, fontSize=10, fontName='Helvetica-Bold')),
                    Paragraph(client_address, self.value_style),
                    Paragraph(f"Tel: {client_phone}", self.value_style),
                    Paragraph(f"Email: {client_email}", self.value_style),
                ],
                [
                    Paragraph("DETALLES:", self.label_style),
                    Paragraph(f"<b>Estado:</b> {sale.status}", self.value_style),
                    Paragraph(f"<b>Vendedor:</b> {sale.user.full_name if sale.user else 'System'}", self.value_style),
                    Paragraph(f"<b>Método Pago:</b> {sale.payment_method or 'Efectivo'}", self.value_style),
                ]
            ]
        ]
        
        t_info = Table(info_data, colWidths=[doc.width*0.6, doc.width*0.4])
        t_info.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 25))

        # 3. Items Table
        headers = [
            Paragraph('<b>ITEM / DESCRIPCIÓN</b>', ParagraphStyle('TH', fontSize=8, textColor=colors.white)), 
            Paragraph('<b>CANT.</b>', ParagraphStyle('TH_C', fontSize=8, textColor=colors.white, alignment=TA_CENTER)), 
            Paragraph('<b>PRECIO UNIT.</b>', ParagraphStyle('TH_R', fontSize=8, textColor=colors.white, alignment=TA_RIGHT)), 
            Paragraph('<b>TOTAL</b>', ParagraphStyle('TH_R2', fontSize=8, textColor=colors.white, alignment=TA_RIGHT))
        ]
        
        data = [headers]
        
        for item in sale.items:
            product_name = item.product.name if item.product else "Producto Desconocido"
            sku = item.product.sku if item.product else ""
            
            desc = f"<b>{product_name}</b>"
            if sku: desc += f"<br/><font size=7 color=#666>SKU: {sku}</font>"
            
            data.append([
                Paragraph(desc, self.value_style),
                Paragraph(str(item.quantity), ParagraphStyle('TD_C', parent=self.value_style, alignment=TA_CENTER)),
                Paragraph(f"${item.price:,.2f}", ParagraphStyle('TD_R', parent=self.value_style, alignment=TA_RIGHT)),
                Paragraph(f"${item.total:,.2f}", ParagraphStyle('TD_R', parent=self.value_style, alignment=TA_RIGHT))
            ])
        
        # Summary
        data.append(['', '', Paragraph('<b>SUBTOTAL</b>', self.label_style), Paragraph(f"${sale.subtotal:,.2f}", ParagraphStyle('S_R', alignment=TA_RIGHT, fontSize=9))])
        data.append(['', '', Paragraph('<b>IMPUESTOS</b>', self.label_style), Paragraph(f"${sale.tax:,.2f}", ParagraphStyle('S_R', alignment=TA_RIGHT, fontSize=9))])
        data.append(['', '', Paragraph('<b>TOTAL</b>', ParagraphStyle('T_B', fontSize=10, fontName='Helvetica-Bold', textColor=self.primary_color)), 
                     Paragraph(f"${sale.total:,.2f}", ParagraphStyle('T_V', fontSize=10, fontName='Helvetica-Bold', alignment=TA_RIGHT, textColor=self.primary_color))])

        col_widths = [doc.width*0.5, doc.width*0.15, doc.width*0.15, doc.width*0.2]
        table = Table(data, colWidths=col_widths)
        
        # Styling
        style = [
            # Header Row
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # General
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -4), 0.5, colors.HexColor("#e0e0e0")), # Grid for items
            
            # Summary Section (Last 3 rows)
            ('LINEABOVE', (-2, -3), (-1, -3), 1, colors.HexColor("#333")), # Line above Subtotal
            ('LINEABOVE', (-2, -1), (-1, -1), 1, self.primary_color),      # Line above Total
        ]
        
        # Zebra Striping
        for i in range(1, len(sale.items) + 1):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), self.light_bg))
        
        table.setStyle(TableStyle(style))
        elements.append(table)
        
        # 4. Footer & Notes
        elements.append(Spacer(1, 40))
        if sale.notes:
            elements.append(Paragraph("<b>NOTAS:</b>", self.label_style))
            elements.append(Paragraph(sale.notes, self.value_style))
            elements.append(Spacer(1, 10))

        footer_text = "Gracias por su compra. Documento generado por Lumefy SaaS."
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=self.value_style, alignment=TA_CENTER, textColor=colors.grey, fontSize=8)))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_picking(self, sale, company=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        self._add_header(doc, elements, company, "LISTA DE PICKING", str(sale.id).split('-')[0].upper())

        headers = ['UBICACIÓN', 'SKU', 'PRODUCTO', 'REQ', 'CHECK']
        data = [headers]
        for item in sale.items:
            product_name = item.product.name if item.product else "Desconocido"
            code = item.product.sku or "-"
            location = "A-01" # Placeholder
            data.append([location, code, product_name, str(item.quantity), "[   ]"])

        t = Table(data, colWidths=[80, 80, 250, 60, 60])
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
             ('ALIGN', (4, 0), (-1, -1), 'CENTER'),
        ]
        for i in range(1, len(data)):
             if i % 2 == 0: style.append(('BACKGROUND', (0, i), (-1, i), self.light_bg))
        
        t.setStyle(TableStyle(style))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_packing(self, sale, company=None):
        return self.generate_picking(sale, company) # Re-use for now, upgrade later if needed

    def generate_purchase_order(self, purchase, company=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        self._add_header(doc, elements, company, "ORDEN DE COMPRA", str(purchase.id).split('-')[0].upper())

        # Supplier Info
        supp = purchase.supplier
        info_data = [
            [
                Paragraph("<b>PROVEEDOR:</b>", self.label_style),
                Paragraph(supp.name if supp else "N/A", self.value_style),
                Paragraph(f"NIT: {getattr(supp, 'tax_id', 'N/A')}", self.value_style),
            ],
            [
                Paragraph(f"<b>Estado:</b> {purchase.status}", self.value_style),
                Paragraph(f"<b>Fecha Entrega:</b> {purchase.expected_date.strftime('%d/%m/%Y') if purchase.expected_date else '---'}", self.value_style)
            ]
        ]
        elements.append(Table(info_data, colWidths=[doc.width*0.6, doc.width*0.4]))
        elements.append(Spacer(1, 20))

        headers = ['PRODUCTO', 'SKU', 'CANT.', 'COSTO', 'TOTAL']
        data = [headers]
        for item in purchase.items:
            product_name = item.product.name if item.product else "N/A"
            if item.variant:
                product_name += f" - {item.variant.name}"
            
            sku = "-"
            if item.variant and item.variant.sku:
                 sku = item.variant.sku
            elif item.product:
                 sku = item.product.sku or "-"

            data.append([
                product_name,
                sku,
                str(item.quantity),
                f"${item.unit_cost:,.2f}",
                f"${item.subtotal:,.2f}"
            ])
            
        data.append(['', '', '', 'TOTAL', f"${purchase.total_amount:,.2f}"])

        t = Table(data, colWidths=[200, 80, 60, 90, 90])
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('BACKGROUND', (-2, -1), (-1, -1), self.light_bg),
            ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
        ]
        for i in range(1, len(data)-1):
            if i % 2 == 0: style.append(('BACKGROUND', (0, i), (-1, i), self.light_bg))
        
        t.setStyle(TableStyle(style))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

