# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall"
Modül: Gerçek NASA NTRS (Technical Reports Server) API İstemcisi

Bu modül YALNIZCA NASA'nın resmi, herkese açık NTRS API'si (https://ntrs.nasa.gov/api) ile konuşur.
- Harici bağımlılık yoktur (yalnızca Python standart kütüphanesi: urllib).
- Tüm istekler salt-okunurdur (HTTP GET); hiçbir uzak sisteme veri yazılmaz.
- Güvenlik: Yalnızca ntrs.nasa.gov alan adına izin verilir, NTRS kimlikleri sayısal olarak doğrulanır,
  yanıt boyutu sınırlandırılır, sorgular temizlenir ve zaman aşımı uygulanır.
- Her kayıt, jürinin doğrulayabilmesi için kalıcı bir https://ntrs.nasa.gov/citations/<ID> bağlantısı taşır.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

NTRS_TABAN_URL = "https://ntrs.nasa.gov"
NTRS_API_ARAMA = NTRS_TABAN_URL + "/api/citations/search"
NTRS_IZINLI_HOST = "ntrs.nasa.gov"
KULLANICI_AJANI = "FlameInFreefall-SpaceApps2026/2.0 (+https://www.spaceappschallenge.org)"

MAKS_YANIT_BAYT = 4 * 1024 * 1024        # JSON yanıtları için 4 MB üst sınır
MAKS_TAM_METIN_BAYT = 3 * 1024 * 1024    # Tam metin (.txt) için 3 MB üst sınır
MAKS_SORGU_UZUNLUGU = 300
VARSAYILAN_ZAMAN_ASIMI = 20

PROJE_KLASORU = os.path.dirname(os.path.abspath(__file__))
VERI_KLASORU = os.path.join(PROJE_KLASORU, "veri")
KORPUS_DOSYASI = os.path.join(VERI_KLASORU, "ntrs_korpus.json")
TAM_METIN_KLASORU = os.path.join(VERI_KLASORU, "tam_metin")

_ID_DESENI = re.compile(r"^\d{8,12}$")


class NtrsHatasi(Exception):
    """NTRS API ile iletişimde oluşan, kullanıcıya gösterilebilir hata."""


@dataclass
class NtrsKaydi:
    """NTRS'den gelen bir yayının normalize edilmiş, doğrulanabilir temsili."""
    ntrs_id: str
    baslik: str
    ozet: str
    yazarlar: List[str] = field(default_factory=list)
    kurumlar: List[str] = field(default_factory=list)
    yil: Optional[int] = None
    merkez: str = ""
    belge_turu: str = ""
    yayin_adi: str = ""
    konu_kategorileri: List[str] = field(default_factory=list)
    anahtar_kelimeler: List[str] = field(default_factory=list)
    pdf_var: bool = False
    tam_metin_var: bool = False
    sorgu_etiketleri: List[str] = field(default_factory=list)
    tam_metin_yolu: str = ""   # NTRS'in döndürdüğü gerçek "/api/citations/<ID>/downloads/<dosya>.txt" yolu

    @property
    def url(self) -> str:
        return f"{NTRS_TABAN_URL}/citations/{self.ntrs_id}"

    @property
    def pdf_url(self) -> str:
        return f"{NTRS_TABAN_URL}/api/citations/{self.ntrs_id}/downloads/{self.ntrs_id}.pdf"

    @property
    def atif_etiketi(self) -> str:
        return f"NTRS:{self.ntrs_id}"

    def kisa_atif(self) -> str:
        ilk_yazar = self.yazarlar[0].split(",")[0] if self.yazarlar else "NASA"
        ek = " vd." if len(self.yazarlar) > 1 else ""
        yil = self.yil if self.yil else "t.y."
        return f"{ilk_yazar}{ek} ({yil})"

    def sozluge(self) -> Dict[str, object]:
        return asdict(self)

    @staticmethod
    def sozlukten(d: Dict[str, object]) -> "NtrsKaydi":
        izinli = {f for f in NtrsKaydi.__dataclass_fields__}
        return NtrsKaydi(**{k: v for k, v in d.items() if k in izinli})


# =============================================================================
# Yardımcılar
# =============================================================================
def ntrs_id_dogrula(ntrs_id: object) -> str:
    """NTRS kimliğinin yalnızca 8-12 haneli sayı olduğunu doğrular (enjeksiyon / SSRF koruması)."""
    s = str(ntrs_id).strip()
    if not _ID_DESENI.match(s):
        raise NtrsHatasi(f"Geçersiz NTRS kimliği: {s!r}")
    return s


def sorgu_temizle(sorgu: str) -> str:
    """Kontrol karakterlerini atar, boşlukları sadeleştirir ve uzunluğu sınırlar."""
    s = re.sub(r"[\x00-\x1f\x7f]", " ", str(sorgu or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:MAKS_SORGU_UZUNLUGU]


def _html_temizle(metin: str) -> str:
    metin = re.sub(r"<[^>]+>", " ", metin or "")
    metin = (metin.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&#39;", "'").replace("\ufffd", "-"))
    return re.sub(r"\s+", " ", metin).strip()


def _yil_ayikla(ham: Dict[str, object]) -> Optional[int]:
    for pub in ham.get("publications") or []:
        tarih = str((pub or {}).get("publicationDate") or "")
        if len(tarih) >= 4 and tarih[:4].isdigit():
            return int(tarih[:4])
    for anahtar in ("distributionDate", "submittedDate", "created"):
        tarih = str(ham.get(anahtar) or "")
        if len(tarih) >= 4 and tarih[:4].isdigit():
            return int(tarih[:4])
    return None


def ham_kaydi_normalize_et(ham: Dict[str, object]) -> Optional[NtrsKaydi]:
    """NTRS API'nin ham JSON kaydını güvenli biçimde NtrsKaydi nesnesine dönüştürür."""
    try:
        ntrs_id = ntrs_id_dogrula(ham.get("id"))
    except NtrsHatasi:
        return None

    yazarlar: List[str] = []
    kurumlar: List[str] = []
    for aff in sorted(ham.get("authorAffiliations") or [], key=lambda a: (a or {}).get("sequence", 0)):
        meta = (aff or {}).get("meta") or {}
        ad = ((meta.get("author") or {}).get("name") or "").strip()
        kurum = ((meta.get("organization") or {}).get("name") or "").strip()
        if ad and ad not in yazarlar:
            yazarlar.append(ad)
        if kurum and kurum not in kurumlar:
            kurumlar.append(kurum)

    merkez = ""
    if isinstance(ham.get("center"), dict):
        merkez = str(ham["center"].get("name") or "")

    yayin_adi = ""
    for pub in ham.get("publications") or []:
        if (pub or {}).get("publicationName"):
            yayin_adi = str(pub["publicationName"])
            break

    indirmeler = ham.get("downloads") or []
    pdf_var = any(((d or {}).get("links") or {}).get("pdf") for d in indirmeler)
    tam_metin_yolu = ""
    for d in indirmeler:
        aday = str((((d or {}).get("links") or {}).get("fulltext")) or "")
        if aday and _tam_metin_yolu_guvenli_mi(ntrs_id, aday):
            tam_metin_yolu = aday
            break
    tam_metin_var = bool(tam_metin_yolu)

    anahtar = ham.get("keywords") or []
    if not isinstance(anahtar, list):
        anahtar = []

    return NtrsKaydi(
        ntrs_id=ntrs_id,
        baslik=_html_temizle(str(ham.get("title") or "Başlıksız NTRS kaydı")),
        ozet=_html_temizle(str(ham.get("abstract") or "")),
        yazarlar=yazarlar[:25],
        kurumlar=kurumlar[:15],
        yil=_yil_ayikla(ham),
        merkez=merkez,
        belge_turu=str(ham.get("stiType") or ""),
        yayin_adi=_html_temizle(yayin_adi),
        konu_kategorileri=[str(k) for k in (ham.get("subjectCategories") or [])][:10],
        anahtar_kelimeler=[_html_temizle(str(k)) for k in anahtar][:20],
        pdf_var=bool(pdf_var),
        tam_metin_var=bool(tam_metin_var),
        tam_metin_yolu=tam_metin_yolu,
    )


def _tam_metin_yolu_guvenli_mi(ntrs_id: str, yol: str) -> bool:
    """Tam metin yolunun yalnızca ilgili kaydın indirme klasörünü gösterdiğini doğrular (path traversal koruması)."""
    on_ek = f"/api/citations/{ntrs_id}/downloads/"
    if not yol.startswith(on_ek) or ".." in yol or "?" in yol or "#" in yol:
        return False
    dosya = urllib.parse.unquote(yol[len(on_ek):])
    return bool(re.match(r"^[\w .()\-]{1,200}\.txt$", dosya)) and "/" not in dosya and "\\" not in dosya


# =============================================================================
# İstemci
# =============================================================================
class NtrsIstemcisi:
    """NASA NTRS herkese açık API'si için hız sınırlı, güvenli ve salt-okunur istemci."""

    def __init__(self, zaman_asimi: int = VARSAYILAN_ZAMAN_ASIMI, min_istek_araligi_sn: float = 0.35) -> None:
        self.zaman_asimi = zaman_asimi
        self.min_istek_araligi_sn = min_istek_araligi_sn
        self._son_istek = 0.0
        self._kilit = threading.Lock()

    # ---- düşük seviye -------------------------------------------------------
    def _bekle(self) -> None:
        with self._kilit:
            gecen = time.monotonic() - self._son_istek
            if gecen < self.min_istek_araligi_sn:
                time.sleep(self.min_istek_araligi_sn - gecen)
            self._son_istek = time.monotonic()

    def _get(self, url: str, maks_bayt: int, kabul: str = "application/json") -> bytes:
        ayr = urllib.parse.urlparse(url)
        if ayr.scheme != "https" or ayr.hostname != NTRS_IZINLI_HOST:
            raise NtrsHatasi("Güvenlik: Yalnızca https://ntrs.nasa.gov adresine istek yapılabilir.")
        self._bekle()
        istek = urllib.request.Request(url, headers={"User-Agent": KULLANICI_AJANI, "Accept": kabul})
        try:
            with urllib.request.urlopen(istek, timeout=self.zaman_asimi) as yanit:
                veri = yanit.read(maks_bayt + 1)
        except urllib.error.HTTPError as exc:
            raise NtrsHatasi(f"NTRS HTTP hatası {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise NtrsHatasi(f"NTRS'e bağlanılamadı (internet bağlantısını kontrol edin): {exc.reason}") from exc
        except TimeoutError as exc:
            raise NtrsHatasi("NTRS isteği zaman aşımına uğradı.") from exc
        if len(veri) > maks_bayt:
            raise NtrsHatasi("NTRS yanıtı izin verilen boyut sınırını aştı.")
        return veri

    # ---- yüksek seviye ------------------------------------------------------
    def ara(self, sorgu: str, sayfa_boyutu: int = 25, baslangic: int = 0) -> Tuple[int, List[NtrsKaydi]]:
        """NTRS'de arama yapar. (toplam_sonuc_sayisi, kayıtlar) döndürür."""
        temiz = sorgu_temizle(sorgu)
        if not temiz:
            return 0, []
        parametreler = {
            "q": temiz,
            "page.size": max(1, min(int(sayfa_boyutu), 100)),
            "page.from": max(0, int(baslangic)),
        }
        url = NTRS_API_ARAMA + "?" + urllib.parse.urlencode(parametreler)
        try:
            veri = json.loads(self._get(url, MAKS_YANIT_BAYT).decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise NtrsHatasi("NTRS geçersiz JSON döndürdü.") from exc
        toplam = int(((veri.get("stats") or {}).get("total")) or 0)
        kayitlar = [k for k in (ham_kaydi_normalize_et(h) for h in veri.get("results") or []) if k]
        return toplam, kayitlar

    def kayit_getir(self, ntrs_id: str) -> Optional[NtrsKaydi]:
        guvenli = ntrs_id_dogrula(ntrs_id)
        url = f"{NTRS_TABAN_URL}/api/citations/{guvenli}"
        veri = json.loads(self._get(url, MAKS_YANIT_BAYT).decode("utf-8", errors="replace"))
        return ham_kaydi_normalize_et(veri)

    def tam_metin_getir(self, ntrs_id: str, onbellek_kullan: bool = True, tam_metin_yolu: str = "") -> str:
        """Yayının NTRS tarafından sağlanan düz metin (.txt) sürümünü indirir ve yerel olarak önbelleğe alır."""
        guvenli = ntrs_id_dogrula(ntrs_id)
        yerel = os.path.join(TAM_METIN_KLASORU, f"{guvenli}.txt")
        if onbellek_kullan and os.path.isfile(yerel):
            with open(yerel, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        if tam_metin_yolu:
            if not _tam_metin_yolu_guvenli_mi(guvenli, tam_metin_yolu):
                raise NtrsHatasi("Güvenlik: Geçersiz tam metin yolu reddedildi.")
            url = NTRS_TABAN_URL + tam_metin_yolu
        else:
            url = f"{NTRS_TABAN_URL}/api/citations/{guvenli}/downloads/{guvenli}.txt"
        metin = self._get(url, MAKS_TAM_METIN_BAYT, kabul="text/plain").decode("utf-8", errors="replace")
        metin = re.sub(r"[ \t]+", " ", metin)
        os.makedirs(TAM_METIN_KLASORU, exist_ok=True)
        with open(yerel, "w", encoding="utf-8") as f:
            f.write(metin)
        return metin


# =============================================================================
# Yerel korpus (önbellek) yönetimi
# =============================================================================
def korpus_yukle(yol: str = KORPUS_DOSYASI) -> Tuple[Dict[str, object], List[NtrsKaydi]]:
    """Yerel NTRS korpusunu yükler. Dosya yoksa boş korpus döner (uygulama çökmez)."""
    if not os.path.isfile(yol):
        return {"olusturma_zamani": None, "sorgular": [], "kayit_sayisi": 0}, []
    with open(yol, "r", encoding="utf-8") as f:
        veri = json.load(f)
    kayitlar: List[NtrsKaydi] = []
    for d in veri.get("kayitlar", []):
        try:
            k = NtrsKaydi.sozlukten(d)
            ntrs_id_dogrula(k.ntrs_id)
            kayitlar.append(k)
        except (TypeError, NtrsHatasi):
            continue
    meta = {k: v for k, v in veri.items() if k != "kayitlar"}
    meta["kayit_sayisi"] = len(kayitlar)
    return meta, kayitlar


def korpus_kaydet(kayitlar: Iterable[NtrsKaydi], sorgular: List[str], yol: str = KORPUS_DOSYASI) -> str:
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    liste = list(kayitlar)
    veri = {
        "kaynak": "NASA Technical Reports Server (NTRS) public API - https://ntrs.nasa.gov/api",
        "olusturma_zamani": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sorgular": sorgular,
        "kayit_sayisi": len(liste),
        "kayitlar": [k.sozluge() for k in liste],
    }
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    os.replace(gecici, yol)  # atomik yazım: yarım kalmış dosya oluşmaz
    return yol


def kayitlari_birlestir(mevcut: List[NtrsKaydi], yeni: List[NtrsKaydi]) -> List[NtrsKaydi]:
    """Aynı NTRS kimliğine sahip kayıtları tekilleştirir, sorgu etiketlerini birleştirir."""
    sozluk: Dict[str, NtrsKaydi] = {k.ntrs_id: k for k in mevcut}
    for k in yeni:
        if k.ntrs_id in sozluk:
            eski = sozluk[k.ntrs_id]
            for etiket in k.sorgu_etiketleri:
                if etiket not in eski.sorgu_etiketleri:
                    eski.sorgu_etiketleri.append(etiket)
        else:
            sozluk[k.ntrs_id] = k
    return list(sozluk.values())
