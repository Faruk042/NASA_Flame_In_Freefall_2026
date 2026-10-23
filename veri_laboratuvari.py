# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall"
Modül: Deney Verisi Laboratuvarı (gerçek NASA PSI / kullanıcı CSV verisi için)

Yetenekler (harici bağımlılık yok, saf Python):
  • CSV'yi salt-okunur, boyut sınırlı ve güvenli biçimde yükleme; sayısal sütunları otomatik algılama
  • d²-yasası regresyonu: d²(t) = d0² − K·t  ->  K, d0, R², RMSE, %95 güven aralığı, artıklar
  • Yarı-ampirik model ile literatür karşılaştırması (korpustan çıkarılan gerçek K değerleri)
  • Sağlam (MAD tabanlı) anomali tespiti ve Pearson korelasyonu
  • Açıkça "SENTETİK DEMO" etiketli örnek veri üretimi (gerçek veri yokken yöntemi göstermek için)

Gerçek veri kaynağı: NASA Physical Sciences Informatics (https://psi.nasa.gov) — ücretsiz kayıt ile
BASS, FLEX, ACME vb. deney veri setleri indirilebilir ve bu modüle CSV olarak verilebilir.
"""

from __future__ import annotations

import csv
import io
import math
import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

MAKS_CSV_BAYT = 25 * 1024 * 1024
MAKS_SATIR = 500_000

# Student-t %97.5 kritik değerleri (iki yönlü %95) — küçük örneklemler için
_T_TABLOSU = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262,
              10: 2.228, 12: 2.179, 15: 2.131, 20: 2.086, 25: 2.060, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980}


def t_kritik(sd: int) -> float:
    if sd <= 0:
        return float("nan")
    for k in sorted(_T_TABLOSU):
        if sd <= k:
            return _T_TABLOSU[k]
    return 1.96


@dataclass
class VeriSeti:
    ad: str
    sutunlar: List[str]
    veri: Dict[str, List[float]]
    sentetik: bool = False
    aciklama: str = ""

    def satir_sayisi(self) -> int:
        return min((len(v) for v in self.veri.values()), default=0)


@dataclass
class D2Uyumu:
    K_mm2_s: float
    d0_kare_mm2: float
    r2: float
    rmse: float
    n: int
    K_guven_araligi: Tuple[float, float]
    artiklar: List[float] = field(default_factory=list)
    t_baslangic: float = 0.0
    t_bitis: float = 0.0

    @property
    def d0_mm(self) -> float:
        return math.sqrt(max(self.d0_kare_mm2, 0.0))

    @property
    def tahmini_yanma_suresi_s(self) -> float:
        return self.d0_kare_mm2 / self.K_mm2_s if self.K_mm2_s > 0 else float("inf")


class VeriYuklemeHatasi(ValueError):
    pass


# =============================================================================
# CSV yükleme
# =============================================================================
def csv_bayttan_yukle(icerik: bytes, ad: str = "yuklenen.csv") -> VeriSeti:
    """Bellekteki CSV içeriğini güvenle ayrıştırır (dosya sistemine yazmaz)."""
    if len(icerik) > MAKS_CSV_BAYT:
        raise VeriYuklemeHatasi(f"Dosya çok büyük (> {MAKS_CSV_BAYT // (1024 * 1024)} MB).")
    metin = icerik.decode("utf-8-sig", errors="replace")
    ornek = metin[:8192]
    try:
        lehce = csv.Sniffer().sniff(ornek, delimiters=",;\t ")
        ayirici = lehce.delimiter
    except csv.Error:
        ayirici = ","
    okuyucu = csv.reader(io.StringIO(metin), delimiter=ayirici)
    satirlar: List[List[str]] = []
    for i, s in enumerate(okuyucu):
        if i > MAKS_SATIR:
            break
        if s and not (len(s) == 1 and not s[0].strip()):
            satirlar.append(s)
    # Yorum / üst bilgi satırlarını atla: ilk "çoğunlukla sayısal" satırın bir üstü başlıktır
    baslik_idx = 0
    for i, s in enumerate(satirlar[:60]):
        sayisal = sum(1 for h in s if _sayiya_cevir(h) is not None)
        if s and sayisal >= max(2, int(0.6 * len(s))):
            baslik_idx = max(0, i - 1)
            break
    if len(satirlar) - baslik_idx < 3:
        raise VeriYuklemeHatasi("CSV'de yeterli veri satırı yok.")
    basliklar_ham = satirlar[baslik_idx]
    ilk_veri_baslik_mi = sum(1 for h in basliklar_ham if _sayiya_cevir(h) is not None) >= max(2, int(0.6 * len(basliklar_ham)))
    if ilk_veri_baslik_mi:
        basliklar = [f"Sutun_{i + 1}" for i in range(len(basliklar_ham))]
        veri_satirlari = satirlar[baslik_idx:]
    else:
        basliklar = [_baslik_temizle(h, i) for i, h in enumerate(basliklar_ham)]
        veri_satirlari = satirlar[baslik_idx + 1:]
    gecici: Dict[str, List[Optional[float]]] = {b: [] for b in basliklar}
    for s in veri_satirlari:
        for i, b in enumerate(basliklar):
            gecici[b].append(_sayiya_cevir(s[i]) if i < len(s) else None)
    sayisal_sutunlar = [b for b, l in gecici.items() if sum(1 for x in l if x is not None) >= max(3, 0.5 * len(l))]
    if not sayisal_sutunlar:
        raise VeriYuklemeHatasi("Sayısal sütun bulunamadı.")
    # Eksik değer içeren satırları ortak olarak at (hizalı seriler)
    temiz: Dict[str, List[float]] = {b: [] for b in sayisal_sutunlar}
    for idx in range(len(veri_satirlari)):
        degerler = [gecici[b][idx] for b in sayisal_sutunlar]
        if all(v is not None and math.isfinite(v) for v in degerler):
            for b, v in zip(sayisal_sutunlar, degerler):
                temiz[b].append(float(v))
    return VeriSeti(ad=ad, sutunlar=sayisal_sutunlar, veri=temiz)


def _baslik_temizle(h: str, i: int) -> str:
    h = re.sub(r"[\x00-\x1f]", "", (h or "").strip())[:60]
    return h or f"Sutun_{i + 1}"


def _sayiya_cevir(s: str) -> Optional[float]:
    s = (s or "").strip().replace("\u2212", "-")
    if not s:
        return None
    if re.match(r"^-?\d+,\d+$", s):  # Avrupa ondalık virgülü
        s = s.replace(",", ".")
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except ValueError:
        return None


def sutun_rolu_tahmin_et(sutunlar: Sequence[str]) -> Dict[str, Optional[str]]:
    """Zaman ve çap / çap² sütunlarını başlık adından tahmin eder."""
    def bul(desen: str) -> Optional[str]:
        for s in sutunlar:
            if re.search(desen, s, re.I):
                return s
        return None
    return {
        "zaman": bul(r"^t$|time|zaman|sure|süre|\bsec|\(s\)"),
        "cap_kare": bul(r"d\^?2|d²|d_?sq|diameter.?sq|cap.?kare|çap.?kare|d2\b"),
        "cap": bul(r"^d$|diam|çap|cap\b|\bd\s*\(mm\)|droplet"),
    }


# =============================================================================
# d²-yasası regresyonu
# =============================================================================
def dogrusal_regresyon(x: Sequence[float], y: Sequence[float]) -> Tuple[float, float, float, float, float]:
    """(eğim, kesişim, R², RMSE, eğim_standart_hatası) döndürür."""
    n = len(x)
    if n < 3:
        raise ValueError("Regresyon için en az 3 nokta gerekir.")
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx == 0:
        raise ValueError("Zaman ekseninde varyans yok.")
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    egim = sxy / sxx
    kesisim = my - egim * mx
    tahmin = [kesisim + egim * xi for xi in x]
    sse = sum((yi - ti) ** 2 for yi, ti in zip(y, tahmin))
    sst = sum((yi - my) ** 2 for yi in y)
    r2 = 1 - sse / sst if sst > 0 else 0.0
    rmse = math.sqrt(sse / n)
    se_egim = math.sqrt(sse / (n - 2) / sxx) if n > 2 else float("nan")
    return egim, kesisim, r2, rmse, se_egim


def d2_yasasi_uydur(zaman_s: Sequence[float], cap_veya_cap_kare: Sequence[float], girdi_cap_kare: bool = False,
                    baslangic_atla_orani: float = 0.0, bitis_atla_orani: float = 0.0) -> D2Uyumu:
    """
    d² = d0² − K·t doğrusal uyumu. Tutuşma geçişi ve son faz genellikle doğrusal olmadığından
    baştan/sondan belirli bir oran atlanabilir (yaygın uygulama).
    """
    cift = [(float(t), float(d)) for t, d in zip(zaman_s, cap_veya_cap_kare)
            if math.isfinite(t) and math.isfinite(d) and d > 0]
    cift.sort()
    n0 = len(cift)
    bas = int(n0 * max(0.0, min(baslangic_atla_orani, 0.45)))
    son = n0 - int(n0 * max(0.0, min(bitis_atla_orani, 0.45)))
    cift = cift[bas:son]
    if len(cift) < 3:
        raise ValueError("d² uyumu için yeterli geçerli nokta yok.")
    t = [c[0] for c in cift]
    d2 = [c[1] if girdi_cap_kare else c[1] ** 2 for c in cift]
    egim, kesisim, r2, rmse, se = dogrusal_regresyon(t, d2)
    K = -egim
    tk = t_kritik(len(t) - 2)
    ga = (K - tk * se, K + tk * se) if math.isfinite(se) else (float("nan"), float("nan"))
    artik = [yi - (kesisim + egim * ti) for ti, yi in zip(t, d2)]
    return D2Uyumu(K_mm2_s=round(K, 5), d0_kare_mm2=round(kesisim, 5), r2=round(r2, 5), rmse=round(rmse, 5),
                   n=len(t), K_guven_araligi=(round(ga[0], 5), round(ga[1], 5)), artiklar=artik,
                   t_baslangic=t[0], t_bitis=t[-1])


# =============================================================================
# İstatistik & anomali
# =============================================================================
def pearson(x: Sequence[float], y: Sequence[float]) -> float:
    n = min(len(x), len(y))
    if n < 3:
        return 0.0
    x, y = list(x[:n]), list(y[:n])
    mx, my = sum(x) / n, sum(y) / n
    pay = sum((a - mx) * (b - my) for a, b in zip(x, y))
    px = math.sqrt(sum((a - mx) ** 2 for a in x))
    py = math.sqrt(sum((b - my) ** 2 for b in y))
    return round(pay / (px * py), 4) if px > 0 and py > 0 else 0.0


def saglam_anomali_tespiti(degerler: Sequence[float], esik: float = 3.5) -> List[Tuple[int, float, float]]:
    """Medyan mutlak sapma (MAD) tabanlı modifiye Z-skoru (Iglewicz & Hoaglin). (indeks, değer, z) listesi."""
    n = len(degerler)
    if n < 5:
        return []
    sirali = sorted(degerler)
    medyan = sirali[n // 2] if n % 2 else 0.5 * (sirali[n // 2 - 1] + sirali[n // 2])
    sapmalar = sorted(abs(v - medyan) for v in degerler)
    mad = sapmalar[n // 2] if n % 2 else 0.5 * (sapmalar[n // 2 - 1] + sapmalar[n // 2])
    if mad == 0:
        return []
    sonuc = []
    for i, v in enumerate(degerler):
        z = 0.6745 * (v - medyan) / mad
        if abs(z) > esik:
            sonuc.append((i, v, round(z, 2)))
    return sonuc


def ozet_istatistik(degerler: Sequence[float]) -> Dict[str, float]:
    n = len(degerler)
    if n == 0:
        return {"n": 0}
    ort = sum(degerler) / n
    std = math.sqrt(sum((v - ort) ** 2 for v in degerler) / (n - 1)) if n > 1 else 0.0
    s = sorted(degerler)
    return {"n": n, "ortalama": ort, "std": std, "min": s[0], "medyan": s[n // 2], "maks": s[-1]}


# =============================================================================
# Açıkça etiketli SENTETİK demo veri
# =============================================================================
def sentetik_damlacik_verisi(K: float = 0.65, d0_mm: float = 3.0, gurultu_mm2: float = 0.08,
                             tutusma_s: float = 0.4, tohum: int = 7) -> VeriSeti:
    """
    YÖNTEM GÖSTERİMİ İÇİN SENTETİK VERİ. Gerçek bir NASA ölçümü DEĞİLDİR.
    d² yasası + Gauss gürültüsü + kısa tutuşma geçişi ile üretilir.
    """
    rnd = random.Random(tohum)
    tb = d0_mm ** 2 / K
    t_list, d_list, d2_list = [], [], []
    adim = tb / 80
    t = 0.0
    while t <= tb * 0.97:
        if t < tutusma_s:
            d2 = d0_mm ** 2 * (1 + 0.02 * math.sin(t * 8))  # tutuşma sırasında hafif ısıl genleşme
        else:
            d2 = d0_mm ** 2 - K * (t - tutusma_s * 0.5)
        d2 = max(0.01, d2 + rnd.gauss(0, gurultu_mm2))
        t_list.append(round(t, 4))
        d2_list.append(round(d2, 5))
        d_list.append(round(math.sqrt(d2), 5))
        t += adim
    return VeriSeti(
        ad="SENTETİK_DEMO_damlacik_d2.csv", sutunlar=["Zaman_s", "Cap_mm", "Cap_kare_mm2"],
        veri={"Zaman_s": t_list, "Cap_mm": d_list, "Cap_kare_mm2": d2_list}, sentetik=True,
        aciklama=f"Sentetik: K={K} mm²/s, d0={d0_mm} mm, σ={gurultu_mm2} mm² (gerçek ölçüm değildir)")


def veri_setini_csv_metnine_cevir(vs: VeriSeti) -> str:
    cikti = io.StringIO()
    w = csv.writer(cikti)
    w.writerow(vs.sutunlar)
    for i in range(vs.satir_sayisi()):
        w.writerow([vs.veri[s][i] for s in vs.sutunlar])
    return cikti.getvalue()
