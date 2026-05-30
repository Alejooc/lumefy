from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


OUTPUT_PATH = Path(__file__).resolve().parent / "GA7-220501096-AA3-EV02_backend_mantis_clientes.docx"


def run(text: str, bold: bool = False) -> str:
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"


def paragraph(
    text: str = "",
    style: str | None = None,
    align: str | None = None,
    bold: bool = False,
    shading: str | None = None,
) -> str:
    props: list[str] = []
    if style:
        props.append(f"<w:pStyle w:val=\"{style}\"/>")
    if align:
        props.append(f"<w:jc w:val=\"{align}\"/>")
    if shading:
        props.append(f"<w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{shading}\"/>")
    ppr = f"<w:pPr>{''.join(props)}</w:pPr>" if props else ""
    runs: list[str] = []
    for i, line in enumerate(text.split("\n")):
        runs.append(run(line, bold=bold))
        if i < len(text.split("\n")) - 1:
            runs.append("<w:r><w:br/></w:r>")
    if not runs:
        runs.append(run("", bold=bold))
    return f"<w:p>{ppr}{''.join(runs)}</w:p>"


def bullet(text: str) -> str:
    return paragraph(f"- {text}", style="BodyText")


def capture_block(title: str) -> str:
    return (
        paragraph(title, style="Heading2")
        + paragraph("[PEGAR PANTALLAZO AQUI]", style="CaptureBox", align="center")
        + paragraph("")
    )


def cell(text: str, width: int, bold_text: bool = False, shading: str | None = None) -> str:
    parts = [
        f"<w:tc><w:tcPr><w:tcW w:w=\"{width}\" w:type=\"dxa\"/>"
    ]
    if shading:
        parts.append(f"<w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{shading}\"/>")
    parts.append("</w:tcPr>")
    parts.append(paragraph(text, style="TableText", bold=bold_text))
    parts.append("</w:tc>")
    return "".join(parts)


def table(rows: list[list[tuple[str, int, bool, str | None]]]) -> str:
    trs: list[str] = []
    for row in rows:
        cells = "".join(cell(text, width, bold_text, shading) for text, width, bold_text, shading in row)
        trs.append(f"<w:tr>{cells}</w:tr>")
    return (
        "<w:tbl>"
        "<w:tblPr>"
        "<w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"B7C9E2\"/>"
        "<w:left w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"B7C9E2\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"B7C9E2\"/>"
        "<w:right w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"B7C9E2\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"D9E2F3\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"D9E2F3\"/>"
        "</w:tblBorders>"
        "</w:tblPr>"
        + "".join(trs)
        + "</w:tbl>"
    )


def section_divider() -> str:
    return paragraph("", shading="D9EAF7")


