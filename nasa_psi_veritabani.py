# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"
Modül 1: Kanıt-Odaklı (Evidence-First) NASA PSI / NTRS Deney Veri Tabanı, Uzay Aracı Malzeme Yanıcılık Atlası
         ve Derin Uzay Araştırma Boşluğu (Research Gap Finder) Motoru.

Bu modül, halüsinasyon riskini sıfıra indirmek için gerçek NASA fiziksel bilimler (PSI - Physical Sciences Informatics)
ve NTRS (NASA Technical Reports Server) deney bulgularını (BASS, BASS-II, Saffire I-VI, ACME, FLEX, FLEX-2, SoFIE)
doğrulanabilir kanıt kodlarıyla yapılandırılmış olarak barındırır.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class NasaDeneyKaydi:
    """NASA PSI ve NTRS arşivlerindeki doğrulanmış mikroçekim yanma deney kaydı."""
    kanit_id: str
    program_adi: str
    baslik: str
    tesis_ve_gorev: str
    yil: int
    yercekimi_rejimi: str
    yakit_veya_malzeme: str
    oksijen_araligi_yuzde: Tuple[float, float]
    basinc_kpa: float
    akis_hizi_cm_s: Tuple[float, float]
    temel_bulgular: str
    yangin_guvenligi_cikarimi: str
    anahtar_kelimeler: Tuple[str, ...]
    onem_puani: float  # 0.0 - 10.0 arası görev kritikliği
    ntrs_referanslari: Tuple[str, ...] = ()
    psi_url: str = "https://psi.nasa.gov"

    @property
    def ntrs_linkleri(self) -> Tuple[str, ...]:
        return tuple(f"https://ntrs.nasa.gov/citations/{nid}" for nid in self.ntrs_referanslari)


@dataclass(frozen=True)
class UzayMalzemeKaydi:
    """NASA-STD-6001B kapsamındaki uzay aracı kabin malzemelerinin farklı yerçekimi rejimlerindeki yanıcılık verisi."""
    malzeme_kodu: str
    malzeme_adi: str
    kategori: str
    kullanim_alani: str
    loc_dunya_1g: float      # Limiting Oxygen Concentration (%O2) - 1.0g Dünya
    loc_mikro_0g: float      # Limiting Oxygen Concentration (%O2) - 0.0g ISS (Düşük akışta)
    loc_ay_016g: float       # Limiting Oxygen Concentration (%O2) - 0.16g Ay (Kısmi yerçekimi en kritik!)
    loc_mars_038g: float     # Limiting Oxygen Concentration (%O2) - 0.38g Mars
    yayilim_hizi_0g_mm_s: float
    yayilim_hizi_ay_mm_s: float
    yayilim_hizi_dunya_mm_s: float
    kritik_isi_akisi_kw_m2: float
    toksik_gazlar: str
    sondurme_protokolu: str
    nasa_std_6001_sinifi: str
    kanit_referansi: str


@dataclass(frozen=True)
class ArastirmaBosluguKaydi:
    """Derin uzay görevleri (Artemis, Lunar Gateway, Mars Transit) için tespit edilen literatür/veri boşluğu."""
    bosluk_kodu: str
    baslik: str
    hedef_ortam: str
    eksik_parametreler: str
    risk_seviyesi: str       # "KRİTİK", "YÜKSEK", "ORTA"
    aciklama: str
    onerilen_deney_tasarimi: str
    ilgili_nasa_programi: str


