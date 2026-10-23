# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"
Modül 3: Canlı NASA NTRS / PSI Açık Veri Sorgulayıcı, Hazır Deney Telemetri Setleri,
         Pearson Korelasyonu, Z-Skoru Anomali Tespiti ve Bellek-İçi Veri Seslendirme (Sonification) Motoru.
"""

import csv
import io
import math
import os
import struct
import wave
from typing import Dict, List, Optional, Tuple

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class NasaTelemetriVeVeriAvcisi:
    """
    1) NASA NTRS (Technical Reports Server) ve NASA Images API üzerinden canlı mikroçekim yanma literatürü arar.
    2) CSV dosyalarını %100 salt-okunur olarak RAM'e yükler veya hazır NASA deney telemetrilerini (FLEX-2, BASS-II, Saffire) üretir.
    3) Çift eksenli Pearson korelasyonu, Z-skoru anomali tespiti ve 16-bit PCM WAV seslendirme (Sonification) yapar.
    """

    @staticmethod
    def canli_nasa_ntrs_ara(sorgu: str, maks_sonuc: int = 8) -> List[Dict[str, str]]:
        """
        NASA Technical Reports Server (NTRS) açık API'sinden (urllib standart kütüphanesi ile)
        ve 673 kayıtlık yerel NTRS korpusundan mikroçekim yanma makalelerini salt-okunur çeker.
        """
        bulunanlar: List[Dict[str, str]] = []
        if not sorgu.strip():
            return bulunanlar

        # 1. Önce yerel 673 kayıtlık doğrulanmış NTRS korpusunda BM25 araması
        try:
            from literatur_ai import motor_al
            motor = motor_al()
            if motor.kayitlar:
                for s in motor.ara(sorgu.strip(), ust_k=maks_sonuc):
                    k = s.kayit
                    bulunanlar.append({
                        "kanit_id": f"NTRS-{k.ntrs_id}",
                        "baslik": f"{k.baslik} ({k.kisa_atif()}, BM25 Skor={s.skor:.2f})",
                        "merkez": k.merkez or "NASA Technical Reports Server (Yerel Korpus)",
                        "ozet": k.ozet[:650],
                        "kaynak_url": k.url,
                    })
                if len(bulunanlar) >= maks_sonuc:
                    return bulunanlar[:maks_sonuc]
        except Exception:
            pass

        # 2. Canlı NTRS API araması (NtrsIstemcisi - stdlib urllib, requests gerektirmez)
        try:
            from ntrs_istemcisi import NtrsIstemcisi
            istemci = NtrsIstemcisi(zaman_asimi=10)
            _, kayitlar = istemci.ara(f"microgravity combustion {sorgu.strip()}", sayfa_boyutu=maks_sonuc)
            mevcut_idler = {b["kanit_id"] for b in bulunanlar}
            for k in kayitlar:
                kid = f"NTRS-{k.ntrs_id}"
                if kid in mevcut_idler:
                    continue
                bulunanlar.append({
                    "kanit_id": kid,
                    "baslik": f"{k.baslik} ({k.kisa_atif()})",
                    "merkez": k.merkez or "NASA Technical Reports Server (Canlı API)",
                    "ozet": k.ozet[:650],
                    "kaynak_url": k.url,
                })
                if len(bulunanlar) >= maks_sonuc:
                    break
        except Exception:
            pass

        return bulunanlar

    @staticmethod
    def hazir_telemetri_veri_seti_uret(senaryo_kodu: str) -> Tuple[str, List[str], Dict[str, List[float]]]:
        """
        Diske hiçbir şey yazmadan doğrudan RAM'de 3 farklı gerçekçi NASA mikroçekim yanma telemetri
        veri seti üretir:
        1) FLEX-2: Sıcak Alev -> Radyatif Sönme -> Görünmez Soğuk Alev (Cool Flame) -> Yeniden Tutuşma
        2) BASS-II: Kapalı Modül O2 Artış Anomalisi (Ventilasyon Fanı Açılması & O2 Sızıntısı)
        3) Saffire-IV: Keşif Atmosferinde (%34 O2, 56.5 kPa) Büyük Ölçekli Basınç ve Isı Piki
        """
        zaman: List[float] = []
        sicaklik_k: List[float] = []
        oksijen_yuzde: List[float] = []
        co_ppm: List[float] = []
        cap_kare_mm2: List[float] = []
        radyatif_isi_kw_m2: List[float] = []

        if "FLEX" in senaryo_kodu:
            dosya_adi = "PSI_FLEX2_Heptan_Iki_Asamali_Soguk_Alev.csv (Bellek-İçi)"
            d2 = 12.25  # d0 = 3.5 mm
            for t in range(65):
                zaman.append(float(t))
                if t < 24:
                    # Faz 1: Küresel Sıcak Alev (Hot Flame ~1950 K)
                    d2 = max(3.8, d2 - 0.34)
                    temp = 1920.0 - t * 8.5 + math.sin(t) * 18.0
                    o2 = 20.9 - t * 0.08
                    co = 45.0 + t * 4.2
                    rad = 28.5 - t * 0.4
                elif 24 <= t < 48:
                    # Faz 2: Radyatif Sönme Sonrası Görünmez Soğuk Alev (Cool Flame ~640 K, Yüksek CO!)
                    d2 = max(1.1, d2 - 0.09)
                    temp = 645.0 + math.cos(t * 0.6) * 22.0
                    o2 = 19.0 - (t - 24) * 0.04
                    co = 185.0 + (t - 24) * 14.5
                    rad = 2.4 + math.sin(t) * 0.3
                else:
                    # Faz 3: Buhar Bulutu Yeniden Tutuşma Piki (Hot Re-ignition) ve Tam Sönme
                    if t < 54:
                        d2 = max(0.2, d2 - 0.16)
                        temp = 1680.0 - (t - 48) * 65.0
                        o2 = 17.8
                        co = 490.0 - (t - 48) * 30.0
                        rad = 21.0
                    else:
                        d2 = 0.0
                        temp = max(310.0, 650.0 - (t - 54) * 45.0)
                        o2 = 18.2
                        co = max(40.0, 260.0 - (t - 54) * 22.0)
                        rad = 0.5

                sicaklik_k.append(round(temp, 1))
                oksijen_yuzde.append(round(o2, 2))
                co_ppm.append(round(co, 1))
                cap_kare_mm2.append(round(d2, 2))
                radyatif_isi_kw_m2.append(round(rad, 2))

        elif "SAFFIRE" in senaryo_kodu:
            dosya_adi = "NTRS_Saffire_Cygnus_Keşif_Atmosferi_34O2.csv (Bellek-İçi)"
            for t in range(65):
                zaman.append(float(t))
                if t < 10:
                    temp = 298.0 + t * 15.0
                    o2 = 34.0 - t * 0.05
                    co = 10.0 + t * 2.5
                    d2 = 56.5 + t * 0.12  # Kabin basıncı kPa
                    rad = 1.5 + t * 1.2
                elif 10 <= t < 45:
                    temp = 450.0 + (t - 10) * 28.0 + math.sin(t) * 30.0
                    o2 = 33.5 - (t - 10) * 0.24
                    co = 40.0 + (t - 10) * 19.5
                    d2 = 57.7 + (t - 10) * 0.48
                    rad = 14.0 + (t - 10) * 1.35
                else:
                    temp = max(340.0, 1380.0 - (t - 45) * 52.0)
                    o2 = 25.1
                    co = max(65.0, 720.0 - (t - 45) * 28.0)
                    d2 = max(56.8, 74.5 - (t - 45) * 0.85)
                    rad = max(1.2, 60.0 - (t - 45) * 2.9)

                sicaklik_k.append(round(temp, 1))
                oksijen_yuzde.append(round(o2, 2))
                co_ppm.append(round(co, 1))
                cap_kare_mm2.append(round(d2, 2))
                radyatif_isi_kw_m2.append(round(rad, 2))

        else:
            # BASS-II: Kapalı Modül O2 Artış ve Fan Anomalisi
            dosya_adi = "PSI_BASS2_Kapali_Modul_O2_Fan_Anomalisi.csv (Bellek-İçi)"
            for t in range(65):
                zaman.append(float(t))
                if t < 20:
                    o2 = 20.9 - t * 0.14
                    temp = 310.0 + t * 14.5
                    co = 18.0 + t * 4.5
                    d2 = 8.0  # Fan hızı cm/s
                    rad = 4.5 + t * 0.65
                elif 20 <= t < 38:
                    # Düşük O2 (<%18) kurum ve CO birikimi
                    o2 = 18.1 - (t - 20) * 0.16
                    temp = 600.0 + math.sin(t) * 24.0
                    co = 110.0 + (t - 20) * 21.0
                    d2 = 4.0
                    rad = 17.5 + math.cos(t) * 1.5
                elif 38 <= t < 50:
                    # ANOMALİ: Fan açılması / O2 sızıntısı ile O2 hızla yükseliyor!
                    o2 = 15.3 + (t - 38) * 0.78
                    temp = 640.0 + (t - 38) * 38.0
                    co = 480.0 - (t - 38) * 18.0
                    d2 = 24.0
                    rad = 22.0 + (t - 38) * 2.4
                else:
                    # İnce Su Sisi (Fine Water Mist) ve Ventilasyon Kesme ile Söndürme
                    o2 = 20.8
                    temp = max(305.0, 1090.0 - (t - 50) * 55.0)
                    co = max(25.0, 260.0 - (t - 50) * 16.0)
                    d2 = 0.0
                    rad = max(0.4, 50.0 - (t - 50) * 3.5)

                sicaklik_k.append(round(temp, 1))
                oksijen_yuzde.append(round(o2, 2))
                co_ppm.append(round(co, 1))
                cap_kare_mm2.append(round(d2, 2))
                radyatif_isi_kw_m2.append(round(rad, 2))

        sutunlar = [
            "Zaman_sn",
            "Sicaklik_K",
            "Oksijen_Yuzde",
            "CO_Emisyon_ppm",
            "Damlacik_d2_veya_Akis",
            "Radyatif_Isi_kW_m2",
        ]
        veri_sozlugu = {
            "Zaman_sn": zaman,
            "Sicaklik_K": sicaklik_k,
            "Oksijen_Yuzde": oksijen_yuzde,
            "CO_Emisyon_ppm": co_ppm,
            "Damlacik_d2_veya_Akis": cap_kare_mm2,
            "Radyatif_Isi_kW_m2": radyatif_isi_kw_m2,
        }
        return dosya_adi, sutunlar, veri_sozlugu

    @staticmethod
    def csv_dosyasi_salt_okunur_yukle(dosya_yolu: str) -> Tuple[str, List[str], Dict[str, List[float]]]:
        with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
            satirlar = list(csv.reader(f))

        if len(satirlar) < 2:
            raise ValueError("CSV dosyasında yeterli veri satırı bulunamadı.")

        basliklar = [b.strip() or f"Sutun_{i+1}" for i, b in enumerate(satirlar[0])]
        gecici: Dict[str, List[float]] = {b: [] for b in basliklar}

        for satir in satirlar[1:]:
            if not satir or len(satir) < len(basliklar):
                continue
            for i, b in enumerate(basliklar):
                try:
                    gecici[b].append(float(satir[i]))
                except ValueError:
                    pass

        sayisal = [b for b, liste in gecici.items() if len(liste) >= 2]
        if not sayisal:
            raise ValueError("CSV dosyasında sayısal sütun bulunamadı.")

        return os.path.basename(dosya_yolu), sayisal, {b: gecici[b] for b in sayisal}

    @staticmethod
    def pearson_ve_anomali_hesapla(
        x_list: List[float],
        y1_list: List[float],
        y2_list: Optional[List[float]] = None
    ) -> Dict[str, object]:
        n = min(len(x_list), len(y1_list))
        if n < 2:
            return {"ortalama": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "pearson": 0.0, "anomaliler": []}

        y1 = y1_list[:n]
        ort_y1 = sum(y1) / n
        std_y1 = math.sqrt(sum((v - ort_y1) ** 2 for v in y1) / n)
        anomaliler: List[Tuple[int, float, float, float]] = []

        if std_y1 > 0:
            for idx, v in enumerate(y1):
                z = abs(v - ort_y1) / std_y1
                if z > 1.95:
                    anomaliler.append((idx, x_list[idx], v, round(z, 2)))

        pearson_r = 0.0
        if y2_list and len(y2_list) >= n:
            y2 = y2_list[:n]
            ort_y2 = sum(y2) / n
            pay = sum((y1[i] - ort_y1) * (y2[i] - ort_y2) for i in range(n))
            px = math.sqrt(sum((y1[i] - ort_y1) ** 2 for i in range(n)))
            py = math.sqrt(sum((y2[i] - ort_y2) ** 2 for i in range(n)))
            if px > 0 and py > 0:
                pearson_r = round(pay / (px * py), 4)

        return {
            "ortalama": round(ort_y1, 2),
            "std": round(std_y1, 2),
            "min": round(min(y1), 2),
            "max": round(max(y1), 2),
            "pearson": pearson_r,
            "anomaliler": anomaliler,
        }

    @staticmethod
    def veriyi_seslendir_wav_bellek(degerler: List[float], sure_ms_toplam: int = 3200) -> bool:
        """
        Sayısal telemetri dizisini 220 Hz - 1100 Hz frekans aralığına eşleyerek diske hiçbir
        dosya yazmadan (io.BytesIO) 16-bit PCM WAV üretir ve çalar.
        """
        if not WINSOUND_AVAILABLE or not degerler or len(degerler) < 2:
            return False

        en_kucuk, en_buyuk = min(degerler), max(degerler)
        aralik = (en_buyuk - en_kucuk) or 1.0
        ornek_hizi = 22050
        adim_suresi_sn = max(0.035, min(0.10, (sure_ms_toplam / 1000.0) / len(degerler)))
        adim_ornek_sayisi = int(ornek_hizi * adim_suresi_sn)

        pcm_tampon = bytearray()
        faz = 0.0
        iki_pi = 2.0 * math.pi

        for d in degerler[:80]:
            norm = (d - en_kucuk) / aralik
            frekans = 220.0 + norm * 860.0
            faz_artisi = iki_pi * frekans / ornek_hizi
            for i in range(adim_ornek_sayisi):
                zarf = 1.0
                if i < 120:
                    zarf = i / 120.0
                elif i > adim_ornek_sayisi - 120:
                    zarf = (adim_ornek_sayisi - i) / 120.0
                ornek = int(math.sin(faz) * 13500.0 * zarf)
                pcm_tampon.extend(struct.pack("<h", ornek))
                faz += faz_artisi

        wav_bellek = io.BytesIO()
        with wave.open(wav_bellek, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(ornek_hizi)
            wf.writeframes(bytes(pcm_tampon))

        winsound.PlaySound(wav_bellek.getvalue(), winsound.SND_MEMORY)
        return True

    @staticmethod
    def html_juri_sunumu_olustur(
        dosya_yolu: str,
        ai_raporu: str,
        malzeme_ozet: str,
        bosluk_ozet: str,
        optik_ozet: str = ""
    ) -> str:
        """
        NASA Space Apps 2026 jürisi için karanlık temalı, bağımsız (self-contained)
        ve tarayıcıda doğrudan açılabilen interaktif bir HTML5 sunum panosu üretir.
        """
        import html as _html
        ai_esc = _html.escape(ai_raporu)
        mat_esc = _html.escape(malzeme_ozet)
        gap_esc = _html.escape(bosluk_ozet)
        opt_esc = _html.escape(optik_ozet)

        icerik = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>NASA Space Apps 2026 — Flame in Freefall Jury Dashboard</title>
<style>
  body {{ background:#050914; color:#E2E8F0; font-family:'Consolas',monospace; margin:0; padding:24px; }}
  .header {{ background:linear-gradient(90deg,#0D1B2A,#1E3A8A); border:1px solid #00F5D4; border-radius:12px; padding:20px; margin-bottom:20px; }}
  h1 {{ color:#00F5D4; margin:0 0 8px 0; font-size:22px; }}
  h2 {{ color:#FFD166; border-bottom:1px solid #1E293B; padding-bottom:6px; font-size:16px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
  .card {{ background:#0D1627; border:1px solid #1E293B; border-radius:10px; padding:16px; }}
  pre {{ background:#040812; color:#00FF88; padding:12px; border-radius:8px; overflow-x:auto; white-space:pre-wrap; font-size:12px; line-height:1.45; }}
  .badge {{ display:inline-block; background:#C62828; color:#FFF; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:bold; }}
</style>
</head>
<body>
  <div class="header">
    <span class="badge">NASA SPACE APPS CHALLENGE 2026</span>
    <h1>🔥 FLAME IN FREEFALL: AI-POWERED MICROGRAVITY FIRE SAFETY INSIGHTS</h1>
    <div>Evidence-First PSI & NTRS Synthesis • 0g / Moon 0.16g / Mars 0.38g • BASS-II • FLEX-2 Cool Flames • Saffire • ACME • SoFIE</div>
  </div>
  <div class="card" style="margin-bottom:18px;">
    <h2>1. 🤖 KANIT-ODAKLI (EVIDENCE-FIRST) AI YANGIN GÜVENLİĞİ VE MONTE CARLO RAPORU</h2>
    <pre>{ai_esc}</pre>
  </div>
  <div class="grid">
    <div class="card">
      <h2>2. 🛡️ UZAY ARACI MALZEME YANICILIK ATLASI (0G vs AY 0.16G)</h2>
      <pre>{mat_esc}</pre>
    </div>
    <div class="card">
      <h2>3. 🔭 DERİN UZAY ARAŞTIRMA BOŞLUĞU MATRİSİ (GAP FINDER)</h2>
      <pre>{gap_esc}</pre>
    </div>
  </div>
  <div class="card" style="margin-top:18px;">
    <h2>4. 📸 ÇOK MODLU OPTİK ALEV SPEKTRAL & KABİN DİJİTAL İKİZ ÖZETİ</h2>
    <pre>{opt_esc}</pre>
  </div>
</body>
</html>"""
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            f.write(icerik)
        return dosya_yolu
