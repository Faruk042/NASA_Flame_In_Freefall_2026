# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall"
Modül: Kanıta Dayalı AI Literatür Motoru (gerçek NTRS korpusu üzerinde)

Challenge hedefleriyle birebir eşleşen yetenekler:
  1) Arama & Sıralama     : Türkçe/İngilizce soru -> alan sözlüğüyle sorgu genişletme -> BM25 + kaynak kalitesi ile sıralama
  2) Özetleme             : Seçilen yayınlardan MMR çeşitlilikli, HER CÜMLESİ KAYNAK KİMLİĞİ TAŞIYAN çıkarımsal özet
  3) Sayısal Bulgu Çıkarımı: Özet ve tam metinlerden K (mm²/s), hız (cm/s, mm/s), basınç, %O2, sıcaklık, ısı akısı vb.
  4) Sınıflandırma        : Deney programı (BASS, FLEX, Saffire, ACME, SoFIE, SPICE...), fenomen, yerçekimi rejimi, malzeme
  5) Konu Haritası        : TF-IDF + deterministik k-means++ konu kümeleme
  6) Araştırma Boşluğu    : Fenomen x yerçekimi rejimi kanıt yoğunluğu matrisi (veriden hesaplanır, elle yazılmaz)
  7) Atıf Doğrulama       : LLM (Gemini) çıktısındaki her [NTRS:ID] atfı, getirilen kanıt kümesine karşı denetlenir

Harici bağımlılık yoktur; Gemini isteğe bağlıdır ve yalnızca standart kütüphane (urllib) ile REST üzerinden çağrılır.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import threading
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ntrs_istemcisi import KORPUS_DOSYASI, TAM_METIN_KLASORU, NtrsKaydi, korpus_yukle

# =============================================================================
# 1. METİN İŞLEME
# =============================================================================
INGILIZCE_DURAK = set("""
a about above after again against all also am an and any are as at be because been before being below between both
but by can could did do does doing down during each few for from further had has have having he her here hers him his
how i if in into is it its itself just me more most my no nor not now of off on once only or other our out over own
same she should so some such than that the their them then there these they this those through to too under until up
very was we were what when where which while who whom why will with would you your yours however thus using used use
paper present presented results result study studies also within based may new two one three well data show shown
work report described describes provide provides et al fig figure table section conducted performed obtained
""".split())

_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def kok_bul(kelime: str) -> str:
    """Hafif İngilizce kök bulucu (Porter benzeri, deterministik)."""
    w = kelime
    if len(w) <= 3:
        return w
    for son, yerine in (("ational", "ate"), ("ization", "ize"), ("ations", "ate"), ("ation", "ate"),
                        ("ities", "ity"), ("ies", "y"), ("ings", ""), ("ing", ""), ("edly", ""), ("ed", ""),
                        ("sses", "ss"), ("es", "e"), ("s", "")):
        if w.endswith(son) and len(w) - len(son) >= 3:
            if son == "s" and w.endswith(("ss", "us", "is")):
                return w
            return w[: len(w) - len(son)] + yerine
    return w


def belirtec_ayir(metin: str) -> List[str]:
    metin = (metin or "").lower().replace("²", "2").replace("μ", "u")
    return [kok_bul(t) for t in _TOKEN.findall(metin) if t not in DURAK_SETI and len(t) > 1]


DURAK_SETI = INGILIZCE_DURAK

_CUMLE_BOL = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")
_KISALTMA = re.compile(r"\b(e\.g|i\.e|et al|Fig|Eq|vs|approx|ca|Ref|No|Vol)\.$", re.IGNORECASE)


def cumlelere_bol(metin: str) -> List[str]:
    parcalar = _CUMLE_BOL.split(re.sub(r"\s+", " ", metin or "").strip())
    cumleler: List[str] = []
    tampon = ""
    for p in parcalar:
        tampon = f"{tampon} {p}".strip() if tampon else p
        if _KISALTMA.search(tampon):
            continue
        if len(tampon) >= 25:
            cumleler.append(tampon)
        tampon = ""
    if tampon and len(tampon) >= 25:
        cumleler.append(tampon)
    return cumleler


# =============================================================================
# 2. TÜRKÇE -> İNGİLİZCE ALAN SÖZLÜĞÜ (sorgu genişletme)
# =============================================================================
TR_EN_ALAN_SOZLUGU: List[Tuple[str, str]] = [
    (r"soğuk alev|soguk alev|görünmez alev", "cool flame low temperature chemistry"),
    (r"damlac[ıi]k", "droplet"),
    (r"alev yay[ıi]l[ıi]m[ıi]?|yay[ıi]lma h[ıi]z[ıi]", "flame spread rate"),
    (r"mikro ?(?:yer)?[çc]ekim|s[ıi]f[ıi]r yer[çc]ekim|a[ğg][ıi]rl[ıi]ks[ıi]z", "microgravity"),
    (r"k[ıi]smi yer[çc]ekim", "partial gravity reduced gravity"),
    (r"\bay\b|ay y[üu]zey|lunar|artemis", "lunar moon gravity"),
    (r"\bmars", "mars martian gravity"),
    (r"duman", "smoke particulate"),
    (r"dedekt[öo]r|alg[ıi]lama|sens[öo]r", "detection detector sensor"),
    (r"s[öo]nd[üu]r", "fire suppression extinguish"),
    (r"s[öo]nme|s[öo]n[üu]m", "extinction"),
    (r"oksijen|\bo2\b", "oxygen concentration"),
    (r"bas[ıi]n[çc]", "pressure"),
    (r"kurum|\bis\b", "soot"),
    (r"malzeme", "material"),
    (r"yan[ıi]c[ıi]l[ıi]k|tutuşabilir", "flammability"),
    (r"kuma[şs]|tekstil", "fabric textile"),
    (r"havaland[ıi]rma|ventilasyon|\bfan\b|ak[ıi][şs]", "forced flow ventilation"),
    (r"yang[ıi]n", "fire"),
    (r"tutu[şs]ma", "ignition"),
    (r"batarya|\bpil\b|lityum", "lithium ion battery thermal runaway"),
    (r"su sisi", "water mist"),
    (r"kabin|uzay arac[ıi]|modül", "spacecraft cabin"),
    (r"yanma", "combustion burning"),
    (r"[ıi]s[ıi] ak[ıi]s[ıi]|radyasyon|ışınım", "radiation heat flux"),
    (r"i[çc]in için yanma|kor halinde", "smoldering"),
    (r"keşif atmosfer|kesif atmosfer", "exploration atmosphere oxygen enriched"),
    (r"zehirli|toksik|karbonmonoksit|\bco\b", "toxic carbon monoxide combustion products"),
    (r"yak[ıi]t", "fuel"),
    (r"heptan", "heptane"),
    (r"dekan", "decane"),
    (r"etanol", "ethanol"),
    (r"metanol", "methanol"),
    (r"pmma|pleksi", "pmma"),
    (r"pamuk", "cotton sibal"),
]