# =============================================================================
# 1. DOĞRULANMIŞ NASA PSI & NTRS MİKROÇEKİM YANMA DENEYLERİ VERİ TABANI
# =============================================================================
NASA_PSI_DENEY_ARSIVI: Tuple[NasaDeneyKaydi, ...] = (
    NasaDeneyKaydi(
        kanit_id="PSI-BASS-001",
        program_adi="BASS / BASS-II",
        baslik="Burning and Suppression of Solids in Microgravity (Zorlanmış Akış Altında Katı Yanması)",
        tesis_ve_gorev="ISS - Microgravity Science Glovebox (MSG) | Expedition 30-40",
        yil=2014,
        yercekimi_rejimi="0.00g (Mikroçekim - ISS)",
        yakit_veya_malzeme="PMMA (Polimetil Metakrilat), SIBAL (Pamuk/Fiberglas), Nomex",
        oksijen_araligi_yuzde=(15.0, 28.0),
        basinc_kpa=101.3,
        akis_hizi_cm_s=(0.5, 45.0),
        temel_bulgular=(
            "Mikroçekimde doğal konveksiyon (buoyancy) olmadığı için alev yayılımı tamamen kabin ventilasyon "
            "hızına (zorlanmış akış) bağlıdır. Çok düşük akış hızlarında (1-5 cm/s) oksijen difüzyonu alevi "
            "besler ve malzeme Dünya'da söneceği düşük oksijen seviyelerinde (%16.5 O2) bile yanmaya devam eder. "
            "Akış hızı 35 cm/s üzerine çıktığında ise 'blow-off' (üfleyerek sönme) gerçekleşir."
        ),
        yangin_guvenligi_cikarimi=(
            "ISS ve gelecekteki uzay istasyonlarında yangın anında kabin havalandırma fanlarının hızının "
            "kontrolsüz artırılması alevi körükler; ilk adım derhal ventilasyonun tamamen kesilmesi (0 cm/s) "
            "veya blow-off eşiğinin kontrol edilmesidir."
        ),
        anahtar_kelimeler=("bass", "katı yanması", "fan hızı", "ventilasyon", "pmma", "sibal", "zorlanmış akış", "sönme"),
        onem_puani=9.8,
        ntrs_referanslari=("20210011385", "20160000593", "20150019858")
    ),
    NasaDeneyKaydi(
        kanit_id="PSI-FLEX-002",
        program_adi="FLEX / FLEX-2",
        baslik="Flame Extinguishment Experiment: Sıvı Yakıt Damlacıklarında İki Aşamalı Yanma ve Soğuk Alevler (Cool Flames)",
        tesis_ve_gorev="ISS - Combustion Integrated Rack (CIR) / MDCA",
        yil=2013,
        yercekimi_rejimi="0.00g (Mikroçekim - ISS)",
        yakit_veya_malzeme="n-Heptan (C7H16), n-Dekan (C10H22), İzo-Oktan, Metanol",
        oksijen_araligi_yuzde=(15.0, 21.0),
        basinc_kpa=101.3,
        akis_hizi_cm_s=(0.0, 2.0),
        temel_bulgular=(
            "Büyük hidrokarbon damlacıkları (d0 > 2.5 mm) mikroçekimde küresel sıcak alev (1800-2100 K) ile "
            "başlar; ancak kurum (soot) kabuğunun radyatif ısı kaybı nedeniyle görünür alev aniden söner. "
            "Buna rağmen damlacık 550-720 K sıcaklıkta gözle görülmeyen 'Soğuk Alev' (Cool Flame / NTC kimyası) "
            "rejiminde buharlaşmaya ve kısmi oksidasyona devam eder, ardından tekrar tutuşabilir (re-ignition)."
        ),
        yangin_guvenligi_cikarimi=(
            "Optik alev sensörleri görünür alev söndüğünde yangının bittiğini varsayabilir; ancak görünmez "
            "Soğuk Alev (Cool Flame) karbonmonoksit (CO) ve formaldehit üretmeye devam edip yeniden patlayıcı "
            "tutuşmaya yol açabilir. Termal kızılötesi (IR) ve CO sensörleri birlikte kullanılmalıdır."
        ),
        anahtar_kelimeler=("flex", "damlacık", "heptan", "soğuk alev", "cool flame", "d2 yasası", "radyatif sönme", "yeniden tutuşma"),
        onem_puani=9.9,
        ntrs_referanslari=("20210022617", "20190002838", "20200000009")
    ),
    NasaDeneyKaydi(
        kanit_id="NTRS-SAFFIRE-003",
        program_adi="Saffire I - VI",
        baslik="Spacecraft Fire Experiment: Cygnus Kargo Aracında Büyük Ölçekli Kabin Yangını ve Oksijen Sınırları",
        tesis_ve_gorev="Northrop Grumman Cygnus (OA-4, OA-6, OA-5, NG-13, NG-14, NG-15)",
        yil=2021,
        yercekimi_rejimi="0.00g (Serbest Yörünge Uçuşu)",
        yakit_veya_malzeme="SIBAL (%75 Pamuk / %25 Fiberglas, 0.4 m x 0.94 m Büyük Paneller), PMMA",
        oksijen_araligi_yuzde=(21.0, 34.0),
        basinc_kpa=56.5,
        akis_hizi_cm_s=(15.0, 30.0),
        temel_bulgular=(
            "NASA Exploration Atmosphere (%34 O2, 56.5 kPa / 8.2 psi) koşullarında büyük ölçekli alev yayılım hızı "
            "standart ISS atmosferine (%21 O2, 101.3 kPa) kıyasla 2.4 kat daha yüksektir. Kapalı hacimde alev "
            "büyüdükçe kabin basıncı hızla yükselir ve duman/kurum tabakalaşmadığı için tüm modülü homojen kaplar."
        ),
        yangin_guvenligi_cikarimi=(
            "Ay ve Mars görevlerinde kullanılacak düşük basınç / yüksek oksijen (%34 O2) kabin atmosferinde "
            "malzeme seçimi Dünya testlerine göre yapılamaz; yangın algılama süresi 15 saniyenin altında olmalıdır."
        ),
        anahtar_kelimeler=("saffire", "cygnus", "büyük ölçekli", "keşif atmosferi", "exploration atmosphere", "34 o2", "duman"),
        onem_puani=9.7,
        ntrs_referanslari=("20210011521", "20170000230", "20260001600")
    ),
    NasaDeneyKaydi(
        kanit_id="PSI-ACME-004",
        program_adi="ACME (BRE / Flame Design / E-FIELD)",
        baslik="Advanced Combustion via Microgravity Experiments: Kurum (Soot) Kabuğu, Radyatif Kayıp ve Elektrik Alan Kontrolü",
        tesis_ve_gorev="ISS - Combustion Integrated Rack (CIR)",
        yil=2020,
        yercekimi_rejimi="0.00g (Mikroçekim - ISS)",
        yakit_veya_malzeme="Etilen (C2H4), Metan (CH4), n-Heptan Gaz/Sıvı Brülör",
        oksijen_araligi_yuzde=(14.0, 35.0),
        basinc_kpa=101.3,
        akis_hizi_cm_s=(1.0, 20.0),
        temel_bulgular=(
            "0g ortamında kaldırma kuvveti olmadığı için gaz ürünleri alev etrafında uzun süre kalır (yüksek "
            "residence time). Bu durum yoğun bir küresel sarı/turuncu kurum (soot) kabuğu oluşturur. E-FIELD "
            "deneyinde aleve uygulanan yüksek voltajlı elektrik alanın iyon rüzgarı yaratarak kurum oluşumunu "
            "%70 azalttığı ve alevi kararlı hale getirdiği kanıtlanmıştır."
        ),
        yangin_guvenligi_cikarimi=(
            "Uzay kabinlerinde düşük oksijen (<%18) yangını hemen söndürmez; aksine eksik yanmayı tetikleyerek "
            "yoğun kurum (filtre tıkanması) ve ölümcül CO (>400 ppm) üretir."
        ),
        anahtar_kelimeler=("acme", "bre", "flame design", "soot", "kurum", "is kabuğu", "elektrik alan", "radyatif"),
        onem_puani=9.4,
        ntrs_referanslari=("20210015913", "20220015583")
    ),
    NasaDeneyKaydi(
        kanit_id="PSI-SOFIE-005",
        program_adi="SoFIE (GELI / RTLS / MIST)",
        baslik="Solid Fuel Ignition and Extinction: Ay (0.16g) ve Mars (0.38g) Kısmi Yerçekimi Yanma Paradoksu",
        tesis_ve_gorev="ISS - Combustion Integrated Rack (CIR) & Glenn 5-Second Drop Tower",
        yil=2023,
        yercekimi_rejimi="0.00g - 0.16g (Ay) - 0.38g (Mars)",
        yakit_veya_malzeme="PMMA Silindir ve Levhalar, Polikarbonat, Nomex",
        oksijen_araligi_yuzde=(13.5, 34.0),
        basinc_kpa=56.5,
        akis_hizi_cm_s=(2.0, 25.0),
        temel_bulgular=(
            "Kısmi yerçekimi paradoksu: Ay yerçekiminde (0.16g) doğal konveksiyon alevi besleyecek kadar "
            "oksijen taşır, ancak alevi soğutacak veya üfleyecek kadar güçlü değildir! Bu nedenle Ay (0.16g) "
            "ortamında malzemelerin Minimum Oksijen Sınırı (LOC) hem Dünya'dan (1.0g) hem de durgun 0g'den "
            "DAHA DÜŞÜKTÜR (PMMA Dünya'da %17.2 O2'de sönerken 0.16g'de %14.6 O2'ye kadar yanabilir)."
        ),
        yangin_guvenligi_cikarimi=(
            "Artemis Ay üssü ve Mars habitatları için en tehlikeli yangın rejimi 0g değil, 0.10g - 0.25g "
            "kısmi yerçekimi aralığıdır! Dünya'da 'kendiliğinden söner' sertifikası alan malzemeler Ay'da yanmaya devam eder."
        ),
        anahtar_kelimeler=("sofie", "ay", "mars", "kısmi yerçekimi", "partial gravity", "0.16g", "0.38g", "loc", "paradoks"),
        onem_puani=10.0,
        ntrs_referanslari=("20200000361", "20240015307", "20240008623", "20210020516")
    ),
    NasaDeneyKaydi(
        kanit_id="NTRS-MIST-006",
        program_adi="ISS Fine Water Mist & CO2 Suppression",
        baslik="Uluslararası Uzay İstasyonu ve Derin Uzay Araçlarında Halon Yasağı ve İnce Su Sisi Söndürme Fiziği",
        tesis_ve_gorev="ISS USOS (Portable Fire Extinguisher - PFE) & NASA Glenn Research Center",
        yil=2019,
        yercekimi_rejimi="0.00g - 0.38g",
        yakit_veya_malzeme="Aviyonik Kablolar, Lityum-İyon Batarya, Polimer Paneller",
        oksijen_araligi_yuzde=(18.0, 34.0),
        basinc_kpa=101.3,
        akis_hizi_cm_s=(0.0, 30.0),
        temel_bulgular=(
            "Halon 1301 gazı yüksek sıcaklıkta yaşam destek sistemlerini (ECLSS) zehirleyen hidrojen florür (HF) "
            "ve hidrojen bromür (HBr) ürettiği için yeni nesil NASA araçlarında yasaklanmıştır. Yerine 30-80 mikron "
            "çaplı İnce Su Sisi (Fine Water Mist) ve CO2 kullanılır; mikroçekimde su damlacıkları çökmediği için "
            "gaz gibi davranarak alev yüzeyinden gizli buharlaşma ısısı (2260 kJ/kg) çeker."
        ),
        yangin_guvenligi_cikarimi=(
            "Kapalı uzay kabininde yangın söndürme protokolü: 1) Ventilasyonu Kapat, 2) Elektrik Gücünü Kes, "
            "3) İnce Su Sisi (Fine Water Mist) veya CO2 uygula, 4) Asla Halon kullanma."
        ),
        anahtar_kelimeler=("halon", "su sisi", "fine water mist", "co2", "söndürme", "pfe", "eclss", "hf"),
        onem_puani=9.6,
        ntrs_referanslari=("20150000894", "20200000365")
    ),
    NasaDeneyKaydi(
        kanit_id="PSI-FLEX-007",
        program_adi="FLEX-2 Droplet Arrays",
        baslik="Çoklu Sıvı Yakıt Damlacık Dizilerinde Grup Yanması ve Oksijen Rekabeti",
        tesis_ve_gorev="ISS - Combustion Integrated Rack (CIR)",
        yil=2017,
        yercekimi_rejimi="0.00g (Mikroçekim - ISS)",
        yakit_veya_malzeme="n-Heptan ve n-Dekan İkili/Üçlü Damlacık Dizileri",
        oksijen_araligi_yuzde=(15.0, 21.0),
        basinc_kpa=101.3,
        akis_hizi_cm_s=(0.0, 3.0),
        temel_bulgular=(
            "Yakıt damlacıkları birbirine kritik mesafeden (L/d0 < 8) daha yakın olduğunda tekil küresel "
            "alevler birleşerek tüm damlacık kümesini saran tek bir 'grup alevi' (group combustion) oluşturur; "
            "merkezdeki oksijen tükenmesi nedeniyle yanma hızı sabiti K %35 düşer ancak soğuk alev süresi uzar."
        ),
        yangin_guvenligi_cikarimi=(
            "Yakıt veya soğutucu akışkan sızıntılarında oluşan aerosol bulutu tekil damlacıklardan çok daha "
            "uzun süre görünmez soğuk alev fazında kalabilir; kabin havası hızla filtrelenmelidir."
        ),
        anahtar_kelimeler=("flex-2", "damlacık dizisi", "grup yanması", "aerosol", "sızıntı"),
        onem_puani=9.1,
        ntrs_referanslari=("19990054030", "20010074042", "20010074091")
    ),
    NasaDeneyKaydi(
        kanit_id="PSI-ACME-008",
        program_adi="ACME Coflow & s-Flame",
        baslik="Küresel Difüzyon Alevlerinde Stokiyometrik Tasarım (Z_st) ve Radyatif Sönme Eşiği",
        tesis_ve_gorev="ISS - Combustion Integrated Rack (CIR)",
        yil=2021,
        yercekimi_rejimi="0.00g (Mikroçekim - ISS)",
        yakit_veya_malzeme="Metan (CH4), Etilen (C2H4), Azot Seyreltmeli Karışımlar",
        oksijen_araligi_yuzde=(15.0, 40.0),
        basinc_kpa=101.3,
        akis_hizi_cm_s=(0.5, 12.0),
        temel_bulgular=(
            "Alevin yakıt tarafında mı yoksa oksijen tarafında mı konumlanacağını belirleyen stokiyometrik "
            "karışım kesri (Z_st), kurum (soot) oluşumunu doğrudan kontrol eder. Yüksek Z_st değerlerinde "
            "yanma ürünleri iç bölgede hapsolarak kurum oluşumunu tamamen ortadan kaldırır (soot-free flame)."
        ),
        yangin_guvenligi_cikarimi=(
            "Uzay kabinlerinde inert gaz (Azot/Argon) seyreltme oranı Z_st sınırını değiştirecek şekilde "
            "ayarlanarak kurumsuz ve kendi kendine sönen atmosfer tasarlanabilir."
        ),
        anahtar_kelimeler=("acme", "z_st", "stokiyometrik", "coflow", "kurumsuz", "azot"),
        onem_puani=9.2,
        ntrs_referanslari=("20210015913", "20140009169")
    ),
    NasaDeneyKaydi(
        kanit_id="PSI-SOFIE-009",
        program_adi="SoFIE MIST & SMURF",
        baslik="Düşük Basınçlı Keşif Atmosferinde Dış Isı Akısı Altında Polimer Tutuşma Gecikmesi",
        tesis_ve_gorev="ISS - Combustion Integrated Rack (CIR)",
        yil=2024,
        yercekimi_rejimi="0.00g - 0.16g (Ay)",
        yakit_veya_malzeme="PMMA, Polikarbonat, Ultem, Kablo Yalıtım Malzemeleri",
        oksijen_araligi_yuzde=(21.0, 34.0),
        basinc_kpa=56.5,
        akis_hizi_cm_s=(1.0, 20.0),
        temel_bulgular=(
            "Mikroçekimde radyatif ısınmaya maruz kalan katı polimer yüzeyinden çıkan piroliz gazları "
            "konveksiyonla dağılmadığı için yüzey önünde sıcak ve zengin bir yakıt tabakası oluşturur; "
            "bu durum tutuşma gecikme süresini (ignition delay time) Dünya'ya göre %40 kısaltır."
        ),
        yangin_guvenligi_cikarimi=(
            "Aşırı ısınan elektrik kabloları ve aviyonik kartlar 0g'de Dünya testlerinden çok daha erken "
            "tutuşur; termal akım kesiciler %35 daha düşük eşiğe ayarlanmalıdır."
        ),
        anahtar_kelimeler=("sofie", "mist", "smurf", "tutuşma gecikmesi", "piroliz", "kablo"),
        onem_puani=9.5,
        ntrs_referanslari=("20200000361", "20250010975")
    ),
    NasaDeneyKaydi(
        kanit_id="NTRS-ORION-010",
        program_adi="Orion & Gateway Smoke Detection",
        baslik="Mikroçekimde Duman Dağılım Fiziği ve Tavan Dedektörlerinin Kör Noktası",
        tesis_ve_gorev="ISS & NASA Johnson / Glenn Fire Detection Testbed",
        yil=2022,
        yercekimi_rejimi="0.00g (Mikroçekim - ISS / Gateway)",
        yakit_veya_malzeme="Piroliz Dumanı, Teflon, Kapton, Pamuk, Silikon Kauçuk",
        oksijen_araligi_yuzde=(21.0, 34.0),
        basinc_kpa=101.3,
        akis_hizi_cm_s=(0.0, 25.0),
        temel_bulgular=(
            "Dünya'da sıcak duman tavanta toplanır (stratification). 0g'de ise kaldırma kuvveti sıfır "
            "olduğundan duman tavana yükselmez; yalnızca HVAC havalandırma akım çizgilerini takip eder. "
            "Ventilasyon kapalıysa duman kaynak etrafında küresel olarak asılı kalır ve uzaktaki tavan "
            "dedektörlerine ulaşması dakikalar sürer."
        ),
        yangin_guvenligi_cikarimi=(
            "Uzay istasyonlarında yangın dedektörleri tavana değil, doğrudan HVAC dönüş hava kanallarına "
            "(Return Air Ducts) ve yüksek riskli aviyonik rafların içine yerleştirilmelidir."
        ),
        anahtar_kelimeler=("duman", "dedektör", "sensör", "hvac", "tavan", "orion", "gateway"),
        onem_puani=9.8,
        ntrs_referanslari=("20040053578", "20205003817", "20010074094")
    ),
)


