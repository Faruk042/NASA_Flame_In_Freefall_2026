# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"
Modül 4: Halüsinasyon Korumalı, Kanıt-Odaklı (Evidence-First) Süper Zeka Sentez Motoru
         ve İsteğe Bağlı Google Gemini Bulut RAG Köprüsü (Ollama Bağımlılığı Kaldırılmıştır).
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from mikroyercekimi_fizik_motoru import MikroYercekimiFizikMotoru
from nasa_psi_veritabani import (
    ARASTIRMA_BOSLUKLARI,
    KanitOdakliAramaMotoru,
    UZAY_MALZEME_ATLASI,
)

try:
    from literatur_ai import motor_al as _ntrs_motor_al
    NTRS_KORPUS_AVAILABLE = True
except Exception:
    NTRS_KORPUS_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from google import genai
    from google.genai import types
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False


class FlameInFreefallAIEngine:
    """
    Uzay güvenliğinde sıfır halüsinasyon ilkesiyle çalışan çift katmanlı AI analiz motoru:
    1) Yerleşik Deterministik Kanıt-Odaklı Sentez Motoru (Çevrimdışı, 0 RAM yükü, <50ms yanıt)
    2) İsteğe Bağlı Google Gemini API + NASA PSI RAG Motoru
    """

    def __init__(self, api_key: str = "") -> None:
        self.arama_motoru = KanitOdakliAramaMotoru()
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.gemini_client = None
        if GEMINI_SDK_AVAILABLE and self.api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.api_key)
            except Exception:
                self.gemini_client = None

    def api_anahtari_guncelle(self, yeni_anahtar: str) -> bool:
        self.api_key = yeni_anahtar.strip()
        if GEMINI_SDK_AVAILABLE and self.api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.api_key)
                return True
            except Exception:
                self.gemini_client = None
                return False
        self.gemini_client = None
        return False

    @staticmethod
    def _metinden_sayisal_telemetri_ayikla(metin: str) -> Dict[str, float]:
        """Kullanıcının doğal dildeki sorusundan sıcaklık, O2, CO, yerçekimi ve akış hızı değerlerini çıkarır."""
        alt = metin.lower()

        # Sıcaklık (K veya C)
        sicaklik_k = 620.0
        m_k = re.search(r"(\d+(?:\.\d+)?)\s*k\b", alt)
        m_c = re.search(r"(\d+(?:\.\d+)?)\s*(?:°c|derece|c\b)", alt)
        if m_k:
            sicaklik_k = float(m_k.group(1))
        elif m_c:
            sicaklik_k = float(m_c.group(1)) + 273.15

        # Oksijen yüzdesi (%O2)
        oksijen = 17.5 if ("düşük oksijen" in alt or "eksik yanma" in alt) else 20.9
        m_o2 = (
            re.search(r"o2[^\d%]{0,12}%\s*(\d+(?:\.\d+)?)", alt)
            or re.search(r"%\s*(\d+(?:\.\d+)?)\s*o2", alt)
            or re.search(r"oksijen[^\d%]{0,15}%\s*(\d+(?:\.\d+)?)", alt)
        )
        if m_o2:
            oksijen = float(m_o2.group(1))

        # CO (ppm)
        co_ppm = 120.0 if ("co " in alt or "karbonmonoksit" in alt) else 35.0
        m_co = re.search(r"(\d+(?:\.\d+)?)\s*ppm", alt)
        if m_co:
            co_ppm = float(m_co.group(1))

        # Yerçekimi (g)
        yercekimi = 0.0
        if "0.16" in alt or "ay " in alt or "lunar" in alt:
            yercekimi = 0.16
        elif "0.38" in alt or "mars" in alt:
            yercekimi = 0.38
        elif "1g" in alt or "dünya" in alt:
            yercekimi = 1.0

        # Fan / Akış hızı (cm/s)
        fan_cm_s = 6.0
        m_fan = re.search(r"(\d+(?:\.\d+)?)\s*cm/s", alt)
        if m_fan:
            fan_cm_s = float(m_fan.group(1))
        elif "0 rpm" in alt or "fan kapalı" in alt:
            fan_cm_s = 0.0

        # O2 artış kontrolü (örn: %20.8'den %23.4'e yükseldi)
        onceki_o2 = 20.9
        m_artis = re.search(r"%\s*(\d+(?:\.\d+)?)[^\d%]{1,15}%\s*(\d+(?:\.\d+)?)", alt)
        if m_artis:
            onceki_o2 = float(m_artis.group(1))
            oksijen = float(m_artis.group(2))

        return {
            "sicaklik_k": sicaklik_k,
            "oksijen_yuzde": oksijen,
            "onceki_oksijen_yuzde": onceki_o2,
            "co_ppm": co_ppm,
            "yercekimi_g": yercekimi,
            "fan_hizi_cm_s": fan_cm_s,
            "basinc_kpa": 56.5 if ("56.5" in alt or "keşif atmosferi" in alt or "saffire" in alt) else 101.3,
        }

    def kanit_odakli_analiz_uret(self, soru: str, bulut_kullan: bool = False) -> str:
        """
        Kullanıcı sorusunu veya deney senaryosunu NASA PSI/NTRS kanıtlarıyla eşleştirerek
        halüsinasyonsuz, sayısal ve referans kodlu yangın güvenliği raporu üretir.
        """
        telemetri = self._metinden_sayisal_telemetri_ayikla(soru)
        anomali_raporu = MikroYercekimiFizikMotoru.kabin_telemetri_anomali_analizi(
            sicaklik_k=telemetri["sicaklik_k"],
            oksijen_yuzde=telemetri["oksijen_yuzde"],
            co_ppm=telemetri["co_ppm"],
            basinc_kpa=telemetri["basinc_kpa"],
            fan_hizi_cm_s=telemetri["fan_hizi_cm_s"],
            onceki_oksijen_yuzde=telemetri["onceki_oksijen_yuzde"],
        )

        damlacik_hesabi = MikroYercekimiFizikMotoru.damlacik_yanma_analizi(
            yakit_adi="n-Heptan (C7H16 - FLEX Referansı)",
            yercekimi_g=telemetri["yercekimi_g"],
            oksijen_yuzde=telemetri["oksijen_yuzde"],
            basinc_kpa=telemetri["basinc_kpa"],
            d0_mm=2.8,
            akis_hizi_cm_s=telemetri["fan_hizi_cm_s"],
        )

        eslesen_deneyler = self.arama_motoru.deneyleri_ara_ve_sirala(soru)[:3]
        malzeme_siralamasi = self.arama_motoru.malzemeleri_atmosfere_gore_degerlendir(
            ortam_o2_yuzde=telemetri["oksijen_yuzde"],
            yercekimi_g=telemetri["yercekimi_g"],
        )

        yerel_rapor = self._formatla_deterministik_rapor(
            soru=soru,
            telemetri=telemetri,
            anomali_raporu=anomali_raporu,
            damlacik_hesabi=damlacik_hesabi,
            eslesen_deneyler=eslesen_deneyler,
            malzeme_siralamasi=malzeme_siralamasi,
        )

        if bulut_kullan and self.gemini_client is not None:
            try:
                rag_baglam = (
                    "Sen NASA Space Apps 2026 'Flame in Freefall' yangın güvenliği baş mühendisisin. "
                    "Aşağıdaki doğrulanmış NASA PSI/NTRS deney kanıtlarını ve fizik motoru hesaplamalarını "
                    "kullanarak soruyu Türkçe, bilimsel, kanıt kodlarını ([PSI-BASS-001] vb.) belirterek yanıtla. "
                    "Asla spekülasyon veya halüsinasyon üretme.\n\n"
                    f"DOĞRULANMIŞ KANIT VE FİZİK ÖZETİ:\n{yerel_rapor}\n\n"
                    f"KULLANICI SORUSU:\n{soru}"
                )
                yanit = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=rag_baglam,
                )
                if yanit and yanit.text:
                    return (
                        "🌐 [MOD: GOOGLE GEMINI BULUT API + NASA PSI KANIT RAG MOTORU]\n"
                        + "=" * 78 + "\n"
                        + yanit.text.strip()
                        + "\n\n" + "=" * 78 + "\n"
                        + "📌 [DOĞRULANMIŞ DETERMINİSTİK FİZİK & PSI KANIT EKİ]:\n"
                        + yerel_rapor
                    )
            except Exception as exc:
                return f"[!] Bulut API uyarısı ({exc}) — Yerleşik Deterministik Kanıt Motoru devreye alındı:\n\n{yerel_rapor}"

        return yerel_rapor

    @staticmethod
    def _formatla_deterministik_rapor(
        soru: str,
        telemetri: Dict[str, float],
        anomali_raporu: Dict[str, object],
        damlacik_hesabi: Dict[str, object],
        eslesen_deneyler: list,
        malzeme_siralamasi: List[Dict[str, object]],
    ) -> str:
        satirlar = [
            "==============================================================================",
            "   🚀 FLAME IN FREEFALL: KANIT-ODAKLI (EVIDENCE-FIRST) YANGIN GÜVENLİĞİ RAPORU",
            "==============================================================================",
            f"Analiz Zamanı       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Algılanan Ortam     : {telemetri['yercekimi_g']:.2f}g | O2: %{telemetri['oksijen_yuzde']:.1f} | "
            f"Sıcaklık: {telemetri['sicaklik_k']:.0f} K | CO: {telemetri['co_ppm']:.0f} ppm | "
            f"Basınç: {telemetri['basinc_kpa']:.1f} kPa | Akış: {telemetri['fan_hizi_cm_s']:.1f} cm/s",
            f"Tehlike Durumu      : {anomali_raporu['tehlike_seviyesi']}",
            "------------------------------------------------------------------------------",
            "1. FİZİKSEL ANOMALİ VE MİKROÇEKİM YANMA TEŞHİSİ:",
        ]

        for b in anomali_raporu["bulgular"]:
            satirlar.append(f"   • {b}")

        satirlar.extend([
            "",
            "2. SAYISAL TERMODİNAMİK VE d²-YASASI SİMÜLASYON ÇIKTISI:",
            f"   • Alev Rejimi              : {damlacik_hesabi['durum_metni']}",
            f"   • Sıcak Alev Sabiti (K)    : {damlacik_hesabi['k_sicak']} mm²/s  |  Soğuk Alev (K_cool): {damlacik_hesabi['k_soguk']} mm²/s",
            f"   • Alev Sıcaklığı (Tf)      : {damlacik_hesabi['t_sicak_k']} K  |  Soğuk Alev (T_cool): {damlacik_hesabi['t_soguk_k']} K",
            f"   • Boyutsuz Sayılar         : Grashof (Gr)={damlacik_hesabi['grashof']} | Reynolds (Re)={damlacik_hesabi['reynolds']} | Damköhler (Da)={damlacik_hesabi['damkohler']}",
            f"   • Kurum (Soot) & CO İndeksi: Soot=%{damlacik_hesabi['soot_indeksi']} | Tahmini CO={damlacik_hesabi['co_ppm']} ppm",
        ])

        mc = MikroYercekimiFizikMotoru.monte_carlo_belirsizlik_analizi(
            yakit_adi="n-Heptan (C7H16 - FLEX Referansı)",
            yercekimi_g=telemetri["yercekimi_g"],
            oksijen_yuzde=telemetri["oksijen_yuzde"],
            basinc_kpa=telemetri["basinc_kpa"],
            d0_mm=2.8,
            akis_hizi_cm_s=telemetri["fan_hizi_cm_s"],
        )
        ikiz = MikroYercekimiFizikMotoru.kabin_duman_ve_sensor_dijital_ikizi_hesapla(
            yercekimi_g=telemetri["yercekimi_g"],
            hvac_akis_cm_s=telemetri["fan_hizi_cm_s"],
        )

        satirlar.extend([
            "",
            "2B. MONTE CARLO (%90 GÜVEN ARALIĞI) BELİRSİZLİK & SENSÖR DİJİTAL İKİZ ANALİZİ:",
            f"   • Yanma Süresi (tb Dağılımı): P05={mc['tb_p05']} sn | Medyan={mc['tb_medyan']} sn | P95={mc['tb_p95']} sn",
            f"   • Soğuk Alev Olasılığı      : %{mc['cool_flame_olasilik_yuzde']}  |  P95 Zirve CO: {mc['co_p95']:.0f} ppm",
            f"   • Sensör Algılama Süreleri  : Tavan Dedektörü={ikiz['t_tavan_sn']} sn | HVAC Kanal={ikiz['t_hvac_sn']} sn | Lokal Mid-IR={ikiz['t_lokal_ir_sn']} sn",
            f"   • Duman Dağılım Teşhisi     : {ikiz['teshis']}",
            "",
            "3. DOĞRULANMIŞ NASA PSI & NTRS KANIT REFERANSLARI (HALÜSİNASYON KORUMALI):",
        ])

        for skor, kayit in eslesen_deneyler:
            ntrs_str = ", ".join(f"https://ntrs.nasa.gov/citations/{nid}" for nid in getattr(kayit, "ntrs_referanslari", ()))
            satirlar.append(
                f"   [{kayit.kanit_id}] ({kayit.program_adi} - Eşleşme Güveni: %{skor})\n"
                f"      Başlık  : {kayit.baslik}\n"
                f"      Bulgu   : {kayit.temel_bulgular}\n"
                f"      Çıkarım : {kayit.yangin_guvenligi_cikarimi}"
                + (f"\n      NTRS URL: {ntrs_str}" if ntrs_str else "")
            )

        if NTRS_KORPUS_AVAILABLE:
            try:
                ntrs_motor = _ntrs_motor_al()
                if ntrs_motor.kayitlar:
                    ntrs_yanit = ntrs_motor.soru_yanitla(soru, ust_k=5)
                    satirlar.extend([
                        "",
                        f"3B. GERÇEK NASA NTRS AKADEMİK KORPUSU ({len(ntrs_motor.kayitlar)} YAYIN) BM25 + MMR KANIT SENTEZİ:",
                        f"   • Literatür Kanıt Güveni: {ntrs_yanit.guven_duzeyi} ({ntrs_yanit.guven_aciklamasi})",
                    ])
                    for oz in ntrs_yanit.ozet[:3]:
                        satirlar.append(f"   • \"{oz.cumle}\" [NTRS:{oz.ntrs_id} — https://ntrs.nasa.gov/citations/{oz.ntrs_id}]")
                    if ntrs_yanit.sayisal_bulgular:
                        satirlar.append("   • Makalelerden Çıkarılan Gerçek Sayısal Bulgular:")
                        for sb in ntrs_yanit.sayisal_bulgular[:5]:
                            satirlar.append(f"      - {sb.nicelik}: {sb.deger_metni} ({sb.kaynak_turu}) [NTRS:{sb.ntrs_id}]")
                    satirlar.append("   • En Yüksek BM25 Skorlu Gerçek NASA NTRS Yayınları:")
                    for idx_r, r_item in enumerate(ntrs_yanit.sonuclar[:4], 1):
                        satirlar.append(
                            f"      {idx_r}) [NTRS:{r_item.kayit.ntrs_id}] {r_item.kayit.baslik} "
                            f"({r_item.kayit.kisa_atif()}, Skor={r_item.skor:.2f}) -> {r_item.kayit.url}"
                        )
            except Exception:
                pass

        satirlar.extend([
            "",
            "4. MEVCUT ATMOSFER İÇİN MALZEME YANICILIK DEĞERLENDİRMESİ (NASA-STD-6001B):",
        ])
        for m_rapor in malzeme_siralamasi[:4]:
            m_obj = m_rapor["malzeme"]
            satirlar.append(
                f"   • {m_obj.malzeme_adi}: {m_rapor['durum']} "
                f"(Kritik LOC: %{m_rapor['aktif_loc']} O2 | Yayılım Hızı: {m_rapor['aktif_hiz']} mm/s)"
            )

        satirlar.extend([
            "",
            "5. NASA STANDARTLARINA UYGUN ACİL MÜDAHALE PROTOKOLÜ:",
        ])
        for adim in anomali_raporu["protokol_adimlari"]:
            satirlar.append(f"   ✅ {adim}")

        satirlar.append("==============================================================================")
        return "\n".join(satirlar)
