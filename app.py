"""Vaistų ir papildų sąveikų tikrintuvas – Streamlit programėlė.

Paleidimas:  streamlit run app.py
"""
from __future__ import annotations

import html
import io
import json
import os

import pandas as pd
import streamlit as st

from src.checker import LEVEL_LT, Checker, display_name

ROOT = os.path.dirname(os.path.abspath(__file__))
COL = {"Major": "#C8382C", "Moderate": "#D98E04", "Minor": "#3E8E5E", None: "#8C8C8C"}
BG = {"Major": "#FDECEA", "Moderate": "#FFF6E0", "Minor": "#EAF5EE", None: "#F3F3F3"}
ICON = {"Major": "🔴", "Moderate": "🟠", "Minor": "🟢", None: "⚪"}
SRC_HELP = {
    "DDInter": "Kuruota klinikinė DDInter duomenų bazė",
    "DDInter + AI": "Sąveika DDInter yra, sunkumą prognozavo AI modelis",
    "Literatūra": "Rankiniu būdu įtrauktas literatūros įrašas",
    "Taisyklės": "Farmakologinė taisyklė (galima, nepatvirtinta sąveika)",
    "Nėra duomenų": "Duomenų apie šią porą nerasta",
}
EXAMPLES = {
    "Skausmas + kraujo skystinimas": "Nurofen 400 mg\nVarfarinas\nŽuvų taukai",
    "Depresija + papildai": "Sertralinas\nJonažolė\nTramadolis",
    "Širdis ir inkstai": "Ramiprilis\nFurozemidas\nIbumetin\nKalis",
    "Statinas + greipfrutas": "Simvastatinas 40 mg\nKlaritromicinas\nGreipfrutų sultys",
    "Skydliaukė + mineralai": "Euthyrox 50\nKalcis\nGeležis\nOmeprazolas",
}