def build_document_xml() -> str:
    parts: list[str] = []

    parts.append(paragraph("SERVICIO NACIONAL DE APRENDIZAJE SENA", "Title", "center"))
    parts.append(paragraph("Evidencia de producto", "Subtitle", "center"))
    parts.append(paragraph("GA7-220501096-AA3-EV02", "BigCenter", "center"))
    parts.append(paragraph("Modulos de software codificados y probados", "Subtitle", "center"))
    parts.append(paragraph(""))
    parts.append(paragraph("Proyecto: Lumefy", "CenteredInfo", "center"))
    parts.append(paragraph("Modulo evaluado: Clientes", "CenteredInfo", "center"))
    parts.append(paragraph("Componentes incluidos: backend y frontend_mantis", "CenteredInfo", "center"))
    parts.append(paragraph(""))
    parts.append(paragraph("Aprendiz: [COMPLETAR]", "CenteredInfo", "center"))
    parts.append(paragraph("Ficha: [COMPLETAR]", "CenteredInfo", "center"))
    parts.append(paragraph("Instructor: [COMPLETAR]", "CenteredInfo", "center"))
    parts.append(paragraph("Fecha: [COMPLETAR]", "CenteredInfo", "center"))
    parts.append(paragraph(""))
    parts.append(paragraph(""))

    parts.append(section_divider())
    parts.append(paragraph("Introduccion", "Heading1"))
    parts.append(
        paragraph(
            "Este documento presenta la evidencia funcional y tecnica del modulo de clientes del proyecto Lumefy. "
            "Para esta actividad solo se tuvo en cuenta el backend desarrollado en FastAPI y la interfaz "
            "administrativa Mantis desarrollada en Angular. El documento queda preparado para pegar capturas, "
            "mostrar validaciones y usarlo como guia del video."
        )
    )

    parts.append(paragraph("Objetivo", "Heading1"))
    parts.append(
        paragraph(
            "Comprobar que el modulo de clientes permite registrar, consultar, editar y gestionar informacion "
            "comercial y financiera, demostrando el cumplimiento funcional del backend y del frontend Mantis."
        )
    )

    parts.append(paragraph("Resumen del modulo probado", "Heading1"))
    parts.append(
        table(
            [
                [("Item", 2600, True, "D9EAF7"), ("Detalle", 7000, True, "D9EAF7")],
                [("Modulo", 2600, False, None), ("Clientes", 7000, False, None)],
                [("Backend", 2600, False, None), ("FastAPI - endpoints y validaciones del modulo de clientes", 7000, False, None)],
                [("Frontend", 2600, False, None), ("Mantis Angular - formulario, listado, perfil, linea de tiempo y abonos", 7000, False, None)],
                [("Prueba automatica", 2600, False, None), ("backend/tests/test_client_validations.py", 7000, False, None)],
                [("Resultado tecnico", 2600, False, None), ("7 pruebas OK", 7000, False, None)],
            ]
        )
    )

    parts.append(paragraph("Pantallas que debes usar para capturas", "Heading1"))
    parts.append(bullet("Listado de clientes: /clients"))
    parts.append(bullet("Crear cliente: /clients/new"))
    parts.append(bullet("Editar cliente: /clients/edit/{id}"))
    parts.append(bullet("Perfil del cliente: /clients/view/{id}"))
    parts.append(bullet("Pestana Linea de Tiempo dentro del perfil"))
    parts.append(bullet("Pestana Estado Financiero dentro del perfil"))

    histories = [
        (
            "Historia de usuario 1. Registrar cliente",
            "Como usuario con permisos de gestion, deseo registrar un cliente para asociarlo a ventas, seguimiento CRM y estado de cuenta.",
            [
                "El formulario carga correctamente.",
                "Permite registrar nombre, identificacion, correo, telefono, direccion, estado y limite de credito.",
                "Al guardar, muestra confirmacion y redirige al listado.",
            ],
            [
                "Nombre obligatorio, minimo 2 y maximo 120 caracteres.",
                "Identificacion maximo 30 caracteres.",
                "Identificacion solo admite letras, numeros, espacios, punto, slash y guion.",
                "Email con formato valido.",
                "Telefono solo admite numeros, espacios, parentesis, + y guion y maximo 25 caracteres.",
                "Direccion maximo 180 caracteres.",
                "Notas maximo 500 caracteres.",
                "Limite de credito no puede ser negativo.",
            ],
            [
                "Captura 1. Formulario vacio",
                "Captura 2. Validaciones del formulario",
                "Captura 3. Registro exitoso del cliente",
            ],
            "En el video debes decir que se esta probando el registro del modulo Clientes y que las validaciones se ejecutan antes de enviar al backend.",
        ),
        (
            "Historia de usuario 2. Consultar y buscar clientes",
            "Como usuario administrativo, deseo listar y buscar clientes para ubicar registros por nombre o estado.",
            [
                "El listado muestra clientes registrados.",
                "La busqueda por texto filtra coincidencias.",
                "El filtro por estado muestra los registros esperados.",
            ],
            [
                "Busqueda por texto.",
                "Filtro por estado activo, inactivo, prospecto y en riesgo.",
            ],
            [
                "Captura 4. Listado general",
                "Captura 5. Resultado de la busqueda o filtro",
            ],
            "En el video debes explicar que se valida la consulta funcional del modulo y la respuesta visual en Mantis.",
        ),
        (
            "Historia de usuario 3. Editar cliente",
            "Como usuario con permisos, deseo editar la informacion de un cliente para mantener actualizados sus datos comerciales.",
            [
                "La vista de edicion carga los datos actuales.",
                "Se pueden modificar datos validos y guardar cambios.",
                "Las validaciones siguen activas en la edicion.",
            ],
            [
                "Repetir una validacion de longitud o formato en la edicion.",
            ],
            [
                "Captura 6. Formulario de edicion",
                "Captura 7. Resultado despues de actualizar",
            ],
            "En el video debes mostrar que el mismo modelo se puede actualizar sin perder las reglas de validacion.",
        ),
        (
            "Historia de usuario 4. Consultar perfil del cliente",
            "Como usuario administrativo, deseo revisar la ficha del cliente para consultar saldo, datos de contacto y metricas.",
            [
                "Se visualiza nombre, identificacion, correo, telefono y direccion.",
                "Se visualiza saldo pendiente y limite de credito.",
                "Se visualizan metricas generales del cliente.",
            ],
            [
                "Validacion visual de fechas y datos registrados por el sistema.",
            ],
            [
                "Captura 8. Vista general del perfil del cliente",
            ],
            "En el video debes explicar que esta pantalla consolida informacion del backend en Mantis.",
        ),
        (
            "Historia de usuario 5. Registrar interaccion CRM",
            "Como usuario, deseo registrar una nota o interaccion para dejar evidencia del seguimiento realizado al cliente.",
            [
                "Se puede seleccionar tipo de interaccion.",
                "El contenido es obligatorio.",
                "La interaccion queda visible en la linea de tiempo.",
            ],
            [
                "Contenido minimo 3 caracteres.",
                "Contenido maximo 500 caracteres.",
            ],
            [
                "Captura 9. Validacion de la interaccion",
                "Captura 10. Linea de tiempo actualizada",
            ],
            "En el video debes decir que se esta probando la trazabilidad CRM del modulo.",
        ),
        (
            "Historia de usuario 6. Registrar abono",
            "Como usuario administrativo, deseo registrar un abono para disminuir la deuda del cliente y actualizar su estado de cuenta.",
            [
                "El modal de pago abre correctamente.",
                "El monto es obligatorio y debe ser mayor a 0.",
                "Despues del abono, el saldo cambia y se registra el movimiento.",
            ],
            [
                "Descripcion del pago obligatoria, minimo 3 y maximo 160 caracteres.",
                "Referencia del pago maximo 80 caracteres.",
            ],
            [
                "Captura 11. Modal de abono",
                "Captura 12. Validaciones del abono",
                "Captura 13. Estado de cuenta actualizado",
            ],
            "En el video debes mostrar antes y despues del saldo para evidenciar el cambio.",
        ),
    ]

    for title, description, tests, validations, captures, video_note in histories:
        parts.append(section_divider())
        parts.append(paragraph(title, "Heading1"))
        parts.append(paragraph(f"Descripcion: {description}", style="BodyText"))
        parts.append(
            table(
                [
                    [("Aspecto", 2200, True, "D9EAF7"), ("Detalle", 7400, True, "D9EAF7")],
                    [("Que probar", 2200, False, None), ("\n".join(f"- {item}" for item in tests), 7400, False, None)],
                    [("Validaciones clave", 2200, False, None), ("\n".join(f"- {item}" for item in validations), 7400, False, None)],
                    [("Que decir en video", 2200, False, None), (video_note, 7400, False, None)],
                ]
            )
        )
        for capture in captures:
            parts.append(capture_block(capture))

    parts.append(section_divider())
    parts.append(paragraph("Matriz de validaciones", "Heading1"))
    parts.append(
        table(
            [
                [("Campo", 2300, True, "D9EAF7"), ("Tipo de validacion", 2300, True, "D9EAF7"), ("Regla", 5000, True, "D9EAF7")],
                [("Nombre", 2300, False, None), ("Texto", 2300, False, None), ("Obligatorio, minimo 2, maximo 120 caracteres", 5000, False, None)],
                [("Identificacion", 2300, False, None), ("Caracteres y longitud", 2300, False, None), ("Maximo 30 caracteres; solo letras, numeros, espacios, punto, slash y guion", 5000, False, None)],
                [("Email", 2300, False, None), ("Formato", 2300, False, None), ("Debe ser correo valido", 5000, False, None)],
                [("Telefono", 2300, False, None), ("Caracteres y longitud", 2300, False, None), ("Maximo 25 caracteres; solo numeros, espacios, parentesis, + y guion", 5000, False, None)],
                [("Direccion", 2300, False, None), ("Longitud", 2300, False, None), ("Maximo 180 caracteres", 5000, False, None)],
                [("Notas", 2300, False, None), ("Longitud", 2300, False, None), ("Maximo 500 caracteres", 5000, False, None)],
                [("Limite de credito", 2300, False, None), ("Numero", 2300, False, None), ("No puede ser negativo", 5000, False, None)],
                [("Contenido de interaccion", 2300, False, None), ("Texto", 2300, False, None), ("Obligatorio, minimo 3, maximo 500", 5000, False, None)],
                [("Monto de abono", 2300, False, None), ("Numero", 2300, False, None), ("Obligatorio, mayor a 0", 5000, False, None)],
                [("Descripcion de pago", 2300, False, None), ("Texto", 2300, False, None), ("Obligatoria, minimo 3, maximo 160", 5000, False, None)],
                [("Referencia de pago", 2300, False, None), ("Longitud", 2300, False, None), ("Maximo 80 caracteres", 5000, False, None)],
                [("Fechas del sistema", 2300, False, None), ("Visualizacion", 2300, False, None), ("Se verifican en listado, perfil, linea de tiempo y estado de cuenta", 5000, False, None)],
            ]
        )
    )

    parts.append(section_divider())
    parts.append(paragraph("Prueba tecnica automatizada", "Heading1"))
    parts.append(
        paragraph(
            "Como soporte tecnico del backend se dejo una prueba automatizada enfocada en validaciones del modulo Clientes."
        )
    )
    parts.append(
        table(
            [
                [("Item", 2600, True, "D9EAF7"), ("Detalle", 7000, True, "D9EAF7")],
                [("Archivo", 2600, False, None), ("backend/tests/test_client_validations.py", 7000, False, None)],
                [("Total de casos", 2600, False, None), ("7", 7000, False, None)],
                [("Resultado", 2600, False, None), ("OK", 7000, False, None)],
                [("Valida", 2600, False, None), ("Nombre, identificacion, telefono, limite de credito, interacciones y pagos", 7000, False, None)],
            ]
        )
    )
    parts.append(capture_block("Captura 14. Ejecucion de la prueba automatizada"))

    parts.append(section_divider())
    parts.append(paragraph("Guion sugerido para el video", "Heading1"))
    for line in [
        "1. Ingresar al modulo Clientes en Mantis.",
        "2. Mostrar el formulario de crear cliente.",
        "3. Provocar errores de validacion y explicarlos.",
        "4. Crear un cliente valido.",
        "5. Mostrar el listado y aplicar una busqueda o filtro.",
        "6. Editar el cliente.",
        "7. Abrir el perfil del cliente.",
        "8. Registrar una interaccion.",
        "9. Registrar un abono.",
        "10. Mostrar el estado final del perfil, linea de tiempo y estado financiero.",
    ]:
        parts.append(bullet(line))
    parts.append(paragraph("Frases clave para decir en el video", "Heading2"))
    parts.append(bullet("El modulo probado es Clientes."))
    parts.append(bullet("Solo se tienen en cuenta backend y frontend_mantis."))
    parts.append(bullet("Ahora se demuestra la validacion de [campo]."))
    parts.append(bullet("El resultado esperado es [resultado] y el resultado obtenido fue [resultado]."))

    parts.append(section_divider())
    parts.append(paragraph("Versionamiento", "Heading1"))
    parts.append(bullet("Tomar captura de git status."))
    parts.append(bullet("Tomar captura de git log --oneline -5."))
    parts.append(bullet("Si tienes un commit del modulo, mostrarlo tambien en el video o en el documento."))
    parts.append(capture_block("Captura 15. git status"))
    parts.append(capture_block("Captura 16. git log --oneline -5"))

    parts.append(section_divider())
    parts.append(paragraph("Conclusiones", "Heading1"))
    parts.append(
        paragraph(
            "El modulo de clientes del proyecto Lumefy fue probado funcional y tecnicamente teniendo en cuenta "
            "el backend y la interfaz Mantis. Se verificaron las operaciones principales y las validaciones de "
            "texto, numeros, longitudes y caracteres especiales, dejando una estructura lista para anexar capturas "
            "y presentar el video de sustentacion."
        )
    )

    body = "".join(parts)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:wpc=\"http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas\" "
        "xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\" "
        "xmlns:o=\"urn:schemas-microsoft-com:office:office\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\" "
        "xmlns:v=\"urn:schemas-microsoft-com:vml\" "
        "xmlns:wp14=\"http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing\" "
        "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" "
        "xmlns:w10=\"urn:schemas-microsoft-com:office:word\" "
        "xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:w14=\"http://schemas.microsoft.com/office/word/2010/wordml\" "
        "xmlns:w15=\"http://schemas.microsoft.com/office/word/2012/wordml\" "
        "xmlns:wpg=\"http://schemas.microsoft.com/office/word/2010/wordprocessingGroup\" "
        "xmlns:wpi=\"http://schemas.microsoft.com/office/word/2010/wordprocessingInk\" "
        "xmlns:wne=\"http://schemas.microsoft.com/office/word/2006/wordml\" "
        "xmlns:wps=\"http://schemas.microsoft.com/office/word/2010/wordprocessingShape\" "
        "mc:Ignorable=\"w14 w15 wp14\">"
        f"<w:body>{body}"
        "<w:sectPr>"
        "<w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
        "<w:pgMar w:top=\"1200\" w:right=\"1100\" w:bottom=\"1200\" w:left=\"1100\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
        "</w:sectPr>"
        "</w:body></w:document>"
    )


