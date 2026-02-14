from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime

class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.primary_color = colors.HexColor("#1A237E")  # Deep Indigo
        self.secondary_color = colors.HexColor("#455A64") # Blue Grey
        self.accent_color = colors.HexColor("#0D47A1")   # Bright Blue
        
        self.title_style = ParagraphStyle(
            'HeaderTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            textColor=self.primary_color,
            spaceAfter=0,
            fontName='Helvetica-Bold'
        )
        
        self.subtitle_style = ParagraphStyle(
            'HeaderSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.secondary_color,
            spaceAfter=4
        )

        self.label_style = ParagraphStyle(
            'Label',
            parent=self.styles['Normal'],
            fontSize=9,
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
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=self.accent_color,
            alignment=TA_RIGHT
        )

    def _add_header(self, doc, elements, company=None, doc_type="FACTURA", doc_id=""):
        # Header Table: [Logo/Name] [Doc Info]
        company_name = company.name if company else "Lumefy SaaS"
        logo_text = Paragraph(company_name.upper(), self.title_style)
        
        # Company Details
        address = company.address if company and company.address else "Calle 123 #45-67, Edificio Tech"
        tax_id = company.tax_id if company and company.tax_id else "NIT: 900.123.456-7"
        phone = company.phone if company and company.phone else "+57 300 123 4567"
        website = company.website if company and company.website else "lumefy.io"

        company_info = [
            Paragraph(address, self.subtitle_style),
            Paragraph(f"NIT: {tax_id}" if "NIT" not in tax_id.upper() else tax_id, self.subtitle_style),
            Paragraph(f"Tel: {phone} | {website}", self.subtitle_style),
        ]
        
        doc_info = [
            Paragraph(doc_type, ParagraphStyle('DT', parent=self.title_style, alignment=TA_RIGHT, fontSize=18)),
            Paragraph(f"Ref: #{doc_id}", self.invoice_num_style),
            Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ParagraphStyle('FD', parent=self.value_style, alignment=TA_RIGHT)),
        ]

        header_data = [
            [[logo_text] + company_info, doc_info]
        ]
        
        t = Table(header_data, colWidths=[doc.width*0.6, doc.width*0.4])
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

    def generate_invoice(self, sale, company=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        elements = []

        # 1. Header
        self._add_header(doc, elements, company, "FACTURA DE VENTA", str(sale.id)[:8])

        # 2. Client & Details Info (Side by Side)
        client_name = sale.client.name if sale.client else 'Consumidor Final'
        client_address = getattr(sale.client, 'address', 'N/A')
        client_phone = getattr(sale.client, 'phone', 'N/A')
        
        info_data = [
            [Paragraph("DATOS DEL CLIENTE", self.label_style), Paragraph("DETALLES DE VENTA", self.label_style)],
            [Paragraph(client_name, self.value_style), Paragraph(f"Estado: {sale.status}", self.value_style)],
            [Paragraph(f"Dirección: {client_address}", self.value_style), Paragraph(f"Vendedor: {sale.user.full_name if sale.user else 'N/A'}", self.value_style)],
            [Paragraph(f"Tel: {client_phone}", self.value_style), Paragraph(f"Pago: {sale.payment_method or 'Manual'}", self.value_style)]
        ]
        
        t_info = Table(info_data, colWidths=[doc.width*0.5, doc.width*0.5])
        t_info.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (1, 0), 1, self.primary_color),
            ('BOTTOMPADDING', (0, 0), (1, 0), 5),
            ('TOPPADDING', (0, 1), (1, -1), 3),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 25))

        # 3. Items Table
        data = [[
            Paragraph('ITEM / PRODUCTO', self.label_style), 
            Paragraph('CANT.', self.label_style), 
            Paragraph('P. UNIT', self.label_style), 
            Paragraph('TOTAL', self.label_style)
        ]]
        
        for i, item in enumerate(sale.items):
            product_name = item.product.name if item.product else "Desconocido"
            sku = item.product.sku if item.product and item.product.sku else ""
            data.append([
                Paragraph(f"{product_name}<br/><font size=7 color=gray>{sku}</font>", self.value_style),
                str(item.quantity),
                f"${item.price:,.2f}",
                f"${item.total:,.2f}"
            ])
        
        # Summary rows at bottom
        data.append(['', '', Paragraph('SUBTOTAL', self.label_style), f"${sale.subtotal:,.2f}"])
        data.append(['', '', Paragraph('IMPUESTOS', self.label_style), f"${sale.tax:,.2f}"])
        data.append(['', '', Paragraph('TOTAL GNRAL', ParagraphStyle('TG', parent=self.label_style, fontSize=11, textColor=self.accent_color)), 
                     f"${sale.total:,.2f}"])

        table = Table(data, colWidths=[doc.width*0.55, doc.width*0.1, doc.width*0.15, doc.width*0.2])
        
        # Table Styling
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('LINEBELOW', (2, -3), (3, -1), 1, self.secondary_color),
        ]
        
        # Zebra striping
        for i in range(1, len(sale.items) + 1):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F5F5F5")))
        
        table.setStyle(TableStyle(style))
        elements.append(table)
        
        # 4. Footer
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("NOTAS Y CONDICIONES", self.label_style))
        elements.append(Paragraph(sale.notes or "Sin notas adicionales.", self.value_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Gracias por confiar en Lumefy. Este documento es un soporte legal de su transacción.", 
                                  ParagraphStyle('Footer', parent=self.value_style, alignment=TA_CENTER, textColor=colors.grey)))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_picking(self, sale, company=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        elements = []
        self._add_header(doc, elements, company, "LISTA DE PICKING", str(sale.id)[:8])

        data = [['Ubicación', 'SKU', 'Producto', 'Requerido', 'Confirmado']]
        for i, item in enumerate(sale.items):
            product_name = item.product.name if item.product else "Desconocido"
            code = item.product.sku or "-"
            location = "A-01-01" 
            data.append([location, code, product_name, str(item.quantity), "[  ]"])

        t = Table(data, colWidths=[100, 80, 200, 70, 70])
        style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), self.secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
        ]
        for i in range(1, len(data)):
             if i % 2 == 0: style.append(('BACKGROUND', (0, i), (-1, i), colors.whitesmoke))
        
        t.setStyle(TableStyle(style))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_packing(self, sale, company=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        elements = []
        self._add_header(doc, elements, company, "LISTA DE PACKING", str(sale.id)[:8])

        if hasattr(sale, 'packages') and sale.packages:
            for pkg in sale.packages:
                elements.append(Paragraph(f"Contenedor: {pkg.package_type.name} | Tracking: {pkg.tracking_number or 'PENDIENTE'}", self.label_style))
                pkg_data = [['Producto', 'SKU', 'Cant.']]
                for item in pkg.items:
                    prod = item.sale_item.product if item.sale_item and item.sale_item.product else None
                    pkg_data.append([prod.name if prod else "N/A", prod.sku if prod else "-", str(item.quantity)])
                
                t = Table(pkg_data, colWidths=[250, 100, 100])
                t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke)]))
                elements.append(t)
                elements.append(Spacer(1, 15))
        else:
            elements.append(Paragraph("Pendiente de asignación de paquetes.", self.value_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    def generate_purchase_order(self, purchase, company=None):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        elements = []
        company_name = company.name if company else "Lumefy SaaS"
        self._add_header(doc, elements, company, "ORDEN DE COMPRA", str(purchase.id)[:8])

        # Supplier Info
        supp = purchase.supplier
        info_data = [
            [Paragraph("PROVEEDOR", self.label_style), Paragraph("DETALLES DE ORDEN", self.label_style)],
            [Paragraph(supp.name if supp else "N/A", self.value_style), Paragraph(f"Estado: {purchase.status}", self.value_style)],
            [Paragraph(f"NIT: {getattr(supp, 'tax_id', 'N/A')}", self.value_style), Paragraph(f"Llegada: {purchase.expected_date.strftime('%d/%m/%Y') if purchase.expected_date else 'N/A'}", self.value_style)]
        ]
        elements.append(Table(info_data, colWidths=[doc.width*0.5, doc.width*0.5]))
        elements.append(Spacer(1, 20))

        data = [['Producto', 'SKU', 'Cant.', 'Costo Unit.', 'Total']]
        for i, item in enumerate(purchase.items):
            data.append([
                item.product.name if item.product else "N/A",
                item.product.sku if item.product else "-",
                str(item.quantity),
                f"${item.unit_cost:,.2f}",
                f"${item.subtotal:,.2f}"
            ])
            
        data.append(['', '', '', Paragraph('TOTAL', self.label_style), f"${purchase.total_amount:,.2f}"])

        t = Table(data, colWidths=[200, 80, 60, 90, 90])
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), self.accent_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
        ]
        for i in range(1, len(data)-1):
            if i % 2 == 0: style.append(('BACKGROUND', (0, i), (-1, i), colors.whitesmoke))
        
        t.setStyle(TableStyle(style))
        elements.append(t)

        doc.build(elements)
        buffer.seek(0)
        return buffer