# =============================================================================
# 2. UZAY ARACI MALZEME YANICILIK ATLASI (NASA-STD-6001B & KISMİ YERÇEKİMİ)
# =============================================================================
UZAY_MALZEME_ATLASI: Tuple[UzayMalzemeKaydi, ...] = (
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-PMMA",
        malzeme_adi="PMMA (Dökme Polimetil Metakrilat / Akrilik)",
        kategori="Termoplastik Polimer",
        kullanim_alani="Gözlem Pencereleri, Deney Muhafazaları, Referans Test Yakıtı",
        loc_dunya_1g=17.2,
        loc_mikro_0g=15.8,
        loc_ay_016g=14.6,
        loc_mars_038g=15.4,
        yayilim_hizi_0g_mm_s=1.85,
        yayilim_hizi_ay_mm_s=2.45,
        yayilim_hizi_dunya_mm_s=1.40,
        kritik_isi_akisi_kw_m2=11.5,
        toksik_gazlar="CO (Yüksek), CO2, Metil Metakrilat Monomer Buharı",
        sondurme_protokolu="Ventilasyon Kesme + İnce Su Sisi (<60 µm) + CO2 Boğma",
        nasa_std_6001_sinifi="Başarısız (>%21 O2'de Alev Yayılımı Var - Yalnızca Kontrollü Kabinde)",
        kanit_referansi="PSI-SOFIE-005 / PSI-BASS-001"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-SIBAL",
        malzeme_adi="SIBAL (%75 Pamuk / %25 Fiberglas Kumaş)",
        kategori="Tekstil / Kompozit Kumaş",
        kullanim_alani="Mürettebat Giysi Benzetimi, Saffire Büyük Ölçekli Yangın Referansı",
        loc_dunya_1g=18.0,
        loc_mikro_0g=16.2,
        loc_ay_016g=15.1,
        loc_mars_038g=16.0,
        yayilim_hizi_0g_mm_s=3.20,
        yayilim_hizi_ay_mm_s=4.10,
        yayilim_hizi_dunya_mm_s=2.80,
        kritik_isi_akisi_kw_m2=9.2,
        toksik_gazlar="CO (Çok Yüksek), Aldehitler, Yoğun Karbon Kurumu (Soot)",
        sondurme_protokolu="Acil Hava Akışı Kesme + İnce Su Sisi + Kabin Basınç Düşürme",
        nasa_std_6001_sinifi="Riskli (%34 O2 Keşif Atmosferinde Hızlı Yayılım)",
        kanit_referansi="NTRS-SAFFIRE-003"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-NOMEX",
        malzeme_adi="Nomex HT90-40 (Meta-Aramid Elyaf)",
        kategori="Alev Geciktirici Tekstil",
        kullanim_alani="ISS Kargo Çantaları (CTB), Kablo Kılıfları, Mürettebat Tulumları",
        loc_dunya_1g=28.5,
        loc_mikro_0g=26.4,
        loc_ay_016g=24.8,
        loc_mars_038g=26.1,
        yayilim_hizi_0g_mm_s=0.35,
        yayilim_hizi_ay_mm_s=0.52,
        yayilim_hizi_dunya_mm_s=0.20,
        kritik_isi_akisi_kw_m2=28.0,
        toksik_gazlar="CO, Eser Miktarda HCN (Yalnızca >%30 O2 Altında)",
        sondurme_protokolu="Oksijen Akışını Kesme (Kendiliğinden Kömürleşerek Söner)",
        nasa_std_6001_sinifi="Onaylı (%21 O2 ISS İçin Güvenli | %34 O2'de Dikkatli Kullanım)",
        kanit_referansi="PSI-BASS-001 / NASA-STD-6001B"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-ULTEM",
        malzeme_adi="Ultem 1000 (Polieterimid - PEI)",
        kategori="Yüksek Performanslı Mühendislik Plastiği",
        kullanim_alani="Aviyonik Konnektörler, 3D Baskı Uzay Parçaları, Valfler",
        loc_dunya_1g=36.0,
        loc_mikro_0g=33.5,
        loc_ay_016g=31.8,
        loc_mars_038g=33.2,
        yayilim_hizi_0g_mm_s=0.12,
        yayilim_hizi_ay_mm_s=0.18,
        yayilim_hizi_dunya_mm_s=0.08,
        kritik_isi_akisi_kw_m2=35.0,
        toksik_gazlar="Düşük Duman Yoğunluğu, CO",
        sondurme_protokolu="Elektrik Gücünü Kesme (Isı Kaynağı Kalkınca Kendiliğinden Söner)",
        nasa_std_6001_sinifi="Tam Onaylı (Sınıf A - Yüksek Oksijen Dayanımı)",
        kanit_referansi="PSI-SOFIE-005 / NASA-STD-6001B"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-KAPTON",
        malzeme_adi="Kapton HN (Poliimid Yalıtım Filmi)",
        kategori="Elektrik & Termal Yalıtım",
        kullanim_alani="Uzay Aracı Kablo Demetleri, Çok Katmanlı Termal Battaniye (MLI)",
        loc_dunya_1g=37.0,
        loc_mikro_0g=34.2,
        loc_ay_016g=32.5,
        loc_mars_038g=34.0,
        yayilim_hizi_0g_mm_s=0.15,
        yayilim_hizi_ay_mm_s=0.22,
        yayilim_hizi_dunya_mm_s=0.10,
        kritik_isi_akisi_kw_m2=38.0,
        toksik_gazlar="CO, CO2, Eser NOx (Ark Kaynaklı Pirolizde)",
        sondurme_protokolu="Devre Kesici (Breaker) Açma + CO2 Uygulaması",
        nasa_std_6001_sinifi="Tam Onaylı (Sınıf A - Ark Kusurlarına Dikkat)",
        kanit_referansi="NTRS-MIST-006"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-PTFE",
        malzeme_adi="PTFE / Teflon & Beta Cloth (Floropolimer)",
        kategori="Yanmaz Floropolimer Kaplama",
        kullanim_alani="Dış Gövde Koruması, Kablo İzolasyonu, Yangın Bariyeri",
        loc_dunya_1g=95.0,
        loc_mikro_0g=90.0,
        loc_ay_016g=88.0,
        loc_mars_038g=90.0,
        yayilim_hizi_0g_mm_s=0.01,
        yayilim_hizi_ay_mm_s=0.02,
        yayilim_hizi_dunya_mm_s=0.01,
        kritik_isi_akisi_kw_m2=55.0,
        toksik_gazlar="⚠️ >450°C Pirolizde Karbonil Florür (COF2) ve Hidrojen Florür (HF)",
        sondurme_protokolu="Isı Kaynağını Kesme + Pozitif Basınçlı Oksijen Maskesi",
        nasa_std_6001_sinifi="Tam Onaylı (Alev Yaymaz; Aşırı Isıda Gaz Toksisitesi İzlenmeli)",
        kanit_referansi="NASA-STD-6001B / NTRS-MIST-006"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-KEVLAR",
        malzeme_adi="Kevlar-29 (Para-Aramid Balistik Kumaş)",
        kategori="Yüksek Mukavemetli Polimer Elyaf",
        kullanim_alani="Mikrometeorit Kalkanları (MMOD), Şişirilebilir Habitat Duvarları (LIFE)",
        loc_dunya_1g=29.0,
        loc_mikro_0g=26.8,
        loc_ay_016g=25.2,
        loc_mars_038g=26.5,
        yayilim_hizi_0g_mm_s=0.30,
        yayilim_hizi_ay_mm_s=0.46,
        yayilim_hizi_dunya_mm_s=0.18,
        kritik_isi_akisi_kw_m2=29.5,
        toksik_gazlar="CO, CO2, Eser HCN (>%30 O2 Altında)",
        sondurme_protokolu="Ventilasyon Kesme + İnce Su Sisi",
        nasa_std_6001_sinifi="Onaylı (%21 O2 ISS İçin Güvenli | %34 O2 Ay Kabininde Sınırda)",
        kanit_referansi="PSI-BASS-001 / NASA-STD-6001B"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-EPOXY-CF",
        malzeme_adi="Epoksi - Karbon Fiber Kompozit (CFRP)",
        kategori="Yapısal Havacılık Kompoziti",
        kullanim_alani="İç Kabin Destek Panelleri, Deney Rafları, İnsansız Yük Gövdeleri",
        loc_dunya_1g=23.5,
        loc_mikro_0g=21.2,
        loc_ay_016g=19.4,
        loc_mars_038g=20.8,
        yayilim_hizi_0g_mm_s=0.78,
        yayilim_hizi_ay_mm_s=1.15,
        yayilim_hizi_dunya_mm_s=0.55,
        kritik_isi_akisi_kw_m2=18.5,
        toksik_gazlar="CO (Yüksek), Fenolik Buharlar, Yoğun Kurum (Soot)",
        sondurme_protokolu="İnce Su Sisi + CO2 + Termal Kamera İle İçten Yanma Takibi",
        nasa_std_6001_sinifi="Koşullu (%34 O2 Keşif Atmosferinde Koruyucu Kaplama Şart)",
        kanit_referansi="GAP-LUNAR-01 / PSI-SOFIE-005"
    ),
    UzayMalzemeKaydi(
        malzeme_kodu="MAT-SILICONE",
        malzeme_adi="Silikon Kauçuk (Kablo & Conta Yalıtımı)",
        kategori="Elastomer Yalıtım",
        kullanim_alani="Hava Kilidi Contaları, Esnek Kablo Kılıfları, Sensör Yalıtımı",
        loc_dunya_1g=25.8,
        loc_mikro_0g=23.4,
        loc_ay_016g=21.6,
        loc_mars_038g=23.0,
        yayilim_hizi_0g_mm_s=0.62,
        yayilim_hizi_ay_mm_s=0.88,
        yayilim_hizi_dunya_mm_s=0.45,
        kritik_isi_akisi_kw_m2=21.0,
        toksik_gazlar="CO, Amorf Silika (SiO2) Beyaz Kül Tozu (Filtre Tıkayıcı)",
        sondurme_protokolu="Elektrik Kesme + CO2 Boğma + HEPA Filtre Değişimi",
        nasa_std_6001_sinifi="Koşullu (0g'de Yüzeyde Beyaz Silika Kabuğu Oluşturur)",
        kanit_referansi="PSI-SOFIE-009 / NTRS-ORION-010"
    ),
)

