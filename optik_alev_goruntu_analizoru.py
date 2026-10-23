# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"
Modül 5: Çok Modlu (Multi-Modal) Optik Alev Görüntü İşleme, Spektral Kemilüminesans (CH* / C2* / Soot),
         Küresellik İndeksi (Sphericity) ve Radyal Yoğunluk Profili Analizörü.

Bu modül:
1) Gerçek NASA CIR / BASS / FLEX yüksek hızlı kamera karelerini (.png, .jpg, .bmp) salt-okunur analiz eder,
2) Veya bellek içinde (PIL.Image) fizik tabanlı sentetik NASA CIR kamera kareleri üretir:
   - 0.00g Küresel Mavi Difüzyon Alevi (Kurumsuz / Düşük Residence Time)
   - 0.00g Küresel Sarı/Turuncu Kurum (Soot) Kabuklu Alev (ACME / FLEX)
   - 0.00g Görünmez Soğuk Alev (Cool Flame - UV/IR Yabancı Renk / False-Color 640 K)
   - 0.16g Ay Kısmi Yerçekimi Konvektif Damla Alevi (SoFIE)
3) Görüntü üzerindeki piksellerden:
   - Mavi Kemilüminesans Oranı (%CH* Radikal Emisyonu)
   - Sarı/Turuncu Siyah Cisim Kurum Radyasyonu Oranı (%Soot Incandescence)
   - Alev Eşdeğer Yarıçapı (R_eq), Küresellik İndeksi (Sphericity Φ = 4πA/P²) ve Eksantriklik
   - Merkezden dışa (r = 0 -> R_max) R, G, B Radyal Işık Yoğunluk Profilini çıkarır.