def sorguyu_genislet(soru: str) -> Tuple[str, List[str]]:
    """Türkçe ifadeleri alan terimlerine çevirir; orijinal metni korur. (genişletilmiş_sorgu, eklenen_terimler)"""
    alt = (soru or "").lower()
    eklenen: List[str] = []
    for desen, karsilik in TR_EN_ALAN_SOZLUGU:
        if re.search(desen, alt):
            eklenen.append(karsilik)
    return (soru + " " + " ".join(eklenen)).strip(), eklenen


# =============================================================================
# 3. ALAN TAKSONOMİSİ (açıklanabilir, deterministik etiketleme)
# =============================================================================
PROGRAM_DESENLERI: Dict[str, str] = {
    "BASS": r"\bbass(?:-ii)?\b|burning and suppression of solids",
    "FLEX": r"\bflex(?:-2)?\b|flame extinguishment experiment",
    "Saffire": r"\bsaffire\b|spacecraft fire experiment",
    "ACME": r"\bacme\b|advanced combustion via microgravity",
    "SoFIE": r"\bsofie\b|solid fuel ignition and extinction",
    "SPICE": r"\bspice\b|smoke point in co-?flow",
    "DCE/FSDC": r"\bdce\b|droplet combustion experiment|\bfsdc\b|fiber[- ]supported droplet",
    "CFI": r"\bcfi\b|cool flames investigation",
    "SAME/Smoke": r"smoke aerosol measurement|\bsame experiment|characterization of smoke particulate|\"smoke\" experiment",
    "FM2 (Ay)": r"\bfm ?2\b|flammability of materials on the moon",
    "CIR": r"combustion integrated rack|\bcir\b",
    "MSG": r"microgravity science glovebox|\bmsg\b",
}

FENOMEN_DESENLERI: Dict[str, str] = {
    "Alev yayılımı": r"flame spread|spread rate|flame propagation",
    "Sönme / Söndürme": r"extinction|extinguish|quench|blow-?off|suppression",
    "Soğuk alev": r"cool flame|low[- ]temperature (?:chemistry|combustion)|two[- ]stage",
    "Damlacık yanması": r"droplet",
    "Kurum / Işınım": r"\bsoot|radiat",
    "Tutuşma": r"ignition|ignite",
    "İçin için yanma": r"smolder|smoulder",
    "Duman / Algılama": r"smoke|detect|particulate|aerosol",
    "Malzeme yanıcılığı": r"flammab|limiting oxygen|oxygen index|nasa-std-6001|material",
    "Zorlanmış akış": r"forced flow|ventilation|opposed flow|concurrent flow|flow velocity",
    "Batarya yangını": r"lithium|battery|thermal runaway",
}

YERCEKIMI_DESENLERI: Dict[str, str] = {
    "Mikroçekim (0g)": r"microgravity|micro-gravity|\b0-?g\b|zero[- ]gravity|weightless|space station|\biss\b|orbit",
    "Ay (0.16g)": r"lunar|\bmoon\b|1/6|0\.16 ?g|0\.17 ?g",
    "Mars (0.38g)": r"\bmars\b|martian|0\.38 ?g|3/8",
    "Kısmi yerçekimi (genel)": r"partial[- ]gravity|reduced[- ]gravity|fractional gravity",
    "Dünya (1g)": r"normal gravity|\b1 ?-?g\b|earth gravity|normal-gravity|ground[- ]based",
}

MALZEME_DESENLERI: Dict[str, str] = {
    "PMMA": r"\bpmma\b|polymethyl ?methacrylate|acrylic",
    "SIBAL (pamuk/cam elyaf)": r"\bsibal\b|cotton[- ]fiberglass|cotton",
    "Nomex": r"\bnomex\b",
    "Ultem": r"\bultem\b",
    "Kapton": r"\bkapton\b",
    "Selüloz / Kağıt": r"cellulose|filter paper|\bpaper\b",
    "n-Heptan": r"heptane",
    "n-Dekan": r"decane",
    "Alkoller": r"ethanol|methanol|alcohol",
    "Gaz yakıtlar": r"ethylene|methane|propane",
}


def _etiketle(metin: str, desenler: Dict[str, str]) -> List[str]:
    alt = metin.lower()
    return [ad for ad, desen in desenler.items() if re.search(desen, alt)]


# =============================================================================
# 4. SAYISAL BULGU ÇIKARIMI
# =============================================================================
_SAYI = r"(\d+(?:\.\d+)?)(?:\s*(?:-|–|to|and)\s*(\d+(?:\.\d+)?))?"