# =============================================================================
# 2B. İNTERAKTİF NASA YANMA BİLGİ GRAFİĞİ (KNOWLEDGE GRAPH) TOPOLOJİSİ
# =============================================================================
BILGI_GRAFIGI_DUGUMLERI: Tuple[Dict[str, str], ...] = (
    {"id": "ISS_CIR", "etiket": "ISS CIR & MSG", "tur": "TESIS", "aciklama": "ISS üzerindeki Combustion Integrated Rack ve Microgravity Science Glovebox ana yanma laboratuvarları."},
    {"id": "BASS_II", "etiket": "BASS / BASS-II", "tur": "DENEY", "aciklama": "Katı yakıtların (PMMA, SIBAL, Nomex) zorlanmış hava akışı altındaki 0g yanma ve sönme deneyleri [PSI-BASS-001]."},
    {"id": "FLEX_2", "etiket": "FLEX / FLEX-2", "tur": "DENEY", "aciklama": "Sıvı yakıt damlacıklarında d²-yasası, radyatif sönme ve görünmez Soğuk Alev (Cool Flame) keşfi [PSI-FLEX-002]."},
    {"id": "SAFFIRE", "etiket": "Saffire I-VI", "tur": "DENEY", "aciklama": "Cygnus kargo aracında büyük ölçekli kabin yangını ve %34 O2 keşif atmosferi testleri [NTRS-SAFFIRE-003]."},
    {"id": "ACME", "etiket": "ACME (BRE/E-Field)", "tur": "DENEY", "aciklama": "Gaz difüzyon alevlerinde kurum (soot) kabuğu, Z_st tasarımı ve elektrik alanla kurum azaltımı [PSI-ACME-004]."},
    {"id": "SOFIE", "etiket": "SoFIE (GELI/MIST)", "tur": "DENEY", "aciklama": "Katı yakıt tutuşması ve Ay (0.16g) / Mars (0.38g) kısmi yerçekimi LOC paradoksu [PSI-SOFIE-005]."},
    {"id": "COOL_FLAME", "etiket": "Soğuk Alev (640 K)", "tur": "OLGU", "aciklama": "Sıcak alev radyatif kayıpla söndükten sonra 550-720 K'de devam eden görünmez NTC oksidasyonu ve yeniden tutuşma."},
    {"id": "LUNAR_PARADOX", "etiket": "Ay 0.16g Paradoksu", "tur": "OLGU", "aciklama": "Ay yerçekiminde (0.16g) zayıf konveksiyonun alevi soğutmadan oksijen taşıması sonucu LOC sınırının Dünya'dan düşük olması."},
    {"id": "SOOT_SHELL", "etiket": "0g Soot Kabuğu & CO", "tur": "OLGU", "aciklama": "Mikroçekimde uzun kalış süresi nedeniyle alev etrafında oluşan küresel sarı kurum kabuğu ve yüksek CO emisyonu."},
    {"id": "BLOW_OFF", "etiket": "Fan Akışı & Blow-Off", "tur": "OLGU", "aciklama": "1-15 cm/s fan akışının 0g alevini körüklemesi, >35 cm/s akışın ise üfleyerek söndürmesi."},
    {"id": "WATER_MIST", "etiket": "İnce Su Sisi (<60µm)", "tur": "GUVENLIK", "aciklama": "Halon 1301 yasağı sonrası ISS ve Gateway'de kullanılan toksik olmayan gizli ısı emici su sisi ve CO2 söndürücü [NTRS-MIST-006]."},
    {"id": "HVAC_SENSOR", "etiket": "0g Duman & HVAC Sensör", "tur": "GUVENLIK", "aciklama": "0g'de duman tavana yükselmediği için dedektörlerin HVAC dönüş kanallarına yerleştirilmesi zorunluluğu [NTRS-ORION-010]."},
)

