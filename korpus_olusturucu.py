# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026 - "Flame in Freefall"
Modül: Gerçek NTRS Literatür Korpusu Oluşturucu

Kullanım:
    python korpus_olusturucu.py              # korpusu oluşturur / günceller
    python korpus_olusturucu.py --tam-metin  # ayrıca önemli yayınların tam metnini indirir

Bu betik NASA NTRS API'sinde mikroçekim yanma ve uzay aracı yangın güvenliği konularında
önceden tanımlı, yarışma kapsamıyla birebir örtüşen sorguları çalıştırır ve sonuçları
veri/ntrs_korpus.json dosyasına kaydeder. Uygulama çevrimdışıyken bu korpusu kullanır.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

from ntrs_istemcisi import (
    NtrsHatasi,
    NtrsIstemcisi,
    NtrsKaydi,
    korpus_kaydet,
    korpus_yukle,
    kayitlari_birlestir,
)

# (Sorgu, etiket, sayfa sayısı) — Challenge kaynak listesinde geçen deneyler önceliklidir.
KORPUS_SORGULARI: List[Tuple[str, str, int]] = [
    ("BASS burning suppression solids", "BASS", 1),
    ("BASS-II", "BASS", 1),
    ("FLEX flame extinguishment experiment", "FLEX", 1),
    ("FLEX droplet ISS", "FLEX", 1),
    ("cool flame", "COOL_FLAME", 1),
    ("cool flame droplet", "COOL_FLAME", 1),
    ("Saffire spacecraft fire", "SAFFIRE", 1),
    ("Saffire", "SAFFIRE", 1),
    ("ACME advanced combustion microgravity", "ACME", 1),
    ("SoFIE solid fuel ignition extinction", "SOFIE", 1),
    ("SPICE smoke point coflow", "SPICE", 1),
    ("smoke point microgravity", "SPICE", 1),
    ("droplet combustion microgravity", "DROPLET", 2),
    ("flame spread microgravity", "FLAME_SPREAD", 2),
    ("material flammability microgravity", "FLAMMABILITY", 1),
    ("NASA-STD-6001 flammability", "FLAMMABILITY", 1),
    ("limiting oxygen index microgravity", "FLAMMABILITY", 1),
    ("partial gravity flame", "PARTIAL_GRAVITY", 1),
    ("lunar gravity flammability", "PARTIAL_GRAVITY", 1),
    ("Mars gravity combustion", "PARTIAL_GRAVITY", 1),
    ("spacecraft fire safety", "FIRE_SAFETY", 2),
    ("spacecraft fire detection", "DETECTION", 1),
    ("smoke detection spacecraft", "DETECTION", 1),
    ("smoke particulate microgravity", "DETECTION", 1),
    ("fire suppression microgravity", "SUPPRESSION", 1),
    ("water mist fire suppression spacecraft", "SUPPRESSION", 1),
    ("extinction microgravity flame", "EXTINCTION", 1),
    ("soot microgravity flame", "SOOT", 1),
    ("smoldering microgravity", "SMOLDER", 1),
    ("exploration atmosphere flammability oxygen", "EXPLORATION_ATM", 1),
    ("microgravity combustion", "GENERAL", 2),
    ("lithium ion battery fire spacecraft", "BATTERY", 1),
]

# Tam metni indirilecek öncelikli etiketler (sayısal bulgu çıkarımı için)
TAM_METIN_ETIKETLERI = {"BASS", "FLEX", "COOL_FLAME", "SAFFIRE", "ACME", "SOFIE", "SPICE", "PARTIAL_GRAVITY", "DETECTION"}


def korpusu_olustur(tam_metin: bool = False, sayfa_boyutu: int = 50, maks_tam_metin: int = 60,
                    sifirdan: bool = False) -> int:
    istemci = NtrsIstemcisi()
    mevcut: List[NtrsKaydi] = [] if sifirdan else korpus_yukle()[1]
    toplanan: List[NtrsKaydi] = list(mevcut)
    basarili_sorgular: List[str] = []

    for sorgu, etiket, sayfa_sayisi in KORPUS_SORGULARI:
        for sayfa in range(sayfa_sayisi):
            try:
                toplam, kayitlar = istemci.ara(sorgu, sayfa_boyutu=sayfa_boyutu, baslangic=sayfa * sayfa_boyutu)
            except NtrsHatasi as exc:
                print(f"  [!] '{sorgu}' sorgusu başarısız: {exc}")
                break
            for k in kayitlar:
                k.sorgu_etiketleri = [etiket]
            toplanan = kayitlari_birlestir(toplanan, kayitlar)
            print(f"  [+] {sorgu!r:55s} sayfa {sayfa + 1}: {len(kayitlar):3d} kayıt (NTRS toplam: {toplam})")
            if sorgu not in basarili_sorgular:
                basarili_sorgular.append(sorgu)
            if (sayfa + 1) * sayfa_boyutu >= toplam:
                break

    # Özeti olmayan kayıtlar AI analizi için değersizdir; yine de başlık bilgisi için tutulur.
    yol = korpus_kaydet(toplanan, basarili_sorgular)
    print(f"\n[OK] {len(toplanan)} benzersiz gerçek NTRS kaydı kaydedildi -> {yol}")

    if tam_metin:
        adaylar = [k for k in toplanan if k.tam_metin_var and set(k.sorgu_etiketleri) & TAM_METIN_ETIKETLERI]
        adaylar.sort(key=lambda k: (k.yil or 0), reverse=True)
        indirilen = 0
        for k in adaylar[:maks_tam_metin]:
            try:
                metin = istemci.tam_metin_getir(k.ntrs_id, tam_metin_yolu=k.tam_metin_yolu)
                indirilen += 1
                print(f"  [txt] {k.ntrs_id} ({len(metin) // 1024} KB) {k.baslik[:70]}")
            except NtrsHatasi as exc:
                print(f"  [!] Tam metin alınamadı {k.ntrs_id}: {exc}")
        print(f"[OK] {indirilen} tam metin önbelleğe alındı.")
    return len(toplanan)


if __name__ == "__main__":
    ayr = argparse.ArgumentParser(description="Gerçek NASA NTRS mikroçekim yanma korpusu oluşturucu")
    ayr.add_argument("--tam-metin", action="store_true", help="Öncelikli yayınların tam metnini de indir")
    ayr.add_argument("--maks-tam-metin", type=int, default=60)
    ayr.add_argument("--sifirdan", action="store_true", help="Mevcut korpusu yok sayıp baştan oluştur")
    arg = ayr.parse_args()
    try:
        korpusu_olustur(tam_metin=arg.tam_metin, maks_tam_metin=arg.maks_tam_metin, sifirdan=arg.sifirdan)
    except KeyboardInterrupt:
        print("\nKullanıcı tarafından durduruldu.")
        sys.exit(1)
