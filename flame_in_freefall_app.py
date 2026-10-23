# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026
"Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"
Ana Uygulama (flame_in_freefall_app.py)

Tam ekran (Maximized) çalışan, %100 kanıt-odaklı (Evidence-First), 6 uzman sekmeli
Mikroçekim & Kısmi Yerçekimi (0g / Ay 0.16g / Mars 0.38g) Yangın Güvenliği ve Karar Destek Platformu.
"""

import math
import os
import sys
import threading
import webbrowser
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import customtkinter as ctk

from ai_uzman_asistan import FlameInFreefallAIEngine
from mikroyercekimi_fizik_motoru import MikroYercekimiFizikMotoru
from nasa_ntrs_psi_veri_avcisi import NasaTelemetriVeVeriAvcisi
from nasa_psi_veritabani import (
    ARASTIRMA_BOSLUKLARI,
    BILGI_GRAFIGI_BAGLANTILARI,
    BILGI_GRAFIGI_DUGUMLERI,
    KanitOdakliAramaMotoru,
    NASA_PSI_DENEY_ARSIVI,
    NasaDeneyKaydi,
    UZAY_MALZEME_ATLASI,
)
from optik_alev_goruntu_analizoru import OptikAlevGoruntuAnalizoru, PIL_AVAILABLE

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_DARK = "#050914"
PANEL_BG = "#0D1627"
CARD_BG = "#111D33"
BORDER_CLR = "#1E293B"
NEON_CYAN = "#00F5D4"
NEON_GOLD = "#FFD166"
NEON_PINK = "#FF3366"
NEON_BLUE = "#38BDF8"
NEON_PURPLE = "#C084FC"


class FlameInFreefallApp(ctk.CTk):
    """
    NASA Space Apps 2026 - Flame in Freefall Ana Komuta Arayüzü.
    Ollama bağımlılığı içermez; sıfır donma ve düşük RAM tüketimi ile çalışır.
    """

    def __init__(self) -> None:
        super().__init__()
        self.title("🚀 NASA Space Apps 2026 — Flame in Freefall: Microgravity Fire Safety & AI Insights")
        self.geometry("1360x840")
        self.minsize(1100, 700)
        self.configure(fg_color=BG_DARK)

        # Çekirdek Motorlar
        self.arama_motoru = KanitOdakliAramaMotoru()
        self.ai_motoru = FlameInFreefallAIEngine()

        # Simülasyon Durum Değişkenleri
        self.sim_calisiyor = False
        self.su_sisi_aktif = False
        self.sim_zaman_sn = 0.0
        self.sim_faz = 0.0

        # Telemetri, Optik ve Dijital İkiz Veri Yapıları
        self.aktif_telemetri_adi = ""
        self.telemetri_sutunlar: List[str] = []
        self.telemetri_veri: Dict[str, List[float]] = {}
        self.eslesen_deney_bellek: Dict[str, NasaDeneyKaydi] = {k.kanit_id: k for k in NASA_PSI_DENEY_ARSIVI}
        self._optik_tk_img = None
        self.secili_kg_dugum_id = "FLEX_2"
        self.kabin_yangin_xy: Tuple[float, float] = (0.30, 0.58)
        self._kg_kutu_koordinatlari: Dict[str, Tuple[int, int, int, int]] = {}

        self._arayuz_kur()
        self.update_idletasks()
        self.after(60, self._tam_ekran_yap)
        self.after(200, self._baslangic_verilerini_yukle)
        self.after(1000, self._sistem_telemetri_guncelle)

    def _tam_ekran_yap(self) -> None:
        try:
            if self.winfo_exists():
                self.state("zoomed")
        except Exception:
            pass

    def _baslangic_verilerini_yukle(self) -> None:
        self._sim_etiket_ve_cizim_yenile()
        self._psi_tabloyu_yenile()
        self._malzeme_atlasi_yenile()
        self._hazir_telemetri_yukle("FLEX")
        self._bosluk_matrisi_ciz()
        self._sentetik_alev_goruntusu_yukle(OptikAlevGoruntuAnalizoru.SENTETIK_SENARYOLAR[1])
        self._kg_ve_kabin_ikizi_ciz()

    # =========================================================================
    # ÜST BAR VE 8 SEKMELİ ANA İSKELET KURULUMU
    # =========================================================================
    def _arayuz_kur(self) -> None:
        ust_bar = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=10, border_width=1, border_color=BORDER_CLR)
        ust_bar.pack(side="top", fill="x", padx=12, pady=(8, 4))

        # Sağ üstteki sistem bellek göstergesi ve butonlar İLK paketlenir (Hiçbir ekranda kırpılmaz)
        sag_bar = ctk.CTkFrame(ust_bar, fg_color="transparent")
        sag_bar.pack(side="right", padx=12, pady=8)

        self.lbl_sistem_ram = ctk.CTkLabel(
            sag_bar,
            text="CPU: %0 | Uygulama RAM: 0 MB",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#00FF88"
        )
        self.lbl_sistem_ram.pack(side="right", padx=(10, 4))

        ctk.CTkButton(
            sag_bar,
            text="🌐 HTML Jüri Sunumu",
            width=150,
            height=30,
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.interaktif_html_juri_sunumu_olustur
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            sag_bar,
            text="💾 Rapor Kaydet (.md)",
            width=142,
            height=30,
            fg_color="#00A86B",
            hover_color="#007F50",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.juri_raporunu_dosyaya_kaydet
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            sag_bar,
            text="🔑 Gemini API",
            width=105,
            height=30,
            fg_color="#374151",
            hover_color="#1F2937",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._api_anahtar_penceresi_ac
        ).pack(side="right", padx=4)

        sol_baslik = ctk.CTkFrame(ust_bar, fg_color="transparent")
        sol_baslik.pack(side="left", padx=14, pady=6)

        ctk.CTkLabel(
            sol_baslik,
            text="🔥 FLAME IN FREEFALL: AI-POWERED MICROGRAVITY FIRE SAFETY PLATFORM",
            font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            text_color=NEON_CYAN
        ).pack(anchor="w")

        ctk.CTkLabel(
            sol_baslik,
            text="NASA Space Apps 2026 • PSI & NTRS Evidence-First • BASS-II • FLEX-2 Cool Flames • Saffire • ACME • SoFIE • Optical Vision & Cabin Digital Twin",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=NEON_GOLD
        ).pack(anchor="w", pady=(1, 0))

        # 8 Uzman Sekmeli Ana Gövde
        self.tabs = ctk.CTkTabview(self, fg_color=PANEL_BG, corner_radius=10)
        self.tabs.pack(side="top", fill="both", expand=True, padx=12, pady=(2, 10))

        self.tab_sim = self.tabs.add("🔥 1. 0G/Ay/Mars Alev Simülatörü")
        self.tab_psi = self.tabs.add("📚 2. NASA PSI & NTRS Kanıt Arama")
        self.tab_malzeme = self.tabs.add("🛡️ 3. Malzeme Yanıcılık Atlası")
        self.tab_telemetri = self.tabs.add("📈 4. Telemetri & Sonifikasyon")
        self.tab_bosluk = self.tabs.add("🔭 5. Araştırma Boşluğu (Gap)")
        self.tab_optik = self.tabs.add("📸 6. Optik Alev Görüntü Analizi")
        self.tab_ikiz = self.tabs.add("🛸 7. Bilgi Grafiği & Kabin İkizi")
        self.tab_ai = self.tabs.add("🤖 8. AI Karar & Jüri Raporu")

        self._kur_sekme_1_simulator()
        self._kur_sekme_2_psi_arama()
        self._kur_sekme_3_malzeme_atlasi()
        self._kur_sekme_4_telemetri_radari()
        self._kur_sekme_5_arastirma_boslugu()
        self._kur_sekme_6_optik_alev_analizi()
        self._kur_sekme_7_bilgi_grafigi_ve_kabin_ikizi()
        self._kur_sekme_6_ai_karar_merkezi()

    # =========================================================================
    # SEKME 1: CANLI 0G / AY / MARS ALEV & SOĞUK ALEV (COOL FLAME) SİMÜLATÖRÜ
    # =========================================================================
    def _kur_sekme_1_simulator(self) -> None:
        ust_kontrol = ctk.CTkFrame(self.tab_sim, fg_color=CARD_BG, corner_radius=8, border_width=1, border_color=BORDER_CLR)
        ust_kontrol.pack(side="top", fill="x", padx=8, pady=6)

        # Hızlı Yerçekimi ve Atmosfer Ön-Ayar Şeridi
        onayar_bar = ctk.CTkFrame(ust_kontrol, fg_color="transparent")
        onayar_bar.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            onayar_bar, text="🪐 Hızlı Ortam Seçimi:", font=ctk.CTkFont(size=12, weight="bold"), text_color=NEON_CYAN
        ).pack(side="left", padx=(2, 6))

        ortam_butonlari = [
            ("🛰️ ISS Mikroçekim (0.00g | %21 O2 | 101 kPa)", 0.00, 21.0, 101.3, 2.0),
            ("🟣 FLEX-2 Soğuk Alev (0.00g | d0=3.2mm | %19 O2)", 0.00, 19.0, 101.3, 0.5),
            ("🌙 Artemis Ay Kabini (0.16g | %34 O2 | 56.5 kPa)", 0.16, 34.0, 56.5, 6.0),
            ("🔴 Mars Habitatı (0.38g | %24 O2 | 70 kPa)", 0.38, 24.0, 70.0, 8.0),
            ("🌍 Dünya Laboratuvarı (1.00g | %21 O2 | 101 kPa)", 1.00, 21.0, 101.3, 5.0),
        ]
        for etiket, g_v, o2_v, p_v, u_v in ortam_butonlari:
            ctk.CTkButton(
                onayar_bar,
                text=etiket,
                height=26,
                fg_color="#1E3A8A",
                hover_color="#1D4ED8",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda g=g_v, o=o2_v, p=p_v, u=u_v: self._ortam_onayari_uygula(g, o, p, u)
            ).pack(side="left", padx=3)

        # Kaydırıcılar (Sliders) Grid
        slider_grid = ctk.CTkFrame(ust_kontrol, fg_color="transparent")
        slider_grid.pack(fill="x", padx=10, pady=(2, 8))
        for col in range(6):
            slider_grid.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(slider_grid, text="Yakıt Türü:", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, padx=4, pady=3, sticky="w"
        )
        self.sim_yakit_var = ctk.StringVar(value="n-Heptan (C7H16 - FLEX Referansı)")
        ctk.CTkOptionMenu(
            slider_grid,
            variable=self.sim_yakit_var,
            values=list(MikroYercekimiFizikMotoru.YAKIT_KATALOGU.keys()),
            width=220,
            height=26,
            command=lambda _: self._sim_etiket_ve_cizim_yenile()
        ).grid(row=1, column=0, padx=4, pady=3, sticky="ew")

        self.lbl_sim_g = ctk.CTkLabel(slider_grid, text="Yerçekimi: 0.00g", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=NEON_CYAN)
        self.lbl_sim_g.grid(row=0, column=1, padx=4, pady=3, sticky="w")
        self.slider_sim_g = ctk.CTkSlider(slider_grid, from_=0.0, to=1.0, number_of_steps=50, command=lambda _: self._sim_etiket_ve_cizim_yenile())
        self.slider_sim_g.set(0.0)
        self.slider_sim_g.grid(row=1, column=1, padx=4, pady=3, sticky="ew")

        self.lbl_sim_o2 = ctk.CTkLabel(slider_grid, text="Oksijen: %21.0", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=NEON_GOLD)
        self.lbl_sim_o2.grid(row=0, column=2, padx=4, pady=3, sticky="w")
        self.slider_sim_o2 = ctk.CTkSlider(slider_grid, from_=12.0, to=38.0, number_of_steps=52, command=lambda _: self._sim_etiket_ve_cizim_yenile())
        self.slider_sim_o2.set(21.0)
        self.slider_sim_o2.grid(row=1, column=2, padx=4, pady=3, sticky="ew")

        self.lbl_sim_basinc = ctk.CTkLabel(slider_grid, text="Basınç: 101.3 kPa", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"))
        self.lbl_sim_basinc.grid(row=0, column=3, padx=4, pady=3, sticky="w")
        self.slider_sim_basinc = ctk.CTkSlider(slider_grid, from_=35.0, to=120.0, number_of_steps=85, command=lambda _: self._sim_etiket_ve_cizim_yenile())
        self.slider_sim_basinc.set(101.3)
        self.slider_sim_basinc.grid(row=1, column=3, padx=4, pady=3, sticky="ew")

        self.lbl_sim_d0 = ctk.CTkLabel(slider_grid, text="Damlacık d₀: 3.0 mm", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#FF9F1C")
        self.lbl_sim_d0.grid(row=0, column=4, padx=4, pady=3, sticky="w")
        self.slider_sim_d0 = ctk.CTkSlider(slider_grid, from_=1.0, to=4.5, number_of_steps=35, command=lambda _: self._sim_etiket_ve_cizim_yenile())
        self.slider_sim_d0.set(3.0)
        self.slider_sim_d0.grid(row=1, column=4, padx=4, pady=3, sticky="ew")

        self.lbl_sim_akis = ctk.CTkLabel(slider_grid, text="Fan Akışı: 2.0 cm/s", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=NEON_BLUE)
        self.lbl_sim_akis.grid(row=0, column=5, padx=4, pady=3, sticky="w")
        self.slider_sim_akis = ctk.CTkSlider(slider_grid, from_=0.0, to=42.0, number_of_steps=42, command=lambda _: self._sim_etiket_ve_cizim_yenile())
        self.slider_sim_akis.set(2.0)
        self.slider_sim_akis.grid(row=1, column=5, padx=4, pady=3, sticky="ew")

        # Orta Çift Tuval Gövdesi
        orta_sim = ctk.CTkFrame(self.tab_sim, fg_color="transparent")
        orta_sim.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        orta_sim.grid_columnconfigure(0, weight=10, uniform="sim_split")
        orta_sim.grid_columnconfigure(1, weight=12, uniform="sim_split")
        orta_sim.grid_rowconfigure(0, weight=1)

        self.canvas_alev = tk.Canvas(orta_sim, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR)
        self.canvas_alev.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.canvas_alev.bind("<Configure>", lambda _: self._sim_ciz())

        self.canvas_grafik = tk.Canvas(orta_sim, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR)
        self.canvas_grafik.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.canvas_grafik.bind("<Configure>", lambda _: self._sim_ciz())

        # Alt Kontrol Butonları
        alt_sim_bar = ctk.CTkFrame(self.tab_sim, fg_color=CARD_BG, corner_radius=8)
        alt_sim_bar.pack(side="bottom", fill="x", padx=8, pady=(2, 6))

        self.btn_sim_oynat = ctk.CTkButton(
            alt_sim_bar, text="▶️ Canlı Simülasyonu Başlat", width=210, height=34,
            fg_color="#00A86B", hover_color="#007F50", font=ctk.CTkFont(size=13, weight="bold"),
            command=self._sim_oynat_durdur
        )
        self.btn_sim_oynat.pack(side="left", padx=8, pady=6)

        self.btn_su_sisi = ctk.CTkButton(
            alt_sim_bar, text="🚿 İnce Su Sisi (Fine Water Mist) Sık", width=240, height=34,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._su_sisi_tetikle
        )
        self.btn_su_sisi.pack(side="left", padx=4, pady=6)

        ctk.CTkButton(
            alt_sim_bar, text="🔄 Sıfırla", width=95, height=34,
            fg_color="#374151", hover_color="#1F2937", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._sim_sifirla
        ).pack(side="left", padx=4, pady=6)

        self.lbl_sim_durum = ctk.CTkLabel(
            alt_sim_bar, text="", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=NEON_CYAN
        )
        self.lbl_sim_durum.pack(side="left", padx=12)

        ctk.CTkButton(
            alt_sim_bar, text="🤖 Bu Deney Verilerini AI Karar Merkezine Gönder", width=310, height=34,
            fg_color="#C62828", hover_color="#8E0000", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._sim_verisini_ai_sekmesine_gonder
        ).pack(side="right", padx=8, pady=6)

    def _ortam_onayari_uygula(self, g_val: float, o2_val: float, p_val: float, u_val: float) -> None:
        self.slider_sim_g.set(g_val)
        self.slider_sim_o2.set(o2_val)
        self.slider_sim_basinc.set(p_val)
        self.slider_sim_akis.set(u_val)
        if g_val == 0.0 and o2_val == 19.0:
            self.slider_sim_d0.set(3.2)
            self.sim_yakit_var.set("n-Heptan (C7H16 - FLEX Referansı)")
        self._sim_sifirla()

    def _aktif_sim_sonucu_hesapla(self) -> Dict[str, object]:
        return MikroYercekimiFizikMotoru.damlacik_yanma_analizi(
            yakit_adi=self.sim_yakit_var.get(),
            yercekimi_g=float(self.slider_sim_g.get()),
            oksijen_yuzde=float(self.slider_sim_o2.get()),
            basinc_kpa=float(self.slider_sim_basinc.get()),
            d0_mm=float(self.slider_sim_d0.get()),
            akis_hizi_cm_s=float(self.slider_sim_akis.get()),
        )

    def _sim_etiket_ve_cizim_yenile(self) -> None:
        g_v = float(self.slider_sim_g.get())
        o2_v = float(self.slider_sim_o2.get())
        p_v = float(self.slider_sim_basinc.get())
        d0_v = float(self.slider_sim_d0.get())
        u_v = float(self.slider_sim_akis.get())

        rejim_ad = "0G ISS" if g_v < 0.05 else ("Ay" if g_v < 0.25 else ("Mars" if g_v < 0.50 else "Dünya"))
        self.lbl_sim_g.configure(text=f"Yerçekimi: {g_v:.2f}g ({rejim_ad})")
        self.lbl_sim_o2.configure(text=f"Oksijen: %{o2_v:.1f}")
        self.lbl_sim_basinc.configure(text=f"Basınç: {p_v:.1f} kPa")
        self.lbl_sim_d0.configure(text=f"Damlacık d₀: {d0_v:.1f} mm")
        self.lbl_sim_akis.configure(text=f"Fan Akışı: {u_v:.1f} cm/s")
        self._sim_ciz()

    def _sim_oynat_durdur(self) -> None:
        self.sim_calisiyor = not self.sim_calisiyor
        if self.sim_calisiyor:
            self.btn_sim_oynat.configure(text="⏸️ Simülasyonu Duraklat", fg_color="#D97706", hover_color="#B45309")
            self._sim_zamanlayici_adimi()
        else:
            self.btn_sim_oynat.configure(text="▶️ Canlı Simülasyonu Başlat", fg_color="#00A86B", hover_color="#007F50")

    def _su_sisi_tetikle(self) -> None:
        self.su_sisi_aktif = not self.su_sisi_aktif
        if self.su_sisi_aktif:
            self.btn_su_sisi.configure(text="🛑 Su Sisini Kapat (Aktif Söndürme)", fg_color="#059669")
        else:
            self.btn_su_sisi.configure(text="🚿 İnce Su Sisi (Fine Water Mist) Sık", fg_color="#0284C7")
        self._sim_ciz()

    def _sim_sifirla(self) -> None:
        self.sim_calisiyor = False
        self.su_sisi_aktif = False
        self.sim_zaman_sn = 0.0
        self.btn_sim_oynat.configure(text="▶️ Canlı Simülasyonu Başlat", fg_color="#00A86B", hover_color="#007F50")
        self.btn_su_sisi.configure(text="🚿 İnce Su Sisi (Fine Water Mist) Sık", fg_color="#0284C7")
        self._sim_etiket_ve_cizim_yenile()

    def _sim_zamanlayici_adimi(self) -> None:
        if not self.sim_calisiyor or not self.winfo_exists():
            return
        sonuc = self._aktif_sim_sonucu_hesapla()
        tb_top = float(sonuc["tb_toplam_sn"])
        if tb_top > 0 and not self.su_sisi_aktif:
            self.sim_zaman_sn += 0.12
            if self.sim_zaman_sn >= tb_top:
                self.sim_zaman_sn = 0.0
        self.sim_faz += 0.35
        self._sim_ciz()
        self.after(60, self._sim_zamanlayici_adimi)

    def _sim_ciz(self) -> None:
        if not hasattr(self, "canvas_alev") or not self.canvas_alev.winfo_exists():
            return
        sonuc = self._aktif_sim_sonucu_hesapla()
        self.lbl_sim_durum.configure(text=str(sonuc["durum_metni"]))

        # --- SOL TUVAL: CANLI 2D ALEV, SOOT KABUĞU, SOĞUK ALEV VE SU SİSİ ---
        ca = self.canvas_alev
        ca.delete("all")
        wa = max(ca.winfo_width(), 440)
        ha = max(ca.winfo_height(), 340)
        cx, cy = wa // 2, int(ha * 0.54)

        g_v = float(self.slider_sim_g.get())
        d0_v = float(self.slider_sim_d0.get())
        u_v = float(self.slider_sim_akis.get())
        tb_top = float(sonuc["tb_toplam_sn"])
        t_rad = float(sonuc["radyatif_gecis_sn"])
        cool_var = bool(sonuc["cool_flame_olusur"])
        t_an = min(self.sim_zaman_sn, tb_top) if tb_top > 0 else 0.0

        ca.create_text(
            wa // 2, 20,
            text="🔬 CANLI MİKROÇEKİM & KISMİ YERÇEKİMİ ALEV FİZİĞİ (BASS / FLEX-2 / ACME)",
            fill=NEON_CYAN, font=("Consolas", 11, "bold")
        )

        # Hava akışı (ventilasyon) okları
        if u_v > 0.5:
            for y_ok in range(60, ha - 40, 45):
                uzunluk = min(55, int(12 + u_v * 1.1))
                ca.create_line(18, y_ok, 18 + uzunluk, y_ok, fill="#38BDF8", width=1.5, arrow=tk.LAST)
            ca.create_text(52, 42, text=f"Akış: {u_v:.1f} cm/s", fill="#38BDF8", font=("Consolas", 9, "bold"))

        if self.su_sisi_aktif:
            for i in range(28):
                sx = (cx - 110 + (i * 37 + int(self.sim_faz * 25)) % 220)
                sy = (cy - 95 + (i * 53 + int(self.sim_faz * 18)) % 190)
                ca.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill="#38BDF8", outline="#E0F2FE")
            ca.create_text(
                cx, cy - 115,
                text="🚿 İNCE SU SİSİ (<60 µm) GİZLİ BUHARLAŞMA ISISI İLE ALEVİ SOĞUTTU (SÖNDÜ)",
                fill="#38BDF8", font=("Consolas", 10, "bold")
            )
        elif float(sonuc["k_sicak"]) <= 0.0:
            ca.create_oval(cx - 22, cy - 22, cx + 22, cy + 22, fill="#334155", outline="#94A3B8", width=2)
            ca.create_text(cx, cy + 45, text=str(sonuc["durum_metni"]), fill=NEON_PINK, font=("Consolas", 10, "bold"))
        else:
            soguk_fazda_mi = cool_var and (t_an > t_rad)
            if not soguk_fazda_mi:
                d_kare = max(0.05, (d0_v ** 2) - float(sonuc["k_sicak"]) * t_an)
                aktif_renk = str(sonuc["renk_sicak"])
                aktif_sicaklik = int(sonuc["t_sicak_k"])
                faz_etiketi = "🔥 FAZ 1: GÖRÜNÜR SICAK DİFÜZYON ALEVİ"
            else:
                d_gecis = float(sonuc["radyatif_gecis_cap_mm"])
                d_kare = max(0.05, (d_gecis ** 2) - float(sonuc["k_soguk"]) * (t_an - t_rad))
                aktif_renk = str(sonuc["renk_soguk"])
                aktif_sicaklik = int(sonuc["t_soguk_k"])
                faz_etiketi = "🟣 FAZ 2: GÖRÜNMEZ SOĞUK ALEV (COOL FLAME ~640 K - NTC KİMYASI)"

            anlik_d = math.sqrt(d_kare)
            titresim = 2.5 * math.sin(self.sim_faz)
            alev_r = max(18.0, (anlik_d / max(d0_v, 1.0)) * 68.0 + titresim)
            konvektif_uzama = g_v * 52.0
            akis_kaymasi = min(28.0, u_v * 0.65)

            # Dış reaksiyon zonu
            ca.create_oval(
                cx - alev_r + akis_kaymasi * 0.2,
                cy - alev_r - konvektif_uzama,
                cx + alev_r + akis_kaymasi,
                cy + alev_r * (1.0 - 0.28 * g_v),
                outline=aktif_renk,
                width=3 if not soguk_fazda_mi else 2,
                dash=(6, 4) if soguk_fazda_mi else ()
            )

            # İç kurum (soot) kabuğu (yalnızca sıcak alevde görünür)
            if not soguk_fazda_mi and int(sonuc["soot_indeksi"]) > 15:
                soot_r = alev_r * 0.66
                ca.create_oval(
                    cx - soot_r + akis_kaymasi * 0.15,
                    cy - soot_r - konvektif_uzama * 0.6,
                    cx + soot_r + akis_kaymasi * 0.7,
                    cy + soot_r * 0.85,
                    outline="#F59E0B",
                    width=2,
                    dash=(4, 2)
                )

            # Merkez sıvı damlacık çekirdeği
            damla_r = max(4.0, (anlik_d / 4.5) * 24.0)
            ca.create_oval(
                cx - damla_r, cy - damla_r, cx + damla_r, cy + damla_r,
                fill="#E2E8F0", outline="#38BDF8", width=1.5
            )

            ca.create_text(cx, 44, text=faz_etiketi, fill=aktif_renk, font=("Consolas", 10, "bold"))
            ca.create_text(
                cx, ha - 38,
                text=f"Anlık Çap d(t): {anlik_d:.2f} mm  |  Zaman: {t_an:.1f}/{tb_top:.1f} sn  |  Sıcaklık: {aktif_sicaklik} K",
                fill="#E2E8F0", font=("Consolas", 10, "bold")
            )

        ca.create_text(
            cx, ha - 16,
            text=f"Grashof: {sonuc['grashof']} | Reynolds: {sonuc['reynolds']} | Damköhler: {sonuc['damkohler']} | Soot: %{sonuc['soot_indeksi']} | CO: {sonuc['co_ppm']} ppm",
            fill=NEON_GOLD, font=("Consolas", 9, "bold")
        )

        # --- SAĞ TUVAL: ÜSTTE d²-YASASI (SICAK & SOĞUK ALEV), ALTTA FAN HIZI YAYILIM EĞRİSİ ---
        cg = self.canvas_grafik
        cg.delete("all")
        wg = max(cg.winfo_width(), 480)
        hg = max(cg.winfo_height(), 340)
        orta_y = hg // 2

        # 1. Üst Grafik: d²-Yasası (d² vs t)
        gx0, gy0, gx1, gy1 = 58, orta_y - 26, wg - 28, 32
        cg.create_text(
            (gx0 + gx1) // 2, 16,
            text=f"📈 1. d²-YASASI EĞRİSİ (K_hot={sonuc['k_sicak']} mm²/s | K_cool={sonuc['k_soguk']} mm²/s)",
            fill=NEON_GOLD, font=("Consolas", 10, "bold")
        )
        cg.create_line(gx0, gy0, gx1, gy0, fill="#64748B", width=1.5)
        cg.create_line(gx0, gy0, gx0, gy1, fill="#64748B", width=1.5)
        cg.create_text(gx0 - 22, gy1 + 6, text="d²(mm²)", fill="#94A3B8", font=("Consolas", 8, "bold"))
        cg.create_text(gx1 - 12, gy0 + 12, text="t(sn)", fill="#94A3B8", font=("Consolas", 8))

        seriler = sonuc["zaman_serisi"]
        if isinstance(seriler, list) and len(seriler) > 1 and tb_top > 0:
            maks_d2 = max(d0_v ** 2, 1.0)
            onceki_pt = None
            for t_pt, d2_pt, _, rejim_pt in seriler:
                px = gx0 + (t_pt / tb_top) * (gx1 - gx0 - 10)
                py = gy0 - (d2_pt / maks_d2) * (gy0 - gy1 - 8)
                renk_cizgi = "#38BDF8" if rejim_pt == "SICAK_ALEV" else "#C084FC"
                if onceki_pt is not None:
                    cg.create_line(onceki_pt[0], onceki_pt[1], px, py, fill=renk_cizgi, width=2.5)
                onceki_pt = (px, py)

            # Anlık zaman imleci
            oran_t = min(1.0, max(0.0, t_an / tb_top))
            idx_imlec = min(len(seriler) - 1, int(oran_t * (len(seriler) - 1)))
            t_sec, d2_sec, _, _ = seriler[idx_imlec]
            ix = gx0 + (t_sec / tb_top) * (gx1 - gx0 - 10)
            iy = gy0 - (d2_sec / maks_d2) * (gy0 - gy1 - 8)
            cg.create_oval(ix - 5, iy - 5, ix + 5, iy + 5, fill=NEON_PINK, outline="#FFFFFF")

        # 2. Alt Grafik: BASS/SoFIE Havalandırma Hızı vs Alev Yayılım Hızı (Quenching -> Peak -> Blow-Off)
        cg.create_line(15, orta_y, wg - 15, orta_y, fill=BORDER_CLR, width=1, dash=(4, 4))
        bx0, by0, bx1, by1 = 58, hg - 30, wg - 28, orta_y + 30
        cg.create_text(
            (bx0 + bx1) // 2, orta_y + 15,
            text="💨 2. BASS / SoFIE KABİN FAN HIZI vs ALEV YAYILIM HIZI (QUENCHING -> PEAK -> BLOW-OFF)",
            fill=NEON_CYAN, font=("Consolas", 10, "bold")
        )
        cg.create_line(bx0, by0, bx1, by0, fill="#64748B", width=1.5)
        cg.create_line(bx0, by0, bx0, by1, fill="#64748B", width=1.5)
        cg.create_text(bx0 - 24, by1 + 6, text="Vf(mm/s)", fill="#94A3B8", font=("Consolas", 8, "bold"))
        cg.create_text(bx1 - 24, by0 + 12, text="Fan(cm/s)", fill="#94A3B8", font=("Consolas", 8))

        akis_egrisi = MikroYercekimiFizikMotoru.akis_hizi_yayilim_egrisi_hesapla(
            yercekimi_g=g_v, oksijen_yuzde=float(self.slider_sim_o2.get())
        )
        maks_hiz = max([h for _, h, _ in akis_egrisi] + [3.5])
        onceki_b = None
        for u_pt, h_pt, _ in akis_egrisi:
            px = bx0 + (u_pt / 45.0) * (bx1 - bx0 - 10)
            py = by0 - (h_pt / maks_hiz) * (by0 - by1 - 8)
            if onceki_b is not None:
                cg.create_line(onceki_b[0], onceki_b[1], px, py, fill="#00FF88", width=2.5)
            onceki_b = (px, py)

        # Seçili fan hızı noktası
        sec_ux = bx0 + (min(u_v, 45.0) / 45.0) * (bx1 - bx0 - 10)
        cg.create_line(sec_ux, by0, sec_ux, by1, fill=NEON_PINK, width=1.5, dash=(3, 3))
        cg.create_text(sec_ux, by1 + 10, text=f"Aktif Fan: {u_v:.1f} cm/s", fill=NEON_PINK, font=("Consolas", 8, "bold"))

    def _sim_verisini_ai_sekmesine_gonder(self) -> None:
        s = self._aktif_sim_sonucu_hesapla()
        g_v = float(self.slider_sim_g.get())
        o2_v = float(self.slider_sim_o2.get())
        p_v = float(self.slider_sim_basinc.get())
        u_v = float(self.slider_sim_akis.get())
        d0_v = float(self.slider_sim_d0.get())

        soru = (
            f"Canlı Simülasyon Senaryosu ({s['yakit']}): Yerçekimi {g_v:.2f}g, Oksijen %{o2_v:.1f}, "
            f"Kabin Basıncı {p_v:.1f} kPa, Fan Akış Hızı {u_v:.1f} cm/s, Damlacık Çapı d0={d0_v:.1f} mm. "
            f"Hesaplanan Sıcak Alev Sabiti K={s['k_sicak']} mm²/s, Soğuk Alev K_cool={s['k_soguk']} mm²/s, "
            f"Alev Sıcaklığı {s['t_sicak_k']} K, Soot İndeksi %{s['soot_indeksi']}, CO {s['co_ppm']} ppm "
            f"({s['durum_metni']}). Bu durumu NASA PSI kanıtlarıyla analiz et ve güvenlik protokolünü oluştur."
        )
        self.tabs.set("🤖 8. AI Karar & Jüri Raporu")
        self.txt_ai_soru.delete("1.0", "end")
        self.txt_ai_soru.insert("1.0", soru)
        self.ai_analiz_calistir()

    # =========================================================================
    # SEKME 2: KANIT-ODAKLI (EVIDENCE-FIRST) NASA PSI & NTRS ARAMA MERKEZİ
    # =========================================================================
    def _kur_sekme_2_psi_arama(self) -> None:
        ust = ctk.CTkFrame(self.tab_psi, fg_color=CARD_BG, corner_radius=8)
        ust.pack(side="top", fill="x", padx=8, pady=6)

        ctk.CTkLabel(ust, text="🔎 Kanıt & Anahtar Kelime:", font=ctk.CTkFont(size=12, weight="bold"), text_color=NEON_CYAN).pack(
            side="left", padx=(10, 4), pady=8
        )
        self.entry_psi_ara = ctk.CTkEntry(
            ust, placeholder_text="Örn: cool flame, heptane, BASS, Saffire, 0.16g, soot, water mist, PMMA...", width=320
        )
        self.entry_psi_ara.pack(side="left", padx=4, pady=8, fill="x", expand=True)
        self.entry_psi_ara.bind("<Return>", lambda _: self._psi_tabloyu_yenile())

        ctk.CTkLabel(ust, text="Yerçekimi:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(8, 4))
        self.psi_yercekimi_var = ctk.StringVar(value="Tümü")
        ctk.CTkOptionMenu(
            ust, variable=self.psi_yercekimi_var, values=["Tümü", "0.00g (ISS)", "0.16g (Ay)", "0.38g (Mars)"],
            width=130, command=lambda _: self._psi_tabloyu_yenile()
        ).pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            ust, text="🔎 Yerel PSI Kanıtlarını Sırala", width=190, fg_color="#00A86B", hover_color="#007F50",
            command=self._psi_tabloyu_yenile
        ).pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            ust, text="🌐 Canlı NASA NTRS API'den Çek", width=210, fg_color="#FF4500", hover_color="#8B0000",
            command=self._canli_ntrs_sorgula
        ).pack(side="left", padx=(4, 10), pady=8)

        orta = ctk.CTkFrame(self.tab_psi, fg_color="transparent")
        orta.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        orta.grid_columnconfigure(0, weight=12)
        orta.grid_columnconfigure(1, weight=10)
        orta.grid_rowconfigure(0, weight=1)

        sol_tablo = ctk.CTkFrame(orta, fg_color=CARD_BG, corner_radius=8)
        sol_tablo.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        stil = ttk.Style()
        try:
            stil.theme_use("clam")
        except Exception:
            pass
        stil.configure("Nasa.Treeview", background="#050811", foreground="#E2E8F0", fieldbackground="#050811", rowheight=27, font=("Consolas", 10))
        stil.configure("Nasa.Treeview.Heading", background="#162038", foreground=NEON_CYAN, font=("Consolas", 10, "bold"))
        stil.map("Nasa.Treeview", background=[("selected", "#1E3A8A")], foreground=[("selected", "#FFFFFF")])

        sutunlar = ("kanit_id", "program", "rejim", "guven", "baslik")
        self.tree_psi = ttk.Treeview(sol_tablo, columns=sutunlar, show="headings", style="Nasa.Treeview")
        self.tree_psi.heading("kanit_id", text="Kanıt Kodu")
        self.tree_psi.heading("program", text="NASA Programı")
        self.tree_psi.heading("rejim", text="Yerçekimi")
        self.tree_psi.heading("guven", text="Önem / Eşleşme")
        self.tree_psi.heading("baslik", text="Deney / Rapor Başlığı")

        self.tree_psi.column("kanit_id", width=120, anchor="w")
        self.tree_psi.column("program", width=135, anchor="w")
        self.tree_psi.column("rejim", width=125, anchor="center")
        self.tree_psi.column("guven", width=110, anchor="center")
        self.tree_psi.column("baslik", width=320, anchor="w")
        self.tree_psi.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        self.tree_psi.bind("<<TreeviewSelect>>", self._psi_secim_degisti)

        sag_detay = ctk.CTkFrame(orta, fg_color=CARD_BG, corner_radius=8)
        sag_detay.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            sag_detay, text="📋 DOĞRULANMIŞ DENEY KANITI VE GÜVENLİK ÇIKARIMI",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color=NEON_GOLD
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.txt_psi_detay = ctk.CTkTextbox(
            sag_detay, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#050811", text_color="#E2E8F0", wrap="word"
        )
        self.txt_psi_detay.pack(fill="both", expand=True, padx=10, pady=6)

        ctk.CTkButton(
            sag_detay, text="🤖 Seçili Kanıtı AI Karar Merkezinde Derin Analiz Et", height=34,
            fg_color="#008080", hover_color="#005959", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._secili_psi_kanitini_ai_gonder
        ).pack(fill="x", padx=10, pady=(0, 10))

    def _psi_tabloyu_yenile(self) -> None:
        for item in self.tree_psi.get_children():
            self.tree_psi.delete(item)
        sorgu = self.entry_psi_ara.get().strip()
        filtre = self.psi_yercekimi_var.get()
        sonuclar = self.arama_motoru.deneyleri_ara_ve_sirala(sorgu=sorgu, yercekimi_filtre=filtre)
        for skor, kayit in sonuclar:
            self.eslesen_deney_bellek[kayit.kanit_id] = kayit
            self.tree_psi.insert(
                "", "end", iid=kayit.kanit_id,
                values=(kayit.kanit_id, kayit.program_adi, kayit.yercekimi_rejimi, f"%{skor:.1f}", kayit.baslik)
            )
        if sonuclar:
            ilk_id = sonuclar[0][1].kanit_id
            self.tree_psi.selection_set(ilk_id)
            self._psi_secim_degisti()

    def _psi_secim_degisti(self, _event: object = None) -> None:
        secim = self.tree_psi.selection()
        if not secim:
            return
        kanit_id = secim[0]
        kayit = self.eslesen_deney_bellek.get(kanit_id)
        if not kayit:
            return
        ntrs_baglantilar = "\n".join(
            f"   • https://ntrs.nasa.gov/citations/{nid} (NTRS:{nid})"
            for nid in getattr(kayit, "ntrs_referanslari", ())
        )
        metin = (
            f"📌 KANIT KODU       : {kayit.kanit_id}\n"
            f"🛰️ NASA PROGRAMI    : {kayit.program_adi} ({kayit.yil})\n"
            f"🔬 TESİS & GÖREV    : {kayit.tesis_ve_gorev}\n"
            f"🪐 YERÇEKİMİ REJİMİ : {kayit.yercekimi_rejimi}\n"
            f"🧪 YAKIT / MALZEME  : {kayit.yakit_veya_malzeme}\n"
            f"💨 PARAMETRELER     : O2: %{kayit.oksijen_araligi_yuzde[0]}-%{kayit.oksijen_araligi_yuzde[1]} | "
            f"Basınç: {kayit.basinc_kpa} kPa | Akış: {kayit.akis_hizi_cm_s[0]}-{kayit.akis_hizi_cm_s[1]} cm/s\n"
            + (f"🔗 DOĞRULANABİLİR NTRS KAYNAKLARI:\n{ntrs_baglantilar}\n" if ntrs_baglantilar else "")
            + "-" * 68 + "\n"
            f"📖 DENEYSEL BULGULAR:\n{kayit.temel_bulgular}\n\n"
            f"🛡️ UZAY ARACI YANGIN GÜVENLİĞİ ÇIKARIMI:\n{kayit.yangin_guvenligi_cikarimi}\n"
        )
        self.txt_psi_detay.delete("1.0", "end")
        self.txt_psi_detay.insert("1.0", metin)

    def _canli_ntrs_sorgula(self) -> None:
        sorgu = self.entry_psi_ara.get().strip() or "flame extinguishment droplet"
        self.txt_psi_detay.delete("1.0", "end")
        self.txt_psi_detay.insert("1.0", f"🌐 NASA NTRS & Science API üzerinden '{sorgu}' sorgulanıyor, lütfen bekleyin...")

        def _worker() -> None:
            canli_kayitlar = NasaTelemetriVeVeriAvcisi.canli_nasa_ntrs_ara(sorgu)

            def _guncelle() -> None:
                if not canli_kayitlar:
                    self.txt_psi_detay.insert(
                        "end",
                        "\n\n[!] Çevrimiçi NTRS API yanıt vermedi veya internet kapalı; yerleşik doğrulanmış PSI arşivi aktif."
                    )
                    return
                rapor = [f"✅ CANLI NASA NTRS / IMAGES API SONUÇLARI ('{sorgu}'):\n" + "=" * 64]
                for c in canli_kayitlar:
                    rapor.append(
                        f"\n[{c['kanit_id']}] {c['baslik']}\n"
                        f"Merkez: {c['merkez']}\n"
                        f"Bağlantı: {c['kaynak_url']}\n"
                        f"Özet: {c['ozet']}\n" + "-" * 54
                    )
                self.txt_psi_detay.delete("1.0", "end")
                self.txt_psi_detay.insert("1.0", "\n".join(rapor))

            self.after(0, _guncelle)

        threading.Thread(target=_worker, daemon=True).start()

    def _secili_psi_kanitini_ai_gonder(self) -> None:
        icerik = self.txt_psi_detay.get("1.0", "end-1c").strip()
        if not icerik:
            return
        self.tabs.set("🤖 8. AI Karar & Jüri Raporu")
        self.txt_ai_soru.delete("1.0", "end")
        self.txt_ai_soru.insert(
            "1.0",
            f"Aşağıdaki doğrulanmış NASA PSI/NTRS deney kaydını derinlemesine analiz et ve "
            f"Ay/Mars görevleri için tasarım kurallarını çıkar:\n\n{icerik[:1500]}"
        )
        self.ai_analiz_calistir()

    # =========================================================================
    # SEKME 3: UZAY ARACI MALZEME YANICILIK ATLASI (0G vs AY 0.16G PARADOKSU)
    # =========================================================================
    def _kur_sekme_3_malzeme_atlasi(self) -> None:
        ust = ctk.CTkFrame(self.tab_malzeme, fg_color=CARD_BG, corner_radius=8)
        ust.pack(side="top", fill="x", padx=8, pady=6)

        self.lbl_mat_o2 = ctk.CTkLabel(
            ust, text="Kabin Oksijen Oranı: %21.0 O2", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=NEON_GOLD
        )
        self.lbl_mat_o2.pack(side="left", padx=(12, 6), pady=8)

        self.slider_mat_o2 = ctk.CTkSlider(
            ust, from_=14.0, to=38.0, number_of_steps=48, width=180, command=lambda _: self._malzeme_atlasi_yenile()
        )
        self.slider_mat_o2.set(21.0)
        self.slider_mat_o2.pack(side="left", padx=6, pady=8)

        self.lbl_mat_g = ctk.CTkLabel(
            ust, text="Hedef Yerçekimi: 0.16g (Ay Paradoksu)", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=NEON_CYAN
        )
        self.lbl_mat_g.pack(side="left", padx=(16, 6), pady=8)

        self.slider_mat_g = ctk.CTkSlider(
            ust, from_=0.0, to=1.0, number_of_steps=25, width=180, command=lambda _: self._malzeme_atlasi_yenile()
        )
        self.slider_mat_g.set(0.16)
        self.slider_mat_g.pack(side="left", padx=6, pady=8)

        ctk.CTkButton(
            ust, text="🌙 Ay Keşif Atmosferi (%34 O2, 0.16g)", fg_color="#6A0DAD", hover_color="#4B0082",
            command=lambda: (self.slider_mat_o2.set(34.0), self.slider_mat_g.set(0.16), self._malzeme_atlasi_yenile())
        ).pack(side="right", padx=10, pady=8)

        orta = ctk.CTkFrame(self.tab_malzeme, fg_color="transparent")
        orta.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        orta.grid_columnconfigure(0, weight=11)
        orta.grid_columnconfigure(1, weight=11)
        orta.grid_rowconfigure(0, weight=1)

        self.canvas_malzeme = tk.Canvas(orta, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR)
        self.canvas_malzeme.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.canvas_malzeme.bind("<Configure>", lambda _: self._malzeme_atlasi_yenile())

        self.txt_malzeme_rapor = ctk.CTkTextbox(
            orta, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#050811", text_color="#E2E8F0", wrap="word"
        )
        self.txt_malzeme_rapor.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def _malzeme_atlasi_yenile(self) -> None:
        o2_v = float(self.slider_mat_o2.get())
        g_v = float(self.slider_mat_g.get())
        self.lbl_mat_o2.configure(text=f"Kabin Oksijen Oranı: %{o2_v:.1f} O2")
        self.lbl_mat_g.configure(text=f"Hedef Yerçekimi: {g_v:.2f}g")

        degerlendirme = self.arama_motoru.malzemeleri_atmosfere_gore_degerlendir(o2_v, g_v)

        # Sol Grafik: Malzemelerin 1g Dünya vs 0g ISS vs 0.16g Ay LOC (%O2) Karşılaştırması
        cm = self.canvas_malzeme
        cm.delete("all")
        w = max(cm.winfo_width(), 480)
        h = max(cm.winfo_height(), 340)

        cm.create_text(
            w // 2, 18,
            text="🛡️ MALZEME KRİTİK OKSİJEN SINIRI (LOC %O2) — DÜNYA (1g) vs ISS (0g) vs AY (0.16g)",
            fill=NEON_CYAN, font=("Consolas", 10, "bold")
        )
        cm.create_text(
            w // 2, 36,
            text="⚠️ SoFIE Bulgusu: Ay'da (0.16g) LOC daha düşüktür; Dünya'da sönen malzeme Ay'da yanmaya devam eder!",
            fill=NEON_GOLD, font=("Consolas", 9, "bold")
        )

        sol_x = 155
        sag_x = w - 35
        ust_y = 62
        satir_yuk = max(38, (h - 90) // len(UZAY_MALZEME_ATLASI))

        # Seçili kabin O2 dikey referans çizgisi
        o2_x = sol_x + (min(o2_v, 45.0) / 45.0) * (sag_x - sol_x)
        cm.create_line(o2_x, ust_y - 8, o2_x, h - 20, fill=NEON_PINK, width=2, dash=(4, 3))
        cm.create_text(o2_x, h - 10, text=f"Kabin O2: %{o2_v:.1f}", fill=NEON_PINK, font=("Consolas", 9, "bold"))

        for idx, m in enumerate(UZAY_MALZEME_ATLASI):
            y_merkez = ust_y + idx * satir_yuk
            kisa_ad = m.malzeme_adi.split("(")[0].strip()
            cm.create_text(sol_x - 10, y_merkez + 10, text=kisa_ad, anchor="e", fill="#E2E8F0", font=("Consolas", 10, "bold"))

            w_1g = (min(m.loc_dunya_1g, 45.0) / 45.0) * (sag_x - sol_x)
            w_0g = (min(m.loc_mikro_0g, 45.0) / 45.0) * (sag_x - sol_x)
            w_ay = (min(m.loc_ay_016g, 45.0) / 45.0) * (sag_x - sol_x)

            cm.create_rectangle(sol_x, y_merkez, sol_x + w_1g, y_merkez + 7, fill="#38BDF8", outline="")
            cm.create_rectangle(sol_x, y_merkez + 8, sol_x + w_0g, y_merkez + 15, fill="#F59E0B", outline="")
            cm.create_rectangle(sol_x, y_merkez + 16, sol_x + w_ay, y_merkez + 23, fill="#FF3366", outline="")
            cm.create_text(
                sol_x + max(w_1g, w_0g, w_ay) + 6, y_merkez + 11,
                text=f"1g:%{m.loc_dunya_1g} | 0g:%{m.loc_mikro_0g} | Ay:%{m.loc_ay_016g}",
                anchor="w", fill="#94A3B8", font=("Consolas", 8)
            )

        # Sağ Rapor Kutusu
        satirlar = [
            f"🛡️ NASA-STD-6001B MALZEME YANICILIK SIRALAMASI (Kabin O2: %{o2_v:.1f} | Yerçekimi: {g_v:.2f}g)",
            "=" * 72,
        ]
        for sira, r in enumerate(degerlendirme, 1):
            m_obj = r["malzeme"]
            satirlar.append(
                f"\n{sira}. {m_obj.malzeme_adi} [{m_obj.malzeme_kodu}]\n"
                f"   • Durum & Risk Puanı : {r['durum']} (Risk: {r['risk_puan']}/100)\n"
                f"   • Aktif LOC Sınırı   : %{r['aktif_loc']} O2  |  Yayılım Hızı: {r['aktif_hiz']} mm/s\n"
                f"   • Toksik Ürünler     : {m_obj.toksik_gazlar}\n"
                f"   • Söndürme Protokolü : {m_obj.sondurme_protokolu}\n"
                f"   • Kanıt Referansı    : {m_obj.kanit_referansi}"
            )
        self.txt_malzeme_rapor.delete("1.0", "end")
        self.txt_malzeme_rapor.insert("1.0", "\n".join(satirlar))

    # =========================================================================
    # SEKME 4: ÇOK EKSENLİ TELEMETRİ ANOMALİ RADARI & VERİ SESLENDİRME
    # =========================================================================
    def _kur_sekme_4_telemetri_radari(self) -> None:
        ust = ctk.CTkFrame(self.tab_telemetri, fg_color=CARD_BG, corner_radius=8)
        ust.pack(side="top", fill="x", padx=8, pady=6)

        ctk.CTkLabel(ust, text="🧪 Hazır NASA Deney Telemetrileri:", font=ctk.CTkFont(size=12, weight="bold"), text_color=NEON_CYAN).pack(
            side="left", padx=(10, 4), pady=8
        )
        ctk.CTkButton(
            ust, text="1) FLEX-2 Soğuk Alev Geçişi", width=175, fg_color="#6A0DAD", hover_color="#4B0082",
            command=lambda: self._hazir_telemetri_yukle("FLEX")
        ).pack(side="left", padx=3, pady=8)

        ctk.CTkButton(
            ust, text="2) BASS-II O2 Artış Anomalisi", width=180, fg_color="#00A86B", hover_color="#007F50",
            command=lambda: self._hazir_telemetri_yukle("BASS")
        ).pack(side="left", padx=3, pady=8)

        ctk.CTkButton(
            ust, text="3) Saffire %34 O2 Basınç Piki", width=180, fg_color="#D97706", hover_color="#B45309",
            command=lambda: self._hazir_telemetri_yukle("SAFFIRE")
        ).pack(side="left", padx=3, pady=8)

        ctk.CTkButton(
            ust, text="📂 Harici CSV Oku (Salt-Okunur)", width=195, fg_color="#1f538d", hover_color="#14375e",
            command=self._harici_csv_sec_ve_yukle
        ).pack(side="left", padx=6, pady=8)

        ctk.CTkButton(
            ust, text="🔊 Telemetriyi Seslendir (Sonification)", width=220, fg_color="#C62828", hover_color="#8E0000",
            command=self._aktif_telemetriyi_seslendir
        ).pack(side="right", padx=10, pady=8)

        eksen_bar = ctk.CTkFrame(self.tab_telemetri, fg_color="transparent")
        eksen_bar.pack(side="top", fill="x", padx=10, pady=2)

        ctk.CTkLabel(eksen_bar, text="Y1 Ekseni (Pembe):", text_color=NEON_PINK, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        self.combo_tel_y1 = ctk.CTkOptionMenu(eksen_bar, values=["Sicaklik_K"], width=180, command=lambda _: self._telemetri_radari_ciz())
        self.combo_tel_y1.pack(side="left", padx=4)

        ctk.CTkLabel(eksen_bar, text="Y2 Ekseni (Mavi):", text_color=NEON_BLUE, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
        self.combo_tel_y2 = ctk.CTkOptionMenu(eksen_bar, values=["CO_Emisyon_ppm"], width=180, command=lambda _: self._telemetri_radari_ciz())
        self.combo_tel_y2.pack(side="left", padx=4)

        self.lbl_tel_dosya = ctk.CTkLabel(eksen_bar, text="", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=NEON_GOLD)
        self.lbl_tel_dosya.pack(side="right", padx=10)

        orta = ctk.CTkFrame(self.tab_telemetri, fg_color="transparent")
        orta.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        orta.grid_columnconfigure(0, weight=13)
        orta.grid_columnconfigure(1, weight=8)
        orta.grid_rowconfigure(0, weight=1)

        self.canvas_tel = tk.Canvas(orta, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR)
        self.canvas_tel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.canvas_tel.bind("<Configure>", lambda _: self._telemetri_radari_ciz())

        self.txt_tel_analiz = ctk.CTkTextbox(
            orta, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#050811", text_color="#E2E8F0", wrap="word"
        )
        self.txt_tel_analiz.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def _hazir_telemetri_yukle(self, kod: str) -> None:
        ad, sutunlar, sozluk = NasaTelemetriVeVeriAvcisi.hazir_telemetri_veri_seti_uret(kod)
        self.aktif_telemetri_adi = ad
        self.telemetri_sutunlar = sutunlar
        self.telemetri_veri = sozluk
        self.combo_tel_y1.configure(values=sutunlar)
        self.combo_tel_y2.configure(values=sutunlar)
        self.combo_tel_y1.set("Sicaklik_K" if "Sicaklik_K" in sutunlar else sutunlar[1])
        self.combo_tel_y2.set("CO_Emisyon_ppm" if "CO_Emisyon_ppm" in sutunlar else sutunlar[2])
        self.lbl_tel_dosya.configure(text=f"📊 Aktif Veri: {ad}")
        self._telemetri_radari_ciz()

    def _harici_csv_sec_ve_yukle(self) -> None:
        yol = filedialog.askopenfilename(
            title="Salt-Okunur Telemetri CSV Dosyası Seçin",
            filetypes=[("CSV Dosyaları", "*.csv"), ("Tüm Dosyalar", "*.*")]
        )
        if not yol:
            return
        try:
            ad, sutunlar, sozluk = NasaTelemetriVeVeriAvcisi.csv_dosyasi_salt_okunur_yukle(yol)
            self.aktif_telemetri_adi = ad
            self.telemetri_sutunlar = sutunlar
            self.telemetri_veri = sozluk
            self.combo_tel_y1.configure(values=sutunlar)
            self.combo_tel_y2.configure(values=sutunlar)
            self.combo_tel_y1.set(sutunlar[1] if len(sutunlar) > 1 else sutunlar[0])
            self.combo_tel_y2.set(sutunlar[2] if len(sutunlar) > 2 else sutunlar[0])
            self.lbl_tel_dosya.configure(text=f"📊 Aktif Veri: {ad}")
            self._telemetri_radari_ciz()
        except Exception as exc:
            messagebox.showerror("CSV Okuma Hatası", str(exc))

    def _telemetri_radari_ciz(self) -> None:
        if not self.telemetri_veri or not hasattr(self, "canvas_tel"):
            return
        ct = self.canvas_tel
        ct.delete("all")
        w = max(ct.winfo_width(), 520)
        h = max(ct.winfo_height(), 320)

        x_kolon = self.telemetri_sutunlar[0]
        y1_kolon = self.combo_tel_y1.get()
        y2_kolon = self.combo_tel_y2.get()

        x_verisi = self.telemetri_veri.get(x_kolon, [])
        y1_verisi = self.telemetri_veri.get(y1_kolon, [])
        y2_verisi = self.telemetri_veri.get(y2_kolon, [])
        n = min(len(x_verisi), len(y1_verisi))
        if n < 2:
            return

        x0, y0, x1, y1 = 55, h - 38, w - 35, 35
        ct.create_line(x0, y0, x1, y0, fill="#64748B", width=1.5)
        ct.create_line(x0, y0, x0, y1, fill="#64748B", width=1.5)

        min_y1, max_y1 = min(y1_verisi[:n]), max(y1_verisi[:n])
        span_y1 = (max_y1 - min_y1) or 1.0

        onceki = None
        for i in range(n):
            px = x0 + (i / (n - 1)) * (x1 - x0)
            py = y0 - ((y1_verisi[i] - min_y1) / span_y1) * (y0 - y1)
            if onceki is not None:
                ct.create_line(onceki[0], onceki[1], px, py, fill=NEON_PINK, width=2.5)
            onceki = (px, py)

        if len(y2_verisi) >= n:
            min_y2, max_y2 = min(y2_verisi[:n]), max(y2_verisi[:n])
            span_y2 = (max_y2 - min_y2) or 1.0
            onceki2 = None
            for i in range(n):
                px = x0 + (i / (n - 1)) * (x1 - x0)
                py = y0 - ((y2_verisi[i] - min_y2) / span_y2) * (y0 - y1)
                if onceki2 is not None:
                    ct.create_line(onceki2[0], onceki2[1], px, py, fill=NEON_BLUE, width=2.0, dash=(4, 2))
                onceki2 = (px, py)

        analiz = NasaTelemetriVeVeriAvcisi.pearson_ve_anomali_hesapla(x_verisi, y1_verisi, y2_verisi)
        for idx, _, val, _ in analiz["anomaliler"]:
            px = x0 + (idx / (n - 1)) * (x1 - x0)
            py = y0 - ((val - min_y1) / span_y1) * (y0 - y1)
            ct.create_oval(px - 5, py - 5, px + 5, py + 5, fill=NEON_GOLD, outline="#FFFFFF")

        rapor = [
            f"📊 TELEMETRİ KORELASYON & Z-SKORU ANOMALİ RAPORU",
            "=" * 50,
            f"Veri Seti          : {self.aktif_telemetri_adi}",
            f"Y1 Ekseni (Pembe)  : {y1_kolon}",
            f"   • Ortalama      : {analiz['ortalama']}",
            f"   • Std. Sapma    : {analiz['std']}",
            f"   • Min / Maks    : {analiz['min']} / {analiz['max']}",
            f"Y2 Ekseni (Mavi)   : {y2_kolon}",
            f"Pearson Korelasyon : r = {analiz['pearson']}",
            "-" * 50,
            f"🚨 Z-SKORU (>1.95σ) ANOMALİ NOKTALARI ({len(analiz['anomaliler'])} Adet):",
        ]
        for _, t_deger, v_deger, z_skor in analiz["anomaliler"][:12]:
            rapor.append(f"   • t={t_deger} sn -> Değer: {v_deger} (Z={z_skor}σ)")

        self.txt_tel_analiz.delete("1.0", "end")
        self.txt_tel_analiz.insert("1.0", "\n".join(rapor))

    def _aktif_telemetriyi_seslendir(self) -> None:
        y1_kolon = self.combo_tel_y1.get()
        degerler = self.telemetri_veri.get(y1_kolon, [])
        if not degerler:
            return
        threading.Thread(
            target=NasaTelemetriVeVeriAvcisi.veriyi_seslendir_wav_bellek,
            args=(degerler,),
            daemon=True
        ).start()

    # =========================================================================
    # SEKME 5: DERİN UZAY ARAŞTIRMA BOŞLUĞU BULUCU (RESEARCH GAP FINDER)
    # =========================================================================
    def _kur_sekme_5_arastirma_boslugu(self) -> None:
        orta = ctk.CTkFrame(self.tab_bosluk, fg_color="transparent")
        orta.pack(fill="both", expand=True, padx=8, pady=6)
        orta.grid_columnconfigure(0, weight=11)
        orta.grid_columnconfigure(1, weight=11)
        orta.grid_rowconfigure(0, weight=1)

        self.canvas_bosluk = tk.Canvas(orta, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR)
        self.canvas_bosluk.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.canvas_bosluk.bind("<Configure>", lambda _: self._bosluk_matrisi_ciz())

        self.txt_bosluk_detay = ctk.CTkTextbox(
            orta, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#050811", text_color="#E2E8F0", wrap="word"
        )
        self.txt_bosluk_detay.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        satirlar = [
            "🔭 DERİN UZAY YANGIN GÜVENLİĞİ ARAŞTIRMA BOŞLUĞU RAPORU (RESEARCH GAP FINDER)",
            "=" * 74,
            "NASA PSI ve NTRS arşivlerinin çapraz analizi sonucunda Artemis Ay Üssü, Lunar Gateway",
            "ve Mars Transit görevleri için tespit edilen kritik deneysel veri boşlukları:\n",
        ]
        for g in ARASTIRMA_BOSLUKLARI:
            satirlar.append(
                f"🚩 [{g.bosluk_kodu}] {g.baslik}\n"
                f"   • Risk Seviyesi      : {g.risk_seviyesi}\n"
                f"   • Hedef Görev Ortamı : {g.hedef_ortam}\n"
                f"   • Eksik Veri         : {g.eksik_parametreler}\n"
                f"   • Bilimsel Açıklama  : {g.aciklama}\n"
                f"   • Önerilen Deney     : {g.onerilen_deney_tasarimi}\n"
                + "-" * 74
            )
        self.txt_bosluk_detay.insert("1.0", "\n".join(satirlar))

    def _bosluk_matrisi_ciz(self) -> None:
        if not hasattr(self, "canvas_bosluk"):
            return
        cb = self.canvas_bosluk
        cb.delete("all")
        w = max(cb.winfo_width(), 480)
        h = max(cb.winfo_height(), 340)

        cb.create_text(
            w // 2, 22,
            text="🗺️ NASA DENEYSEL VERİ KAPSAMA VE ARAŞTIRMA BOŞLUĞU ISI HARİTASI (HEATMAP)",
            fill=NEON_CYAN, font=("Consolas", 10, "bold")
        )
        cb.create_text(
            w // 2, 42,
            text="🟩 Yüksek Veri (İyi Bilinen)   🟨 Kısmi Veri (Sınırlı Süre)   🟥 Kritik Veri Boşluğu (Research Gap)",
            fill="#E2E8F0", font=("Consolas", 9, "bold")
        )

        sutun_basliklari = ["1.0g Dünya", "0.0g ISS", "0.16g Ay", "0.38g Mars"]
        satir_basliklari = [
            "İnce Kumaş / PMMA Yanması",
            "Sıvı Damlacık & Soğuk Alev",
            "Kalın Kompozit (>5mm) Sönme",
            "Gezegen Tozu (Regolit) Etkisi",
            "Li-Ion Batarya Termal Kaçak",
        ]
        # Kapsama yüzdeleri (0-100)
        matris = [
            [98, 92, 45, 35],
            [95, 88, 20, 15],
            [90, 52, 12, 10],
            [75, 18, 8, 5],
            [92, 30, 10, 8],
        ]

        sol_x = 185
        ust_y = 80
        hucre_w = max(65, (w - sol_x - 25) // 4)
        hucre_h = max(42, (h - ust_y - 35) // 5)

        for c_idx, baslik in enumerate(sutun_basliklari):
            hx = sol_x + c_idx * hucre_w + hucre_w // 2
            cb.create_text(hx, ust_y - 14, text=baslik, fill=NEON_GOLD, font=("Consolas", 10, "bold"))

        for r_idx, s_baslik in enumerate(satir_basliklari):
            hy = ust_y + r_idx * hucre_h
            cb.create_text(sol_x - 10, hy + hucre_h // 2, text=s_baslik, anchor="e", fill="#E2E8F0", font=("Consolas", 9, "bold"))
            for c_idx, skor in enumerate(matris[r_idx]):
                hx = sol_x + c_idx * hucre_w
                renk = "#059669" if skor >= 75 else ("#D97706" if skor >= 35 else "#DC2626")
                cb.create_rectangle(hx + 3, hy + 3, hx + hucre_w - 3, hy + hucre_h - 3, fill=renk, outline="#0F172A")
                durum = f"%{skor} Veri" if skor >= 35 else f"🚨 BOŞLUK (%{skor})"
                cb.create_text(hx + hucre_w // 2, hy + hucre_h // 2, text=durum, fill="#FFFFFF", font=("Consolas", 9, "bold"))

    # =========================================================================
    # SEKME 6: ÇOK MODLU (MULTI-MODAL) OPTİK ALEV GÖRÜNTÜ İŞLEME & SPEKTRAL ANALİZ
    # =========================================================================
    def _kur_sekme_6_optik_alev_analizi(self) -> None:
        ust = ctk.CTkFrame(self.tab_optik, fg_color=CARD_BG, corner_radius=8)
        ust.pack(side="top", fill="x", padx=8, pady=6)

        ctk.CTkLabel(
            ust, text="📸 Sentetik NASA CIR Kamera Karesi:", font=ctk.CTkFont(size=12, weight="bold"), text_color=NEON_CYAN
        ).pack(side="left", padx=(10, 6), pady=8)

        self.optik_senaryo_var = ctk.StringVar(value=OptikAlevGoruntuAnalizoru.SENTETIK_SENARYOLAR[1])
        ctk.CTkOptionMenu(
            ust,
            variable=self.optik_senaryo_var,
            values=list(OptikAlevGoruntuAnalizoru.SENTETIK_SENARYOLAR),
            width=430,
            command=self._sentetik_alev_goruntusu_yukle
        ).pack(side="left", padx=6, pady=8)

        ctk.CTkButton(
            ust, text="📂 Gerçek Alev Görüntüsü Yükle (.png/.jpg)", width=250,
            fg_color="#1f538d", hover_color="#14375e", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._harici_alev_goruntusu_yukle
        ).pack(side="right", padx=10, pady=8)

        orta = ctk.CTkFrame(self.tab_optik, fg_color="transparent")
        orta.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        orta.grid_columnconfigure(0, weight=8)
        orta.grid_columnconfigure(1, weight=10)
        orta.grid_columnconfigure(2, weight=9)
        orta.grid_rowconfigure(0, weight=1)

        self.canvas_optik_img = tk.Canvas(orta, bg="#04070F", highlightthickness=1, highlightbackground=BORDER_CLR)
        self.canvas_optik_img.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.canvas_optik_profil = tk.Canvas(orta, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR)
        self.canvas_optik_profil.grid(row=0, column=1, sticky="nsew", padx=4)

        self.txt_optik_rapor = ctk.CTkTextbox(
            orta, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#050811", text_color="#E2E8F0", wrap="word"
        )
        self.txt_optik_rapor.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

    def _sentetik_alev_goruntusu_yukle(self, senaryo_adi: str) -> None:
        if not PIL_AVAILABLE:
            return
        img = OptikAlevGoruntuAnalizoru.sentetik_nasa_kamera_karesi_uret(senaryo_adi, boyut=300)
        self._optik_goruntuyu_isle_ve_ciz(img, kaynak_adi=senaryo_adi)

    def _harici_alev_goruntusu_yukle(self) -> None:
        if not PIL_AVAILABLE or Image is None:
            messagebox.showwarning("Uyarı", "Pillow kütüphanesi yüklü değil.")
            return
        yol = filedialog.askopenfilename(
            title="Alev Görüntüsü Seçin (Salt-Okunur)",
            filetypes=[("Görüntü Dosyaları", "*.png;*.jpg;*.jpeg;*.bmp"), ("Tüm Dosyalar", "*.*")]
        )
        if not yol:
            return
        try:
            img = Image.open(yol).convert("RGB").resize((300, 300))
            self._optik_goruntuyu_isle_ve_ciz(img, kaynak_adi=os.path.basename(yol))
        except Exception as exc:
            messagebox.showerror("Görüntü Okuma Hatası", str(exc))

    def _optik_goruntuyu_isle_ve_ciz(self, img: "Image.Image", kaynak_adi: str) -> None:
        analiz = OptikAlevGoruntuAnalizoru.goruntuyu_analiz_et(img)

        # 1. Sol Tuval: Kamera Görüntüsü ve Merkez Crosshair
        ci = self.canvas_optik_img
        ci.delete("all")
        wi = max(ci.winfo_width(), 320)
        hi = max(ci.winfo_height(), 340)
        if ImageTk is not None:
            self._optik_tk_img = ImageTk.PhotoImage(img)
            ci.create_image(wi // 2, hi // 2, image=self._optik_tk_img)
        ci.create_text(wi // 2, 18, text="📸 YÜKSEK HIZLI KAMERA KARESİ", fill=NEON_CYAN, font=("Consolas", 10, "bold"))
        ci.create_text(wi // 2, hi - 14, text=f"Küresellik Φ={analiz['kuresellik_indeksi']} | Çap={analiz['esdeger_cap_mm']} mm", fill=NEON_GOLD, font=("Consolas", 9, "bold"))

        # 2. Orta Tuval: Radyal RGB Işık Yoğunluk Profili I(r)
        cp = self.canvas_optik_profil
        cp.delete("all")
        wp = max(cp.winfo_width(), 380)
        hp = max(cp.winfo_height(), 340)
        x0, y0, x1, y1 = 48, hp - 36, wp - 24, 38
        cp.create_text((x0 + x1) // 2, 18, text="🌈 RADYAL SPEKTRAL YOĞUNLUK PROFİLİ I(r) [R=Soot, B=CH*]", fill=NEON_GOLD, font=("Consolas", 10, "bold"))
        cp.create_line(x0, y0, x1, y0, fill="#64748B", width=1.5)
        cp.create_line(x0, y0, x0, y1, fill="#64748B", width=1.5)
        cp.create_text(x0 - 18, y1 + 6, text="I(0-255)", fill="#94A3B8", font=("Consolas", 8))
        cp.create_text(x1 - 18, y0 + 14, text="Yarıçap r(mm)", fill="#94A3B8", font=("Consolas", 8))

        profil = analiz["radyal_profil"]
        if isinstance(profil, list) and len(profil) > 2:
            maks_r = max(profil[-1][0], 1.0)
            onceki_r, onceki_g, onceki_b = None, None, None
            for r_mm, rv, gv, bv in profil:
                px = x0 + (r_mm / maks_r) * (x1 - x0 - 8)
                pyr = y0 - (rv / 255.0) * (y0 - y1 - 8)
                pyg = y0 - (gv / 255.0) * (y0 - y1 - 8)
                pyb = y0 - (bv / 255.0) * (y0 - y1 - 8)
                if onceki_r is not None:
                    cp.create_line(onceki_r[0], onceki_r[1], px, pyr, fill="#FF4444", width=2.2)
                    cp.create_line(onceki_g[0], onceki_g[1], px, pyg, fill="#00FF88", width=1.8, dash=(3, 2))
                    cp.create_line(onceki_b[0], onceki_b[1], px, pyb, fill="#38BDF8", width=2.5)
                onceki_r, onceki_g, onceki_b = (px, pyr), (px, pyg), (px, pyb)

        # 3. Sağ Rapor Kutusu
        rapor = (
            "🔬 ÇOK MODLU (MULTI-MODAL) OPTİK ALEV ANALİZ RAPORU\n"
            + "=" * 54 + "\n"
            f"İncelenen Kare         : {kaynak_adi}\n"
            f"Küresellik İndeksi (Φ) : {analiz['kuresellik_indeksi']} (1.00 = Tam Küre 0g)\n"
            f"Eşdeğer Alev Çapı      : {analiz['esdeger_cap_mm']} mm\n"
            f"Tahmini Alev Sıcaklığı : {analiz['tahmini_sicaklik_k']} K\n"
            + "-" * 54 + "\n"
            "📊 SPEKTRAL EMİSYON DAĞILIMI:\n"
            f"   • Mavi CH* Kemilüminesans : %{analiz['mavi_kemiluminesans_yuzde']}\n"
            f"   • Sarı/Turuncu Soot Işıma : %{analiz['sari_soot_radyasyon_yuzde']}\n"
            f"   • Mor/UV Soğuk Alev (NTC) : %{analiz['mor_soguk_alev_yuzde']}\n"
            + "-" * 54 + "\n"
            f"🧠 OTOMATİK FİZİKSEL REJİM TEŞHİSİ:\n{analiz['rejim_teshisi']}\n\n"
            "📌 MÜHENDİSLİK YORUMU:\n"
            "• Küresellik Φ >= 0.88 ise kaldırma kuvveti (buoyancy) etkisizdir (0g).\n"
            "• Sarı Soot oranı > %20 ise radyatif ısı kaybı artar ve büyük damlacıklarda "
            "radyatif sönme sonrası görünmez Soğuk Alev (Cool Flame) oluşur [PSI-FLEX-002]."
        )
        self.txt_optik_rapor.delete("1.0", "end")
        self.txt_optik_rapor.insert("1.0", rapor)

    # =========================================================================
    # SEKME 7: İNTERAKTİF BİLGİ GRAFİĞİ (KNOWLEDGE GRAPH) & KABİN DİJİTAL İKİZİ
    # =========================================================================
    def _kur_sekme_7_bilgi_grafigi_ve_kabin_ikizi(self) -> None:
        ust = ctk.CTkFrame(self.tab_ikiz, fg_color=CARD_BG, corner_radius=8)
        ust.pack(side="top", fill="x", padx=8, pady=6)

        ctk.CTkLabel(
            ust, text="🛸 Kabin Dijital İkizi Ayarları — Yerçekimi:", font=ctk.CTkFont(size=12, weight="bold"), text_color=NEON_CYAN
        ).pack(side="left", padx=(10, 4), pady=8)

        self.slider_ikiz_g = ctk.CTkSlider(ust, from_=0.0, to=1.0, number_of_steps=25, width=140, command=lambda _: self._kg_ve_kabin_ikizi_ciz())
        self.slider_ikiz_g.set(0.0)
        self.slider_ikiz_g.pack(side="left", padx=4, pady=8)

        ctk.CTkLabel(ust, text="HVAC Fan Akışı (cm/s):", font=ctk.CTkFont(size=12, weight="bold"), text_color=NEON_GOLD).pack(
            side="left", padx=(12, 4), pady=8
        )
        self.slider_ikiz_hvac = ctk.CTkSlider(ust, from_=0.0, to=25.0, number_of_steps=25, width=140, command=lambda _: self._kg_ve_kabin_ikizi_ciz())
        self.slider_ikiz_hvac.set(0.0)
        self.slider_ikiz_hvac.pack(side="left", padx=4, pady=8)

        ctk.CTkButton(
            ust, text="🚨 0G Fan Kapalı Kör Nokta Testi", fg_color="#C62828", hover_color="#8E0000",
            command=lambda: (self.slider_ikiz_g.set(0.0), self.slider_ikiz_hvac.set(0.0), self._kg_ve_kabin_ikizi_ciz())
        ).pack(side="right", padx=6, pady=8)

        ctk.CTkButton(
            ust, text="🛰️ 0G Aktif HVAC Kanal Testi", fg_color="#00A86B", hover_color="#007F50",
            command=lambda: (self.slider_ikiz_g.set(0.0), self.slider_ikiz_hvac.set(14.0), self._kg_ve_kabin_ikizi_ciz())
        ).pack(side="right", padx=6, pady=8)

        orta = ctk.CTkFrame(self.tab_ikiz, fg_color="transparent")
        orta.pack(side="top", fill="both", expand=True, padx=8, pady=4)
        orta.grid_columnconfigure(0, weight=11)
        orta.grid_columnconfigure(1, weight=11)
        orta.grid_rowconfigure(0, weight=1)

        self.canvas_kg = tk.Canvas(orta, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR, cursor="hand2")
        self.canvas_kg.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.canvas_kg.bind("<Configure>", lambda _: self._kg_ve_kabin_ikizi_ciz())
        self.canvas_kg.bind("<Button-1>", self._kg_tiklandi)

        sag_bolum = ctk.CTkFrame(orta, fg_color="transparent")
        sag_bolum.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        sag_bolum.grid_rowconfigure(0, weight=12)
        sag_bolum.grid_rowconfigure(1, weight=8)
        sag_bolum.grid_columnconfigure(0, weight=1)

        self.canvas_kabin = tk.Canvas(sag_bolum, bg="#040812", highlightthickness=1, highlightbackground=BORDER_CLR, cursor="cross")
        self.canvas_kabin.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        self.canvas_kabin.bind("<Configure>", lambda _: self._kg_ve_kabin_ikizi_ciz())
        self.canvas_kabin.bind("<Button-1>", self._kabin_tiklandi)

        self.txt_ikiz_bilgi = ctk.CTkTextbox(
            sag_bolum, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#050811", text_color="#E2E8F0", wrap="word"
        )
        self.txt_ikiz_bilgi.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

    def _kg_tiklandi(self, event: tk.Event) -> None:
        for dugum_id, (x1, y1, x2, y2) in self._kg_kutu_koordinatlari.items():
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.secili_kg_dugum_id = dugum_id
                self._kg_ve_kabin_ikizi_ciz()
                break

    def _kabin_tiklandi(self, event: tk.Event) -> None:
        w = max(self.canvas_kabin.winfo_width(), 420)
        h = max(self.canvas_kabin.winfo_height(), 220)
        nx = min(0.85, max(0.12, event.x / w))
        ny = min(0.82, max(0.22, event.y / h))
        self.kabin_yangin_xy = (nx, ny)
        self._kg_ve_kabin_ikizi_ciz()

    def _kg_ve_kabin_ikizi_ciz(self) -> None:
        if not hasattr(self, "canvas_kg"):
            return

        # 1. SOL TUVAL: İNTERAKTİF NASA YANMA BİLGİ GRAFİĞİ (KNOWLEDGE GRAPH)
        ck = self.canvas_kg
        ck.delete("all")
        wk = max(ck.winfo_width(), 480)
        hk = max(ck.winfo_height(), 360)
        ck.create_text(
            wk // 2, 18,
            text="🕸️ İNTERAKTİF NASA YANMA BİLGİ GRAFİĞİ (Düğümlere Tıklayarak İnceleyin)",
            fill=NEON_CYAN, font=("Consolas", 10, "bold")
        )

        merkez_x, merkez_y = wk // 2, int(hk * 0.53)
        rx, ry = int(wk * 0.36), int(hk * 0.36)
        konumlar: Dict[str, Tuple[int, int]] = {}
        self._kg_kutu_koordinatlari.clear()

        for idx, d in enumerate(BILGI_GRAFIGI_DUGUMLERI):
            if d["id"] == "ISS_CIR":
                konumlar[d["id"]] = (merkez_x, merkez_y)
            else:
                aci = (2.0 * math.pi * (idx - 1)) / (len(BILGI_GRAFIGI_DUGUMLERI) - 1)
                konumlar[d["id"]] = (int(merkez_x + rx * math.cos(aci)), int(merkez_y + ry * math.sin(aci)))

        for k_id, h_id, iliski in BILGI_GRAFIGI_BAGLANTILARI:
            if k_id in konumlar and h_id in konumlar:
                x1, y1 = konumlar[k_id]
                x2, y2 = konumlar[h_id]
                aktif_bag = (self.secili_kg_dugum_id in (k_id, h_id))
                renk = NEON_GOLD if aktif_bag else "#334155"
                kalinlik = 2.5 if aktif_bag else 1.2
                ck.create_line(x1, y1, x2, y2, fill=renk, width=kalinlik)

        renk_haritasi = {"TESIS": "#0284C7", "DENEY": "#059669", "OLGU": "#7C3AED", "GUVENLIK": "#D97706"}
        secili_aciklama = ""
        for d in BILGI_GRAFIGI_DUGUMLERI:
            d_id = d["id"]
            dx, dy = konumlar[d_id]
            secili_mi = (d_id == self.secili_kg_dugum_id)
            if secili_mi:
                secili_aciklama = f"[{d['tur']}] {d['etiket']}: {d['aciklama']}"
            kutu_w, kutu_h = 66, 20
            x1, y1, x2, y2 = dx - kutu_w, dy - kutu_h, dx + kutu_w, dy + kutu_h
            self._kg_kutu_koordinatlari[d_id] = (x1, y1, x2, y2)
            dolgu = renk_haritasi.get(d["tur"], "#1E3A8A")
            cerceve_renk = "#FFFFFF" if secili_mi else "#0F172A"
            ck.create_rectangle(x1, y1, x2, y2, fill=dolgu, outline=cerceve_renk, width=2 if secili_mi else 1)
            ck.create_text(dx, dy, text=d["etiket"], fill="#FFFFFF", font=("Consolas", 8, "bold"))

        ck.create_text(wk // 2, hk - 14, text=secili_aciklama[:90], fill=NEON_GOLD, font=("Consolas", 8, "bold"))

        # 2. SAĞ ÜST TUVAL: UZAY ARACI KABİN DUMAN & SENSÖR DİJİTAL İKİZİ
        cc = self.canvas_kabin
        cc.delete("all")
        wc = max(cc.winfo_width(), 460)
        hc = max(cc.winfo_height(), 210)

        g_v = float(self.slider_ikiz_g.get())
        hvac_v = float(self.slider_ikiz_hvac.get())
        ikiz = MikroYercekimiFizikMotoru.kabin_duman_ve_sensor_dijital_ikizi_hesapla(g_v, hvac_v, self.kabin_yangin_xy)

        cc.create_text(
            wc // 2, 16,
            text="🛸 UZAY İSTASYONU KABİN DİJİTAL İKİZİ (Yangın Noktasını Değiştirmek İçin Tıklayın)",
            fill=NEON_CYAN, font=("Consolas", 9, "bold")
        )
        # Kabin dış duvarı
        kx0, ky0, kx1, ky1 = 28, 32, wc - 28, hc - 22
        cc.create_rectangle(kx0, ky0, kx1, ky1, outline="#475569", width=2)

        # Sensörler: 1) Tavan Dedektörü, 2) Sağ HVAC Dönüş Kanalı Dedektörü
        tavan_sx, tavan_sy = (kx0 + kx1) // 2, ky0 + 8
        hvac_sx, hvac_sy = kx1 - 10, (ky0 + ky1) // 2
        cc.create_rectangle(tavan_sx - 35, tavan_sy - 6, tavan_sx + 35, tavan_sy + 8, fill="#1E3A8A", outline=NEON_BLUE)
        cc.create_text(tavan_sx, tavan_sy + 1, text=f"TAVAN ({ikiz['t_tavan_sn']}s)", fill="#FFFFFF", font=("Consolas", 7, "bold"))

        cc.create_rectangle(hvac_sx - 68, hvac_sy - 14, hvac_sx, hvac_sy + 14, fill="#065F46", outline="#00FF88")
        cc.create_text(hvac_sx - 34, hvac_sy, text=f"HVAC ({ikiz['t_hvac_sn']}s)", fill="#FFFFFF", font=("Consolas", 7, "bold"))

        # Yangın kaynağı ve duman vektörü
        fx = int(kx0 + self.kabin_yangin_xy[0] * (kx1 - kx0))
        fy = int(ky0 + self.kabin_yangin_xy[1] * (ky1 - ky0))

        # Duman bulutu yayılımı (0g'de küresel/yatay, 1g'de yukarı)
        for i in range(1, 6):
            dx_step = int(i * hvac_v * 1.3)
            dy_step = int(-i * g_v * 22.0)
            r_bulut = 10 + i * 7
            cc.create_oval(
                fx + dx_step - r_bulut, fy + dy_step - r_bulut,
                fx + dx_step + r_bulut, fy + dy_step + r_bulut,
                outline="#94A3B8", width=1, dash=(3, 3)
            )

        cc.create_oval(fx - 10, fy - 10, fx + 10, fy + 10, fill=NEON_PINK, outline=NEON_GOLD, width=2)
        cc.create_text(fx, fy + 18, text=f"🔥 Yangın (Mid-IR: {ikiz['t_lokal_ir_sn']}s)", fill=NEON_GOLD, font=("Consolas", 8, "bold"))

        bilgi_metin = (
            f"🕸️ SEÇİLİ BİLGİ GRAFİĞİ DÜĞÜMÜ:\n   {secili_aciklama}\n"
            + "-" * 68 + "\n"
            f"🛸 KABİN DUMAN & DEDEKTÖR DİJİTAL İKİZ ANALİZİ [NTRS-ORION-010]:\n"
            f"   • Ortam: {g_v:.2f}g  |  HVAC Akışı: {hvac_v:.1f} cm/s  |  Dikey Konveksiyon: {ikiz['v_yukari_cm_s']} cm/s\n"
            f"   • Algılama Süreleri -> Tavan Dedektörü: {ikiz['t_tavan_sn']} sn | HVAC Dönüş Kanalı: {ikiz['t_hvac_sn']} sn | Lokal Mid-IR: {ikiz['t_lokal_ir_sn']} sn\n"
            f"   • Teşhis: {ikiz['teshis']}"
        )
        self.txt_ikiz_bilgi.delete("1.0", "end")
        self.txt_ikiz_bilgi.insert("1.0", bilgi_metin)

    # =========================================================================
    # SEKME 6: AI YANGIN GÜVENLİĞİ KARAR DESTEK & JÜRİ RAPORU ÜRETİCİ
    # =========================================================================
    def _kur_sekme_6_ai_karar_merkezi(self) -> None:
        ust = ctk.CTkFrame(self.tab_ai, fg_color=CARD_BG, corner_radius=8)
        ust.pack(side="top", fill="x", padx=8, pady=6)

        ctk.CTkLabel(ust, text="🧠 Sentez Motoru:", font=ctk.CTkFont(size=12, weight="bold"), text_color=NEON_CYAN).pack(
            side="left", padx=(10, 4), pady=6
        )
        self.ai_mod_var = ctk.StringVar(value="⚡ Yerleşik Deterministik Kanıt & Fizik Motoru (0 Halüsinasyon / Çevrimdışı)")
        ctk.CTkOptionMenu(
            ust,
            variable=self.ai_mod_var,
            values=[
                "⚡ Yerleşik Deterministik Kanıt & Fizik Motoru (0 Halüsinasyon / Çevrimdışı)",
                "🌐 Google Gemini Bulut API + NASA PSI RAG Motoru",
            ],
            width=430
        ).pack(side="left", padx=6, pady=6)

        senaryo_cerceve = ctk.CTkFrame(self.tab_ai, fg_color="transparent")
        senaryo_cerceve.pack(side="top", fill="x", padx=8, pady=2)
        for i in range(4):
            senaryo_cerceve.grid_columnconfigure(i, weight=1, uniform="ai_sen")

        hazir_sorular = [
            (
                "🧪 1. ISS O2 Artışı & Fan Anomalisi",
                "ISS kapalı yanma modülünde sıcaklık 635 K iken Oksijen (O2) oranı %20.8'den %23.6'ya yükseldi ve CO 55 ppm ölçüldü. Bu telemetri anomalisini NASA BASS/Saffire kanıtlarıyla analiz et."
            ),
            (
                "🟣 2. FLEX-2 Görünmez Soğuk Alev",
                "Mikroçekimde (0g) n-Heptan damlacık yanmasında görünür alev söndükten sonra sıcaklık 640 K seviyesinde sabit kaldı ve CO 290 ppm'e yükseldi. FLEX-2 soğuk alev (cool flame) fiziğini ve yeniden tutuşma riskini analiz et."
            ),
            (
                "🌙 3. Artemis Ay (0.16g) %34 O2 Paradoksu",
                "Ay yerçekiminde (0.16g) ve %34 O2, 56.5 kPa keşif atmosferinde PMMA ve Nomex malzemelerin yanıcılık davranışını SoFIE deney kanıtlarına göre Dünya (1g) ile karşılaştır."
            ),
            (
                "🚿 4. ISS Halon Yasağı & Su Sisi",
                "Uzay aracı kabininde elektrik kaynaklı yangında neden Halon 1301 kullanılmadığını, İnce Su Sisi (Fine Water Mist) ve CO2 söndürme protokolünü kanıt kodlarıyla raporla."
            ),
        ]
        for idx, (baslik, metin) in enumerate(hazir_sorular):
            ctk.CTkButton(
                senaryo_cerceve, text=baslik, height=30, fg_color="#374151", hover_color="#1F2937",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda m=metin: (self.txt_ai_soru.delete("1.0", "end"), self.txt_ai_soru.insert("1.0", m), self.ai_analiz_calistir())
            ).grid(row=0, column=idx, sticky="ew", padx=3, pady=3)

        giris_bar = ctk.CTkFrame(self.tab_ai, fg_color="transparent")
        giris_bar.pack(side="top", fill="x", padx=8, pady=4)

        self.txt_ai_soru = ctk.CTkTextbox(
            giris_bar, height=72, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#050811", text_color=NEON_CYAN
        )
        self.txt_ai_soru.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.txt_ai_soru.insert("1.0", hazir_sorular[0][1])

        ctk.CTkButton(
            giris_bar, text="🔥 Kanıt-Odaklı\nAnaliz Üret", width=165, height=72,
            fg_color="#C62828", hover_color="#8E0000", font=ctk.CTkFont(size=13, weight="bold"),
            command=self.ai_analiz_calistir
        ).pack(side="right")

        self.txt_ai_cikti = ctk.CTkTextbox(
            self.tab_ai, font=ctk.CTkFont(family="Consolas", size=12), fg_color="#040812", text_color="#00FF88", wrap="word"
        )
        self.txt_ai_cikti.pack(side="top", fill="both", expand=True, padx=8, pady=(2, 8))
        self.ai_analiz_calistir()

    def ai_analiz_calistir(self) -> None:
        soru = self.txt_ai_soru.get("1.0", "end-1c").strip()
        if not soru:
            return
        bulut_mu = "Gemini" in self.ai_mod_var.get()

        def _worker() -> None:
            yanit = self.ai_motoru.kanit_odakli_analiz_uret(soru, bulut_kullan=bulut_mu)
            self.after(0, lambda: (self.txt_ai_cikti.delete("1.0", "end"), self.txt_ai_cikti.insert("1.0", yanit)))

        threading.Thread(target=_worker, daemon=True).start()

    def _api_anahtar_penceresi_ac(self) -> None:
        pencere = ctk.CTkToplevel(self)
        pencere.title("🔑 Google Gemini API Anahtarı (İsteğe Bağlı)")
        pencere.geometry("480x210")
        pencere.attributes("-topmost", True)

        ctk.CTkLabel(
            pencere,
            text="Yerleşik Deterministik Kanıt Motoru API olmadan %100 çevrimdışı çalışır.\n"
                 "İsterseniz bulut RAG sentezi için Google Gemini API anahtarı girebilirsiniz:",
            font=ctk.CTkFont(size=12), wraplength=440
        ).pack(padx=16, pady=(16, 8))

        entry = ctk.CTkEntry(pencere, width=420, placeholder_text="AIzaSy...", show="*")
        entry.pack(padx=16, pady=6)
        if self.ai_motoru.api_key:
            entry.insert(0, self.ai_motoru.api_key)

        def _kaydet() -> None:
            basarili = self.ai_motoru.api_anahtari_guncelle(entry.get())
            messagebox.showinfo(
                "Bilgi",
                "Gemini API anahtarı aktif edildi." if basarili else "Çevrimdışı Deterministik Kanıt Motoru aktif.",
                parent=pencere
            )
            pencere.destroy()

        ctk.CTkButton(pencere, text="Kaydet", fg_color="#00A86B", command=_kaydet).pack(pady=10)

    def juri_raporunu_dosyaya_kaydet(self) -> None:
        varsayilan_ad = f"NASA_FlameInFreefall_Rapor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        yol = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=varsayilan_ad,
            filetypes=[("Markdown Raporu", "*.md"), ("Metin Dosyası", "*.txt")]
        )
        if not yol:
            return
        ai_raporu = self.txt_ai_cikti.get("1.0", "end-1c").strip()
        malzeme_ozet = self.txt_malzeme_rapor.get("1.0", "end-1c").strip()
        bosluk_ozet = self.txt_bosluk_detay.get("1.0", "end-1c").strip()

        tam_metin = (
            "# 🚀 NASA SPACE APPS CHALLENGE 2026 — FLAME IN FREEFALL TEKNİK JÜRİ RAPORU\n\n"
            f"**Oluşturulma Tarihi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "## 1. KANIT-ODAKLI (EVIDENCE-FIRST) AI YANGIN GÜVENLİĞİ ANALİZİ\n"
            f"```text\n{ai_raporu}\n```\n\n"
            "## 2. UZAY ARACI MALZEME YANICILIK ATLASI (0G vs AY 0.16G)\n"
            f"```text\n{malzeme_ozet}\n```\n\n"
            "## 3. DERİN UZAY ARAŞTIRMA BOŞLUĞU MATRİSİ (RESEARCH GAP FINDER)\n"
            f"```text\n{bosluk_ozet}\n```\n"
        )
        with open(yol, "w", encoding="utf-8") as f:
            f.write(tam_metin)
        messagebox.showinfo("Başarılı", f"Kapsamlı NASA Jüri Raporu kaydedildi:\n{yol}")

    def interaktif_html_juri_sunumu_olustur(self) -> None:
        varsayilan_ad = f"NASA_SpaceApps2026_Jury_Dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        yol = filedialog.asksaveasfilename(
            defaultextension=".html",
            initialfile=varsayilan_ad,
            filetypes=[("HTML5 İnteraktif Jüri Panosu", "*.html")]
        )
        if not yol:
            return
        ai_raporu = self.txt_ai_cikti.get("1.0", "end-1c").strip()
        malzeme_ozet = self.txt_malzeme_rapor.get("1.0", "end-1c").strip()
        bosluk_ozet = self.txt_bosluk_detay.get("1.0", "end-1c").strip()
        optik_ve_kabin = (
            self.txt_optik_rapor.get("1.0", "end-1c").strip()
            + "\n\n"
            + self.txt_kabin_ikiz_rapor.get("1.0", "end-1c").strip()
        )
        NasaTelemetriVeVeriAvcisi.html_juri_sunumu_olustur(
            dosya_yolu=yol,
            ai_raporu=ai_raporu,
            malzeme_ozet=malzeme_ozet,
            bosluk_ozet=bosluk_ozet,
            optik_ozet=optik_ve_kabin,
        )
        try:
            webbrowser.open(f"file:///{os.path.abspath(yol).replace(os.sep, '/')}")
        except Exception:
            pass
        messagebox.showinfo(
            "HTML5 Jüri Sunumu Hazır",
            f"İnteraktif HTML5 Jüri Sunum Panosu oluşturuldu ve tarayıcıda açıldı:\n{yol}"
        )

    def _sistem_telemetri_guncelle(self) -> None:
        if not self.winfo_exists():
            return
        try:
            if PSUTIL_AVAILABLE:
                cpu = psutil.cpu_percent(interval=None)
                ram_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2)
                self.lbl_sistem_ram.configure(text=f"CPU: %{cpu:.0f} | Uygulama RAM: {ram_mb:.0f} MB")
        except Exception:
            pass
        self.after(3000, self._sistem_telemetri_guncelle)


if __name__ == "__main__":
    app = FlameInFreefallApp()
    app.mainloop()