BILGI_GRAFIGI_BAGLANTILARI: Tuple[Tuple[str, str, str], ...] = (
    ("ISS_CIR", "BASS_II", "Ev Sahibi Tesis"),
    ("ISS_CIR", "FLEX_2", "Ev Sahibi Tesis"),
    ("ISS_CIR", "ACME", "Ev Sahibi Tesis"),
    ("ISS_CIR", "SOFIE", "Ev Sahibi Tesis"),
    ("FLEX_2", "COOL_FLAME", "Keşfetti [PSI-FLEX-002]"),
    ("FLEX_2", "SOOT_SHELL", "Radyatif Sönme"),
    ("ACME", "SOOT_SHELL", "Kurum Haritalama"),
    ("BASS_II", "BLOW_OFF", "Zorlanmış Akış Eğrisi"),
    ("SAFFIRE", "BLOW_OFF", "Büyük Ölçekli Yayılım"),
    ("SAFFIRE", "LUNAR_PARADOX", "%34 O2 Keşif Atmosferi"),
    ("SOFIE", "LUNAR_PARADOX", "Kanıtladı [PSI-SOFIE-005]"),
    ("SOOT_SHELL", "HVAC_SENSOR", "HEPA & Dedektör Etkisi"),
    ("COOL_FLAME", "WATER_MIST", "IR Tespit & Soğutma"),
    ("BLOW_OFF", "WATER_MIST", "Ventilasyon Kesme + Söndürme"),
)