SAYISAL_DESENLER: List[Tuple[str, str, re.Pattern, Tuple[float, float]]] = [
    ("Yanma hızı sabiti K", "mm²/s",
     re.compile(_SAYI + r"\s*(?:mm\s*(?:\^?\s*2|²|\(exp\s*2\))\s*/\s*s(?:ec)?\b|sq\.?\s*mm\s*/\s*s|square millimet\w* per second)", re.I),
     (0.01, 5.0)),
    ("Hız (alev yayılımı / akış)", "cm/s",
     re.compile(_SAYI + r"\s*(?:cm\s*/\s*s(?:ec)?\b|centimet\w* per second)", re.I), (0.01, 500.0)),
    ("Hız (alev yayılımı / akış)", "mm/s",
     re.compile(_SAYI + r"\s*(?:mm\s*/\s*s(?:ec)?\b|millimet\w* per second)", re.I), (0.001, 500.0)),
    ("Basınç", "kPa", re.compile(_SAYI + r"\s*kpa\b", re.I), (1.0, 1000.0)),
    ("Basınç", "psia", re.compile(_SAYI + r"\s*psi[ag]?\b", re.I), (0.5, 150.0)),
    ("Basınç", "atm", re.compile(_SAYI + r"\s*atm\b", re.I), (0.01, 10.0)),
    ("Oksijen konsantrasyonu", "% O2",
     re.compile(_SAYI + r"\s*(?:%|percent|vol\.?\s*%)\s*(?:o2|o\(sub ?2\)|oxygen)", re.I), (5.0, 100.0)),
    ("Oksijen konsantrasyonu", "% O2",
     re.compile(r"(?:o2|oxygen)\s+(?:concentrations?|levels?|mole fractions?|contents?)\s*(?:of|=|:|from)?\s*" + _SAYI + r"\s*%", re.I),
     (5.0, 100.0)),
    ("Sıcaklık", "K", re.compile(_SAYI + r"\s*K\b"), (200.0, 3500.0)),
    ("Isı akısı", "kW/m²",
     re.compile(_SAYI + r"\s*kw\s*/\s*m\s*(?:\^?\s*2|²|\(exp\s*2\))", re.I), (0.01, 500.0)),
    ("Damlacık / numune çapı", "mm",
     re.compile(_SAYI + r"\s*mm\b(?!\s*/)(?!\s*(?:\^|²|2\b|\(exp))(?=[^.]{0,60}\b(?:diameter|droplet|drop)\b)|"
                r"(?:diameter|droplet)s?\b[^.]{0,40}?" + _SAYI + r"\s*mm\b(?!\s*/)(?!\s*(?:\^|²|2\b|\(exp))", re.I),
     (0.1, 50.0)),
]

# Nicelik -> (cümlede bulunması GEREKEN bağlam, cümlede bulunmaması gereken bağlam)
# Yanlış pozitifleri (ör. termal yayınım "mm²/s" birimini taşır) eler.
BAGLAM_KOSULLARI: Dict[str, Tuple[re.Pattern, Optional[re.Pattern]]] = {
    "Yanma hızı sabiti K": (
        re.compile(r"burn|evaporat|vapori[sz]|droplet|d\s*(?:\^?2|²)|d-squared|rate constant", re.I),
        re.compile(r"diffusivit|viscosit|thermal conductiv", re.I)),
    "Sıcaklık": (re.compile(r"temperat|flame|heat|hot|cool|ignit|K\b", re.I), None),
}


@dataclass
class SayisalBulgu:
    nicelik: str
    deger: float
    deger_ust: Optional[float]
    birim: str
    cumle: str
    ntrs_id: str
    kaynak_turu: str  # "özet" | "tam metin"

    @property
    def deger_metni(self) -> str:
        if self.deger_ust is not None and self.deger_ust != self.deger:
            return f"{self.deger:g}–{self.deger_ust:g} {self.birim}"
        return f"{self.deger:g} {self.birim}"


def sayisal_bulgulari_cikar(metin: str, ntrs_id: str, kaynak_turu: str = "özet",
                            maks: int = 60) -> List[SayisalBulgu]:
    bulgular: List[SayisalBulgu] = []
    gorulen = set()
    for cumle in cumlelere_bol(metin):
        if len(cumle) > 600:
            continue
        for nicelik, birim, desen, (alt_sinir, ust_sinir) in SAYISAL_DESENLER:
            baglam = BAGLAM_KOSULLARI.get(nicelik)
            if baglam is not None and (not baglam[0].search(cumle) or (baglam[1] and baglam[1].search(cumle))):
                continue
            for m in desen.finditer(cumle):
                gruplar = [g for g in m.groups() if g is not None]
                if not gruplar:
                    continue
                try:
                    d1 = float(gruplar[0])
                    d2 = float(gruplar[1]) if len(gruplar) > 1 else None
                except ValueError:
                    continue
                if not (alt_sinir <= d1 <= ust_sinir):
                    continue
                if d2 is not None and not (alt_sinir <= d2 <= ust_sinir and d2 >= d1):
                    d2 = None
                anahtar = (nicelik, birim, d1, d2, ntrs_id)
                if anahtar in gorulen:
                    continue
                gorulen.add(anahtar)
                bulgular.append(SayisalBulgu(nicelik, d1, d2, birim, cumle.strip()[:420], ntrs_id, kaynak_turu))
                if len(bulgular) >= maks:
                    return bulgular
    return bulgular


