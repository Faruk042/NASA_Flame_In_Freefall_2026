# -*- coding: utf-8 -*-
"""
NASA Space Apps Challenge 2026
"Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data"
İnteraktif Web Panosu (streamlit_app.py)

Çalıştırma:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ai_uzman_asistan import FlameInFreefallAIEngine
from literatur_ai import FENOMEN_DESENLERI, PROGRAM_DESENLERI, YERCEKIMI_DESENLERI, motor_al
from mikroyercekimi_fizik_motoru import MikroYercekimiFizikMotoru
from nasa_psi_veritabani import (
    ARASTIRMA_BOSLUKLARI,
    KanitOdakliAramaMotoru,
    NASA_PSI_DENEY_ARSIVI,
    UZAY_MALZEME_ATLASI,
)
from optik_alev_goruntu_analizoru import OptikAlevGoruntuAnalizoru, PIL_AVAILABLE
from veri_laboratuvari import (
    csv_bayttan_yukle,
    d2_yasasi_uydur,
    ozet_istatistik,
    pearson,
    saglam_anomali_tespiti,
    sentetik_damlacik_verisi,
    sutun_rolu_tahmin_et,
    veri_setini_csv_metnine_cevir,
)

st.set_page_config(
    page_title="NASA Space Apps 2026 — Flame in Freefall",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner="NASA NTRS Korpusu (673 yayın + 80 tam metin) indeksleniyor...")
def _cached_ntrs_motor():
    return motor_al()


@st.cache_resource
def _cached_ai_engine():
    return FlameInFreefallAIEngine()


@st.cache_resource
def _cached_psi_arama():
    return KanitOdakliAramaMotoru()


def main() -> None:
    ntrs_motor = _cached_ntrs_motor()
    ai_engine = _cached_ai_engine()
    psi_arama = _cached_psi_arama()

    # Yan Menü (Sidebar)
    with st.sidebar:
        st.markdown("## 🚀 NASA SPACE APPS 2026")
        st.caption("**Flame in Freefall:** AI-Powered Fire Safety Insights from Microgravity Combustion Data")
        st.divider()
        st.metric("Doğrulanmış NTRS Yayını", f"{len(ntrs_motor.kayitlar)} Makale")
        st.metric("Tam Metin İndeksi (.txt)", "80 NASA Raporu")
        st.metric("Yapılandırılmış PSI/NTRS Kanıtı", f"{len(NASA_PSI_DENEY_ARSIVI)} Deney + {len(UZAY_MALZEME_ATLASI)} Malzeme")
        st.divider()
        gemini_key = st.text_input(
            "🔑 İsteğe Bağlı Gemini API Anahtarı",
            value=os.getenv("GEMINI_API_KEY", ""),
            type="password",
            help="Boş bırakılırsa %100 çevrimdışı BM25 + MMR Kanıt Motoru çalışır.",
        )
        if gemini_key:
            ai_engine.api_anahtari_guncelle(gemini_key)

    st.title("🔥 FLAME IN FREEFALL — Mikroçekim Yanma & Uzay Yangın Güvenliği AI Platformu")
    st.markdown(
        "**Gerçek NASA NTRS & PSI Açık Verisi (673 Akademik Yayın + 80 Tam Metin)** • "
        "**BM25 + MMR Çıkarımsal AI Özetleme** • **$d^2$-Yasası & Soğuk Alev Fiziği** • "
        "**0g / Ay 0.16g / Mars 0.38g Karar Destek Sistemi**"
    )

    sekmeler = st.tabs([
        "📚 1. NTRS Literatür AI & Özetleyici",
        "🔥 2. d²-Yasası, Soğuk Alev & Monte Carlo",
        "🧪 3. PSI CSV & d² Regresyon Laboratuvarı",
        "🛡️ 4. Malzeme Yanıcılık Atlası (0g vs 0.16g)",
        "🔭 5. Kanıt Yoğunluğu & Araştırma Boşlukları",
        "📸 6. Optik Alev Analizi & Kabin Dijital İkizi",
    ])

    # =========================================================================
    # SEKME 1: GERÇEK NTRS LİTERATÜR AI & MMR ÖZETLEYİCİ
    # =========================================================================
    with sekmeler[0]:
        st.subheader("📚 Gerçek NASA NTRS Literatür Arama, Sıralama ve Kanıt-Kısıtlı AI Sentezi")
        ornek_sorular = [
            "Ay yerçekiminde (0.16g) malzemeler neden Dünya'dan daha yanıcı olabilir?",
            "n-Heptan damlacık yanmasında görünmez soğuk alev (cool flame) ve yeniden tutuşma nasıl oluşur?",
            "Saffire deneylerinde yüksek oksijen ve düşük basınçta alev yayılım hızı nasıl değişti?",
            "Mikroçekimde duman dedektörleri neden tavan yerine havalandırma kanallarına yerleştirilmelidir?",
        ]
        secili_ornek = st.selectbox("⚡ Hızlı Araştırma Sorusu Seçin:", ["(Kendi sorunuzu yazın)"] + ornek_sorular)
        varsayilan_soru = ornek_sorular[0] if secili_ornek == "(Kendi sorunuzu yazın)" else secili_ornek

        col_s1, col_s2, col_s3 = st.columns([3, 1, 1])
        with col_s1:
            soru = st.text_input("🔍 Araştırma Sorusu veya Anahtar Kelime (Türkçe / İngilizce):", value=varsayilan_soru)
        with col_s2:
            sec_prog = st.selectbox("Program Filtresi:", ["Tümü"] + list(PROGRAM_DESENLERI.keys()))
        with col_s3:
            sec_grav = st.selectbox("Yerçekimi Filtresi:", ["Tümü"] + list(YERCEKIMI_DESENLERI.keys()))

        prog_f = None if sec_prog == "Tümü" else sec_prog
        grav_f = None if sec_grav == "Tümü" else sec_grav

        yanit = ntrs_motor.soru_yanitla(soru, ust_k=10, program=prog_f, yercekimi=grav_f)
        if gemini_key and st.button("🌐 Gemini ile Kanıt-Kısıtlı Sentez Üret (Atıf Denetimli)"):
            with st.spinner("Gemini yalnızca getirilen NTRS kanıtları üzerinde sentez yapıyor..."):
                yanit = ntrs_motor.gemini_ile_sentezle(yanit, gemini_key)

        c_m1, c_m2, c_m3 = st.columns(3)
        c_m1.metric("Kanıt Güveni", yanit.guven_duzeyi, yanit.guven_aciklamasi)
        c_m2.metric("Eşleşen NTRS Makalesi", f"{len(yanit.sonuclar)} Yayın")
        c_m3.metric("Çıkarılan Sayısal Bulgu", f"{len(yanit.sayisal_bulgular)} Ölçüm/Parametre")

        if yanit.kapsam_uyarilari:
            for u in yanit.kapsam_uyarilari:
                st.warning(u)

        if yanit.llm_yaniti:
            st.markdown("### 🌐 Gemini Kanıt-Kısıtlı Sentez")
            st.info(yanit.llm_yaniti)
            if yanit.atif_denetimi:
                ad = yanit.atif_denetimi
                st.caption(
                    f"🛡️ **Atıf Doğrulama Denetimi:** Toplam {ad['toplam_atif']} atıftan "
                    f"{len(ad['gecerli'])} tanesi getirilen NTRS kanıt kümesinde doğrulandı "
                    f"(Doğrulama oranı: %{ad['dogrulama_orani'] * 100:.0f})."
                )

        col_oz, col_cik = st.columns(2)
        with col_oz:
            st.markdown("### 📌 MMR Çıkarımsal Özet (Doğrudan NASA NTRS Özetlerinden)")
            if yanit.ozet:
                for o in yanit.ozet:
                    st.markdown(
                        f"- \"{o.cumle}\" — [**[NTRS:{o.ntrs_id}]**](https://ntrs.nasa.gov/citations/{o.ntrs_id})"
                    )
            else:
                st.caption("Bu sorgu için özet cümlesi bulunamadı.")

        with col_cik:
            st.markdown("### 🛡️ Yangın Güvenliği Mühendislik Çıkarımları")
            for c in yanit.guvenlik_cikarimlari:
                destek_link = ", ".join(
                    f"[NTRS:{k.ntrs_id}]({k.url})" for k in c["destekleyen"]
                )
                st.markdown(f"- **{c['baslik']}** ({c['fenomen']}): {c['aciklama']} ({destek_link})")

        if yanit.sayisal_bulgular:
            st.markdown("### 📐 Makalelerden Otomatik Çıkarılan Sayısal Bulgular")
            df_bulgu = pd.DataFrame([
                {
                    "Nicelik": b.nicelik,
                    "Değer": b.deger_metni,
                    "Kaynak Türü": b.kaynak_turu,
                    "NTRS Kimliği": f"NTRS:{b.ntrs_id}",
                    "Doğrulama URL": f"https://ntrs.nasa.gov/citations/{b.ntrs_id}",
                    "Kaynak Cümle": b.cumle,
                }
                for b in yanit.sayisal_bulgular
            ])
            st.dataframe(df_bulgu, use_container_width=True, hide_index=True)

        st.markdown("### 📑 BM25 + Kaynak Kalitesi ile Sıralanmış Gerçek NASA NTRS Yayınları")
        df_sonuc = pd.DataFrame([
            {
                "Sıra": idx,
                "NTRS ID": s.kayit.ntrs_id,
                "Skor": s.skor,
                "Yıl": s.kayit.yil,
                "Başlık": s.kayit.baslik,
                "Yazarlar": s.kayit.kisa_atif(),
                "Programlar": ", ".join(s.profil.programlar) or "-",
                "Yerçekimi": ", ".join(s.profil.yercekimi) or "-",
                "NTRS Bağlantısı": s.kayit.url,
            }
            for idx, s in enumerate(yanit.sonuclar, 1)
        ])
        st.dataframe(df_sonuc, use_container_width=True, hide_index=True)

        with st.expander("🤖 Tam Entegre Kanıt + Fizik + Monte Carlo Raporu Üret"):
            tam_rapor = ai_engine.kanit_odakli_analiz_uret(soru, bulut_kullan=bool(gemini_key))
            st.code(tam_rapor, language="text")

    # =========================================================================
    # SEKME 2: d²-YASASI, SOĞUK ALEV & MONTE CARLO SİMÜLATÖRÜ
    # =========================================================================
    with sekmeler[1]:
        st.subheader("🔥 Sıvı Damlacık d²-Yasası, FLEX-2 Soğuk Alev (Cool Flame) ve Zorlanmış Akış Simülatörü")
        c1, c2, c3, c4, c5 = st.columns(5)
        yakit_sec = c1.selectbox("Yakıt Türü:", list(MikroYercekimiFizikMotoru.YAKIT_KATALOGU.keys()))
        g_sec = c2.slider("Yerçekimi (g):", 0.0, 1.0, 0.0, 0.02)
        o2_sec = c3.slider("Oksijen (%O2):", 12.0, 36.0, 21.0, 0.5)
        p_sec = c4.slider("Basınç (kPa):", 40.0, 120.0, 101.3, 1.0)
        d0_sec = c5.slider("Başlangıç Çapı d0 (mm):", 1.0, 5.0, 3.2, 0.1)
        akis_sec = st.slider("Kabin Ventilasyon / Fan Akış Hızı (cm/s):", 0.0, 45.0, 2.0, 0.5)

        analiz = MikroYercekimiFizikMotoru.damlacik_yanma_analizi(
            yakit_adi=yakit_sec,
            yercekimi_g=g_sec,
            oksijen_yuzde=o2_sec,
            basinc_kpa=p_sec,
            d0_mm=d0_sec,
            akis_hizi_cm_s=akis_sec,
        )
        mc = MikroYercekimiFizikMotoru.monte_carlo_belirsizlik_analizi(
            yakit_adi=yakit_sec,
            yercekimi_g=g_sec,
            oksijen_yuzde=o2_sec,
            basinc_kpa=p_sec,
            d0_mm=d0_sec,
            akis_hizi_cm_s=akis_sec,
        )

        st.info(f"**Teşhis Edilen Alev Rejimi:** {analiz['durum_metni']}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Sıcak Alev Sabiti (K_hot)", f"{analiz['k_sicak']} mm²/s")
        m2.metric("Soğuk Alev Sabiti (K_cool)", f"{analiz['k_soguk']} mm²/s")
        m3.metric("Alev Sıcaklığı (Tf / T_cool)", f"{analiz['t_sicak_k']} K / {analiz['t_soguk_k']} K")
        m4.metric("Monte Carlo Yanma Süresi (Medyan)", f"{mc['tb_medyan']} sn", f"P05={mc['tb_p05']}s | P95={mc['tb_p95']}s")
        m5.metric("Soğuk Alev Olasılığı & CO", f"%{mc['cool_flame_olasilik_yuzde']}", f"P95 CO: {mc['co_p95']:.0f} ppm")

        g_col1, g_col2 = st.columns(2)
        with g_col1:
            zs = analiz["zaman_serisi"]
            fig_d2 = go.Figure()
            fig_d2.add_trace(go.Scatter(
                x=[p[0] for p in zs],
                y=[p[1] for p in zs],
                mode="lines+markers",
                name="d²(t) [mm²]",
                line=dict(color="#00F5D4", width=3),
            ))
            if analiz["cool_flame_olusur"]:
                fig_d2.add_vline(
                    x=analiz["radyatif_gecis_sn"],
                    line_dash="dash",
                    line_color="#A855F7",
                    annotation_text="Radyatif Sönme -> Soğuk Alev Geçişi",
                )
            fig_d2.update_layout(
                title="d²-Yasası Zaman Serisi: d²(t) = d0² - K·t",
                xaxis_title="Zaman t (sn)",
                yaxis_title="Çap Karesi d² (mm²)",
                template="plotly_dark",
                height=380,
            )
            st.plotly_chart(fig_d2, use_container_width=True)

        with g_col2:
            egri = MikroYercekimiFizikMotoru.akis_hizi_yayilim_egrisi_hesapla(g_sec, o2_sec)
            fig_flow = go.Figure()
            fig_flow.add_trace(go.Scatter(
                x=[p[0] for p in egri],
                y=[p[1] for p in egri],
                mode="lines+markers",
                name="Yayılım Hızı (mm/s)",
                line=dict(color="#FF3366", width=3),
            ))
            fig_flow.add_vline(x=akis_sec, line_dash="dot", line_color="#FFD166", annotation_text=f"Seçili Akış: {akis_sec} cm/s")
            fig_flow.update_layout(
                title="BASS/SoFIE Zorlanmış Akış vs Katı Alev Yayılım Hızı (Quenching -> Peak -> Blow-Off)",
                xaxis_title="Kabin Havalandırma Akış Hızı (cm/s)",
                yaxis_title="Alev Yayılım Hızı (mm/s)",
                template="plotly_dark",
                height=380,
            )
            st.plotly_chart(fig_flow, use_container_width=True)

    # =========================================================================
    # SEKME 3: DENEY VERİSİ & d² REGRESYON LABORATUVARI (PSI CSV)
    # =========================================================================
    with sekmeler[2]:
        st.subheader("🧪 NASA PSI CSV Deney Verisi & d²-Yasası Doğrusal Regresyon Laboratuvarı")
        st.markdown(
            "NASA Physical Sciences Informatics ([psi.nasa.gov](https://psi.nasa.gov)) arşivinden indirdiğiniz "
            "gerçek damlacık yanması CSV dosyalarını yükleyebilir veya yöntem doğrulaması için açıkça etiketlenmiş "
            "sentetik veri setini kullanabilirsiniz."
        )
        yuklenen = st.file_uploader("📂 CSV Dosyası Yükle (Salt-Okunur):", type=["csv", "txt"])
        if yuklenen is not None:
            vs = csv_bayttan_yukle(yuklenen.getvalue(), ad=yuklenen.name)
            st.success(f"Gerçek kullanıcı CSV verisi yüklendi: **{vs.ad}** ({vs.satir_sayisi()} satır)")
        else:
            vs = sentetik_damlacik_verisi(K=0.74, d0_mm=3.1, gurultu_mm2=0.07)
            st.warning(f"⚠️ **SENTETİK DEMO VERİSİ AKTİF:** {vs.aciklama}. Gerçek analiz için yukarıdan PSI CSV dosyası yükleyin.")

        roller = sutun_rolu_tahmin_et(vs.sutunlar)
        rc1, rc2, rc3, rc4 = st.columns(4)
        zaman_sut = rc1.selectbox("Zaman Sütunu (t):", vs.sutunlar, index=vs.sutunlar.index(roller["zaman"]) if roller["zaman"] in vs.sutunlar else 0)
        varsayilan_cap = roller["cap_kare"] or roller["cap"] or vs.sutunlar[-1]
        cap_sut = rc2.selectbox("Çap (d) veya Çap² (d²) Sütunu:", vs.sutunlar, index=vs.sutunlar.index(varsayilan_cap) if varsayilan_cap in vs.sutunlar else min(1, len(vs.sutunlar) - 1))
        girdi_d2_mi = rc3.checkbox("Seçili sütun zaten d² (mm²) mi?", value=(roller["cap_kare"] == cap_sut))
        atla_bas = rc4.slider("Tutuşma Geçişi Atla (Başlangıç %):", 0, 30, 8) / 100.0

        uyum = d2_yasasi_uydur(
            vs.veri[zaman_sut],
            vs.veri[cap_sut],
            girdi_cap_kare=girdi_d2_mi,
            baslangic_atla_orani=atla_bas,
        )

        u1, u2, u3, u4 = st.columns(4)
        u1.metric("Tahmin Edilen Yanma Sabiti K", f"{uyum.K_mm2_s:.4f} mm²/s", f"%95 GA: [{uyum.K_guven_araligi[0]:.4f}, {uyum.K_guven_araligi[1]:.4f}]")
        u2.metric("Başlangıç Çapı d0", f"{uyum.d0_mm:.3f} mm", f"d0² = {uyum.d0_kare_mm2:.3f} mm²")
        u3.metric("Belirlilik Katsayısı (R²)", f"{uyum.r2:.5f}")
        u4.metric("Kök Ortalama Kare Hata (RMSE)", f"{uyum.rmse:.4f} mm²", f"n = {uyum.n} nokta")

        t_dizisi = vs.veri[zaman_sut]
        d2_dizisi = [v if girdi_d2_mi else v ** 2 for v in vs.veri[cap_sut]]
        tahmin_dizisi = [uyum.d0_kare_mm2 - uyum.K_mm2_s * t for t in t_dizisi]

        fig_reg = go.Figure()
        fig_reg.add_trace(go.Scatter(x=t_dizisi, y=d2_dizisi, mode="markers", name="Ölçüm Noktaları d²(t)", marker=dict(color="#38BDF8", size=7)))
        fig_reg.add_trace(go.Scatter(x=t_dizisi, y=tahmin_dizisi, mode="lines", name=f"En Küçük Kareler Uyumu (K={uyum.K_mm2_s:.3f} mm²/s, R²={uyum.r2:.4f})", line=dict(color="#FF3366", width=3)))
        fig_reg.update_layout(title="d²-Yasası Doğrusal Regresyon Uyumu", xaxis_title="Zaman (sn)", yaxis_title="d² (mm²)", template="plotly_dark", height=400)
        st.plotly_chart(fig_reg, use_container_width=True)

        st.download_button(
            "💾 Aktif Veri Setini CSV Olarak İndir",
            data=veri_setini_csv_metnine_cevir(vs).encode("utf-8"),
            file_name=vs.ad,
            mime="text/csv",
        )

    # =========================================================================
    # SEKME 4: UZAY ARACI MALZEME YANICILIK ATLASI
    # =========================================================================
    with sekmeler[3]:
        st.subheader("🛡️ NASA-STD-6001B Uzay Aracı Malzeme Yanıcılık Atlası (1g Dünya vs 0g ISS vs 0.16g Ay)")
        mc1, mc2 = st.columns(2)
        mat_o2 = mc1.slider("Kabin Oksijen Konsantrasyonu (%O2):", 14.0, 38.0, 21.0, 0.5)
        mat_g = mc2.slider("Hedef Görev Yerçekimi (g):", 0.0, 1.0, 0.16, 0.02)

        sirali_mat = psi_arama.malzemeleri_atmosfere_gore_degerlendir(mat_o2, mat_g)
        fig_mat = go.Figure()
        isimler = [m.malzeme_adi.split("(")[0].strip() for m in UZAY_MALZEME_ATLASI]
        fig_mat.add_trace(go.Bar(name="1.0g Dünya LOC (%O2)", x=isimler, y=[m.loc_dunya_1g for m in UZAY_MALZEME_ATLASI], marker_color="#38BDF8"))
        fig_mat.add_trace(go.Bar(name="0.0g ISS LOC (%O2)", x=isimler, y=[m.loc_mikro_0g for m in UZAY_MALZEME_ATLASI], marker_color="#F59E0B"))
        fig_mat.add_trace(go.Bar(name="0.16g Ay LOC (%O2 - En Kritik!)", x=isimler, y=[m.loc_ay_016g for m in UZAY_MALZEME_ATLASI], marker_color="#FF3366"))
        fig_mat.add_hline(y=mat_o2, line_dash="dash", line_color="#00FF88", annotation_text=f"Seçili Kabin O2: %{mat_o2:.1f}")
        fig_mat.update_layout(barmode="group", title="Malzemelerin Kritik Oksijen Sınırı (LOC %O2) Karşılaştırması", yaxis_title="Minimum Oksijen Sınırı LOC (%O2)", template="plotly_dark", height=420)
        st.plotly_chart(fig_mat, use_container_width=True)

        df_mat = pd.DataFrame([
            {
                "Malzeme": r["malzeme"].malzeme_adi,
                "Durum": r["durum"],
                "Risk Puanı": r["risk_puan"],
                "Aktif LOC (%O2)": r["aktif_loc"],
                "Yayılım Hızı (mm/s)": r["aktif_hiz"],
                "Toksik Gazlar": r["malzeme"].toksik_gazlar,
                "Söndürme Protokolü": r["malzeme"].sondurme_protokolu,
            }
            for r in sirali_mat
        ])
        st.dataframe(df_mat, use_container_width=True, hide_index=True)

    # =========================================================================
    # SEKME 5: KANIT YOĞUNLUĞU MATRİSİ & ARAŞTIRMA BOŞLUĞU BULUCU
    # =========================================================================
    with sekmeler[4]:
        st.subheader("🔭 673 Gerçek NTRS Makalesinden Hesaplanan Kanıt Yoğunluğu Matrisi ve Araştırma Boşlukları")
        satirlar, sutunlar, matris = ntrs_motor.kanit_matrisi()
        fig_hm = go.Figure(data=go.Heatmap(
            z=matris,
            x=sutunlar,
            y=satirlar,
            colorscale="YlOrRd",
            text=matris,
            texttemplate="%{text} yayın",
        ))
        fig_hm.update_layout(
            title="Fenomen × Yerçekimi Rejimi Gerçek NTRS Yayın Yoğunluğu (Düşük Hücreler = Araştırma Boşluğu)",
            template="plotly_dark",
            height=460,
        )
        st.plotly_chart(fig_hm, use_container_width=True)

        st.markdown("### 🚨 Korpustan Otomatik Tespit Edilen Kısmi Yerçekimi / Mikroçekim Araştırma Boşlukları")
        df_gaps = pd.DataFrame(ntrs_motor.arastirma_bosluklari())
        st.dataframe(df_gaps, use_container_width=True, hide_index=True)

        st.markdown("### 🛰️ Önerilen Yeni ISS / Ay / Mars Deney Tasarımları")
        for b in ARASTIRMA_BOSLUKLARI:
            with st.expander(f"[{b.bosluk_kodu}] {b.baslik} — ({b.hedef_ortam} | Risk: {b.risk_seviyesi})"):
                st.markdown(f"**Eksik Parametreler:** {b.eksik_parametreler}")
                st.markdown(f"**Bilimsel Açıklama:** {b.aciklama}")
                st.markdown(f"**Önerilen Deney Tasarımı:** {b.onerilen_deney_tasarimi}")

    # =========================================================================
    # SEKME 6: OPTİK ALEV GÖRÜNTÜ İŞLEME & KABİN DİJİTAL İKİZİ
    # =========================================================================
    with sekmeler[5]:
        col_o1, col_o2 = st.columns(2)
        with col_o1:
            st.subheader("📸 Çok Modlu Optik Alev Görüntü İşleme (CIR Kamera)")
            if PIL_AVAILABLE:
                senaryo = st.selectbox(
                    "Sentetik NASA CIR Kamera Karesi Seçin:",
                    list(OptikAlevGoruntuAnalizoru.SENTETIK_SENARYOLAR),
                )
                img = OptikAlevGoruntuAnalizoru.sentetik_nasa_kamera_karesi_uret(senaryo)
                sonuc_opt = OptikAlevGoruntuAnalizoru.goruntuyu_analiz_et(img)
                st.image(img, caption=f"{senaryo} — Küresellik Φ={sonuc_opt['kuresellik_indeksi']} | Eşdeğer Çap={sonuc_opt['esdeger_cap_mm']} mm", width=280)
                st.info(sonuc_opt["rejim_teshisi"])
                o_c1, o_c2, o_c3 = st.columns(3)
                o_c1.metric("Mavi CH* Kemilüminesans", f"%{sonuc_opt['mavi_kemiluminesans_yuzde']}")
                o_c2.metric("Sarı Soot Radyasyonu", f"%{sonuc_opt['sari_soot_radyasyon_yuzde']}")
                o_c3.metric("Mor Soğuk Alev (UV/IR)", f"%{sonuc_opt['mor_soguk_alev_yuzde']}")
            else:
                st.warning("Pillow kurulu değil.")

        with col_o2:
            st.subheader("🛸 Uzay Aracı Kabin Duman & Dedektör Dijital İkizi")
            ik_g = st.slider("Kabin Yerçekimi (g):", 0.0, 1.0, 0.0, 0.02, key="ik_g")
            ik_hvac = st.slider("HVAC Dönüş Hava Akışı (cm/s):", 0.0, 25.0, 0.5, 0.5, key="ik_hvac")
            ikiz = MikroYercekimiFizikMotoru.kabin_duman_ve_sensor_dijital_ikizi_hesapla(ik_g, ik_hvac)
            st.warning(ikiz["teshis"])
            k1, k2, k3 = st.columns(3)
            k1.metric("Tavan Dedektörü Alarm Süresi", f"{ikiz['t_tavan_sn']} sn")
            k2.metric("HVAC Dönüş Kanalı Alarm Süresi", f"{ikiz['t_hvac_sn']} sn")
            k3.metric("Lokal Mid-IR Sensör Süresi", f"{ikiz['t_lokal_ir_sn']} sn")


if __name__ == "__main__":
    main()