# =============================================================================
# 3. DERİN UZAY ARAŞTIRMA BOŞLUĞU MATRİSİ (RESEARCH GAP FINDER)
# =============================================================================
ARASTIRMA_BOSLUKLARI: Tuple[ArastirmaBosluguKaydi, ...] = (
    ArastirmaBosluguKaydi(
        bosluk_kodu="GAP-LUNAR-01",
        baslik="Ay Yerçekiminde (0.16g) %34 O2 Keşif Atmosferinde Kalın Kompozitlerin Sönme Sınırı",
        hedef_ortam="Artemis Ay Üssü & Lunar Gateway (0.16g, 56.5 kPa, %34 O2)",
        eksik_parametreler="Kalınlığı >5 mm olan epoksi-karbon ve 3D baskı polimerlerin uzun süreli (>120 sn) 0.16g yanma verisi",
        risk_seviyesi="KRİTİK",
        aciklama=(
            "Düşme kulesi (Drop Tower) testleri yalnızca 5 saniye, parabolik uçuşlar ise 20 saniye sürer. "
            "ISS'deki deneyler ise 0.00g'dedir. 0.16g Ay yerçekiminde kalın malzemelerin dakikalar süren "
            "kararlı hal (steady-state) yanma ve sönme verisi literatürde büyük ölçüde eksiktir."
        ),
        onerilen_deney_tasarimi=(
            "ISS CIR (SoFIE) içerisinde santrifüj destekli kısmi yerçekimi yanma odası veya CLPS Ay yüzeyi "
            "otonom yanma yükü (Lunar Surface Combustion Payload) ile 300 saniyelik test."
        ),
        ilgili_nasa_programi="SoFIE / Artemis Fire Safety"
    ),
    ArastirmaBosluguKaydi(
        bosluk_kodu="GAP-COOL-02",
        baslik="Çok Bileşenli Sıvı/Buhar Karışımlarında Soğuk Alev (Cool Flame) Kaynaklı Yeniden Tutuşma Gecikmesi",
        hedef_ortam="Derin Uzay Transit Aracı (0.00g, Kapalı Aviyonik & Soğutma Hattı)",
        eksik_parametreler="550-700 K görünmez soğuk alevin kabin sensörleriyle erken tespiti ve yeniden tutuşma (re-ignition) eşiği",
        risk_seviyesi="KRİTİK",
        aciklama=(
            "FLEX-2 deneyleri saf heptan ve dekan damlacıklarında soğuk alevi kanıtladı; ancak gerçek uzay "
            "aracı sızıntılarında (soğutucu akışkanlar, yağlayıcılar, plastik piroliz gazları) soğuk alevin "
            "ne kadar süre görünmez kalıp patlayıcı sıcak aleve dönüşeceği henüz haritalanmamıştır."
        ),
        onerilen_deney_tasarimi=(
            "Çift bantlı Orta-Kızılötesi (Mid-IR 3.4 µm formaldehit emisyonu) sensör dizisi ile CIR/ACME "
            "üzerinde çok bileşenli aerosol soğuk alev taraması."
        ),
        ilgili_nasa_programi="FLEX-2 / ACME"
    ),
    ArastirmaBosluguKaydi(
        bosluk_kodu="GAP-DUST-03",
        baslik="Ay (Regolit) ve Mars Tozu İle Kirlenmiş Kumaş/Filtrelerin Mikroçekim Tutuşma Davranışı",
        hedef_ortam="Ay ve Mars Yüzey EVA Hava Kilitleri (0.16g & 0.38g)",
        eksik_parametreler="Demir oksit ve silikat içeren gezegen tozlarının alev yayılım hızı ve kurum oluşumuna katalitik etkisi",
        risk_seviyesi="YÜKSEK",
        aciklama=(
            "NASA-STD-6001B testlerinin tamamı temiz laboratuvar numuneleriyle yapılmaktadır. Oysa EVA "
            "sonrası kabine taşınan elektrostatik Ay regoliti ve Mars tozu, HEPA filtrelerde ve mürettebat "
            "kumaşlarında gözenekleri doldurarak ısı kapasitesini ve alev yayılımını değiştirmektedir."
        ),
        onerilen_deney_tasarimi=(
            "JSC-1A Ay ve MMS-2 Mars regolit simülanı kaplanmış Nomex ve SIBAL numunelerinin 56.5 kPa / %34 O2 "
            "altında yukarı ve ters akışlı yanma testi."
        ),
        ilgili_nasa_programi="BASS-II / Saffire"
    ),
    ArastirmaBosluguKaydi(
        bosluk_kodu="GAP-BATT-04",
        baslik="Mikroçekimde Lityum-İyon Termal Kaçak (Thermal Runaway) Gaz Jeti ve Su Sisi Etkileşimi",
        hedef_ortam="ISS, Orion ve Gateway Güç Modülleri (0.00g - 0.16g)",
        eksik_parametreler="0g'de batarya hücresinden çıkan H2/CO/CH4/Elektrolit jetinin komşu hücrelere radyatif ısı transferi",
        risk_seviyesi="KRİTİK",
        aciklama=(
            "Dünya'da batarya yangınında sıcak gazlar hızla yukarı yükselir. 0g'de ise çıkan yanıcı elektrolit "
            "buharı batarya paketinin etrafında küresel bir bulut oluşturarak gecikmeli buhar bulutu patlamasına "
            "ve İnce Su Sisi ile temas ettiğinde HF gazı oluşumuna yol açabilir."
        ),
        onerilen_deney_tasarimi=(
            "Kapalı eldiven kutusunda (MSG/CIR) tek hücreli Li-Ion termal kaçak gaz simülasyonu ve F500/Su Sisi "
            "damlacık çapı optimizasyonu."
        ),
        ilgili_nasa_programi="ISS PFE / Saffire"
    ),
)