# =============================================================================
# 5. GÜVENLİK ÇIKARIMLARI (mühendislik yorumu -> korpustaki kanıtlara bağlanır)
# =============================================================================
GUVENLIK_CIKARIMLARI: Dict[str, Tuple[str, str]] = {
    "Zorlanmış akış": (
        "Havalandırmayı kesin",
        "Mikroçekimde kaldırma kuvveti (buoyancy) olmadığından alevi besleyen oksijen ağırlıkla kabin "
        "havalandırma akışıyla taşınır. Yangın müdahalesinde ilk adımlardan biri havalandırmanın kesilmesidir."),
    "Soğuk alev": (
        "Görünür alev sönünce yangın bitmiş sayılmamalı",
        "Literatürde görünür (sıcak) alev söndükten sonra düşük sıcaklıklı 'soğuk alev' yanmasının sürebildiği "
        "raporlanmıştır. Yalnızca görünür ışık/UV alev dedektörlerine güvenmek yerine sıcaklık ve gaz (CO vb.) "
        "algılaması birlikte kullanılmalıdır."),
    "Malzeme yanıcılığı": (
        "Malzeme seçimini hedef ortama göre doğrulayın",
        "Malzeme yanıcılığı oksijen konsantrasyonu, basınç, akış hızı ve yerçekimi düzeyine birlikte bağlıdır. "
        "1g'de yapılan kabul testlerinin mikroçekim ve kısmi yerçekimi koşullarını temsil edip etmediği "
        "ilgili kaynaklarla birlikte değerlendirilmelidir."),
    "Duman / Algılama": (
        "Dedektörleri mikroçekim dumanına göre kalibre edin",
        "Mikroçekimde duman tabakalaşmaz ve parçacık boyut dağılımı farklılaşabilir. Dedektör konumu "
        "(ör. havalandırma dönüş kanalları) ve kalibrasyonu bu farklara göre seçilmelidir."),
    "Sönme / Söndürme": (
        "Söndürme stratejisini mikroçekim fiziğine göre seçin",
        "Sönme sınırları (düşük akışta oksijen açlığı, yüksek akışta üfleme ile sönme) Dünya'dakinden farklıdır; "
        "söndürücü tipi ve uygulama biçimi bu sınırlara göre değerlendirilmelidir."),
    "Kurum / Işınım": (
        "Işınım ısı kaybını ve kurumu hesaba katın",
        "Mikroçekimde alevler daha geniş ve daha uzun kalış süreli olabilir; kurum ve ışınım hem sönme "
        "davranışını hem de toksik ürün oluşumunu etkiler."),
    "İçin için yanma": (
        "Alevsiz yanmayı izleyin",
        "İçin için yanma (smoldering) alevsiz ilerleyebilir ve alevli yanmaya geçebilir; sürekli gaz ve "
        "sıcaklık izlemesi gerektirir."),
    "Batarya yangını": (
        "Lityum-iyon bataryalar için özel önlem",
        "Termal kaçak (thermal runaway) yanıcı gaz ve yüksek ısı üretir; kapalı kabinde yayılımı sınırlayacak "
        "muhafaza ve algılama tasarımı gerekir."),
    "Alev yayılımı": (
        "Alev yayılım hızını ortam koşullarıyla birlikte değerlendirin",
        "Alev yayılım hızı yakıt kalınlığı, akış yönü (karşı/eş akış), oksijen ve basınca bağlıdır; risk "
        "değerlendirmesi bu parametreler birlikte ele alınarak yapılmalıdır."),
}


# =============================================================================
# 6. VERİ YAPILARI
# =============================================================================
@dataclass
class BelgeProfili:
    kayit: NtrsKaydi
    programlar: List[str]
    fenomenler: List[str]
    yercekimi: List[str]
    malzemeler: List[str]
    kaynak_kalitesi: float


@dataclass
class AramaSonucu:
    kayit: NtrsKaydi
    skor: float
    bm25: float
    eslesen_terimler: List[str]
    profil: BelgeProfili


@dataclass
class OzetCumlesi:
    cumle: str
    ntrs_id: str
    skor: float


@dataclass
class KanitYaniti:
    soru: str
    genisletilmis_sorgu: str
    eklenen_terimler: List[str]
    sonuclar: List[AramaSonucu]
    ozet: List[OzetCumlesi]
    sayisal_bulgular: List[SayisalBulgu]
    guvenlik_cikarimlari: List[Dict[str, object]]
    guven_duzeyi: str
    guven_aciklamasi: str
    kapsam_uyarilari: List[str]
    llm_yaniti: Optional[str] = None
    atif_denetimi: Optional[Dict[str, object]] = None

    def kanit_kimlikleri(self) -> List[str]:
        return [s.kayit.ntrs_id for s in self.sonuclar]


