#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leta-Takip — Tüm formlar için örnek PDF'ler
BEP Raporu, ONAM Formu ve Çocuk Takip Bilgi Formu örneklerini oluşturur (son halleriyle).
Çalıştırma: python scripts/olustur_ornek_form_pdfleri.py
"""

import os
import sys
import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("Hata: reportlab yüklü değil. Şunu çalıştırın: pip install reportlab")
    sys.exit(1)

PDF_AVAILABLE = True
TURKISH_FONT_NAME = None


def _register_font():
    global TURKISH_FONT_NAME
    try:
        if sys.platform == "win32":
            path = "C:/Windows/Fonts/segoeui.ttf"
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont("SegoeUI", path))
                TURKISH_FONT_NAME = "SegoeUI"
                return "SegoeUI"
        TURKISH_FONT_NAME = "Helvetica"
        return "Helvetica"
    except Exception:
        TURKISH_FONT_NAME = "Helvetica"
        return "Helvetica"


def _pdf_page_canvas_callbacks(form_title):
    """Her sayfada üstte Leta + form adı + çizgi, altta çizgi + sayfa numarası."""
    font_name = TURKISH_FONT_NAME or "Helvetica"
    w, h = A4[0], A4[1]
    margin = 1.5 * cm

    def _draw(canvas, doc):
        canvas.saveState()
        page_num = canvas.getPageNumber()
        canvas.setFont(font_name, 9)
        canvas.setFillColor(colors.HexColor("#666666"))
        header_y = h - 1 * cm
        canvas.drawString(margin, header_y, f"Leta Aile ve Çocuk — {form_title}")
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.setLineWidth(0.5)
        canvas.line(margin, header_y - 0.3 * cm, w - margin, header_y - 0.3 * cm)
        footer_y = 1.5 * cm
        canvas.line(margin, footer_y + 0.4 * cm, w - margin, footer_y + 0.4 * cm)
        canvas.drawRightString(w - margin, footer_y, f"Sayfa {page_num}")
        canvas.restoreState()

    return _draw, _draw


def _s(v):
    return (v or "").strip() if v is not None else ""


def _evet_hayir(n):
    if n is None:
        return ""
    return "Evet" if n == 1 else "Hayır"


def _radio(secili, secenekler):
    out = []
    for val, lbl in secenekler:
        x = "( X )" if _s(secili) == val or _s(secili) == lbl else "( )"
        out.append(f"{x} {lbl}")
    return "   ".join(out)


def build_bep_pdf(path, font_name):
    """Örnek BEP Raporu PDF."""
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=0.8 * cm, rightMargin=0.8 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    story = []
    styles = getSampleStyleSheet()
    on_first, on_later = _pdf_page_canvas_callbacks("BEP Raporu")

    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Heading1"], fontName=font_name, fontSize=16,
        textColor=colors.HexColor("#1a1a1a"), spaceAfter=30, alignment=TA_CENTER,
    )
    info_style = ParagraphStyle(
        "InfoStyle", parent=styles["Normal"], fontName=font_name, fontSize=11, spaceAfter=12,
    )

    story.append(Paragraph("BİREYSEL EĞİTİM PROGRAMI (BEP)", title_style))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("<b>Çocuk Adı:</b> Örnek Danışan Adı", info_style))
    story.append(Paragraph("<b>Doğum Tarihi:</b> 2018-05-12", info_style))
    story.append(Paragraph("<b>Program Yılı:</b> 2025", info_style))
    story.append(Spacer(1, 0.5 * cm))

    AYLAR_KISA = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
    beceriler = [
        "Erken Okur Yazarlık Becerisi",
        "Yazı Farkındalığı",
        "Hece Bilgisi",
        "Uyak Farkındalığı",
        "Sesbilişsel Farkındalık",
        "İnce Motor Becerileri",
        "İşitsel ve Görsel Algı Dikkat",
        "Neden Sonuç İlişkisi",
        "Muhakeme Tahmin Etme",
    ]
    header_row = ["Hedef Beceriler"] + AYLAR_KISA
    data = [header_row]
    for beceri in beceriler:
        row = [beceri] + ["✓", "○", "○", "○", "○", "○", "○", "○", "○", "○", "○", "○"]
        data.append(row)

    col_widths = [4.2 * cm] + [1.15 * cm] * 12
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.6 * cm))
    legend_style = ParagraphStyle(
        "Legend", parent=styles["Normal"], fontName=font_name, fontSize=9,
    )
    story.append(Paragraph("Açıklama: ✓ = Hedeflendi / Gösterildi, ○ = Henüz değerlendirilmedi", legend_style))
    doc.build(story, onFirstPage=on_first, onLaterPages=on_later)
    print(f"  [OK] BEP Raporu: {path}")


def build_onam_pdf(path, font_name):
    """Örnek ONAM Formu PDF."""
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    story = []
    styles = getSampleStyleSheet()
    on_first, on_later = _pdf_page_canvas_callbacks("ONAM Formu")

    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Heading1"], fontName=font_name, fontSize=16,
        textColor=colors.HexColor("#1a1a1a"), spaceAfter=30, alignment=TA_CENTER,
    )
    info_style = ParagraphStyle(
        "InfoStyle", parent=styles["Normal"], fontName=font_name, fontSize=11,
        spaceAfter=15, leftIndent=1 * cm,
    )
    normal_style = ParagraphStyle(
        "NormalTurkish", parent=styles["Normal"], fontName=font_name, fontSize=10,
    )

    story.append(Paragraph("KİŞİSEL VERİ KORUMA ONAM FORMU", title_style))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("<b>Danışan Adı:</b> Örnek Danışan Adı Soyadı", info_style))
    story.append(Paragraph("<b>Danışan İmza Tarihi:</b> 2025-01-15", info_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>Terapist Adı:</b> Örnek Terapist Adı", info_style))
    story.append(Paragraph("<b>Terapist İmza Tarihi:</b> 2025-01-15", info_style))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>Onam Durumu:</b> Onaylandı", info_style))
    story.append(Paragraph("<b>Oluşturma Tarihi:</b> " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), info_style))
    story.append(Spacer(1, 1 * cm))
    onam_text = """
    Bu form, kişisel verilerin korunması ve işlenmesi konusunda danışanın bilgilendirilmesi ve onayının alınması amacıyla düzenlenmiştir.

    Danışan, kişisel verilerinin işlenmesi konusunda bilgilendirilmiş ve bu konuda onay vermiştir.
    """
    story.append(Paragraph(onam_text, normal_style))
    doc.build(story, onFirstPage=on_first, onLaterPages=on_later)
    print(f"  [OK] ONAM Formu: {path}")


def build_cocuk_takip_pdf(path, font_name):
    """Örnek Çocuk Takip Bilgi Formu PDF (form düzeni, bölümler, ( X ) stili)."""
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    story = []
    styles = getSampleStyleSheet()
    on_first, on_later = _pdf_page_canvas_callbacks("Çocuk Takip Bilgi Formu")

    title_style = ParagraphStyle(
        "FormTitle", parent=styles["Heading1"], fontName=font_name, fontSize=16,
        textColor=colors.HexColor("#1a1a1a"), spaceAfter=20, alignment=TA_CENTER,
    )
    sect_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontName=font_name, fontSize=12,
        textColor=colors.HexColor("#333333"), spaceBefore=18, spaceAfter=10, leftIndent=0,
    )
    q_style = ParagraphStyle(
        "Question", parent=styles["Normal"], fontName=font_name, fontSize=10, spaceAfter=4, leftIndent=0,
    )
    a_style = ParagraphStyle(
        "Answer", parent=styles["Normal"], fontName=font_name, fontSize=10,
        spaceAfter=12, leftIndent=1 * cm, textColor=colors.HexColor("#222222"),
    )

    story.append(Paragraph("ÇOCUK TAKİP BİLGİ FORMU", title_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("<b>Adı Soyadı:</b> Örnek Danışan Adı Soyadı", a_style))
    story.append(Paragraph("<b>Form Tarihi:</b> " + datetime.datetime.now().strftime("%Y-%m-%d"), a_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Doğum Süreci ve Doğum Sonrasına İlişkin Bilgiler", sect_style))
    story.append(Paragraph("Cinsiyeti:", q_style))
    story.append(Paragraph(_radio("Erkek", [("Kız", "Kız"), ("Erkek", "Erkek")]), a_style))
    story.append(Paragraph("Doğum Tarihi (gg/aa/yyyy):", q_style))
    story.append(Paragraph("12.05.2018", a_style))
    story.append(Paragraph("Doğum Yeri:", q_style))
    story.append(Paragraph("Ankara", a_style))
    story.append(Paragraph("Gebelik Şekli:", q_style))
    story.append(Paragraph(_radio("Planlı", [("Planlı", "Planlı"), ("Plansız", "Plansız")]), a_style))
    story.append(Paragraph("Doğum Şekli:", q_style))
    story.append(Paragraph(_radio("Normal", [("Normal", "Normal"), ("Sezaryen", "Sezaryen"), ("Müdahaleli", "Müdahaleli-Vakum"), ("Diğer", "Diğer")]), a_style))
    story.append(Paragraph("Çocuğunuz doğumun esnasında ya da hemen sonrasında bir problem yaşadı mı?", q_style))
    story.append(Paragraph(_radio("Hayır", [("Evet", "Evet"), ("Hayır", "Hayır")]), a_style))
    story.append(Paragraph("Anne sütü alma durumu:", q_style))
    story.append(Paragraph(_radio("Aldı", [("Almadı", "Almadı"), ("Aldı", "Aldı")]) + " — 18 ay", a_style))
    story.append(Paragraph("Bebekliğinin ilk yıllarında temel bakım veren:", q_style))
    story.append(Paragraph("Anne ve baba", a_style))

    story.append(Paragraph("Temel Gelişim Bilgileri", sect_style))
    story.append(Paragraph("Çocuğunuz kaç yaşında yürüdü:", q_style))
    story.append(Paragraph("1 yaş", a_style))
    story.append(Paragraph("Çocuğunuz kaç yaşında tuvalet eğitimini tamamladı:", q_style))
    story.append(Paragraph("2,5 yaş", a_style))
    story.append(Paragraph("Çocuğunuz kaç yaşında konuştu:", q_style))
    story.append(Paragraph("1,5 yaş", a_style))
    story.append(PageBreak())

    story.append(Paragraph("Sayfa 2: Eğitim Bilgileri", sect_style))
    story.append(Paragraph("Gelişim döneminde yaygın gelişimsel bozukluk tanısı aldı mı?", q_style))
    story.append(Paragraph(_radio("Hayır", [("Evet", "Evet"), ("Hayır", "Hayır")]), a_style))
    story.append(Paragraph("Okul Adı/İl/İlçe:", q_style))
    story.append(Paragraph("Örnek İlkokulu / Ankara / Çankaya", a_style))
    story.append(Paragraph("Sınıfı:", q_style))
    story.append(Paragraph("2", a_style))
    story.append(Paragraph("Alınan Eğitim türü:", q_style))
    story.append(Paragraph("Zorunlu(örgün) temel eğitim", a_style))
    story.append(Paragraph("Okumada sorunu var mı? Varsa belirtiniz.", q_style))
    story.append(Paragraph(_radio("Hayır", [("Evet", "Evet"), ("Hayır", "Hayır")]), a_style))
    story.append(PageBreak())

    story.append(Paragraph("Sayfa 3: Demografik Bilgiler", sect_style))
    story.append(Paragraph("Yönleri ayırt etmede sorunu var mı?", q_style))
    story.append(Paragraph(_radio("Hayır", [("Evet", "Evet"), ("Hayır", "Hayır")]), a_style))
    story.append(Paragraph("Karne notları: Türkçe / Matematik / Hayat Bilgisi / Sosyal / Fen:", q_style))
    story.append(Paragraph("4 — 5 — 5 — 4 — 5", a_style))
    story.append(Paragraph("Ailenin kaçıncı çocuğu:", q_style))
    story.append(Paragraph("1", a_style))
    story.append(Paragraph("Anne baba arasında akrabalık var mı?", q_style))
    story.append(Paragraph(_radio("Hayır", [("Evet", "Evet"), ("Hayır", "Hayır")]), a_style))
    story.append(Paragraph("Aile Türü:", q_style))
    story.append(Paragraph("Çekirdek", a_style))
    story.append(Paragraph("Ailenin sosyoekonomik düzeyi:", q_style))
    story.append(Paragraph("Orta", a_style))
    story.append(Paragraph("<b>Veli Adı:</b> Örnek Veli   <b>Veli Telefon:</b> 05XX XXX XX XX", a_style))
    story.append(Paragraph("<b>Adres:</b> Örnek mahalle, örnek sokak No: 1", a_style))
    story.append(Paragraph("<b>Oluşturma Tarihi:</b> " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), a_style))

    doc.build(story, onFirstPage=on_first, onLaterPages=on_later)
    print(f"  [OK] Cocuk Takip Formu: {path}")


def main():
    _register_font()
    font_name = TURKISH_FONT_NAME or "Helvetica"

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    out_dir = desktop if os.path.isdir(desktop) else base

    paths = []
    paths.append(os.path.join(out_dir, "Ornek_BEP_Raporu.pdf"))
    paths.append(os.path.join(out_dir, "Ornek_ONAM_Formu.pdf"))
    paths.append(os.path.join(out_dir, "Ornek_Cocuk_Takip_Formu.pdf"))

    print("Örnek form PDF'leri oluşturuluyor...")
    build_bep_pdf(paths[0], font_name)
    build_onam_pdf(paths[1], font_name)
    build_cocuk_takip_pdf(paths[2], font_name)
    print("Tamamlandı. Dosyalar masaüstüne kaydedildi.")

    if sys.platform == "win32":
        for p in paths:
            if os.path.isfile(p):
                os.startfile(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