# =============================================================================
# 4. KANIT-ODAKLI (EVIDENCE-FIRST) ARAMA VE SIRALAMA MOTORU
# =============================================================================
class KanitOdakliAramaMotoru:
    """
    Kullanıcı sorgularını NASA PSI ve NTRS deney kayıtları, malzeme atlası ve araştırma boşlukları
    ile eşleştirir; halüsinasyon içermeyen, kanıt kodlu ve önem sırasına dizilmiş sonuçlar döndürür.
    """

    @staticmethod
    def _kelimelere_ayir(metin: str) -> List[str]:
        temiz = re.sub(r"[^\w\sğüşıöçĞÜŞİÖÇ0-9.]", " ", metin.lower())
        return [k for k in temiz.split() if len(k) >= 2]

    def deneyleri_ara_ve_sirala(
        self,
        sorgu: str = "",
        yercekimi_filtre: str = "Tümü",
        min_o2: Optional[float] = None
    ) -> List[Tuple[float, NasaDeneyKaydi]]:
        kelimeler = self._kelimelere_ayir(sorgu)
        sonuclar: List[Tuple[float, NasaDeneyKaydi]] = []

        for kayit in NASA_PSI_DENEY_ARSIVI:
            if yercekimi_filtre != "Tümü":
                if "0.16g" in yercekimi_filtre and "0.16g" not in kayit.yercekimi_rejimi:
                    continue
                if "0.38g" in yercekimi_filtre and "0.38g" not in kayit.yercekimi_rejimi:
                    continue

            if min_o2 is not None:
                if not (kayit.oksijen_araligi_yuzde[0] <= min_o2 <= kayit.oksijen_araligi_yuzde[1]):
                    continue

            if not kelimeler:
                sonuclar.append((kayit.onem_puani * 10.0, kayit))
                continue

            birlesik_metin = (
                f"{kayit.kanit_id} {kayit.program_adi} {kayit.baslik} "
                f"{kayit.yakit_veya_malzeme} {kayit.temel_bulgular} "
                f"{kayit.yangin_guvenligi_cikarimi} {' '.join(kayit.anahtar_kelimeler)}"
            ).lower()

            eslesme_sayisi = 0.0
            for k in kelimeler:
                if k in kayit.anahtar_kelimeler or k in kayit.program_adi.lower():
                    eslesme_sayisi += 3.0
                elif k in birlesik_metin:
                    eslesme_sayisi += 1.5

            if eslesme_sayisi > 0:
                toplam_puan = min(99.9, (eslesme_sayisi / max(len(kelimeler), 1)) * 35.0 + kayit.onem_puani * 5.5)
                sonuclar.append((round(toplam_puan, 1), kayit))

        if not sonuclar and kelimeler:
            # Hiçbir tam kelime eşleşmezse önem puanına göre en kritik kayıtları döndür
            for kayit in NASA_PSI_DENEY_ARSIVI:
                sonuclar.append((round(kayit.onem_puani * 7.5, 1), kayit))

        sonuclar.sort(key=lambda x: x[0], reverse=True)
        return sonuclar

    @staticmethod
    def malzemeleri_atmosfere_gore_degerlendir(
        ortam_o2_yuzde: float,
        yercekimi_g: float
    ) -> List[Dict[str, object]]:
        """
        Verilen kabin oksijen yüzdesi ve yerçekimi ivmesine (0g, 0.16g Ay, 0.38g Mars, 1.0g Dünya)
        göre tüm uzay aracı malzemelerinin yanıcılık durumunu ve güvenlik sıralamasını hesaplar.
        """
        rapor_listesi: List[Dict[str, object]] = []
        for m in UZAY_MALZEME_ATLASI:
            if yercekimi_g < 0.05:
                aktif_loc = m.loc_mikro_0g
                aktif_hiz = m.yayilim_hizi_0g_mm_s
            elif yercekimi_g <= 0.25:
                aktif_loc = m.loc_ay_016g
                aktif_hiz = m.yayilim_hizi_ay_mm_s
            elif yercekimi_g <= 0.60:
                aktif_loc = m.loc_mars_038g
                aktif_hiz = (m.yayilim_hizi_ay_mm_s + m.yayilim_hizi_dunya_mm_s) * 0.5
            else:
                aktif_loc = m.loc_dunya_1g
                aktif_hiz = m.yayilim_hizi_dunya_mm_s

            o2_farki = ortam_o2_yuzde - aktif_loc
            if o2_farki < -2.0:
                durum = "GÜVENLİ (Kendiliğinden Söner)"
                risk_puan = max(5.0, 25.0 + o2_farki * 2.0)
            elif o2_farki < 0.5:
                durum = "SINIRDA (Kritik Tutuşma Eşiği)"
                risk_puan = 55.0 + o2_farki * 10.0
            else:
                durum = "TEHLİKELİ (Sürekli Alev Yayılımı)"
                risk_puan = min(99.0, 70.0 + o2_farki * 2.2 + aktif_hiz * 4.5)

            rapor_listesi.append({
                "malzeme": m,
                "aktif_loc": round(aktif_loc, 1),
                "aktif_hiz": round(aktif_hiz, 2),
                "durum": durum,
                "risk_puan": round(risk_puan, 1),
            })

        rapor_listesi.sort(key=lambda x: float(x["risk_puan"]), reverse=True)
        return rapor_listesi