# =============================================================================
# 7. ANA MOTOR
# =============================================================================
class LiteraturAIMotoru:
    """Gerçek NTRS korpusu üzerinde arama, özetleme, bulgu çıkarımı ve boşluk analizi yapan motor."""

    BM25_K1 = 1.4
    BM25_B = 0.72
    BASLIK_AGIRLIGI = 3

    def __init__(self, kayitlar: Optional[Sequence[NtrsKaydi]] = None, korpus_meta: Optional[Dict] = None) -> None:
        if kayitlar is None:
            korpus_meta, kayitlar = korpus_yukle()
        self.meta: Dict[str, object] = dict(korpus_meta or {})
        self.kayitlar: List[NtrsKaydi] = list(kayitlar)
        self.kimlik_indeksi: Dict[str, int] = {k.ntrs_id: i for i, k in enumerate(self.kayitlar)}
        self.profiller: List[BelgeProfili] = [self._profil_cikar(k) for k in self.kayitlar]
        self._indeks_olustur()
        self._tam_metin_bulgu_onbellegi: Dict[str, List[SayisalBulgu]] = {}
        self._kumeler: Optional[List[Dict[str, object]]] = None

    # ---- indeksleme ---------------------------------------------------------
    @staticmethod
    def _profil_cikar(k: NtrsKaydi) -> BelgeProfili:
        metin = " ".join([k.baslik, k.ozet, " ".join(k.anahtar_kelimeler), k.yayin_adi])
        tur = (k.belge_turu or "").upper()
        kalite = {"JOURNAL_ARTICLE": 1.0, "TECHNICAL_PUBLICATION": 0.95, "CONTRACTOR_REPORT": 0.85,
                  "TECHNICAL_MEMORANDUM": 0.9, "CONFERENCE_PAPER": 0.85, "REPRINT": 0.85,
                  "PRESENTATION": 0.6, "ABSTRACT": 0.5}.get(tur, 0.7)
        if len(k.ozet) < 80:
            kalite *= 0.6
        if k.tam_metin_var:
            kalite = min(1.0, kalite + 0.05)
        return BelgeProfili(
            kayit=k,
            programlar=_etiketle(metin, PROGRAM_DESENLERI),
            fenomenler=_etiketle(metin, FENOMEN_DESENLERI),
            yercekimi=_etiketle(metin, YERCEKIMI_DESENLERI),
            malzemeler=_etiketle(metin, MALZEME_DESENLERI),
            kaynak_kalitesi=round(kalite, 3),
        )

    def _belge_belirtecleri(self, k: NtrsKaydi) -> List[str]:
        baslik = belirtec_ayir(k.baslik)
        return baslik * self.BASLIK_AGIRLIGI + belirtec_ayir(k.ozet) + belirtec_ayir(" ".join(k.anahtar_kelimeler))

    def _indeks_olustur(self) -> None:
        self.belge_tf: List[Counter] = []
        self.belge_uzunluk: List[int] = []
        df: Counter = Counter()
        for k in self.kayitlar:
            tf = Counter(self._belge_belirtecleri(k))
            self.belge_tf.append(tf)
            self.belge_uzunluk.append(sum(tf.values()))
            df.update(tf.keys())
        n = max(1, len(self.kayitlar))
        self.ort_uzunluk = (sum(self.belge_uzunluk) / n) if self.kayitlar else 1.0
        self.idf: Dict[str, float] = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tfidf_vektorleri: List[Dict[str, float]] = [self._tfidf(tf) for tf in self.belge_tf]

    def _tfidf(self, tf: Counter) -> Dict[str, float]:
        v = {t: (1 + math.log(c)) * self.idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    @staticmethod
    def _kosinus(a: Dict[str, float], b: Dict[str, float]) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(t, 0.0) for t, x in a.items())

    # ---- arama --------------------------------------------------------------
    def ara(self, soru: str, ust_k: int = 10, program: Optional[str] = None,
            yercekimi: Optional[str] = None, min_yil: Optional[int] = None) -> List[AramaSonucu]:
        if not self.kayitlar:
            return []
        genis, _ = sorguyu_genislet(soru)
        sorgu_bel = belirtec_ayir(genis)
        if not sorgu_bel:
            return []
        sorgu_tf = Counter(sorgu_bel)
        hedef_program = set(_etiketle(genis, PROGRAM_DESENLERI))
        sonuclar: List[AramaSonucu] = []
        maks_bm25 = 0.0
        ham: List[Tuple[int, float, List[str]]] = []
        for i, tf in enumerate(self.belge_tf):
            p = self.profiller[i]
            if program and program not in p.programlar:
                continue
            if yercekimi and yercekimi not in p.yercekimi:
                continue
            if min_yil and (self.kayitlar[i].yil or 0) < min_yil:
                continue
            skor = 0.0
            eslesen: List[str] = []
            dl = self.belge_uzunluk[i] or 1
            for t, qf in sorgu_tf.items():
                f = tf.get(t)
                if not f:
                    continue
                eslesen.append(t)
                idf = self.idf.get(t, 0.0)
                skor += idf * (f * (self.BM25_K1 + 1)) / (f + self.BM25_K1 * (1 - self.BM25_B + self.BM25_B * dl / self.ort_uzunluk)) * (1 + 0.15 * (qf - 1))
            if skor <= 0:
                continue
            ham.append((i, skor, eslesen))
            maks_bm25 = max(maks_bm25, skor)
        for i, bm25, eslesen in ham:
            p = self.profiller[i]
            norm = bm25 / (maks_bm25 or 1.0)
            program_bonus = 0.12 if hedef_program and hedef_program & set(p.programlar) else 0.0
            kapsam = len(set(eslesen)) / max(1, len(set(sorgu_tf)))
            skor = 0.62 * norm + 0.16 * kapsam + 0.10 * p.kaynak_kalitesi + program_bonus
            sonuclar.append(AramaSonucu(self.kayitlar[i], round(skor, 4), round(bm25, 3), sorted(set(eslesen)), p))
        sonuclar.sort(key=lambda s: s.skor, reverse=True)
        return sonuclar[:ust_k]

    # ---- özetleme (MMR) -----------------------------------------------------
    def kaynakli_ozet(self, soru: str, sonuclar: Sequence[AramaSonucu], maks_cumle: int = 6,
                      lambda_mmr: float = 0.72) -> List[OzetCumlesi]:
        genis, _ = sorguyu_genislet(soru)
        q = self._tfidf(Counter(belirtec_ayir(genis)))
        adaylar: List[Tuple[str, str, Dict[str, float], float]] = []
        for s in sonuclar[:8]:
            for c in cumlelere_bol(s.kayit.ozet)[:14]:
                if len(c) < 50 or len(c) > 480:
                    continue
                v = self._tfidf(Counter(belirtec_ayir(c)))
                if not v:
                    continue
                alaka = self._kosinus(q, v) * 0.8 + s.skor * 0.2
                adaylar.append((c, s.kayit.ntrs_id, v, alaka))
        secilen: List[Tuple[str, str, Dict[str, float], float]] = []
        while adaylar and len(secilen) < maks_cumle:
            en_iyi, en_iyi_skor = None, -1e9
            for a in adaylar:
                benzerlik = max((self._kosinus(a[2], b[2]) for b in secilen), default=0.0)
                mmr = lambda_mmr * a[3] - (1 - lambda_mmr) * benzerlik
                if mmr > en_iyi_skor:
                    en_iyi, en_iyi_skor = a, mmr
            if en_iyi is None:
                break
            secilen.append(en_iyi)
            adaylar.remove(en_iyi)
        return [OzetCumlesi(c, nid, round(sk, 4)) for c, nid, _, sk in secilen]

    # ---- sayısal bulgular ---------------------------------------------------
    def tam_metin_mevcut_mu(self, ntrs_id: str) -> bool:
        return os.path.isfile(os.path.join(TAM_METIN_KLASORU, f"{ntrs_id}.txt"))

    def belge_bulgulari(self, kayit: NtrsKaydi, tam_metin_dahil: bool = True) -> List[SayisalBulgu]:
        bulgular = sayisal_bulgulari_cikar(kayit.baslik + ". " + kayit.ozet, kayit.ntrs_id, "özet")
        if tam_metin_dahil and self.tam_metin_mevcut_mu(kayit.ntrs_id):
            if kayit.ntrs_id not in self._tam_metin_bulgu_onbellegi:
                yol = os.path.join(TAM_METIN_KLASORU, f"{kayit.ntrs_id}.txt")
                with open(yol, "r", encoding="utf-8", errors="replace") as f:
                    metin = f.read(1_500_000)
                self._tam_metin_bulgu_onbellegi[kayit.ntrs_id] = sayisal_bulgulari_cikar(
                    metin, kayit.ntrs_id, "tam metin", maks=120)
            bulgular += self._tam_metin_bulgu_onbellegi[kayit.ntrs_id]
        return bulgular

    def korpus_bulgulari(self, nicelik: Optional[str] = None, tam_metin_dahil: bool = True) -> List[SayisalBulgu]:
        tum: List[SayisalBulgu] = []
        for k in self.kayitlar:
            tum.extend(b for b in self.belge_bulgulari(k, tam_metin_dahil) if not nicelik or b.nicelik == nicelik)
        return tum

    # ---- kanıt yoğunluğu & araştırma boşluğu --------------------------------
    def kanit_matrisi(self) -> Tuple[List[str], List[str], List[List[int]]]:
        satirlar = list(FENOMEN_DESENLERI.keys())
        sutunlar = list(YERCEKIMI_DESENLERI.keys())
        matris = [[0] * len(sutunlar) for _ in satirlar]
        for p in self.profiller:
            for f in p.fenomenler:
                for g in p.yercekimi:
                    matris[satirlar.index(f)][sutunlar.index(g)] += 1
        return satirlar, sutunlar, matris

    def arastirma_bosluklari(self, esik_orani: float = 0.12, min_satir_toplami: int = 8) -> List[Dict[str, object]]:
        """Bir fenomen için toplam kanıtın çok küçük bir kısmının belirli bir yerçekimi rejiminde olduğu hücreler."""
        satirlar, sutunlar, matris = self.kanit_matrisi()
        bosluklar: List[Dict[str, object]] = []
        hedef = {"Ay (0.16g)", "Mars (0.38g)", "Kısmi yerçekimi (genel)", "Mikroçekim (0g)"}
        for i, f in enumerate(satirlar):
            toplam = sum(matris[i])
            if toplam < min_satir_toplami:
                continue
            for j, g in enumerate(sutunlar):
                if g not in hedef:
                    continue
                oran = matris[i][j] / toplam
                if oran < esik_orani:
                    bosluklar.append({
                        "fenomen": f, "yercekimi": g, "belge_sayisi": matris[i][j],
                        "fenomen_toplami": toplam, "oran": round(oran, 3),
                        "oncelik": round((1 - oran / esik_orani) * math.log1p(toplam), 2),
                    })
        bosluklar.sort(key=lambda b: b["oncelik"], reverse=True)
        return bosluklar

    def program_istatistikleri(self) -> Dict[str, int]:
        c = Counter()
        for p in self.profiller:
            c.update(p.programlar)
        return dict(c.most_common())

    def yillik_dagilim(self) -> Dict[int, int]:
        c = Counter(k.yil for k in self.kayitlar if k.yil)
        return dict(sorted(c.items()))

    def program_yil_dagilimi(self) -> Dict[str, Dict[int, int]]:
        sonuc: Dict[str, Counter] = defaultdict(Counter)
        for p in self.profiller:
            if p.kayit.yil:
                for pr in p.programlar:
                    sonuc[pr][p.kayit.yil] += 1
        return {k: dict(sorted(v.items())) for k, v in sonuc.items()}

    # ---- konu kümeleme ------------------------------------------------------
    def konu_kumeleri(self, k: int = 8, iterasyon: int = 25, tohum: int = 2026) -> List[Dict[str, object]]:
        if self._kumeler is not None and len(self._kumeler) == k:
            return self._kumeler
        indeksler = [i for i, v in enumerate(self.tfidf_vektorleri) if len(v) >= 5]
        if len(indeksler) < k:
            self._kumeler = []
            return self._kumeler
        rnd = random.Random(tohum)
        vekt = [self.tfidf_vektorleri[i] for i in indeksler]
        merkezler = [dict(vekt[rnd.randrange(len(vekt))])]
        while len(merkezler) < k:  # k-means++
            mesafeler = [1 - max(self._kosinus(v, m) for m in merkezler) for v in vekt]
            toplam = sum(d * d for d in mesafeler) or 1.0
            r, birikim = rnd.random() * toplam, 0.0
            for idx, d in enumerate(mesafeler):
                birikim += d * d
                if birikim >= r:
                    merkezler.append(dict(vekt[idx]))
                    break
        atama = [0] * len(vekt)
        for _ in range(iterasyon):
            degisti = False
            for idx, v in enumerate(vekt):
                en_iyi = max(range(k), key=lambda c: self._kosinus(v, merkezler[c]))
                if en_iyi != atama[idx]:
                    atama[idx], degisti = en_iyi, True
            for c in range(k):
                uyeler = [vekt[i] for i in range(len(vekt)) if atama[i] == c]
                if not uyeler:
                    continue
                toplam_v: Dict[str, float] = defaultdict(float)
                for v in uyeler:
                    for t, x in v.items():
                        toplam_v[t] += x
                en_onemli = sorted(toplam_v.items(), key=lambda kv: kv[1], reverse=True)[:300]
                norm = math.sqrt(sum(x * x for _, x in en_onemli)) or 1.0
                merkezler[c] = {t: x / norm for t, x in en_onemli}
            if not degisti:
                break
        kumeler: List[Dict[str, object]] = []
        for c in range(k):
            uye_idx = [indeksler[i] for i in range(len(vekt)) if atama[i] == c]
            if not uye_idx:
                continue
            terimler = [t for t, _ in sorted(merkezler[c].items(), key=lambda kv: kv[1], reverse=True)
                        if not t.isdigit()][:7]
            temsilci = sorted(uye_idx, key=lambda i: self._kosinus(self.tfidf_vektorleri[i], merkezler[c]), reverse=True)
            yillar = [self.kayitlar[i].yil for i in uye_idx if self.kayitlar[i].yil]
            kumeler.append({
                "kume_no": c + 1,
                "etiket": ", ".join(terimler[:4]),
                "anahtar_terimler": terimler,
                "belge_sayisi": len(uye_idx),
                "ortalama_yil": round(sum(yillar) / len(yillar)) if yillar else None,
                "temsilci_belgeler": [self.kayitlar[i] for i in temsilci[:5]],
                "uye_kimlikleri": [self.kayitlar[i].ntrs_id for i in uye_idx],
            })
        kumeler.sort(key=lambda d: d["belge_sayisi"], reverse=True)
        self._kumeler = kumeler
        return kumeler

    # ---- soru yanıtlama -----------------------------------------------------
    def soru_yanitla(self, soru: str, ust_k: int = 8, **filtreler) -> KanitYaniti:
        genis, eklenen = sorguyu_genislet(soru)
        sonuclar = self.ara(soru, ust_k=ust_k, **filtreler)
        ozet = self.kaynakli_ozet(soru, sonuclar)

        sorgu_kokleri = set(belirtec_ayir(genis))
        bulgular: List[SayisalBulgu] = []
        for s in sonuclar[:6]:
            for b in self.belge_bulgulari(s.kayit):
                ortak = len(sorgu_kokleri & set(belirtec_ayir(b.cumle)))
                if ortak >= 1:
                    bulgular.append(b)
        bulgular = bulgular[:25]

        # Güvenlik çıkarımları: sorguda ve en iyi sonuçlarda baskın olan fenomenler
        fenomen_sayaci: Counter = Counter()
        for s in sonuclar[:6]:
            fenomen_sayaci.update(s.profil.fenomenler)
        for f in _etiketle(genis, FENOMEN_DESENLERI):
            fenomen_sayaci[f] += 3
        cikarimlar: List[Dict[str, object]] = []
        for f, _ in fenomen_sayaci.most_common():
            if f not in GUVENLIK_CIKARIMLARI:
                continue
            destek = [s.kayit for s in sonuclar if f in s.profil.fenomenler][:4]
            if not destek:
                continue
            baslik, aciklama = GUVENLIK_CIKARIMLARI[f]
            cikarimlar.append({"fenomen": f, "baslik": baslik, "aciklama": aciklama,
                               "destekleyen": destek})
            if len(cikarimlar) >= 4:
                break

        # Güven düzeyi: kanıt sayısı, skor ve kaynak kalitesi
        guclu = [s for s in sonuclar if s.skor >= 0.55]
        if len(guclu) >= 4:
            guven, aciklama = "YÜKSEK", f"{len(guclu)} güçlü eşleşen NTRS kaynağı bulundu."
        elif len(guclu) >= 2 or len(sonuclar) >= 5:
            guven, aciklama = "ORTA", f"{len(guclu)} güçlü, toplam {len(sonuclar)} ilgili kaynak bulundu."
        elif sonuclar:
            guven, aciklama = "DÜŞÜK", "Az sayıda / zayıf eşleşen kaynak; sonuçları dikkatle yorumlayın."
        else:
            guven, aciklama = "YOK", "Korpusta bu soruyla eşleşen kaynak bulunamadı; canlı NTRS araması deneyin."

        uyarilar: List[str] = []
        hedef_g = _etiketle(genis, YERCEKIMI_DESENLERI)
        for g in hedef_g:
            say = sum(1 for p in self.profiller if g in p.yercekimi)
            if say < 25:
                uyarilar.append(f"'{g}' rejiminde korpusta yalnızca {say} yayın var — bu bir araştırma boşluğu göstergesidir.")
        if not self.kayitlar:
            uyarilar.append("Yerel NTRS korpusu boş. 'python korpus_olusturucu.py' ile oluşturun.")

        return KanitYaniti(soru, genis, eklenen, sonuclar, ozet, bulgular, cikarimlar, guven, aciklama, uyarilar)

    # ---- LLM (isteğe bağlı) & atıf doğrulama --------------------------------
    @staticmethod
    def atiflari_denetle(metin: str, izinli_kimlikler: Iterable[str]) -> Dict[str, object]:
        izinli = set(izinli_kimlikler)
        bulunan = re.findall(r"NTRS[:\s#-]*(\d{8,12})", metin or "")
        gecerli = sorted({b for b in bulunan if b in izinli})
        gecersiz = sorted({b for b in bulunan if b not in izinli})
        toplam = len(set(bulunan))
        return {
            "toplam_atif": toplam,
            "gecerli": gecerli,
            "gecersiz": gecersiz,
            "dogrulama_orani": round(len(gecerli) / toplam, 3) if toplam else 0.0,
        }

    def gemini_ile_sentezle(self, yanit: KanitYaniti, api_anahtari: str,
                            model: str = "gemini-2.5-flash", zaman_asimi: int = 45) -> KanitYaniti:
        """Yalnızca getirilen kanıtlarla sınırlı (grounded) Gemini sentezi; atıflar sonradan doğrulanır."""
        anahtar = (api_anahtari or "").strip()
        if not anahtar or not yanit.sonuclar:
            return yanit
        if not re.match(r"^[A-Za-z0-9_\-]{20,80}$", anahtar):
            yanit.llm_yaniti = "[!] API anahtarı biçimi geçersiz."
            return yanit
        if not re.match(r"^[a-z0-9.\-]{3,60}$", model):
            model = "gemini-2.5-flash"
        kanitlar = []
        for s in yanit.sonuclar[:8]:
            k = s.kayit
            kanitlar.append(f"[NTRS:{k.ntrs_id}] {k.baslik} ({k.kisa_atif()})\nÖZET: {k.ozet[:1400]}")
        bulgu_satirlari = [f"- {b.nicelik}: {b.deger_metni} [NTRS:{b.ntrs_id}]" for b in yanit.sayisal_bulgular[:12]]
        istem = (
            "Sen NASA mikroçekim yanma ve uzay aracı yangın güvenliği konusunda uzman bir araştırma asistanısın.\n"
            "KURALLAR:\n"
            "1) YALNIZCA aşağıdaki KANITLAR bölümündeki bilgileri kullan. Kanıtlarda olmayan hiçbir sayı veya iddia üretme.\n"
            "2) Her iddianın sonuna kaynağını [NTRS:ID] biçiminde ekle. Listede olmayan kimlik ASLA kullanma.\n"
            "3) Kanıt yetersizse bunu açıkça söyle ve hangi verinin eksik olduğunu belirt.\n"
            "4) Yanıtı Türkçe yaz: (a) Kısa yanıt, (b) Temel bulgular, (c) Yangın güvenliği çıkarımları, "
            "(d) Belirsizlikler ve araştırma boşlukları.\n\n"
            f"SORU: {yanit.soru}\n\nKANITLAR:\n" + "\n\n".join(kanitlar)
            + ("\n\nÇIKARILMIŞ SAYISAL BULGULAR:\n" + "\n".join(bulgu_satirlari) if bulgu_satirlari else "")
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        govde = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": istem}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        }).encode("utf-8")
        istek = urllib.request.Request(url, data=govde, method="POST", headers={
            "Content-Type": "application/json", "x-goog-api-key": anahtar})
        try:
            with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
                veri = json.loads(r.read(2_000_000).decode("utf-8", errors="replace"))
            parcalar = (((veri.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
            metin = "\n".join(p.get("text", "") for p in parcalar).strip()
            if not metin:
                yanit.llm_yaniti = "[!] Gemini boş yanıt döndürdü."
                return yanit
            yanit.llm_yaniti = metin
            yanit.atif_denetimi = self.atiflari_denetle(metin, yanit.kanit_kimlikleri())
        except urllib.error.HTTPError as exc:
            yanit.llm_yaniti = f"[!] Gemini API hatası (HTTP {exc.code}). Anahtarı ve kotanızı kontrol edin."
        except (urllib.error.URLError, TimeoutError) as exc:
            yanit.llm_yaniti = f"[!] Gemini API'ye ulaşılamadı: {getattr(exc, 'reason', exc)}"
        except (ValueError, KeyError, IndexError) as exc:
            yanit.llm_yaniti = f"[!] Gemini yanıtı çözümlenemedi: {exc}"
        return yanit

    # ---- düz metin rapor ----------------------------------------------------
    @staticmethod
    def yaniti_metne_cevir(y: KanitYaniti) -> str:
        s = ["=" * 78, "  KANITA DAYALI LİTERATÜR YANITI (Gerçek NASA NTRS kaynakları)", "=" * 78,
             f"Soru           : {y.soru}",
             f"Genişletme     : {', '.join(y.eklenen_terimler) or '-'}",
             f"Güven düzeyi   : {y.guven_duzeyi} — {y.guven_aciklamasi}", ""]
        if y.ozet:
            s.append("1) KAYNAKLI ÖZET (her cümle orijinal NTRS özetinden alınmıştır):")
            for o in y.ozet:
                s.append(f"   • {o.cumle} [NTRS:{o.ntrs_id}]")
            s.append("")
        if y.sayisal_bulgular:
            s.append("2) ÇIKARILAN SAYISAL BULGULAR:")
            for b in y.sayisal_bulgular[:12]:
                s.append(f"   • {b.nicelik}: {b.deger_metni}  ({b.kaynak_turu}) [NTRS:{b.ntrs_id}]")
            s.append("")
        if y.guvenlik_cikarimlari:
            s.append("3) YANGIN GÜVENLİĞİ ÇIKARIMLARI (mühendislik yorumu + destekleyen kaynaklar):")
            for c in y.guvenlik_cikarimlari:
                kimlikler = ", ".join(f"NTRS:{k.ntrs_id}" for k in c["destekleyen"])
                s.append(f"   ✅ {c['baslik']}: {c['aciklama']}  [{kimlikler}]")
            s.append("")
        s.append("4) SIRALANMIŞ KANITLAR:")
        for i, r in enumerate(y.sonuclar, 1):
            s.append(f"   {i}. [NTRS:{r.kayit.ntrs_id}] {r.kayit.baslik} — {r.kayit.kisa_atif()} "
                     f"| skor={r.skor:.2f} | {r.kayit.url}")
        if y.kapsam_uyarilari:
            s.append("")
            s.append("5) KAPSAM UYARILARI:")
            s.extend(f"   ⚠ {u}" for u in y.kapsam_uyarilari)
        if y.llm_yaniti:
            s += ["", "6) GEMINI SENTEZİ (yalnızca yukarıdaki kanıtlarla sınırlı):", y.llm_yaniti]
            if y.atif_denetimi:
                a = y.atif_denetimi
                s.append(f"   Atıf doğrulama: {len(a['gecerli'])}/{a['toplam_atif']} geçerli"
                         + (f" | GEÇERSİZ: {', '.join(a['gecersiz'])}" if a["gecersiz"] else ""))
        s.append("=" * 78)
        return "\n".join(s)


# =============================================================================
# Tekil (singleton) erişim — GUI ve web uygulaması aynı indeksi paylaşır
# =============================================================================
_MOTOR: Optional[LiteraturAIMotoru] = None
_MOTOR_KILIT = threading.Lock()


def motor_al(yeniden_yukle: bool = False) -> LiteraturAIMotoru:
    global _MOTOR
    with _MOTOR_KILIT:
        if _MOTOR is None or yeniden_yukle:
            _MOTOR = LiteraturAIMotoru()
        return _MOTOR
