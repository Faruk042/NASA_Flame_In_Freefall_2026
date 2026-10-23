# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall"
Kapsamlı Kullanım ve Jüri Rehberi İçin 6 Yüksek Çözünürlüklü (1280x720) Görsel Üretici
"""

import math
import os
from PIL import Image, ImageDraw, ImageFont

from literatur_ai import motor_al
from mikroyercekimi_fizik_motoru import MikroYercekimiFizikMotoru
from nasa_psi_veritabani import (
    BILGI_GRAFIGI_BAGLANTILARI,
    BILGI_GRAFIGI_DUGUMLERI,
    NASA_PSI_DENEY_ARSIVI,
    UZAY_MALZEME_ATLASI,
)
from optik_alev_goruntu_analizoru import OptikAlevGoruntuAnalizoru

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "gorseller")
os.makedirs(OUT_DIR, exist_ok=True)


def get_font(size: int = 16, bold: bool = False):
    candidates = ["consolab.ttf", "arialbd.ttf", "segoeuib.ttf"] if bold else ["consola.ttf", "arial.ttf", "segoeui.ttf"]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def uret_tum_gorseller() -> None:
    f_title = get_font(20, True)
    f_sub = get_font(15, True)
    f_body = get_font(13, False)
    f_small = get_font(11, False)

    # =========================================================================
    # 2. 02_sekme1_d2_yasasi_ve_soguk_alev.png
    # =========================================================================
    img2 = Image.new("RGB", (1280, 720), (6, 10, 22))
    d = ImageDraw.Draw(img2)
    d.rectangle([16, 16, 1264, 72], fill=(13, 25, 48), outline=(0, 245, 212), width=2)
    d.text((28, 30), "SEKME 1 REHBERİ: SIVI DAMLACIK d²-YASASI, FLEX-2 SOĞUK ALEV VE 4G ALEV MORFOLOJİSİ", fill=(0, 245, 212), font=f_title)

    d.rounded_rectangle([16, 86, 410, 704], radius=10, fill=(13, 22, 39), outline=(30, 41, 59), width=2)
    d.text((30, 100), "SOL KONTROL PANELİ NASIL KULLANILIR?", fill=(255, 209, 102), font=f_sub)
    ctrl_lines = [
        "1) Yakıt Seçimi Menüsü:",
        "   n-Heptan, n-Dekan, Etanol veya",
        "   Metanol yakıtını seçin.",
        "2) 5 Fiziksel Sürgü (Slider):",
        "   • Yerçekimi (g): 0.00g - 1.00g",
        "   • Oksijen (%O2): %12.0 - %36.0",
        "   • Basınç (kPa): 40 - 120 kPa",
        "   • Damlacık Çapı d0: 1.0 - 5.0 mm",
        "   • Ventilasyon Akışı: 0 - 45 cm/s",
        "3) 4 Hızlı NASA Senaryo Butonu:",
    ]
    for i, ln in enumerate(ctrl_lines):
        d.text((30, 134 + i * 26), ln, fill=(226, 232, 240), font=f_body)

    qbtns = [
        ("[ISS 0g Küresel Alev]", (0, 119, 182), "0g, %21 O2, d0=2.8mm kararlı alev"),
        ("[FLEX-2 Soğuk Alev]", (106, 13, 173), "0g, d0=3.6mm Sıcak -> Cool Flame"),
        ("[Ay 0.16g Keşif (%34 O2)]", (224, 122, 95), "0.16g, 56.5 kPa Artemis ortamı"),
        ("[Yüksek Fan Blow-Off]", (198, 40, 40), "38 cm/s akışta üfleyerek sönme"),
    ]
    for i, (btxt, bcol, bdesc) in enumerate(qbtns):
        y0 = 410 + i * 68
        d.rounded_rectangle([30, y0, 394, y0 + 34], radius=6, fill=bcol, outline=(255, 255, 255))
        d.text((42, y0 + 8), btxt, fill=(255, 255, 255), font=f_body)
        d.text((36, y0 + 38), "-> " + bdesc, fill=(148, 163, 184), font=f_small)

    d.rounded_rectangle([426, 86, 1264, 390], radius=10, fill=(10, 16, 30), outline=(0, 245, 212), width=1)
    d.text((444, 98), "CANLI GRAFİK 1: d²(t) = d0² - K·t (Sıcak Alev -> Radyatif Sönme -> Görünmez Soğuk Alev)", fill=(0, 245, 212), font=f_sub)
    res = MikroYercekimiFizikMotoru.damlacik_yanma_analizi("n-Heptan (C7H16 - FLEX Referansı)", 0.0, 20.5, 101.3, 3.5, 1.5)
    zs = res["zaman_serisi"]
    gx0, gy0, gx1, gy1 = 480, 350, 1230, 140
    d.line([gx0, gy0, gx1, gy0], fill=(100, 116, 139), width=2)
    d.line([gx0, gy0, gx0, gy1], fill=(100, 116, 139), width=2)
    max_t = max(p[0] for p in zs) or 1.0
    max_d2 = max(p[1] for p in zs) or 1.0
    prev = None
    for t_val, d2_val, _temp_k, rejim in zs:
        px = gx0 + (t_val / max_t) * (gx1 - gx0)
        py = gy0 - (d2_val / max_d2) * (gy0 - gy1)
        col = (56, 189, 248) if rejim == "SICAK_ALEV" else (168, 85, 247)
        if prev:
            d.line([prev[0], prev[1], px, py], fill=col, width=4)
        prev = (px, py)
    gecis_x = gx0 + (res["radyatif_gecis_sn"] / max_t) * (gx1 - gx0)
    d.line([gecis_x, gy1, gecis_x, gy0], fill=(255, 209, 102), width=2)
    d.text(
        (gecis_x + 10, gy1 + 10),
        f"Radyatif Sönme (t={res['radyatif_gecis_sn']} sn)\nGörünmez Soğuk Alev (640 K)\nK_hot={res['k_sicak']} | K_cool={res['k_soguk']} mm²/s",
        fill=(255, 209, 102),
        font=f_body,
    )

    d.rounded_rectangle([426, 404, 1264, 704], radius=10, fill=(10, 16, 30), outline=(255, 209, 102), width=1)
    d.text((444, 416), "CANLI KANVAS 2: 4 YERÇEKİMİ REJİMİNDE ALEV MORFOLOJİSİ KARŞILAŞTIRMASI", fill=(255, 209, 102), font=f_sub)
    regimes = [
        ("1.00g DÜNYA", "Gözyaşı Konvektif\nYüksek Kaldırma Kuvveti", 530, (255, 140, 0), 0.55),
        ("0.38g MARS", "Orta Uzamış Alev\nZayıf Konveksiyon", 735, (251, 146, 60), 0.72),
        ("0.16g AY (KRİTİK!)", "Yarı-Küresel Alev\nEn Düşük LOC (%14.6 O2)", 940, (255, 51, 102), 0.85),
        ("0.00g ISS (MİKRO)", "Tam Küresel Difüzyon\nSoot Kabuğu + Cool Flame", 1145, (56, 189, 248), 1.0),
    ]
    for title, sub, cx, col, ratio in regimes:
        cy = 555
        ry = 58
        rx = int(ry * ratio)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col, outline=(255, 255, 255), width=2)
        d.ellipse([cx - 8, cy + 10, cx + 8, cy + 26], fill=(30, 41, 59), outline=(255, 255, 255))
        d.text((cx - 75, 452), title, fill=col, font=f_body)
        d.text((cx - 80, 630), sub, fill=(226, 232, 240), font=f_small)
    img2.save(os.path.join(OUT_DIR, "02_sekme1_d2_yasasi_ve_soguk_alev.png"))

    # =========================================================================
    # 3. 03_sekme2_ve_3_ntrs_korpus_ve_malzeme_atlasi.png
    # =========================================================================
    img3 = Image.new("RGB", (1280, 720), (6, 10, 22))
    d = ImageDraw.Draw(img3)
    d.rectangle([16, 16, 1264, 72], fill=(13, 25, 48), outline=(56, 189, 248), width=2)
    d.text((28, 30), "SEKME 2 & 3 REHBERİ: 673 GERÇEK NASA NTRS KANIT ARŞİVİ VE MALZEME YANICILIK ATLASI", fill=(56, 189, 248), font=f_title)

    # Left: Tab 2 NTRS Search & Corpus
    d.rounded_rectangle([16, 86, 628, 704], radius=10, fill=(13, 22, 39), outline=(56, 189, 248), width=2)
    d.text((30, 100), "SEKME 2: NASA PSI & NTRS KANIT KEŞİF MOTORU", fill=(0, 245, 212), font=f_sub)
    d.text((30, 128), "• [Arama Kutusu]: Türkçe/İngilizce anahtar kelime yazın", fill=(226, 232, 240), font=f_body)
    d.text((30, 152), "• [🌐 Canlı NTRS API Sorgula]: 673 yerel + canlı NASA kaydı", fill=(226, 232, 240), font=f_body)
    d.text((30, 176), "• [🤖 Seçili Kanıtı AI Merkezinde Analiz Et]: Derin sentez", fill=(226, 232, 240), font=f_body)

    for idx, k in enumerate(NASA_PSI_DENEY_ARSIVI[:7]):
        y0 = 212 + idx * 68
        d.rounded_rectangle([28, y0, 614, y0 + 60], radius=6, fill=(7, 13, 25), outline=(30, 58, 138))
        ntrs_ref = ", ".join(f"NTRS:{r}" for r in k.ntrs_referanslari[:2])
        d.text((38, y0 + 8), f"[{k.kanit_id}] {k.program_adi} ({k.yil}) — {ntrs_ref}", fill=(255, 209, 102), font=f_body)
        d.text((38, y0 + 32), k.baslik[:66] + "...", fill=(203, 213, 225), font=f_small)

    # Right: Tab 3 Material Flammability Atlas Bar Chart
    d.rounded_rectangle([644, 86, 1264, 704], radius=10, fill=(13, 22, 39), outline=(255, 209, 102), width=2)
    d.text((660, 100), "SEKME 3: UZAY MALZEME ATLASI (1g vs 0g vs 0.16g AY LOC %O2)", fill=(255, 209, 102), font=f_sub)
    d.text((660, 126), "SoFIE Bulgusu: Ay'da (0.16g) LOC daha düşüktür (Kırmızı barlar)!", fill=(255, 51, 102), font=f_body)

    bx0 = 830
    bx1 = 1235
    for idx, m in enumerate(UZAY_MALZEME_ATLASI):
        ym = 166 + idx * 58
        short_name = m.malzeme_adi.split("(")[0].strip()[:18]
        d.text((656, ym + 8), short_name, fill=(226, 232, 240), font=f_small)
        w1 = int((min(m.loc_dunya_1g, 45.0) / 45.0) * (bx1 - bx0))
        w0 = int((min(m.loc_mikro_0g, 45.0) / 45.0) * (bx1 - bx0))
        wa = int((min(m.loc_ay_016g, 45.0) / 45.0) * (bx1 - bx0))
        d.rectangle([bx0, ym, bx0 + w1, ym + 10], fill=(56, 189, 248))
        d.rectangle([bx0, ym + 13, bx0 + w0, ym + 23], fill=(245, 158, 11))
        d.rectangle([bx0, ym + 26, bx0 + wa, ym + 36], fill=(255, 51, 102))
        d.text((bx0 + max(w1, w0, wa) + 6, ym + 10), f"{m.loc_ay_016g}%", fill=(255, 209, 102), font=f_small)
    img3.save(os.path.join(OUT_DIR, "03_sekme2_ve_3_ntrs_korpus_ve_malzeme_atlasi.png"))

    # =========================================================================
    # 4. 04_sekme4_ve_5_telemetri_ve_arastirma_boslugu.png
    # =========================================================================
    img4 = Image.new("RGB", (1280, 720), (6, 10, 22))
    d = ImageDraw.Draw(img4)
    d.rectangle([16, 16, 1264, 72], fill=(13, 25, 48), outline=(168, 85, 247), width=2)
    d.text((28, 30), "SEKME 4 & 5 REHBERİ: TELEMETRİ ANOMALİ RADARI VE 673 NTRS KANIT YOĞUNLUĞU MATRİSİ", fill=(168, 85, 247), font=f_title)

    # Left: Telemetry & Sonification
    d.rounded_rectangle([16, 86, 560, 704], radius=10, fill=(13, 22, 39), outline=(255, 51, 102), width=2)
    d.text((30, 100), "SEKME 4: TELEMETRİ RADARI & WAV SESLENDİRME", fill=(255, 51, 102), font=f_sub)
    tel_notes = [
        "• [1) FLEX-2 Soğuk Alev Geçişi] Butonu",
        "• [2) BASS-II O2 Artış Anomalisi] Butonu",
        "• [3) Saffire %34 O2 Keşif Atmosferi] Butonu",
        "• [🔊 Veriyi Seslendir (WAV)] Butonu:",
        "  Seçili Y1 eğrisini diske dosya yazmadan",
        "  220 Hz - 1080 Hz arasında seslendirir.",
        "• Z-Skoru (>1.95σ) Anomali Noktaları:",
        "  Altın sarısı halkalarla grafikte işaretlenir.",
    ]
    for i, ln in enumerate(tel_notes):
        d.text((30, 134 + i * 28), ln, fill=(226, 232, 240), font=f_body)

    # Simulated dual-axis telemetry curve
    tx0, ty0, tx1, ty1 = 46, 660, 530, 410
    d.rectangle([tx0, ty1, tx1, ty0], fill=(7, 12, 24), outline=(71, 85, 105))
    pts1, pts2 = [], []
    for i in range(40):
        px = tx0 + (i / 39.0) * (tx1 - tx0)
        py1 = ty0 - (0.2 + 0.65 * abs(math.sin(i * 0.14))) * (ty0 - ty1)
        py2 = ty0 - (0.75 - 0.5 * (i / 39.0)) * (ty0 - ty1)
        pts1.append((px, py1))
        pts2.append((px, py2))
    d.line(pts1, fill=(255, 51, 102), width=3)
    d.line(pts2, fill=(56, 189, 248), width=2)
    d.ellipse([pts1[11][0] - 6, pts1[11][1] - 6, pts1[11][0] + 6, pts1[11][1] + 6], fill=(255, 209, 102), outline=(255, 255, 255))
    d.text((tx0 + 12, ty1 + 10), "Pembe: Y1 (Sıcaklık/CO) | Mavi: Y2 (%O2) | Sarı: Z-Anomali", fill=(255, 209, 102), font=f_small)

    # Right: Real 673-Paper NTRS Evidence Density Heatmap
    d.rounded_rectangle([576, 86, 1264, 704], radius=10, fill=(13, 22, 39), outline=(0, 245, 212), width=2)
    d.text((592, 100), "SEKME 5: 673 GERÇEK NTRS YAYININDAN HESAPLANAN KANIT MATRİSİ", fill=(0, 245, 212), font=f_sub)
    motor = motor_al()
    satirlar, sutunlar, matris = motor.kanit_matrisi()
    hx0 = 760
    hy0 = 165
    cw = 94
    ch = 44
    kisa_sut = ["0g Mikro", "Ay 0.16g", "Mars 0.38g", "Kısmi Genel", "1g Dünya"]
    for c_i, s_ad in enumerate(kisa_sut):
        d.text((hx0 + c_i * cw + 8, hy0 - 24), s_ad, fill=(255, 209, 102), font=f_small)
    for r_i, f_ad in enumerate(satirlar):
        ry = hy0 + r_i * ch
        d.text((590, ry + 12), f_ad[:20], fill=(226, 232, 240), font=f_small)
        for c_i, val in enumerate(matris[r_i]):
            rx = hx0 + c_i * cw
            bg = (220, 38, 38) if val <= 5 else ((217, 119, 6) if val <= 20 else (5, 150, 105))
            d.rectangle([rx + 2, ry + 2, rx + cw - 2, ry + ch - 2], fill=bg, outline=(15, 23, 42))
            d.text((rx + 22, ry + 13), f"{val} yayın", fill=(255, 255, 255), font=f_small)
    img4.save(os.path.join(OUT_DIR, "04_sekme4_ve_5_telemetri_ve_arastirma_boslugu.png"))

    # =========================================================================
    # 5. 05_sekme6_optik_alev_goruntu_analizi.png
    # =========================================================================
    img5 = Image.new("RGB", (1280, 720), (6, 10, 22))
    d = ImageDraw.Draw(img5)
    d.rectangle([16, 16, 1264, 72], fill=(13, 25, 48), outline=(74, 222, 128), width=2)
    d.text((28, 30), "SEKME 6 REHBERİ: ÇOK MODLU OPTİK ALEV GÖRÜNTÜ İŞLEME VE KEMİLÜMİNESANS ANALİZÖRÜ", fill=(74, 222, 128), font=f_title)

    modes = [
        ("1) ISS 0.00g", "1) 0g Saf Mavi CH*"),
        ("2) ISS 0.00g", "2) 0g Küresel İs Kabuğu"),
        ("3) ISS 0.00g", "3) FLEX-2 Soğuk Alev (UV/Mor)"),
        ("4) Ay 0.16g", "4) 0.16g Ay Konvektif Alev"),
    ]
    for idx, (m_code, m_title) in enumerate(modes):
        x0 = 24 + idx * 310
        y0 = 92
        d.rounded_rectangle([x0, y0, x0 + 296, y0 + 596], radius=10, fill=(13, 22, 39), outline=(56, 189, 248), width=2)
        d.text((x0 + 14, y0 + 12), m_title, fill=(255, 209, 102), font=f_sub)
        f_img = OptikAlevGoruntuAnalizoru.sentetik_nasa_kamera_karesi_uret(m_code, boyut=240)
        res_opt = OptikAlevGoruntuAnalizoru.goruntuyu_analiz_et(f_img)
        img5.paste(f_img, (x0 + 28, y0 + 44))
        metrics = [
            f"Küresellik (Phi) : {res_opt['kuresellik_indeksi']}",
            f"Eşdeğer Çap Deq  : {res_opt['esdeger_cap_mm']} mm",
            f"Mavi CH* Radikal : %{res_opt['mavi_kemiluminesans_yuzde']}",
            f"Sarı Soot Işıması: %{res_opt['sari_soot_radyasyon_yuzde']}",
            f"Mor Soğuk Alev   : %{res_opt['mor_soguk_alev_yuzde']}",
            f"Sıcaklık Tahmini : {res_opt['tahmini_sicaklik_k']} K",
        ]
        for m_i, m_line in enumerate(metrics):
            d.text((x0 + 18, y0 + 305 + m_i * 28), m_line, fill=(226, 232, 240), font=f_body)

        # Mini Radial RGB profile at bottom of card
        px0, py0, px1, py1 = x0 + 20, y0 + 572, x0 + 276, y0 + 495
        d.rectangle([px0, py1, px1, py0], fill=(6, 10, 20), outline=(51, 65, 85))
        prof = res_opt["radyal_profil"]
        if len(prof) > 2:
            for ch_idx, ch_col in [(1, (255, 70, 70)), (2, (74, 222, 128)), (3, (56, 189, 248))]:
                pts = []
                for p_i, row in enumerate(prof):
                    rx = px0 + (p_i / (len(prof) - 1)) * (px1 - px0)
                    ry = py0 - (row[ch_idx] / 255.0) * (py0 - py1)
                    pts.append((rx, ry))
                d.line(pts, fill=ch_col, width=2)
    img5.save(os.path.join(OUT_DIR, "05_sekme6_optik_alev_goruntu_analizi.png"))

    # =========================================================================
    # 6. 06_sekme7_ve_8_bilgi_grafigi_kabin_ikizi_ai.png
    # =========================================================================
    img6 = Image.new("RGB", (1280, 720), (6, 10, 22))
    d = ImageDraw.Draw(img6)
    d.rectangle([16, 16, 1264, 72], fill=(13, 25, 48), outline=(251, 146, 60), width=2)
    d.text((28, 30), "SEKME 7 & 8 REHBERİ: BİLGİ GRAFİĞİ, KABİN DUMAN DİJİTAL İKİZİ VE AI KARAR MERKEZİ", fill=(251, 146, 60), font=f_title)

    # Left: Knowledge Graph visualization
    d.rounded_rectangle([16, 86, 628, 704], radius=10, fill=(13, 22, 39), outline=(0, 245, 212), width=2)
    d.text((30, 100), "SEKME 7 (SOL): İNTERAKTİF NASA YANMA BİLGİ GRAFİĞİ", fill=(0, 245, 212), font=f_sub)
    d.text((30, 126), "Herhangi bir düğüme tıkladığınızda sağ altta kanıt detayı açılır:", fill=(226, 232, 240), font=f_body)

    pos_map = {}
    tier_y = {"TESIS": 200, "DENEY": 320, "OLGU": 460, "GUVENLIK": 590}
    tier_counts = {"TESIS": 0, "DENEY": 0, "OLGU": 0, "GUVENLIK": 0}
    tier_totals = {"TESIS": 1, "DENEY": 5, "OLGU": 4, "GUVENLIK": 2}
    for n in BILGI_GRAFIGI_DUGUMLERI:
        t = n.get("tur", "DENEY")
        idx_t = tier_counts.get(t, 0)
        tier_counts[t] = idx_t + 1
        tot_t = tier_totals.get(t, 4)
        nx = int(80 + (idx_t + 0.5) * (500 / tot_t))
        ny = tier_y.get(t, 320)
        pos_map[n["id"]] = (nx, ny, n)
    for src, dst, lbl in BILGI_GRAFIGI_BAGLANTILARI:
        if src in pos_map and dst in pos_map:
            x1, y1, _ = pos_map[src]
            x2, y2, _ = pos_map[dst]
            d.line([x1, y1, x2, y2], fill=(71, 85, 105), width=2)
    for nid, (nx, ny, n) in pos_map.items():
        d.ellipse([nx - 22, ny - 22, nx + 22, ny + 22], fill=(30, 58, 138), outline=(0, 245, 212), width=2)
        d.text((nx - 38, ny + 25), n["etiket"].replace("\n", " "), fill=(255, 209, 102), font=f_small)

    # Right Top: Cabin Smoke Digital Twin
    d.rounded_rectangle([644, 86, 1264, 390], radius=10, fill=(13, 22, 39), outline=(255, 51, 102), width=2)
    d.text((660, 100), "SEKME 7 (SAĞ): UZAY ARACI KABİN DUMAN & SENSÖR DİJİTAL İKİZİ", fill=(255, 51, 102), font=f_sub)
    ikiz = MikroYercekimiFizikMotoru.kabin_duman_ve_sensor_dijital_ikizi_hesapla(0.0, 0.5)
    twin_lines = [
        "• Kabin kesiti üzerinde istediğiniz noktaya tıklayarak yangın başlatın.",
        "• [Yerçekimi Sürgüsü] ve [HVAC Fan Sürgüsü] ile duman taşınımını test edin.",
        f"• 0g + Fan Kapalı (0.5 cm/s) Simülasyon Çıktısı:",
        f"  - Tavan Dedektörü Alarm Süresi : {ikiz['t_tavan_sn']} sn (KÖR NOKTA!)",
        f"  - HVAC Dönüş Kanalı Süresi     : {ikiz['t_hvac_sn']} sn",
        f"  - Lokal Mid-IR Optik Sensör    : {ikiz['t_lokal_ir_sn']} sn",
        "• Fiziksel Neden [NTRS:20040053578]: 0g'de sıcak duman yükselmez!",
    ]
    for i, ln in enumerate(twin_lines):
        d.text((660, 134 + i * 32), ln, fill=(226, 232, 240), font=f_body)

    # Right Bottom: Tab 8 AI Decision Center
    d.rounded_rectangle([644, 404, 1264, 704], radius=10, fill=(13, 22, 39), outline=(74, 222, 128), width=2)
    d.text((660, 418), "SEKME 8: KANIT-ODAKLI AI KARAR MERKEZİ & JÜRİ RAPORU", fill=(74, 222, 128), font=f_sub)
    ai_lines = [
        "• 4 Hazır Senaryo Butonu veya Serbest Soru Kutusu ile çalışır.",
        "• [🔥 Kanıt-Odaklı Analiz Üret] butonuna basıldığında 6 katman üretir:",
        "  1) Fiziksel Anomali Teşhisi (O2 artışı, Soğuk Alev, Soot riski)",
        "  2) Sayısal Termodinamik & d²-Yasası (K, Tf, Gr, Re, Pe, Da)",
        "  3) 120-İterasyon Monte Carlo (%90 Güven Aralığı P05/Medyan/P95)",
        "  4) Doğrulanmış PSI Deneyleri + 673 NTRS BM25/MMR Makale Sentezi",
        "  5) NASA-STD-6001B Malzeme Risk Sıralaması ve Müdahale Protokolü",
        "• [🌐 HTML Jüri Sunumu] & [💾 Jüri Raporu İndir (.MD)] ile dışa aktarılır.",
    ]
    for i, ln in enumerate(ai_lines):
        d.text((660, 450 + i * 29), ln, fill=(226, 232, 240), font=f_body)

    img6.save(os.path.join(OUT_DIR, "06_sekme7_ve_8_bilgi_grafigi_kabin_ikizi_ai.png"))
    print("ALL 6 VISUAL GUIDE IMAGES GENERATED SUCCESSFULLY!")

    # HTML Görsel Kullanım Rehberi Üretimi (Base64 Gömülü Görseller + Detaylı Tablolar)
    import base64
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_items = [
        (
            "01_genel_mimari_ve_ust_bar.png",
            "1. Genel Mimari, Üst Kontrol Barı Butonları ve 8 Uzman Sekme Haritası",
            "Üst bardaki <b>[📊 Telemetri CSV Yükle]</b> gerçek PSI CSV dosyalarını salt-okunur açar; "
            "<b>[🌐 HTML Jüri Sunumu]</b> tüm sekmelerin çıktısını tek tıkla tarayıcıda açılan karanlık temalı bir panoya dönüştürür; "
            "<b>[💾 Jüri Raporu İndir (.MD)]</b> Markdown raporu kaydeder; <b>[🔑 Gemini API]</b> ise isteğe bağlı bulut RAG anahtarını tanımlar."
        ),
        (
            "02_sekme1_d2_yasasi_ve_soguk_alev.png",
            "2. Sekme 1: Sıvı Damlacık d²-Yasası, FLEX-2 Soğuk Alev ve 4g Alev Morfolojisi",
            "Sol panelden yakıt türünü ve 5 fiziksel sürgüyü (Yerçekimi, %O2, Basınç, d0 çapı, Fan akışı) ayarlayın veya "
            "4 hızlı NASA senaryo butonuna tıklayın. Sağ üstte canlı d²(t) = d0² - K·t eğrisi ve soğuk alev geçişi, "
            "sağ altta ise 1.0g Dünya, 0.38g Mars, 0.16g Ay ve 0.0g ISS alev şekilleri karşılaştırılır."
        ),
        (
            "03_sekme2_ve_3_ntrs_korpus_ve_malzeme_atlasi.png",
            "3. Sekme 2 & 3: 673 Gerçek NASA NTRS Kanıt Arşivi ve NASA-STD-6001B Malzeme Atlası",
            "Sekme 2'de 673 gerçek NASA NTRS makalesi ve 10 yapılandırılmış PSI deneyi içinde BM25 araması yapılır ve "
            "doğrudan https://ntrs.nasa.gov/citations/&lt;ID&gt; linkleriyle doğrulanır. Sekme 3'te 9 uzay aracı malzemesinin "
            "1g, 0g ve 0.16g Ay Kritik Oksijen Sınırı (LOC %O2) karşılaştırılır."
        ),
        (
            "04_sekme4_ve_5_telemetri_ve_arastirma_boslugu.png",
            "4. Sekme 4 & 5: Çok Eksenli Telemetri Radarı (WAV Seslendirme) ve Araştırma Boşluğu Matrisi",
            "Sekme 4'te çift eksenli Pearson korelasyonu, Z-skoru (>1.95σ) anomali tespiti ve bellek-içi 16-bit PCM WAV seslendirme "
            "(Sonification) yapılır. Sekme 5'te 673 gerçek NTRS makalesinden hesaplanan Fenomen × Yerçekimi Kanıt Yoğunluğu Matrisi "
            "ile Ay/Mars araştırma boşlukları tespit edilir."
        ),
        (
            "05_sekme6_optik_alev_goruntu_analizi.png",
            "5. Sekme 6: Çok Modlu Optik Alev Görüntü İşleme ve Kemilüminesans Analizörü",
            "Sentetik NASA CIR yüksek hızlı kamera karelerini veya bilgisayarınızdan yüklediğiniz gerçek alev fotoğraflarını "
            "piksel düzeyinde tarayarak Küresellik İndeksi (Φ), Eşdeğer Çap (Deq), Mavi CH* Kemilüminesans %, Sarı Soot % "
            "ve Mor Soğuk Alev % oranlarını ve Radyal RGB Yoğunluk Profilini I(r) çıkarır."
        ),
        (
            "06_sekme7_ve_8_bilgi_grafigi_kabin_ikizi_ai.png",
            "6. Sekme 7 & 8: İnteraktif Bilgi Grafiği, Kabin Dijital İkizi ve AI Karar Merkezi",
            "Sekme 7 sol panelde 12 düğümlü tıklanabilir NASA Yanma Bilgi Grafiği, sağ panelde ise 0g tavan dedektörü kör noktasını "
            "gösteren Kabin Duman & Sensör Dijital İkizi yer alır. Sekme 8'de Fizik + 120-İterasyon Monte Carlo + 673 NTRS BM25/MMR "
            "sentezini birleştiren Kanıt-Odaklı AI Karar Merkezi bulunur."
        ),
    ]

    cards = []
    for fname, title, desc in img_items:
        with open(os.path.join(OUT_DIR, fname), "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        cards.append(
            f'<div class="card"><h2>{title}</h2><p>{desc}</p>'
            f'<img src="data:image/png;base64,{b64}" alt="{title}" /></div>'
        )

    html_content = (
        "<!DOCTYPE html><html lang='tr'><head><meta charset='UTF-8'>"
        "<title>NASA Space Apps 2026 — Flame in Freefall Görsel Kullanım Rehberi</title>"
        "<style>"
        "body{background:#050914;color:#E2E8F0;font-family:'Segoe UI',Consolas,sans-serif;margin:0;padding:28px;line-height:1.6;}"
        ".header{background:linear-gradient(90deg,#0D1B2A,#1E3A8A);border:2px solid #00F5D4;border-radius:14px;padding:24px;margin-bottom:24px;}"
        "h1{color:#00F5D4;margin:0 0 8px 0;font-size:26px;}"
        "h2{color:#FFD166;border-bottom:1px solid #1E293B;padding-bottom:8px;margin-top:0;}"
        ".card{background:#0D1627;border:1px solid #1E293B;border-radius:12px;padding:20px;margin-bottom:24px;}"
        "img{width:100%;max-width:1240px;border-radius:8px;border:1px solid #334155;display:block;margin:12px auto;}"
        "</style></head><body>"
        "<div class='header'><h1>🔥 NASA SPACE APPS CHALLENGE 2026 — FLAME IN FREEFALL GÖRSEL KULLANIM VE ÖZELLİK REHBERİ</h1>"
        "<p>673 Gerçek NASA NTRS Akademik Yayını + 80 Tam Metin • 8 Uzman Masaüstü Sekmesi (flame_in_freefall_app.py) • 6 Uzman Web Panosu Sekmesi (streamlit_app.py)</p></div>"
        + "".join(cards)
        + "</body></html>"
    )
    with open(os.path.join(base_dir, "KULLANIM_VE_OZELLIK_REHBERI.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    print("HTML HANDBOOK GENERATED SUCCESSFULLY!")


if __name__ == "__main__":
    uret_tum_gorseller()
