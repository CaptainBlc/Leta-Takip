#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Çocuk Takip Bilgi Formu — Örnek PDF
Uygulamadaki Çocuk Takip Formu PDF çıktısının örneğini oluşturur.
Çalıştırma: python cocuk_takip_formu_pdf_ornegi.py
"""

import os
import sys
import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("Hata: reportlab yüklü değil. Şunu çalıştırın: pip install reportlab")
    sys.exit(1)


def _register_font():
    """Türkçe karakter için font (Windows: Segoe UI)."""
    try:
        if sys.platform == "win32":
            path = "C:/Windows/Fonts/segoeui.ttf"
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont("SegoeUI", path))
                return "SegoeUI"
        return "Helvetica"
    except Exception:
        return "Helvetica"


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    out_dir = desktop if os.path.isdir(desktop) else base
    path = os.path.join(out_dir, "Cocuk_Takip_Formu_Ornek.pdf")

    font_name = _register_font()
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()

    # —— Başlık (uygulamayla aynı) ——
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=16,
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    story.append(Paragraph("ÇOCUK TAKİP BİLGİ FORMU", title_style))
    story.append(Spacer(1, 1 * cm))

    # —— Form bilgileri (örnek veriler) ——
    info_style = ParagraphStyle(
        "InfoStyle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=11,
        spaceAfter=12,
        leftIndent=1 * cm,
    )

    story.append(Paragraph("<b>Danışan Adı:</b> Örnek Danışan Adı Soyadı", info_style))
    story.append(Paragraph("<b>Form Tarihi:</b> " + datetime.datetime.now().strftime("%Y-%m-%d"), info_style))
    story.append(Paragraph("<b>Cinsiyet:</b> Erkek", info_style))
    story.append(Paragraph("<b>Doğum Tarihi:</b> 2018-05-12", info_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Okul Adı:</b> Örnek İlkokulu / İl / İlçe", info_style))
    story.append(Paragraph("<b>Sınıf:</b> 2", info_style))
    story.append(Paragraph("<b>Eğitim Durumu:</b> Zorunlu(örgün) temel eğitim", info_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Veli Adı:</b> Veli Adı Soyadı", info_style))
    story.append(Paragraph("<b>Veli Telefon:</b> 05XX XXX XX XX", info_style))
    story.append(Paragraph("<b>Adres:</b> Örnek mahalle, örnek sokak No: X", info_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Anne Adı:</b> Anne Adı Soyadı", info_style))
    story.append(Paragraph("<b>Baba Adı:</b> Baba Adı Soyadı", info_style))
    story.append(Paragraph("<b>Kardeş Sayısı:</b> 2 çocuk (yaşları, cinsiyetleri belirtildi)", info_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Tanı:</b> Örnek tanı / Gelişim takibi", info_style))
    story.append(Paragraph("<b>Sağlık Durumu:</b> Genel sağlık iyi", info_style))
    story.append(Paragraph("<b>Ailenin Ekonomik Durumu:</b> Orta", info_style))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("<b>Oluşturma Tarihi:</b> " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), info_style))

    doc.build(story)
    print(f"Çocuk Takip Formu örnek PDF oluşturuldu: {path}")
    if sys.platform == "win32" and os.path.isfile(path):
        os.startfile(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