def build_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:b/>
      <w:color w:val="1F4E79"/>
      <w:sz w:val="32"/>
      <w:szCs w:val="32"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:i/>
      <w:color w:val="44546A"/>
      <w:sz w:val="24"/>
      <w:szCs w:val="24"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="BigCenter">
    <w:name w:val="BigCenter"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:b/>
      <w:color w:val="2F5597"/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CenteredInfo">
    <w:name w:val="CenteredInfo"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="Heading1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:b/>
      <w:color w:val="1F1F1F"/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="Heading2"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:b/>
      <w:color w:val="2F5597"/>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="BodyText">
    <w:name w:val="BodyText"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TableText">
    <w:name w:val="TableText"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:sz w:val="20"/>
      <w:szCs w:val="20"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CaptureBox">
    <w:name w:val="CaptureBox"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="240" w:after="240"/>
      <w:ind w:left="240" w:right="240"/>
      <w:jc w:val="center"/>
      <w:shd w:val="clear" w:color="auto" w:fill="F4F8FC"/>
      <w:pBdr>
        <w:top w:val="single" w:sz="8" w:space="4" w:color="9FBAD0"/>
        <w:left w:val="single" w:sz="8" w:space="4" w:color="9FBAD0"/>
        <w:bottom w:val="single" w:sz="8" w:space="4" w:color="9FBAD0"/>
        <w:right w:val="single" w:sz="8" w:space="4" w:color="9FBAD0"/>
      </w:pBdr>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:color w:val="5B6572"/>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
</w:styles>
"""


def build_content_types_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""


def build_root_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""


def build_document_rels_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""


def build_core_xml() -> str:
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>GA7-220501096-AA3-EV02 backend y mantis</dc:title>
  <dc:subject>Evidencia de producto</dc:subject>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>
"""


def build_app_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <Company>OpenAI</Company>
  <LinksUpToDate>false</LinksUpToDate>
  <SharedDoc>false</SharedDoc>
  <HyperlinksChanged>false</HyperlinksChanged>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""


def main() -> None:
    with ZipFile(OUTPUT_PATH, "w", compression=ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", build_content_types_xml())
        docx.writestr("_rels/.rels", build_root_rels_xml())
        docx.writestr("docProps/core.xml", build_core_xml())
        docx.writestr("docProps/app.xml", build_app_xml())
        docx.writestr("word/document.xml", build_document_xml())
        docx.writestr("word/styles.xml", build_styles_xml())
        docx.writestr("word/_rels/document.xml.rels", build_document_rels_xml())
    print(f"Documento generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
