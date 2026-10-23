# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"
Modül 2: Mikroçekim (0g), Kısmi Yerçekimi (Ay 0.16g, Mars 0.38g) ve Dünya (1.0g) Yanma Fiziği,
         FLEX İki Aşamalı Soğuk Alev (Cool Flame) Simülatörü ve Kabin Yangın Karar Destek Motoru.
"""

import math
from typing import Dict, List, Tuple


class MikroYercekimiFizikMotoru:
    """
    NASA BASS, FLEX-2, ACME ve SoFIE deneysel korelasyonlarına dayanan deterministik yanma fiziği motoru.
    """

    YAKIT_KATALOGU: Dict[str, Dict[str, float | str]] = {
        "n-Heptan (C7H16 - FLEX Referansı)": {
            "k_baz_mm2_s": 0.79,
            "k_cool_mm2_s": 0.24,
            "t_adiyabatik_k": 2240.0,
            "soot_egilimi": 0.68,
            "cool_flame_aktif": 1.0,
            "renk_sicak": "#38BDF8",
            "renk_soguk": "#A855F7",
        },
        "n-Dekan (C10H22 - FLEX-2 Ağır Hidrokarbon)": {
            "k_baz_mm2_s": 0.72,
            "k_cool_mm2_s": 0.28,
            "t_adiyabatik_k": 2260.0,
            "soot_egilimi": 0.82,
            "cool_flame_aktif": 1.0,
            "renk_sicak": "#60A5FA",
            "renk_soguk": "#C084FC",
        },
        "Metanol (CH3OH - Kurumsuz Alkol)": {
            "k_baz_mm2_s": 0.86,
            "k_cool_mm2_s": 0.0,
            "t_adiyabatik_k": 2080.0,
            "soot_egilimi": 0.04,
            "cool_flame_aktif": 0.0,
            "renk_sicak": "#34D399",
            "renk_soguk": "#34D399",
        },
        "Metan (CH4 - ACME Gaz Brülör)": {
            "k_baz_mm2_s": 0.98,
            "k_cool_mm2_s": 0.0,
            "t_adiyabatik_k": 2225.0,
            "soot_egilimi": 0.22,
            "cool_flame_aktif": 0.0,
            "renk_sicak": "#2DD4BF",
            "renk_soguk": "#2DD4BF",
        },
        "Etanol (C2H5OH - Biyo-Yakıt)": {
            "k_baz_mm2_s": 0.74,
            "k_cool_mm2_s": 0.12,
            "t_adiyabatik_k": 2140.0,
            "soot_egilimi": 0.30,
            "cool_flame_aktif": 0.5,
            "renk_sicak": "#4ADE80",
            "renk_soguk": "#818CF8",
        },
    }

    @classmethod
    def damlacik_yanma_analizi(
        cls,
        yakit_adi: str,
        yercekimi_g: float,
        oksijen_yuzde: float,
        basinc_kpa: float,
        d0_mm: float,
        akis_hizi_cm_s: float
    ) -> Dict[str, object]:
        """
        Sıvı damlacık yanmasını d²-yasası (d²(t) = d0² - K*t), doğal/zorlanmış konveksiyon (Grashof & Reynolds)
        ve FLEX deneylerindeki Radyatif Sönme -> Görünmez Soğuk Alev (Cool Flame) geçişiyle hesaplar.
        """
        bilgi = cls.YAKIT_KATALOGU.get(yakit_adi, cls.YAKIT_KATALOGU["n-Heptan (C7H16 - FLEX Referansı)"])
        k_baz = float(bilgi["k_baz_mm2_s"])
        k_cool_baz = float(bilgi["k_cool_mm2_s"])
        t_baz = float(bilgi["t_adiyabatik_k"])
        soot_baz = float(bilgi["soot_egilimi"])
        cool_yatkinlik = float(bilgi["cool_flame_aktif"])

        # 1. Doğal konveksiyon (buoyancy) hızı ve Grashof / Reynolds boyutsuz sayıları
        # v_buoy = sqrt(g * beta * dT * L)
        g_m_s2 = max(0.0, yercekimi_g) * 9.80665
        karakteristik_uzunluk_m = max(0.0005, d0_mm * 0.001 * 4.0)
        v_buoy_cm_s = math.sqrt(g_m_s2 * 0.003 * 1400.0 * karakteristik_uzunluk_m) * 100.0
        v_etkin_cm_s = math.sqrt((akis_hizi_cm_s ** 2) + (v_buoy_cm_s ** 2))

        grashof = (g_m_s2 * 0.003 * 1500.0 * (karakteristik_uzunluk_m ** 3)) / ((1.8e-5) ** 2)
        reynolds = ((v_etkin_cm_s * 0.01) * karakteristik_uzunluk_m) / 1.8e-5
        peclet = reynolds * 0.72

        # 2. Oksijen ve basınç düzeltmesi (Spalding B-transfer sayısı yaklaşımı)
        basinc_oran = max(0.25, basinc_kpa / 101.3)
        loc_esik = max(13.2, 15.2 - 1.1 * (basinc_oran - 1.0) - (0.6 if 0.05 < yercekimi_g < 0.30 else 0.0))

        # Blow-off (yüksek hava akışında üfleyerek sönme) kontrolü
        blow_off_esik_cm_s = 28.0 + (oksijen_yuzde - 18.0) * 2.2
        blow_off_var = akis_hizi_cm_s > blow_off_esik_cm_s
        oksijen_yetersiz = oksijen_yuzde < loc_esik

        if oksijen_yetersiz or blow_off_var:
            return {
                "yakit": yakit_adi,
                "durum_kodu": "BLOW_OFF" if blow_off_var else "EXTINCTION_LOC",
                "durum_metni": (
                    f"💨 ÜFLEYEREK SÖNME (Blow-Off > {blow_off_esik_cm_s:.1f} cm/s)"
                    if blow_off_var
                    else f"⚠️ KRİTİK OKSİJEN ALTINDA SÖNME (O2 < %{loc_esik:.1f} LOC)"
                ),
                "k_sicak": 0.0,
                "k_soguk": 0.0,
                "t_sicak_k": 300,
                "t_soguk_k": 300,
                "tb_sicak_sn": 0.0,
                "tb_toplam_sn": 0.0,
                "radyatif_gecis_sn": 0.0,
                "radyatif_gecis_cap_mm": 0.0,
                "cool_flame_olusur": False,
                "soot_indeksi": 0,
                "co_ppm": 0,
                "grashof": round(grashof, 2),
                "reynolds": round(reynolds, 2),
                "peclet": round(peclet, 2),
                "damkohler": 0.45,
                "v_buoy_cm_s": round(v_buoy_cm_s, 2),
                "v_etkin_cm_s": round(v_etkin_cm_s, 2),
                "alev_standoff_orani": 0.0,
                "renk_sicak": str(bilgi["renk_sicak"]),
                "renk_soguk": str(bilgi["renk_soguk"]),
                "zaman_serisi": [(0.0, d0_mm ** 2, 300.0, "SONUK")],
            }

        # 3. Yanma Hızı Sabiti K_hot (mm²/s)
        o2_faktor = math.log(1.0 + 1.8 * (oksijen_yuzde / 21.0)) / math.log(2.8)
        konveksiyon_carpani = 1.0 + 0.28 * math.sqrt(reynolds) + 0.12 * (grashof ** 0.25)
        k_sicak = round(k_baz * o2_faktor * (basinc_oran ** 0.25) * min(konveksiyon_carpani, 2.2), 3)

        # 4. FLEX Deneyi: Büyük Damlacıklarda Radyatif Sönme ve Görünmez Soğuk Alev (Cool Flame) Geçişi
        # Mikroçekimde (g < 0.08) ve d0 >= 2.2 mm olduğunda sıcak alev radyatif kayıpla sönüp Cool Flame'e geçer
        cool_flame_olusur = bool(
            cool_yatkinlik > 0.3 and yercekimi_g < 0.12 and d0_mm >= 2.1 and oksijen_yuzde <= 24.0
        )

        if cool_flame_olusur:
            gecis_cap_mm = round(d0_mm * 0.58, 2)
            radyatif_gecis_sn = round(((d0_mm ** 2) - (gecis_cap_mm ** 2)) / max(k_sicak, 0.05), 2)
            k_soguk = round(k_cool_baz * (basinc_oran ** 0.3), 3)
            plato_cap_mm = round(gecis_cap_mm * 0.45, 2)
            soguk_faz_sn = round(((gecis_cap_mm ** 2) - (plato_cap_mm ** 2)) / max(k_soguk, 0.05), 2)
            tb_toplam_sn = round(radyatif_gecis_sn + soguk_faz_sn, 2)
            durum_kodu = "TWO_STAGE_COOL_FLAME"
            durum_metni = "🟣 İKİ AŞAMALI YANMA: Sıcak Alev -> Radyatif Sönme -> Görünmez Soğuk Alev (FLEX)"
        else:
            gecis_cap_mm = 0.0
            radyatif_gecis_sn = round((d0_mm ** 2) / max(k_sicak, 0.05), 2)
            k_soguk = 0.0
            tb_toplam_sn = radyatif_gecis_sn
            durum_kodu = "HOT_STEADY"
            durum_metni = "🔵 KARARLI KÜRESEL DİFÜZYON ALEVİ (0G)" if yercekimi_g < 0.08 else f"🟠 KONVEKTİF ALEV ({yercekimi_g:.2f}g)"

        # 5. Alev Sıcaklığı, Kurum (Soot) Kabuğu ve CO Emisyonu
        radyatif_kayip_k = 145.0 if yercekimi_g < 0.1 else (75.0 if yercekimi_g < 0.4 else 25.0)
        t_sicak_k = int(t_baz * (0.82 + 0.18 * min(oksijen_yuzde / 21.0, 1.6)) - radyatif_kayip_k)
        t_soguk_k = 640 if cool_flame_olusur else t_sicak_k

        # 0g'de uzun kalış süresi (residence time) kurum kabuğunu artırır
        residence_carpani = 1.45 if yercekimi_g < 0.08 else (1.15 if yercekimi_g < 0.4 else 0.80)
        soot_indeksi = min(100, int(soot_baz * 100.0 * residence_carpani * (21.0 / max(oksijen_yuzde, 14.0))))
        co_ppm = int(35.0 + soot_indeksi * (5.4 if oksijen_yuzde < 18.5 else 1.8) + (180.0 if cool_flame_olusur else 0.0))

        damkohler = round((12.5 * (oksijen_yuzde / 21.0) * basinc_oran) / max(1.0, v_etkin_cm_s * 0.25), 2)
        alev_standoff_orani = round(5.8 - 1.4 * min(yercekimi_g, 1.0) + 0.06 * (oksijen_yuzde - 21.0), 2)

        # 6. Zaman serisi noktaları (t, d², T, rejim)
        zaman_serisi: List[Tuple[float, float, float, str]] = []
        adim_sayisi = 40
        dt = max(tb_toplam_sn / adim_sayisi, 0.05)
        for i in range(adim_sayisi + 1):
            t_an = round(i * dt, 2)
            if not cool_flame_olusur or t_an <= radyatif_gecis_sn:
                d2_an = max(0.0, (d0_mm ** 2) - k_sicak * t_an)
                zaman_serisi.append((t_an, round(d2_an, 3), float(t_sicak_k), "SICAK_ALEV"))
            else:
                t_fark = t_an - radyatif_gecis_sn
                d2_an = max(0.08, (gecis_cap_mm ** 2) - k_soguk * t_fark)
                zaman_serisi.append((t_an, round(d2_an, 3), float(t_soguk_k), "SOGUK_ALEV"))

        return {
            "yakit": yakit_adi,
            "durum_kodu": durum_kodu,
            "durum_metni": durum_metni,
            "k_sicak": k_sicak,
            "k_soguk": k_soguk,
            "t_sicak_k": t_sicak_k,
            "t_soguk_k": t_soguk_k,
            "tb_sicak_sn": radyatif_gecis_sn,
            "tb_toplam_sn": tb_toplam_sn,
            "radyatif_gecis_sn": radyatif_gecis_sn,
            "radyatif_gecis_cap_mm": gecis_cap_mm,
            "cool_flame_olusur": cool_flame_olusur,
            "soot_indeksi": soot_indeksi,
            "co_ppm": co_ppm,
            "grashof": round(grashof, 2),
            "reynolds": round(reynolds, 2),
            "peclet": round(peclet, 2),
            "damkohler": damkohler,
            "v_buoy_cm_s": round(v_buoy_cm_s, 2),
            "v_etkin_cm_s": round(v_etkin_cm_s, 2),
            "alev_standoff_orani": alev_standoff_orani,
            "renk_sicak": str(bilgi["renk_sicak"]),
            "renk_soguk": str(bilgi["renk_soguk"]),
            "zaman_serisi": zaman_serisi,
        }

    @staticmethod
    def akis_hizi_yayilim_egrisi_hesapla(
        yercekimi_g: float,
        oksijen_yuzde: float
    ) -> List[Tuple[float, float, str]]:
        """
        BASS ve SoFIE deneylerine göre kabin havalandırma hızı (0 - 45 cm/s) değiştikçe
        katı yakıt alev yayılım hızının (mm/s) nasıl değiştiğini (Quenching -> Peak -> Blow-off) hesaplar.
        """
        noktalar: List[Tuple[float, float, str]] = []
        v_buoy = math.sqrt(max(0.0, yercekimi_g) * 9.81 * 0.003 * 1200.0 * 0.02) * 100.0
        o2_carpan = max(0.0, (oksijen_yuzde - 14.2) / 6.8)
        blow_off_limit = 28.0 + (oksijen_yuzde - 18.0) * 2.2

        for u_akis in range(0, 46, 3):
            u_top = math.sqrt((u_akis ** 2) + (v_buoy ** 2))
            if oksijen_yuzde < 14.5 or u_top < 0.8:
                noktalar.append((float(u_akis), 0.0, "QUENCHING (Oksijen Açlığı Sönmesi)"))
            elif u_akis > blow_off_limit:
                noktalar.append((float(u_akis), 0.0, "BLOW-OFF (Üfleyerek Sönme)"))
            else:
                # 8-14 cm/s arasında maksimum yayılım hızı (mikroçekim ventilasyon tehlike piki)
                norm = u_top / 11.0
                hiz = 2.6 * o2_carpan * (norm * math.exp(1.0 - norm * 0.65))
                noktalar.append((float(u_akis), round(max(0.05, hiz), 2), "AKTİF YAYILIM"))
        return noktalar

    @staticmethod
    def kabin_telemetri_anomali_analizi(
        sicaklik_k: float,
        oksijen_yuzde: float,
        co_ppm: float,
        basinc_kpa: float,
        fan_hizi_cm_s: float,
        onceki_oksijen_yuzde: float = 20.9
    ) -> Dict[str, object]:
        """
        NASA ISS / Lunar Gateway / Orion yangın güvenlik kurallarına göre sensör telemetrisini
        değerlendirir ve kanıt-odaklı acil müdahale protokolü üretir.
        """
        bulgular: List[str] = []
        protokol_adimlari: List[str] = []
        kanitlar: List[str] = []
        tehlike_seviyesi = "NORMAL"

        # Kural 1: Oksijen Artışı Anomalisi (BASS / Saffire Kuralı)
        if oksijen_yuzde > onceki_oksijen_yuzde + 0.5 and sicaklik_k > 450:
            tehlike_seviyesi = "KRİTİK ALARM"
            bulgular.append(
                f"🚨 OKSİJEN ARTIŞ ANOMALİSİ (%{onceki_oksijen_yuzde:.1f} -> %{oksijen_yuzde:.1f}): "
                "Kapalı bir yanma modülünde yangın oksijeni tüketir; O2 seviyesinin yükselmesi yanmanın kendi "
                "kendine hızlandığını DEĞİL, kabin ventilasyon fanlarının açıldığını veya O2 besleme hattında "
                "sızıntı olduğunu kanıtlar!"
            )
            protokol_adimlari.append("1. DERHAL kabin ventilasyon fanlarını ve O2 besleme valfini kapatın (Ventilation Shutoff).")
            kanitlar.append("PSI-BASS-001")

        # Kural 2: Görünmez Soğuk Alev (Cool Flame - FLEX-2 Kuralı)
        if 520 <= sicaklik_k <= 760 and co_ppm >= 80:
            tehlike_seviyesi = "KRİTİK ALARM"
            bulgular.append(
                f"🟣 GÖRÜNMEZ SOĞUK ALEV (COOL FLAME) TESPİTİ ({sicaklik_k:.0f} K, CO: {co_ppm:.0f} ppm): "
                "Sıcaklık görünür sıcak alevin (1600+ K) altında olmasına rağmen yüksek CO üretimi mevcut. "
                "FLEX-2 deneylerine göre sıvı/polimer yakıt şu an gözle görülmeyen 'Soğuk Alev' (NTC) rejiminde "
                "okside olmakta ve her an patlayıcı yeniden tutuşmaya (re-ignition) geçebilir!"
            )
            protokol_adimlari.append("2. Görünür alev olmasa bile Termal IR kamerayla 600 K sıcak noktayı izole edin ve İnce Su Sisi uygulayın.")
            kanitlar.append("PSI-FLEX-002")

        # Kural 3: Düşük Oksijen (<%18) Eksik Yanma, Soot Kabuğu ve CO Zehirlenmesi (ACME Kuralı)
        if oksijen_yuzde < 18.2 and (sicaklik_k > 450 or co_ppm > 100):
            tehlike_seviyesi = "KRİTİK ALARM"
            bulgular.append(
                f"🟡 DÜŞÜK OKSİJEN EKSİK YANMA & KURUM (SOOT) RİSKİ (O2: %{oksijen_yuzde:.1f}, CO: {co_ppm:.0f} ppm): "
                "0g ortamında düşük oksijen alevi hemen söndürmez; küresel sarı/turuncu kurum (soot) kabuğu "
                "ve ölümcül karbonmonoksit (CO) birikimi oluşturarak HEPA filtreleri tıkar."
            )
            protokol_adimlari.append("3. Mürettebata derhal kapalı devre oksijen maskesi (PBA) taktırın ve CO yıkayıcıları (Scrubber) tam kapasiteye alın.")
            kanitlar.append("PSI-ACME-004")

        # Kural 4: Zorlanmış Akış (Fan Hızı) Alev Körükleme Etkisi
        if 2.0 <= fan_hizi_cm_s <= 25.0 and sicaklik_k > 420:
            if tehlike_seviyesi == "NORMAL":
                tehlike_seviyesi = "YÜKSEK RİSK"
            bulgular.append(
                f"💨 ZORLANMIŞ AKIŞ (FAN: {fan_hizi_cm_s:.1f} cm/s) ALEVİ BESLİYOR: "
                "Mikroçekimde doğal konveksiyon olmadığı için mevcut fan akışı aleve taze oksijen taşıyarak "
                "yayılım hızını tepe noktasına çıkarmaktadır."
            )
            protokol_adimlari.append("4. Fan hızını 0 cm/s'ye düşürerek alevi kendi yanma ürünleriyle (CO2) boğun.")
            kanitlar.append("PSI-BASS-001")

        # Kural 5: Söndürme Ajanı Seçimi (Halon Yasağı - ISS MIST Kuralı)
        if sicaklik_k > 420 or co_ppm > 50:
            protokol_adimlari.append(
                "5. SÖNDÜRME AJANI KURALI: Kesinlikle Halon 1301 KULLANMAYIN (ECLSS'de toksik HF/HBr üretir). "
                "Yalnızca İnce Su Sisi (Fine Water Mist <80 µm) veya CO2 taşınabilir söndürücü (PFE) kullanın."
            )
            kanitlar.append("NTRS-MIST-006")

        if not bulgular:
            bulgular.append("✅ Tüm kabin yanma ve atmosferik telemetri değerleri nominal ISS/Gateway güvenlik sınırları içerisindedir.")
            protokol_adimlari.append("• Rutin sensör izlemesine devam edin.")

        return {
            "tehlike_seviyesi": tehlike_seviyesi,
            "bulgular": bulgular,
            "protokol_adimlari": protokol_adimlari,
            "kanitlar": sorted(set(kanitlar)),
        }

    @staticmethod
    def kabin_duman_ve_sensor_dijital_ikizi_hesapla(
        yercekimi_g: float,
        hvac_akis_cm_s: float,
        yangin_konum_xy: Tuple[float, float] = (0.32, 0.58)
    ) -> Dict[str, object]:
        """
        Uzay aracı kabininde (0g ISS/Gateway, 0.16g Ay, 0.38g Mars, 1.0g Dünya) çıkan bir yangında
        duman/CO bulutunun hareketini ve 3 farklı sensör tipinin (Tavan Dedektörü, HVAC Dönüş Kanalı,
        Lokal IR/CO Sensörü) algılama sürelerini [NTRS-ORION-010] kanıtına göre hesaplar.
        """
        # Doğal konveksiyon yükselme hızı (cm/s)
        v_yukari_cm_s = math.sqrt(max(0.0, yercekimi_g) * 9.81 * 0.003 * 650.0 * 0.45) * 100.0
        # Moleküler/türbülanslı difüzyon hızı (0g'de fan kapalıyken çok yavaştır ~0.6 cm/s)
        v_difuzyon_cm_s = 0.65 + 0.08 * hvac_akis_cm_s

        # Kabin yüksekliği 220 cm, uzunluğu 450 cm varsayımı
        tavan_mesafe_cm = max(25.0, yangin_konum_xy[1] * 210.0)
        hvac_kanal_mesafe_cm = max(35.0, (1.0 - yangin_konum_xy[0]) * 420.0)

        # 1. Tavan Dedektörü Algılama Süresi (sn)
        etkin_dikey_hiz = v_yukari_cm_s + v_difuzyon_cm_s * 0.45
        t_tavan_sn = round(tavan_mesafe_cm / max(0.35, etkin_dikey_hiz), 1)

        # 2. HVAC Dönüş Kanalı Dedektörü Algılama Süresi (sn)
        etkin_yatay_hiz = hvac_akis_cm_s + v_difuzyon_cm_s * 0.35
        t_hvac_sn = round(hvac_kanal_mesafe_cm / max(0.35, etkin_yatay_hiz), 1)

        # 3. Çok Bantlı Mid-IR (3.4 µm) + Lokal CO Sensörü Algılama Süresi (sn)
        t_lokal_ir_sn = round(2.2 + (8.0 / max(2.0, hvac_akis_cm_s + v_yukari_cm_s + 2.0)), 1)

        if yercekimi_g < 0.05 and hvac_akis_cm_s < 1.5:
            teshis = (
                "🚨 KRİTİK KÖR NOKTA (0G + Fan Kapalı): Kaldırma kuvveti ve hava akışı olmadığı için duman "
                "kaynak etrafında küresel olarak asılı kalır! Tavan dedektörü dakikalarca yangını algılayamaz."
            )
        elif yercekimi_g < 0.05:
            teshis = (
                "🛰️ 0G HVAC AKIM TAŞINIMI: Duman tavana yükselmez; doğrudan yatay ventilasyon akım çizgilerini "
                "izleyerek HVAC dönüş kanalındaki dedektöre ulaşır."
            )
        elif yercekimi_g <= 0.25:
            teshis = (
                "🌙 AY (0.16G) ZAYIF PLUME: Zayıf kaldırma kuvveti ile yatay HVAC akışı birleşerek dumanı "
                "diyagonal (eğik) bir yörüngeyle hem tavana hem dönüş kanalına taşır."
            )
        else:
            teshis = (
                "🌍 GÜÇLÜ KONVEKTİF YÜKSELME: Sıcak duman sütunu hızla tavana çarparak tavan dedektörünü tetikler."
            )

        return {
            "v_yukari_cm_s": round(v_yukari_cm_s, 1),
            "hvac_akis_cm_s": round(hvac_akis_cm_s, 1),
            "t_tavan_sn": min(t_tavan_sn, 600.0),
            "t_hvac_sn": min(t_hvac_sn, 600.0),
            "t_lokal_ir_sn": t_lokal_ir_sn,
            "teshis": teshis,
        }

    @classmethod
    def monte_carlo_belirsizlik_analizi(
        cls,
        yakit_adi: str,
        yercekimi_g: float,
        oksijen_yuzde: float,
        basinc_kpa: float,
        d0_mm: float,
        akis_hizi_cm_s: float,
        iterasyon: int = 120
    ) -> Dict[str, float]:
        """
        Sensör ve kabin atmosferi dalgalanmalarını (±%0.8 O2, ±%8 akış hızı, ±%5 damlacık çapı)
        deterministik sözde-rassal (Halton/Golden-Ratio) örnekleme ile simüle ederek %90 güven aralığını hesaplar.
        """
        tb_listesi: List[float] = []
        co_listesi: List[float] = []
        cool_sayac = 0

        altin_oran = 0.61803398875
        for i in range(1, iterasyon + 1):
            # Deterministik düşük-diskrepanslı sapmalar (-1.0 .. +1.0)
            u1 = ((i * altin_oran) % 1.0) * 2.0 - 1.0
            u2 = ((i * altin_oran * 1.4142) % 1.0) * 2.0 - 1.0
            u3 = ((i * altin_oran * 1.7320) % 1.0) * 2.0 - 1.0

            o2_sim = max(12.0, min(38.0, oksijen_yuzde + u1 * 0.85))
            d0_sim = max(0.8, d0_mm * (1.0 + u2 * 0.06))
            akis_sim = max(0.0, akis_hizi_cm_s * (1.0 + u3 * 0.10))

            res = cls.damlacik_yanma_analizi(
                yakit_adi=yakit_adi,
                yercekimi_g=yercekimi_g,
                oksijen_yuzde=o2_sim,
                basinc_kpa=basinc_kpa,
                d0_mm=d0_sim,
                akis_hizi_cm_s=akis_sim,
            )
            tb_listesi.append(float(res["tb_toplam_sn"]))
            co_listesi.append(float(res["co_ppm"]))
            if res["cool_flame_olusur"]:
                cool_sayac += 1

        tb_listesi.sort()
        co_listesi.sort()
        n = len(tb_listesi)
        return {
            "tb_p05": round(tb_listesi[max(0, int(n * 0.05))], 2),
            "tb_medyan": round(tb_listesi[n // 2], 2),
            "tb_p95": round(tb_listesi[min(n - 1, int(n * 0.95))], 2),
            "co_medyan": round(co_listesi[n // 2], 0),
            "co_p95": round(co_listesi[min(n - 1, int(n * 0.95))], 0),
            "cool_flame_olasilik_yuzde": round((cool_sayac / n) * 100.0, 1),
        }