st.set_page_config(page_title="Vaistų sąveikų tikrintuvas", page_icon="💊", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.card {border-radius: 10px; padding: 14px 16px 10px 16px; margin: 0 0 12px 0;
       border: 1px solid #e6e6e6; border-left-width: 6px; background: #fff;}
.card h4 {margin: 0 0 4px 0; font-size: 1.05rem;}
.badge {display:inline-block; padding: 2px 10px; border-radius: 999px; color: #fff;
        font-size: .78rem; font-weight: 600; margin-right: 6px; vertical-align: middle;}
.src {display:inline-block; padding: 1px 8px; border-radius: 999px; background:#eef1f5;
      color:#334; font-size: .74rem; margin-right: 6px; vertical-align: middle;}
.meta {color:#666; font-size:.82rem; margin: 2px 0 8px 0;}
.row {margin: 3px 0; font-size: .93rem;}
.row b {color:#333;}
.caution {background:#FFF8E1; border:1px solid #F2D27A; border-radius:8px; padding:6px 10px;
          margin-top:8px; font-size:.86rem; color:#5c4500;}
.prob {display:flex; height:16px; border-radius:6px; overflow:hidden; margin:6px 0 2px 0;
       font-size:.7rem; color:#fff; font-weight:600;}
.prob div {display:flex; align-items:center; justify-content:center; white-space:nowrap;}
.stat {border-radius:10px; padding:10px 12px; text-align:center;}
.stat .n {font-size:1.7rem; font-weight:700; line-height:1.1;}
.stat .l {font-size:.8rem; color:#444;}
.entry {padding:6px 0; border-bottom:1px solid #f0f0f0; font-size:.93rem;}
.small {font-size:.8rem; color:#777;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Įkeliama duomenų bazė ir AI modelis…")
def get_checker() -> Checker:
    return Checker(ROOT)


checker = get_checker()
E = html.escape

# ------------------------------------------------------------------ Šoninė juosta
with st.sidebar:
    st.markdown("### ⚙️ Rodymo nustatymai")
    show_minor = st.checkbox("Rodyti mažos rizikos sąveikas", value=True)
    show_nodata = st.checkbox("Rodyti poras, kurių duomenų nėra", value=True)
    show_ai = st.checkbox("Rodyti AI prognozės paaiškinimą", value=True)
    st.divider()
    st.markdown("### 🎨 Žymėjimas")
    st.markdown(
        f"{ICON['Major']} **Didelė rizika** – derinio dažniausiai reikia vengti\n\n"
        f"{ICON['Moderate']} **Vidutinė** – gali reikėti stebėti ar keisti dozę\n\n"
        f"{ICON['Minor']} **Maža** – kliniškai mažai reikšminga\n\n"
        f"{ICON[None]} **Nėra duomenų** – tai NEREIŠKIA, kad derinys saugus")
    st.divider()
    st.caption("🚑 Pasireiškus sunkiems simptomams – skambinkite **112**.\n\n"
               "☎️ Apsinuodijimų informacija (VVKT): **+370 5 236 2052**")

# ------------------------------------------------------------------ Antraštė
st.markdown("## 💊 Vaistų ir papildų sąveikų tikrintuvas")
st.info("**Informacinis mokomasis įrankis.** Jis nepakeičia gydytojo ar vaistininko konsultacijos. "
        "Nekeiskite ir nenutraukite paskirto gydymo vien remdamiesi šiais rezultatais.", icon="ℹ️")

tab_check, tab_model, tab_about = st.tabs(["🔍 Tikrinimas", "📊 AI modelis", "📚 Apie ir ribotumai"])

def _clear():
    st.session_state.input_text = ""
    st.session_state.overrides = {}
    st.session_state.pop("ran", None)


def _load_example(txt: str):
    st.session_state.input_text = txt
    st.session_state.overrides = {}
    st.session_state.ran = True


def render_results(picked):
    """Atpažinimas, santrauka, sąveikų kortelės ir atsisiuntimas."""
    entries = checker.resolve(st.session_state.input_text, st.session_state.overrides, picked)

    # ---------------- Atpažinimas
    st.markdown("#### 2. Kaip atpažinti įvesti preparatai")
    status_icon = {"exact": "✅", "approx": "🟡", "suggest": "❓", "not_in_db": "⛔",
                   "unknown": "❌"}
    for i, e in enumerate(entries):
        r = e.res
        subs = " + ".join(display_name(s) for s in r.substances) if r.substances else ""
        if r.status in ("exact", "approx"):
            body = f"<b>{E(e.query)}</b> → {E(subs)}"
        elif r.status == "not_in_db":
            body = f"<b>{E(e.query)}</b> → {E(r.label)}"
        else:
            body = f"<b>{E(e.query)}</b>"
        note = f"<div class='small'>⚠️ {E(r.note)}</div>" if r.note else ""
        st.markdown(f"<div class='entry'>{status_icon[r.status]} {body}{note}</div>",
                    unsafe_allow_html=True)
        if r.status == "suggest":
            opts = ["— nepasirinkta (praleisti) —"] + [s for s, _ in r.suggestions]
            choice = st.selectbox(f"Ar turėjote omenyje? („{e.query}“)", opts, key=f"sug_{i}")
            if choice != opts[0] and st.session_state.overrides.get(e.query) != choice:
                st.session_state.overrides[e.query] = choice
                st.rerun()

    n_subs = len({s for e in entries for s in e.substances})
    problems = [e for e in entries if e.res.status in ("unknown", "suggest", "not_in_db")]
    if problems:
        st.warning(f"**{len(problems)}** įraš. nepavyko patikrinti (neatpažinti arba nėra "
                   "duomenų bazėje). Jų sąveikos į rezultatus **neįtrauktos** – rezultatai "
                   "gali būti neišsamūs.", icon="⚠️")
    if n_subs < 2:
        st.info("Sąveikoms patikrinti reikia bent dviejų atpažintų medžiagų.")
        return

    results, groups = checker.check(entries)
    found = [r for r in results if r.level]
    nodata = [r for r in results if not r.level]

    # ---------------- Santrauka
    st.markdown("#### 3. Rezultatų santrauka")
    cnt = {l: sum(r.level == l for r in found) for l in ("Major", "Moderate", "Minor")}
    cols = st.columns(4)
    for col, (lvl, lab) in zip(cols, [("Major", "Didelė rizika"), ("Moderate", "Vidutinė"),
                                      ("Minor", "Maža"), (None, "Nėra duomenų")]):
        n = cnt[lvl] if lvl else len(nodata)
        col.markdown(f"<div class='stat' style='background:{BG[lvl]}'>"
                     f"<div class='n' style='color:{COL[lvl]}'>{n}</div>"
                     f"<div class='l'>{ICON[lvl]} {lab}</div></div>", unsafe_allow_html=True)
    n_ai = sum(r.source == "DDInter + AI" for r in found)
    n_rule = sum(r.source == "Taisyklės" for r in found)
    st.caption(f"Patikrinta porų: {len(results)} · iš jų sunkumą prognozavo AI: {n_ai} · "
               f"tik taisyklėmis nustatytų: {n_rule}")

    for g in groups:
        st.error(f"**{g.title}** ({LEVEL_LT[g.level].lower()}): {g.text}\n\n**Ką daryti:** {g.advice}",
                 icon="🚨")

    # ---------------- Kortelės
    st.markdown("#### 4. Rastos sąveikos")
    shown = [r for r in found if show_minor or r.level != "Minor"]
    if not shown:
        st.success("Duomenų bazėje reikšmingų sąveikų tarp atpažintų medžiagų nerasta. "
                   "Tai nereiškia, kad derinys tikrai saugus – pasitarkite su vaistininku.")
    for r in shown:
        lvl = r.level
        rows = []
        for h in r.rules:
            rows.append(f"<div class='row'><b>Galimas poveikis:</b> {E(h['effect'])}</div>"
                        f"<div class='row'><b>Mechanizmas:</b> {E(h['mechanism'])}</div>"
                        f"<div class='row'><b>Ką daryti:</b> {E(h['advice'])}</div>")
        if r.extra:
            rows.insert(0, f"<div class='row'><b>Galimas poveikis:</b> {E(r.extra['effect'])}</div>"
                           f"<div class='row'><b>Mechanizmas:</b> {E(r.extra['mechanism'])}</div>"
                           f"<div class='row small'>Šaltinis: {E(r.extra['source'])}</div>")
        if r.ai_probs:
            p = r.ai_probs
            segs = "".join(
                f"<div style='width:{p[l] * 100:.1f}%;background:{COL[l]}'>"
                f"{(LEVEL_LT[l].split()[0] + ' ' + f'{p[l]:.0%}') if p[l] > 0.12 else ''}</div>"
                for l in ("Minor", "Moderate", "Major"))
            rows.append(f"<div class='row'><b>🤖 AI prognozė (sunkumo tikimybės):</b></div>"
                        f"<div class='prob'>{segs}</div>")
        cautions = "".join(f"<div>⚠️ {E(c)}</div>" for c in r.cautions)
        caution_html = f"<div class='caution'>{cautions}</div>" if cautions else ""
        st.markdown(
            f"<div class='card' style='border-left-color:{COL[lvl]}'>"
            f"<h4>{ICON[lvl]} {E(display_name(r.a))} + {E(display_name(r.b))}</h4>"
            f"<span class='badge' style='background:{COL[lvl]}'>{LEVEL_LT[lvl]}"
        f"{' · AI prognozė' if r.source == 'DDInter + AI' else ''}"
        f"{' · galima' if r.source == 'Taisyklės' else ''}</span>"
            f"<span class='src' title='{E(SRC_HELP[r.source])}'>Šaltinis: {E(r.source)}</span>"
            f"<div class='meta'>Iš įrašų: „{E(r.from_a)}“ ir „{E(r.from_b)}“</div>"
            + "".join(rows) + caution_html + "</div>", unsafe_allow_html=True)
        if show_ai and r.ai_explain:
            with st.expander("Kodėl modelis taip mano? (SHAP paaiškinimas)"):
                df = pd.DataFrame(r.ai_explain, columns=["Požymis", "Indėlis"])
                st.caption("Teigiamas indėlis didina prognozuotos klasės tikimybę, neigiamas – mažina.")
                st.bar_chart(df.set_index("Požymis"), horizontal=True, height=220)

    if show_nodata and nodata:
        with st.expander(f"⚪ Poros, apie kurias duomenų nėra ({len(nodata)})"):
            st.caption("Duomenų bazėje šių porų nėra ir jos nepateko į jokią rizikos taisyklę. "
                       "Tai dažniausiai reiškia, kad reikšminga sąveika nežinoma, bet "
                       "**negarantuoja saugumo** – ypač papildams ir retiems vaistams.")
            for r in nodata:
                extra = f" <span class='small'>– {E(r.cautions[0])}</span>" if r.cautions else ""
                st.markdown(f"<div class='entry'>⚪ {E(display_name(r.a))} + "
                            f"{E(display_name(r.b))}{extra}</div>", unsafe_allow_html=True)

    # ---------------- Atsisiuntimas
    rep = pd.DataFrame([{
        "Medžiaga A": display_name(r.a), "Medžiaga B": display_name(r.b),
        "Sunkumas": LEVEL_LT.get(r.level, "Nėra duomenų"), "Šaltinis": r.source,
        "Galimas poveikis": " | ".join(h["effect"] for h in r.rules) or
        (r.extra["effect"] if r.extra else ""),
        "Įspėjimai": " | ".join(r.cautions),
        "AI tikimybės": json.dumps({k: round(v, 3) for k, v in r.ai_probs.items()})
        if r.ai_probs else "",
    } for r in results])
    buf = io.StringIO()
    rep.to_csv(buf, index=False)
    st.download_button("⬇️ Atsisiųsti rezultatus (CSV)", buf.getvalue().encode("utf-8-sig"),
                       "saveiku_ataskaita.csv", "text/csv")


# ================================================================== TIKRINIMAS
with tab_check:
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""
    if "overrides" not in st.session_state:
        st.session_state.overrides = {}

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("#### 1. Įveskite vaistus ir papildus")
        st.text_area(
            "Kiekvieną preparatą rašykite naujoje eilutėje (arba atskirkite kableliais). "
            "Tinka lietuviški, angliški ir prekiniai pavadinimai, dozės nebūtinos.",
            key="input_text", height=170,
            placeholder="pvz.:\nNurofen 400 mg\nVarfarinas\nŽuvų taukai\nJonažolė")
        picked = st.multiselect(
            "…arba pasirinkite iš sąrašo (galima ieškoti rašant)",
            options=sorted(checker.all_names, key=lambda s: display_name(s).lower()),
            format_func=display_name, placeholder="Pradėkite rašyti pavadinimą…")
        b1, b2 = st.columns([1, 1])
        run = b1.button("🔍 Tikrinti sąveikas", type="primary", width="stretch")
        b2.button("🗑️ Išvalyti", width="stretch", on_click=_clear)
    with c2:
        st.markdown("#### Greiti pavyzdžiai")
        for name, txt in EXAMPLES.items():
            st.button(name, width="stretch", key=f"ex_{name}", on_click=_load_example, args=(txt,))
        st.caption("Patarimas: įrašykite ir papildus (vitaminus, mineralus, žolelių preparatus), "
                   "alkoholį, greipfrutų sultis – jie taip pat gali sąveikauti.")

    if run:
        st.session_state.ran = True

    if st.session_state.get("ran") and (st.session_state.input_text.strip() or picked):
        render_results(picked)
    elif st.session_state.get("ran"):
        st.info("Įveskite bent du preparatus.")


# ================================================================== MODELIS
with tab_model:
    mpath = os.path.join(ROOT, "reports", "metrics.json")
    if not os.path.exists(mpath):
        st.warning("Modelio ataskaita nerasta. Paleiskite `python -m src.train`.")
    else:
        m = json.load(open(mpath, encoding="utf-8"))
        ds = m["dataset"]
        st.markdown("#### Ką daro AI modelis?")
        st.markdown(
            f"DDInter turi **{ds['unknown']:_}** porų, kurių sąveika užfiksuota, bet **sunkumas "
            "nenurodytas**. AI modelis (LightGBM) pagal vaistų ATC grupes, farmakologines klases, "
            "taisykles ir vaistų sąveikų istoriją prognozuoja tokių porų sunkumą. Mokyta su "
            f"**{ds['labeled']:_}** porų su žinomu sunkumu.".replace("_", "\u00a0"))
        best = m["experiment_random_split"][m["best_model"]]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tikslumas (accuracy)", f"{best['accuracy']:.1%}")
        k2.metric("Macro F1", f"{best['f1_macro']:.3f}")
        k3.metric("Weighted F1", f"{best['f1_weighted']:.3f}")
        k4.metric("Macro F1 su naujais vaistais", f"{m['experiment_cold_drugs'][m['best_model_cold']]['f1_macro']:.3f}")
        st.markdown(open(os.path.join(ROOT, "reports", "metrics_table.md"),
                         encoding="utf-8").read().replace("## ", "##### "))
        figs = [("01_klasiu_pasiskirstymas.png", "Klasių pasiskirstymas"),
                ("02_saveiku_skaicius.png", "Sąveikų skaičius vienam vaistui"),
                ("03_konfuzija_baseline.png", "Konfuzijos matrica: baseline"),
                ("04_konfuzija_lightgbm.png", "Konfuzijos matrica: LightGBM"),
                ("05_mokymosi_kreive.png", "Mokymosi kreivė"),
                ("06_modeliu_palyginimas.png", "Modelių palyginimas"),
                ("07_shap_svarbiausi.png", "Svarbiausi požymiai (SHAP)")]
        for i in range(0, len(figs), 2):
            cc = st.columns(2)
            for c, (f, cap) in zip(cc, figs[i:i + 2]):
                p = os.path.join(ROOT, "reports", "figures", f)
                if os.path.exists(p):
                    c.image(p, caption=cap, width="stretch")

# ================================================================== APIE
with tab_about:
    st.markdown(open(os.path.join(ROOT, "docs", "apie.md"), encoding="utf-8").read())