"""

import math
from typing import Dict, List, Tuple

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class OptikAlevGoruntuAnalizoru:
    """
    Yüksek hızlı yanma kamerası görüntülerinden alev morfolojisi, küresellik (0g vs 1g),
    kurum (soot) kabuk kalınlığı ve radyal spektral profil çıkaran görüntü işleme motoru.
    """

    SENTETIK_SENARYOLAR: Tuple[str, ...] = (
        "1) ISS 0.00g — Küresel Mavi Difüzyon Alevi (Metanol / Düşük Kurum)",
        "2) ISS 0.00g — Küresel Sarı/Turuncu Soot Kabuklu Alev (n-Heptan / ACME)",
        "3) ISS 0.00g — FLEX-2 Görünmez Soğuk Alev (UV/IR False-Color 640 K)",
        "4) Ay 0.16g — SoFIE Kısmi Yerçekimi Konvektif Uzamış Alev",
    )

    @staticmethod
    def sentetik_nasa_kamera_karesi_uret(senaryo_adi: str, boyut: int = 320) -> "Image.Image":
        """
        Fiziksel radyal emisyon denklemlerine göre bellek içinde (RAM) 320x320 RGB
        yüksek hızlı yanma kamerası görüntüsü üretir.
        """
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow (PIL) kütüphanesi yüklü değil.")

        img = Image.new("RGB", (boyut, boyut), (4, 7, 15))
        pikseller = img.load()
        cx, cy = boyut // 2, int(boyut * 0.54)

        if "1)" in senaryo_adi:
            # 0g Küresel Mavi Difüzyon Alevi
            r_damla = 14.0
            r_alev = 86.0
            uzama_y = 1.0
            mod = "MAVI_0G"
        elif "2)" in senaryo_adi:
            # 0g Küresel Sarı Soot Halkalı Alev
            r_damla = 16.0
            r_alev = 94.0
            uzama_y = 1.0
            mod = "SOOT_0G"
        elif "3)" in senaryo_adi:
            # 0g FLEX-2 UV/IR Soğuk Alev (Cool Flame)
            r_damla = 18.0
            r_alev = 68.0
            uzama_y = 1.0
            mod = "COOL_0G"
        else:
            # 0.16g Ay Kısmi Yerçekimi Uzamış Konvektif Alev
            r_damla = 14.0
            r_alev = 82.0
            uzama_y = 1.55
            mod = "LUNAR_016G"

        for y in range(boyut):
            dy = y - cy
            # Yukarı yönlü (dy < 0) konvektif uzama ölçeklemesi
            etkin_dy = dy / uzama_y if (dy < 0 and uzama_y > 1.0) else dy * (1.12 if dy > 0 and uzama_y > 1.0 else 1.0)
            for x in range(boyut):
                dx = x - cx
                r = math.sqrt(dx * dx + etkin_dy * etkin_dy)

                if r <= r_damla:
                    # Merkez yakıt damlacığı (koyu gri/mavi yansıma)
                    parlaklik = int(45 + 35 * (1.0 - r / r_damla))
                    pikseller[x, y] = (parlaklik, parlaklik + 10, parlaklik + 25)
                    continue

                norm_r = r / r_alev
                if norm_r > 1.35:
                    continue

                if mod == "MAVI_0G":
                    # İnce mavi CH* reaksiyon kabuğu (norm_r ~ 0.85 - 1.05)
                    mavi_zarf = math.exp(-((norm_r - 0.92) ** 2) / 0.022)
                    ic_isima = 0.25 * math.exp(-((norm_r - 0.65) ** 2) / 0.08)
                    r_val = int(min(255, 35 * mavi_zarf + 20 * ic_isima))
                    g_val = int(min(255, 165 * mavi_zarf + 85 * ic_isima))
                    b_val = int(min(255, 255 * mavi_zarf + 140 * ic_isima))
                    pikseller[x, y] = (r_val, g_val, b_val)

                elif mod == "SOOT_0G":
                    # İçte parlak sarı/turuncu kurum kabuğu (norm_r ~ 0.55 - 0.82), dışta ince mavi reaksiyon zonu (0.98)
                    soot_zarf = math.exp(-((norm_r - 0.68) ** 2) / 0.032)
                    mavi_zarf = math.exp(-((norm_r - 0.98) ** 2) / 0.014)
                    r_val = int(min(255, 255 * soot_zarf + 40 * mavi_zarf))
                    g_val = int(min(255, 185 * soot_zarf + 150 * mavi_zarf))
                    b_val = int(min(255, 25 * soot_zarf + 255 * mavi_zarf))
                    pikseller[x, y] = (r_val, g_val, b_val)

                elif mod == "COOL_0G":
                    # UV/IR Kamera: Mor/Eflatun formaldehit emisyonu (norm_r ~ 0.45 - 0.95)
                    cool_zarf = math.exp(-((norm_r - 0.72) ** 2) / 0.055)
                    r_val = int(min(255, 185 * cool_zarf))
                    g_val = int(min(255, 55 * cool_zarf))
                    b_val = int(min(255, 245 * cool_zarf))
                    pikseller[x, y] = (r_val, g_val, b_val)

                else:
                    # Ay 0.16g: Konvektif sarı/turuncu plume + alt mavi taban
                    taban_mavi = math.exp(-((norm_r - 0.92) ** 2) / 0.025) if dy >= -15 else 0.3 * math.exp(-((norm_r - 0.95) ** 2) / 0.02)
                    ust_soot = math.exp(-((norm_r - 0.62) ** 2) / 0.045) * (1.25 if dy < 0 else 0.55)
                    r_val = int(min(255, 245 * ust_soot + 45 * taban_mavi))
                    g_val = int(min(255, 165 * ust_soot + 155 * taban_mavi))
                    b_val = int(min(255, 30 * ust_soot + 250 * taban_mavi))
                    pikseller[x, y] = (r_val, g_val, b_val)

        # Ölçek çubuğu (Scale bar: 5 mm)
        cizim = ImageDraw.Draw(img)
        cizim.line([(16, boyut - 18), (66, boyut - 18)], fill=(0, 245, 212), width=2)
        return img

    @staticmethod
    def goruntuyu_analiz_et(img: "Image.Image", piksel_basina_mm: float = 0.065) -> Dict[str, object]:
        """
        Verilen alev görüntüsünü (PIL.Image) piksel düzeyinde tarayarak:
        - Alev ağırlık merkezi (centroid),
        - Yatay ve dikey yayılım (bounding box) ve Küresellik İndeksi (Sphericity / Aspect Ratio),
        - Mavi Kemilüminesans (CH*), Sarı/Turuncu Soot Radyasyonu ve Mor/UV Soğuk Alev oranları,
        - Merkezden dışa (r = 0..R_max) RGB Radyal Yoğunluk Profilini hesaplar.
        """
        calisma_img = img.convert("RGB").resize((240, 240))
        w, h = calisma_img.size
        pikseller = calisma_img.load()

        alev_piksel_sayisi = 0
        mavi_piksel = 0
        soot_piksel = 0
        cool_piksel = 0

        toplam_x, toplam_y = 0.0, 0.0
        min_x, max_x = w, 0
        min_y, max_y = h, 0

        for y in range(h):
            for x in range(w):
                r, g, b = pikseller[x, y]
                parlaklik = max(r, g, b)
                if parlaklik < 38:
                    continue

                alev_piksel_sayisi += 1
                toplam_x += x
                toplam_y += y
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

                # Spektral sınıflandırma
                if b > r + 35 and b > 80:
                    mavi_piksel += 1
                elif r > 130 and g > 80 and b < 95:
                    soot_piksel += 1
                elif r > 90 and b > 120 and g < 90:
                    cool_piksel += 1

        if alev_piksel_sayisi < 20:
            cx, cy = w // 2, h // 2
            kuresellik = 1.0
            esdeger_cap_mm = 0.0
        else:
            cx = int(toplam_x / alev_piksel_sayisi)
            cy = int(toplam_y / alev_piksel_sayisi)
            genislik_px = max(1, max_x - min_x)
            yukseklik_px = max(1, max_y - min_y)
            oran_wh = min(genislik_px, yukseklik_px) / max(genislik_px, yukseklik_px)
            kuresellik = round(oran_wh, 3)
            esdeger_yaricap_px = math.sqrt(alev_piksel_sayisi / math.pi)
            esdeger_cap_mm = round(2.0 * esdeger_yaricap_px * piksel_basina_mm, 2)

        toplam_aktif = max(1, alev_piksel_sayisi)
        mavi_oran = round((mavi_piksel / toplam_aktif) * 100.0, 1)
        soot_oran = round((soot_piksel / toplam_aktif) * 100.0, 1)
        cool_oran = round((cool_piksel / toplam_aktif) * 100.0, 1)

        # Radyal Yoğunluk Profili (r = 0 .. 105 piksel)
        radyal_profil: List[Tuple[float, float, float, float]] = []
        maks_r_px = 105
        for r_adim in range(0, maks_r_px, 3):
            r_top, g_top, b_top, sayac = 0.0, 0.0, 0.0, 0
            for aci_deg in range(0, 360, 15):
                rad = math.radians(aci_deg)
                px = int(cx + r_adim * math.cos(rad))
                py = int(cy + r_adim * math.sin(rad))
                if 0 <= px < w and 0 <= py < h:
                    rv, gv, bv = pikseller[px, py]
                    r_top += rv
                    g_top += gv
                    b_top += bv
                    sayac += 1
            if sayac > 0:
                r_mm = round(r_adim * piksel_basina_mm, 2)
                radyal_profil.append((r_mm, r_top / sayac, g_top / sayac, b_top / sayac))

        # Fiziksel rejim teşhisi
        if cool_oran > 25.0:
            teshis = "🟣 FLEX-2 GÖRÜNMEZ SOĞUK ALEV (Cool Flame ~640 K - Formaldehit UV/IR Emisyonu)"
            tahmini_sicaklik_k = 645
        elif kuresellik >= 0.88 and soot_oran < 20.0:
            teshis = "🔵 0.00g KÜRESEL TEMİZ DİFÜZYON ALEVİ (Yüksek CH* Kemilüminesans, Kurumsuz)"
            tahmini_sicaklik_k = 1980
        elif kuresellik >= 0.86 and soot_oran >= 20.0:
            teshis = "🟡 0.00g KÜRESEL KURUM (SOOT) KABUKLU ALEV (Uzun Kalış Süresi & Radyatif Isı Kaybı Riski)"
            tahmini_sicaklik_k = 1790
        else:
            teshis = f"🟠 KISMİ YERÇEKİMİ / KONVEKTİF UZAMIŞ ALEV (Küresellik Φ={kuresellik:.2f} < 0.85, Buoyancy Aktif)"
            tahmini_sicaklik_k = 2120

        return {
            "merkez_xy": (cx, cy),
            "kuresellik_indeksi": kuresellik,
            "esdeger_cap_mm": esdeger_cap_mm,
            "mavi_kemiluminesans_yuzde": mavi_oran,
            "sari_soot_radyasyon_yuzde": soot_oran,
            "mor_soguk_alev_yuzde": cool_oran,
            "tahmini_sicaklik_k": tahmini_sicaklik_k,
            "rejim_teshisi": teshis,
            "radyal_profil": radyal_profil,
        }
