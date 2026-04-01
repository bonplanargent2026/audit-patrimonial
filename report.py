"""
report.py — v2.2 clone AXA complet — Rapport patrimonial complet style AXA / My Campus Patrimoine.
Pages :
  1. Couverture
  2. Rappel de situation (famille, carrière)
  3. Vos actifs (tableau par détenteur)
  4. Vos passifs + budget annuel
  5. Analyse de structure (répartition patrimoine)
  6. Analyse financière (revenus/charges détaillés, indicateurs)
  7. Prévoyance & retraite
  8. Analyse qualitative & recommandations
  9. Annexes fiscales
"""
import io
import os
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF

from calculations import BilanPatrimonial
from succession import (
    simuler_succession,
    projeter_patrimoine,
    _droits_ligne_directe,
)
_DIR        = os.path.dirname(os.path.abspath(__file__))
COVER_IMAGE = os.path.join(_DIR, "Image_pour_bilan_pat2.png")

# ── Palette ───────────────────────────────────────────────────────────────────
C_NAVY  = (30,  58,  95)
C_TEAL  = (44, 122, 123)
C_RED   = (196,  30,  58)
C_LGREY = (245, 245, 245)
C_MGREY = (220, 225, 232)
C_ORANGE = (237, 125,  49)
C_WHITE = (255, 255, 255)
C_GREEN = (34,  84,  61)
C_DRED  = (116,  42,  42)

# Barème IR 2024
TRANCHES = [
    (11497,  0.00),
    (16206,  0.11),
    (47836,  0.30),
    (205736, 0.41),
    (999999999, 0.45),
]

C_GOLD  = (180, 140,  30)


# ─────────────────────────────────────────────
#  Nettoyage texte PDF
# ─────────────────────────────────────────────

def _clean(t: str) -> str:
    MAP = {
        "\u20ac":"EUR","\u202f":" ","\u00a0":" ","\u2018":"'","\u2019":"'",
        "\u201c":'"',"\u201d":'"',"\u2013":"-","\u2014":"-","\u2026":"...",
        "\u00b0":" deg","\u2265":">=","\u2264":"<=",
        "\u00e9":"e","\u00e8":"e","\u00ea":"e","\u00eb":"e",
        "\u00e0":"a","\u00e2":"a","\u00f4":"o","\u00fb":"u","\u00ee":"i",
        "\u00e7":"c","\u00e9":"e","\u00ef":"i","\u00f9":"u",
    }
    for c, r in MAP.items():
        t = t.replace(c, r)
    return t


# ═══════════════════════════════════════════════════════════════
#  GRAPHIQUES STYLE AXA — Couleurs et structure exactes
# ═══════════════════════════════════════════════════════════════

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np

AXA_DONUT_FAMILLE = ["#43425D","#9AB9EA","#A07390","#F3E1C8","#848F9E"]
AXA_DONUT_HORIZON = ["#43425D","#9AB9EA","#A1A0AE"]
AXA_DONUT_RISQUE  = ["#848F9E","#43425D","#9AB9EA"]
C_NAVY2  = (30,  58,  95)
C_RED2   = (196, 30,  58)
C_TEAL2  = (44,  122, 123)
C_LGREY2 = (245, 245, 245)
C_MGREY2 = (220, 225, 232)
C_WHITE2 = (255, 255, 255)
C_GREEN2 = (34,  84,  61)
C_DRED2  = (116, 42,  42)
C_ORANGE2= (237, 125, 49)


def _fig2bytes(fig):
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    buf.seek(0); data = buf.read(); plt.close(fig); return data


def _donut_axa(labels, values, colors, title="", figsize=(6.0, 4.2)):
    vals = [v for v in values if v > 0]
    lbls = [l for l, v in zip(labels, values) if v > 0]
    cols = [c for c, v in zip(colors, values) if v > 0]
    if not vals:
        return b""
    total = sum(vals)
    fig, ax = plt.subplots(figsize=figsize)
    wedges, _, auts = ax.pie(
        vals, labels=None, colors=cols,
        autopct=lambda p: "{:.0f} %".format(p) if p > 2 else "",
        startangle=90,
        wedgeprops={"linewidth": 2, "edgecolor": "white"},
        pctdistance=0.74,
    )
    for at in auts:
        at.set_color("white"); at.set_fontsize(9); at.set_fontweight("bold")
    ax.add_patch(plt.Circle((0, 0), 0.52, color="white"))
    ll = ["{} ({:.0f} %)\n{:,.0f} EUR".format(l, v/total*100, v).replace(",", " ")
          for l, v in zip(lbls, vals)]
    ax.legend(wedges, ll, loc="center left", bbox_to_anchor=(1.02, 0.5),
              fontsize=8, frameon=False, handlelength=1.2, handleheight=1.2)
    ax.set_aspect("equal")
    if title:
        ax.set_title(title, fontsize=10, fontweight="bold", color="#43425D", pad=8)
    fig.tight_layout()
    return _fig2bytes(fig)


def _courbe_patrimoine_axa(projection, figsize=(8, 3.4)):
    if not projection:
        return b""
    ann = [p.annee for p in projection]
    br  = [p.actif_brut for p in projection]
    ne  = [p.actif_net for p in projection]
    pa  = [p.passif for p in projection]
    fig, ax = plt.subplots(figsize=figsize)
    ax.fill_between(ann, br, alpha=0.08, color="#43425D")
    ax.plot(ann, br, color="#43425D", linewidth=2.5, label="Actif brut",
            marker="o", markersize=3)
    ax.plot(ann, ne, color="#9AB9EA", linewidth=2,   label="Actif net",
            marker="o", markersize=3)
    ax.plot(ann, pa, color="#c41e3a", linewidth=1.5, label="Passif",
            linestyle="--", alpha=0.7)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: "{:.1f}M".format(x/1e6) if x >= 1e6 else "{:.0f}k".format(x/1000)))
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#ddd")
    ax.tick_params(colors="#666", labelsize=8)
    ax.grid(axis="y", alpha=0.3, linestyle=":", color="#ccc")
    fig.tight_layout()
    return _fig2bytes(fig)


def _courbe_budget_axa(revenus, charges, epargne, annee, figsize=(7.5, 3.0)):
    fig, ax = plt.subplots(figsize=figsize)
    solde = max(0, revenus - charges)
    cats  = ["Revenus totaux", "Charges totales", "Solde"]
    vals  = [revenus, charges, solde]
    cols  = ["#43425D", "#c41e3a", "#2c7a7b"]
    bars  = ax.bar(cats, vals, color=cols, width=0.5, edgecolor="white")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+revenus*0.01,
                "{:,.0f} EUR".format(v).replace(",", " "),
                ha="center", va="bottom", fontsize=8, color="#444", fontweight="bold")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: "{:.0f}k".format(x/1000)))
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#ddd")
    ax.tick_params(colors="#666", labelsize=8)
    ax.grid(axis="y", alpha=0.3, linestyle=":", color="#ccc")
    ax.set_title("Budget annuel {}".format(annee), fontsize=9,
                 color="#43425D", fontweight="bold")
    fig.tight_layout()
    return _fig2bytes(fig)


def _bareme_ir_axa(rfr, parts, figsize=(7, 1.3)):
    if rfr <= 0:
        return b""
    qf = rfr / parts if parts > 0 else rfr
    max_val = 250_000
    widths_raw = [11497, 16206, 47836, 205736-75539, max_val-281275]
    colors  = ["#DDF0FF","#9EBED9","#658FAF","#0C3147","#2F5975"]
    fgcols  = ["#0C3147","#0C3147","white","white","white"]
    tauxs   = ["0 %","11 %","30 %","41 %","45 %"]
    total_w = sum(max(0, w) for w in widths_raw)
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    x = 0.0
    for w, bg, fg, taux in zip(widths_raw, colors, fgcols, tauxs):
        if w <= 0:
            continue
        rw = max(0, w) / total_w * 0.88 if total_w > 0 else 0.17
        rect = mpatches.FancyBboxPatch((x, 0.2), rw, 0.6,
            boxstyle="square,pad=0", lw=0.5, ec="white", fc=bg)
        ax.add_patch(rect)
        ax.text(x+rw/2, 0.5, taux, ha="center", va="center",
                fontsize=8, color=fg, fontweight="bold")
        x += rw
    pos_c = min(qf / max_val * 0.88, 0.86) if max_val > 0 else 0.5
    ax.annotate("Votre QF", xy=(pos_c, 0.2), xytext=(pos_c, 0.94),
                ha="center", fontsize=7, color="#c41e3a",
                arrowprops=dict(arrowstyle="-", color="#c41e3a", lw=1.2))
    fig.tight_layout(pad=0.1)
    return _fig2bytes(fig)


def _ps_axa(base_ps, figsize=(7, 2.0)):
    if base_ps <= 0:
        return b""
    csg    = base_ps * 0.092
    crds   = base_ps * 0.005
    psolid = base_ps * 0.075
    total  = csg + crds + psolid
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize,
                                    gridspec_kw={"width_ratios": [1, 1.7]})
    wedges, _, auts = ax1.pie(
        [csg, crds, psolid], colors=["#338EED","#A1D750","#F8BC30"],
        autopct=lambda p: "{:.0f}%".format(p),
        startangle=90, wedgeprops={"linewidth": 2, "edgecolor": "white"},
        pctdistance=0.72)
    for at in auts:
        at.set_color("white"); at.set_fontsize(7); at.set_fontweight("bold")
    ax1.add_patch(plt.Circle((0,0), 0.52, color="white"))
    ax1.text(0, 0, "{:,.0f}".format(total).replace(",", " "),
             ha="center", va="center", fontsize=7, fontweight="bold", color="#43425D")
    ax1.set_aspect("equal")
    ax2.axis("off")
    rows = [
        ["Composante","Base","Taux","Montant"],
        ["CSG",    "{:,.0f} EUR".format(base_ps).replace(",", " "), "9,20 %",  "{:,.0f} EUR".format(csg).replace(",", " ")],
        ["CRDS",   "{:,.0f} EUR".format(base_ps).replace(",", " "), "0,50 %",  "{:,.0f} EUR".format(crds).replace(",", " ")],
        ["Prel.sol.","{:,.0f} EUR".format(base_ps).replace(",", " "),"7,50 %", "{:,.0f} EUR".format(psolid).replace(",", " ")],
        ["TOTAL",  "", "17,20 %", "{:,.0f} EUR".format(total).replace(",", " ")],
    ]
    tbl = ax2.table(cellText=rows[1:], colLabels=rows[0], loc="center", cellLoc="right")
    tbl.auto_set_font_size(False); tbl.set_fontsize(7); tbl.scale(1, 1.4)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#ddd")
        if r == 0:
            cell.set_facecolor("#43425D"); cell.set_text_props(color="white", fontweight="bold")
        elif r == len(rows)-1:
            cell.set_facecolor("#E1EBF7"); cell.set_text_props(fontweight="bold")
        else:
            cell.set_facecolor("white" if r % 2 else "#f8f8f8")
    fig.tight_layout()
    return _fig2bytes(fig)


def _pression_fiscale_axa(ir, ps, ifi, rev_total, figsize=(8, 2.6)):
    items = []
    if ir  > 0: items.append(("PAS / Acomptes IR",     ir,  "#43425D"))
    if ps  > 0: items.append(("Prelevements sociaux",  ps,  "#9AB9EA"))
    if ifi > 0: items.append(("IFI",                   ifi, "#c41e3a"))
    dispo = max(0, rev_total - ir - ps - ifi)
    if dispo > 0:
        items.append(("Revenu disponible net", dispo, "#e8e8e8"))
    if not items:
        return b""
    fig, ax = plt.subplots(figsize=figsize)
    left = 0
    for lbl, val, col in items:
        ax.barh([""], val, left=left, color=col, edgecolor="white",
                linewidth=1.5, height=0.5)
        pct = val / rev_total * 100 if rev_total > 0 else 0
        if pct > 5:
            ax.text(left+val/2, 0,
                    "{}\n{:,.0f} EUR".format(lbl, val).replace(",", " "),
                    ha="center", va="center", fontsize=7,
                    color="white" if col != "#e8e8e8" else "#444",
                    fontweight="bold")
        left += val
    if rev_total > 0:
        pct_tot = (ir + ps + ifi) / rev_total * 100
        ax.set_title("Pression fiscale globale : {:.2f} % des revenus".format(pct_tot),
                     fontsize=9, fontweight="bold", color="#43425D")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, _: "{:.0f}k".format(x/1000)))
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(left=False, labelsize=8)
    fig.tight_layout()
    return _fig2bytes(fig)


def _prev_deces_barre_axa(besoin, couvert, label_couvert, titre, figsize=(7.5, 1.1)):
    if besoin <= 0:
        return b""
    fig, ax = plt.subplots(figsize=figsize)
    ax.barh([""], besoin,              color="#E1EBF7", edgecolor="#ccc",
            linewidth=0.8, height=0.6)
    ax.barh([""], min(couvert, besoin),color="#43425D", edgecolor="white",
            linewidth=1, height=0.6)
    if couvert > 0:
        ax.text(min(couvert, besoin)/2, 0,
                "{:,.0f} EUR".format(couvert).replace(",", " "),
                va="center", ha="center", fontsize=7.5, color="white",
                fontweight="bold")
    ax.text(besoin*1.01, 0, "{:,.0f} EUR".format(besoin).replace(",", " "),
            va="center", fontsize=7.5, color="#666")
    ax.set_xlim(0, besoin * 1.28)
    ax.set_title(titre, fontsize=9, fontweight="bold", color="#43425D")
    ax.axis("off")
    fig.tight_layout(pad=0.3)
    return _fig2bytes(fig)


def _incapacite_courbe_axa(rev_j, nom, g_j1_j3, g_j4_j363, g_j364, figsize=(7.5, 3.0)):
    if rev_j <= 0:
        return b""
    fig, ax = plt.subplots(figsize=figsize)
    x   = [0,   3,   3,   363,  363,  1095]
    y_g = [g_j1_j3, g_j1_j3, g_j4_j363, g_j4_j363, g_j364, g_j364]
    ax.fill_between(x, y_g, alpha=0.15, color="#43425D", step="pre")
    ax.step(x, y_g, color="#43425D", linewidth=2.5, label="Garanties", where="pre")
    ax.hlines(rev_j, 0, 1095, colors="#c41e3a", linestyles="--",
              linewidth=1.8, label="Besoin")
    for xv, lbl in [(3,"J3"), (363,"J363"), (1095,"J1095")]:
        ax.axvline(xv, color="#ddd", linewidth=0.8, linestyle=":")
        ax.text(xv, rev_j*1.06, lbl, ha="center", fontsize=7, color="#888")
    ax.set_xlim(0, 1095); ax.set_ylim(0, rev_j*1.25)
    ax.set_xlabel("Jours d arret de travail", fontsize=8)
    ax.set_ylabel("EUR / jour", fontsize=8)
    ax.set_title("Garanties incapacite de {}".format(nom),
                 fontsize=9, fontweight="bold", color="#43425D")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#ddd")
    ax.tick_params(colors="#666", labelsize=8)
    ax.grid(axis="y", alpha=0.3, linestyle=":", color="#ccc")
    fig.tight_layout()
    return _fig2bytes(fig)


def _invalidite_barres_axa(besoin_ann, nom, g33, g66, g100, gptia, figsize=(7.5, 3.0)):
    if besoin_ann <= 0:
        return b""
    fig, ax = plt.subplots(figsize=figsize)
    niveaux   = ["Invalidite\n> 33 %","Invalidite\n> 66 %",
                 "Invalidite\n100 %","Perte\nd autonomie"]
    garanties = [g33, g66, g100, gptia]
    x = np.arange(len(niveaux))
    ax.bar(x, [besoin_ann]*4, color="#E1EBF7", edgecolor="#ccc",
           linewidth=0.8, width=0.6, label="Besoin")
    bars = ax.bar(x, garanties, color="#43425D", edgecolor="white",
                  linewidth=1, width=0.6, label="Garanties")
    for bar, g in zip(bars, garanties):
        if g > 0:
            ax.text(bar.get_x()+bar.get_width()/2,
                    bar.get_height()+besoin_ann*0.02,
                    "{:,.0f}".format(g).replace(",", " "),
                    ha="center", fontsize=7, color="#43425D", fontweight="bold")
        else:
            ax.text(bar.get_x()+bar.get_width()/2, besoin_ann*0.04,
                    "0 EUR", ha="center", fontsize=7, color="#888")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: "{:.0f}k".format(v/1000)))
    ax.set_xticks(x); ax.set_xticklabels(niveaux, fontsize=8)
    ax.set_title("Garanties invalidite de {}".format(nom),
                 fontsize=9, fontweight="bold", color="#43425D")
    ax.legend(fontsize=8, frameon=False)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#ddd")
    ax.tick_params(colors="#666", labelsize=8)
    ax.grid(axis="y", alpha=0.3, linestyle=":", color="#ccc")
    fig.tight_layout()
    return _fig2bytes(fig)


def _retraite_multi_ages(pension_base, taux_base, age_ref=67):
    rows = []
    for age in range(65, 70):
        diff    = age - age_ref
        facteur = 1 + diff * 0.05
        rows.append((age, round(pension_base * facteur),
                     round(taux_base * facteur, 1)))
    return rows


def _h3_axa(pdf, titre):
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(176, 7, titre, ln=True)
    pdf.set_draw_color(30, 58, 95); pdf.set_line_width(0.3)
    pdf.line(14, pdf.get_y(), 85, pdf.get_y())
    pdf.set_line_width(0.2); pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0); pdf.ln(2)


def _h4_axa(pdf, titre):
    pdf.set_x(18)
    pdf.set_font("Helvetica", "BI", 8.5)
    pdf.set_text_color(30, 58, 95)
    pdf.cell(172, 6, titre, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)
    pdf.ln(1)


def _important2(pdf, txt):
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(237, 125, 49)
    pdf.multi_cell(190, 6, txt)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)


def _legende2(pdf, txt):
    pdf.set_x(10)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(190, 4.5, txt)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


# Aliases utilisés dans generer_pdf
def _important(pdf, txt):
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(237, 125, 49)
    pdf.multi_cell(190, 6, txt)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)


def _legende(pdf, txt):
    pdf.set_x(10)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(190, 4.5, txt)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _insert_img(pdf, img_bytes: bytes, tmp_path: str,
                x: float = None, w: float = 170, h: float = 0) -> None:
    """Insère une image matplotlib dans le PDF."""
    if not img_bytes:
        return
    try:
        with open(tmp_path, "wb") as f:
            f.write(img_bytes)
        if x is None:
            x = (210 - w) / 2
        if pdf.get_y() + (h if h > 0 else 55) > 272:
            pdf.add_page()
        pdf.image(tmp_path, x=x, y=None, w=w, h=h)
        pdf.ln(2)
    except Exception:
        pass


class PDF(FPDF):
    def cell(self, w, h=0, txt="", **kw):
        super().cell(w, h, _clean(str(txt)), **kw)
    def multi_cell(self, w, h, txt="", **kw):
        super().multi_cell(w, h, _clean(str(txt)), **kw)


# ─────────────────────────────────────────────
#  Utilitaires
# ─────────────────────────────────────────────

def _e(v: float) -> str:
    """EUR formaté pour PDF."""
    s = "-" if v < 0 else ""
    return f"{s}{abs(v):,.0f} EUR".replace(",", " ")

def _ep(v: float) -> str:
    """EUR formaté pour Streamlit (avec €)."""
    s = "-\u202f" if v < 0 else ""
    return f"{s}{abs(v):,.0f}\u202f\u20ac".replace(",", "\u202f")

def _p(v: float) -> str:
    return f"{v:.1f} %"

def _age(dob: str) -> str:
    try:
        p = dob.strip().split("/")
        if len(p) == 3:
            return f"{(date.today() - date(int(p[2]),int(p[1]),int(p[0]))).days//365} ans"
    except Exception:
        pass
    return ""

def _age_str(dob: str) -> str:
    return _age(dob)

def _annee_fiscalite_av(date_souscription: str) -> str:
    """Retourne l'ancienneté fiscale d'une AV."""
    try:
        p = date_souscription.strip().split("/")
        if len(p) >= 2:
            yr = int(p[-1]) if len(p[0]) <= 2 else int(p[0])
            ans = date.today().year - yr
            if ans >= 8:
                return f"{ans} ans — regime fiscal favorable (>8 ans)"
            else:
                return f"{ans} ans — regime fiscal standard (<8 ans)"
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────
#  Helpers PDF
# ─────────────────────────────────────────────

def _h1(pdf: PDF, titre: str) -> None:
    pdf.set_x(10)
    pdf.set_fill_color(*C_NAVY)
    pdf.set_text_color(*C_WHITE)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(190, 10, f"  {titre}", border=0, fill=True, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


def _h2(pdf: PDF, titre: str) -> None:
    y = pdf.get_y()
    pdf.set_draw_color(*C_RED)
    pdf.set_line_width(1.2)
    pdf.line(10, y+2, 10, y+8)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*C_NAVY)
    pdf.set_xy(14, y)
    pdf.cell(176, 8, titre, ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _th(pdf: PDF, headers: list, widths: list, bg=None) -> None:
    pdf.set_x(10)
    pdf.set_fill_color(*(bg or C_NAVY))
    pdf.set_text_color(*C_WHITE)
    pdf.set_font("Helvetica", "B", 8)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, f"  {h}", border=1, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)


def _tr(pdf: PDF, rows: list, widths: list, bold_last=False,
        highlight_last_bg=None) -> None:
    for i, row in enumerate(rows):
        is_last = bold_last and i == len(rows)-1
        fill = i % 2 == 0
        if is_last:
            pdf.set_fill_color(*(highlight_last_bg or (220,230,242)))
            pdf.set_font("Helvetica", "B", 8)
        else:
            pdf.set_fill_color(*C_LGREY) if fill else pdf.set_fill_color(*C_WHITE)
            pdf.set_font("Helvetica", "", 8)
        pdf.set_x(10)
        for j, (cell, w) in enumerate(zip(row, widths)):
            s = str(cell)
            al = "R" if (j > 0 and s.replace(" ","").replace("EUR","").replace("-","").replace(",","").isdigit()) else "L"
            pdf.cell(w, 6, f"  {s}" if al == "L" else s, border=1, fill=True, align=al)
        pdf.ln()
    pdf.set_font("Helvetica", "", 8)


def _bullet(pdf: PDF, txt: str, color=None, symbol="-") -> None:
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*(color or C_RED))
    pdf.cell(5, 6, symbol)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(171, 6, txt)


def _footer(pdf: PDF, today: str) -> None:
    pdf.set_y(-13)
    pdf.set_draw_color(*C_RED)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(130, 130, 130)
    pdf.ln(1)
    pdf.set_x(10)
    pdf.cell(95, 5, "Document confidentiel — a titre informatif uniquement", align="L")
    pdf.cell(95, 5, f"My Campus Patrimoine — {today}", align="R")
    pdf.set_text_color(0, 0, 0)


def _kpi_band(pdf: PDF, items: list) -> None:
    """Bande de KPI colorée — items = [(label, valeur, couleur_bg)]."""
    w = 190 // len(items)
    pdf.set_x(10)
    for label, val, bg in items:
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*C_WHITE)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(w, 5, f"  {label}", border=0, fill=True, ln=False)
    pdf.ln()
    pdf.set_x(10)
    for label, val, bg in items:
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*C_WHITE)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(w, 8, f"  {val}", border=1, fill=True, ln=False)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


# ─────────────────────────────────────────────
#  Affichage Streamlit
# ─────────────────────────────────────────────

def afficher_rapport_streamlit(data: dict, bilan: BilanPatrimonial) -> None:
    identite = data.get("identite", {})
    nom_c = (f"{identite.get('prenom','')} {identite.get('nom','')}".strip() or "Client")

    st.markdown("---")
    st.markdown(f"<h2 style='color:#1e3a5f;'>Bilan Patrimonial — {nom_c}</h2>",
                unsafe_allow_html=True)
    st.caption(f"Établi le {date.today().strftime('%d/%m/%Y')}")

    st.markdown("### Synthèse patrimoniale")
    c1,c2,c3 = st.columns(3)
    c1.metric("Actif brut", _ep(bilan.actif_brut))
    c2.metric("Passif total", _ep(bilan.passif_total))
    c3.metric("Actif net", _ep(bilan.actif_net),
              delta="positif" if bilan.actif_net>=0 else "négatif",
              delta_color="normal" if bilan.actif_net>=0 else "inverse")
    c4,c5,c6 = st.columns(3)
    c4.metric("Revenus annuels", _ep(bilan.revenus_annuels_total))
    c5.metric("Charges annuelles", _ep(bilan.charges_annuelles_total))
    c6.metric("Épargne mensuelle", _ep(bilan.capacite_epargne_mensuelle)+"/mois",
              delta="positif" if bilan.capacite_epargne_mensuelle>=0 else "négatif",
              delta_color="normal" if bilan.capacite_epargne_mensuelle>=0 else "inverse")

    gcol1, gcol2 = st.columns(2)
    with gcol1:
        st.markdown("#### Répartition du patrimoine")
        if bilan.actif_brut > 0:
            fig = px.pie(values=list(bilan.repartition_patrimoine.values()),
                         names=list(bilan.repartition_patrimoine.keys()),
                         color_discrete_sequence=["#1e3a5f","#2c7a7b","#68d391"], hole=0.45)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=270,
                              showlegend=True, legend=dict(orientation="h",y=-0.1))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Renseignez votre patrimoine pour voir la répartition.")
    with gcol2:
        st.markdown("#### Flux financiers annuels")
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="Revenus", x=["Foyer"], y=[bilan.revenus_annuels_total], marker_color="#2c7a7b"))
        fig2.add_trace(go.Bar(name="Charges courantes", x=["Foyer"], y=[bilan.charges_annuelles_courantes], marker_color="#fc8181"))
        fig2.add_trace(go.Bar(name="Mensualités crédits", x=["Foyer"], y=[bilan.charges_annuelles_credits], marker_color="#f6ad55"))
        fig2.update_layout(barmode="group", margin=dict(t=10,b=10,l=10,r=10), height=270,
                           legend=dict(orientation="h",y=-0.25), yaxis_title="EUR")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Indicateurs clés")
    ki1,ki2,ki3,ki4 = st.columns(4)
    with ki1:
        icon = "🟢" if bilan.taux_endettement<=33 else ("🟡" if bilan.taux_endettement<=35 else "🔴")
        st.metric(f"{icon} Taux endettement", _p(bilan.taux_endettement))
        st.caption("Seuil : 35 %")
    with ki2:
        st.metric("💰 Épargne mensuelle", _ep(bilan.capacite_epargne_mensuelle))
    with ki3:
        icon3 = "🟢" if bilan.taux_epargne>=10 else ("🟡" if bilan.taux_epargne>=5 else "🔴")
        st.metric(f"{icon3} Taux d'épargne", _p(bilan.taux_epargne))
    with ki4:
        profil = data.get("objectifs",{}).get("profil_risque","N/R")
        st.metric("Profil investisseur", profil.split("—")[0].strip())

    st.markdown("---")
    acol1, acol2 = st.columns(2)
    with acol1:
        st.markdown("### ✅ Points forts")
        for pt in bilan.points_forts:
            st.success(f"• {pt}")
    with acol2:
        st.markdown("### ⚠️ Points de vigilance")
        if bilan.points_vigilance:
            for pt in bilan.points_vigilance:
                st.warning(f"• {pt}")
        else:
            st.info("Aucun point de vigilance majeur.")

    st.markdown("### 🎯 Recommandations prioritaires")
    for i, reco in enumerate(bilan.recommandations, 1):
        st.info(f"**{i}.** {reco}")

    od = data.get("objectifs", {})
    if od.get("objectifs"):
        st.markdown("### Objectifs patrimoniaux")
        oc1, oc2 = st.columns(2)
        with oc1:
            st.markdown(f"**Profil :** {od.get('profil_risque','N/R')}")
            st.markdown(f"**Horizon :** {od.get('horizon_investissement','N/R')}")
        with oc2:
            for obj in od.get("objectifs", []):
                st.markdown(f"• {obj}")
    if od.get("commentaires","").strip():
        st.markdown("**Commentaires :**")
        st.write(od["commentaires"])


# ─────────────────────────────────────────────
#  GÉNÉRATION PDF COMPLÈTE
# ─────────────────────────────────────────────


def generer_pdf(data: dict, bilan: BilanPatrimonial) -> bytes:
    """
    Génère un PDF clone exact du document AXA Bilan Patrimonial.
    Structure H1/H2/H3/H4 et graphiques identiques au document de référence 36 pages.
    """
    pdf = PDF()
    pdf.set_margins(left=10, top=10, right=10)
    pdf.set_auto_page_break(auto=True, margin=16)

    # ── Extraction données ────────────────────────────────────────────────────
    ide  = data.get("identite", {})
    sfam = data.get("situation_familiale", {})
    immo = data.get("immobilier", [])
    afin = data.get("actifs_financiers", [])
    tres = data.get("tresorerie", {})
    cred = data.get("credits", [])
    rev  = data.get("revenus", {})
    ch   = data.get("charges", {})
    fisc = data.get("fiscalite", {})
    obj  = data.get("objectifs", {})
    prev = data.get("prevoyance", {})
    enf  = sfam.get("enfants", [])

    prenom  = ide.get("prenom", "")
    nom     = ide.get("nom", "").upper()
    nom_c   = "{} {}".format(prenom, nom).strip() or "Client"
    pren_cj = ide.get("prenom_conjoint", "")
    nom_cj  = ide.get("nom_conjoint", "").upper()
    nom_ccj = "{} {}".format(pren_cj, nom_cj).strip()
    has_cj  = ide.get("a_conjoint", False)
    dob1    = ide.get("date_naissance", "") or ide.get("dob", "")
    dob2    = ide.get("date_naissance_conjoint", "") or ide.get("dob_conjoint", "")
    prof1   = ide.get("profession", "")
    prof2   = ide.get("profession_conjoint", "")
    emb1    = ide.get("date_embauche", "")
    emb2    = ide.get("date_embauche_conjoint", "")
    fin1    = ide.get("date_fin_activite", "")
    fin2    = ide.get("date_fin_activite_conjoint", "")
    date_ret1 = ide.get("date_retraite", "")
    date_ret2 = ide.get("date_retraite_conjoint", "")

    today = date.today().strftime("%d/%m/%Y")
    yr    = date.today().strftime("%Y")
    nb_enf = sfam.get("nb_enfants", 0)

    sit = sfam.get("situation", "")
    reg = sfam.get("regime_matrimonial", "")
    unio= sfam.get("annee_union", "")

    # ── Données fiscales ──────────────────────────────────────────────────────
    ir_ann  = fisc.get("impot_revenu_annuel", 0)
    rfr     = fisc.get("revenu_fiscal_reference", 0) or bilan.revenus_annuels_total
    parts   = fisc.get("parts_fiscales", 1.0)
    tmi     = fisc.get("tranche_marginale_imposition", "N/R")
    ifi_bool= fisc.get("assujetti_ifi", False)
    ifi_ann = fisc.get("ifi_annuel", 0)
    base_ps = rfr * 0.12
    ps_ann  = round(base_ps * 0.172)

    # ── Budget ────────────────────────────────────────────────────────────────
    rev_sal  = rev.get("salaire_net_mensuel", 0)*12 + rev.get("primes_annuelles", 0)
    rev_sal += rev.get("revenus_independants_annuels", 0)
    rev_cj   = rev.get("salaire_net_mensuel_conjoint", 0)*12 + rev.get("primes_annuelles_conjoint", 0)
    rev_immo_= rev.get("revenus_fonciers_annuels", 0)
    rev_fin_ = rev.get("revenus_financiers_annuels", 0)
    rev_pen  = rev.get("pensions_annuelles", 0) + rev.get("pensions_annuelles_conjoint", 0)
    solde_bud= bilan.revenus_annuels_total - bilan.charges_annuelles_total

    # ── Prévoyance ────────────────────────────────────────────────────────────
    age_ret  = prev.get("age_retraite", 0)
    pen_est  = prev.get("pension_estimee", 0)
    cap_deces= prev.get("capital_deces", 0)
    cap_deces_cj = prev.get("capital_deces_conjoint", 0)
    ind_inv  = prev.get("indemnite_invalidite", 0)
    rev_j    = bilan.revenus_annuels_client / 365 if bilan.revenus_annuels_client else 0
    rev_j_cj = bilan.revenus_annuels_conjoint / 365 if bilan.revenus_annuels_conjoint else 0

    # ── Catégories actifs ─────────────────────────────────────────────────────
    immo_usage  = [b for b in immo if b.get("type_bien","") in ["Residence principale","Residence secondaire"]]
    immo_loc    = [b for b in immo if b.get("type_bien","") not in ["Residence principale","Residence secondaire"]]
    av_list     = [a for a in afin if "Assurance" in a.get("type_actif","")]
    per_list    = [a for a in afin if "PER" in a.get("type_actif","") or "PEE" in a.get("type_actif","") or "PERCO" in a.get("type_actif","")]
    autres_afin = [a for a in afin if a not in av_list and a not in per_list]

    val_usage = sum(b.get("valeur_actuelle",0) for b in immo_usage)
    val_loc   = sum(b.get("valeur_actuelle",0) for b in immo_loc)
    val_av    = sum(a.get("valeur_actuelle",0) for a in av_list)
    val_per   = sum(a.get("valeur_actuelle",0) for a in per_list)

    nm1 = (nom_c[:14] or "Client")
    nm2 = (nom_ccj[:14] if nom_ccj else "Conjoint")

    # ─────────────────────────────────────────────────────────────────────────
    #  PAGE COUVERTURE
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page()

    if os.path.exists(COVER_IMAGE):
        pdf.image(COVER_IMAGE, x=0, y=0, w=210, h=148)
    else:
        pdf.set_fill_color(*C_NAVY)
        pdf.rect(0, 0, 210, 148, "F")

    pdf.set_fill_color(*C_RED)
    pdf.rect(0, 148, 210, 2.5, "F")
    pdf.set_fill_color(*C_WHITE)
    pdf.rect(0, 150.5, 210, 97, "F")

    pdf.set_xy(20, 157)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*C_NAVY)
    pdf.cell(170, 11, "Bilan Social et Patrimonial", ln=True)

    pdf.set_x(20)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*C_RED)
    dest = "A l attention de : {}".format(nom_c)
    if has_cj and nom_ccj:
        dest += " et {}".format(nom_ccj)
    pdf.cell(170, 8, dest, ln=True)

    pdf.set_x(20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(170, 6, "Etude realisee sur une base d evaluation au {}".format(today), ln=True)

    pdf.set_draw_color(*C_RED)
    pdf.set_line_width(0.8)
    pdf.line(20, pdf.get_y()+2, 190, pdf.get_y()+2)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)

    # KPIs couverture
    kpis = [
        ("Actif brut total",      _e(bilan.actif_brut),    C_NAVY),
        ("Passif total",          _e(bilan.passif_total),   C_TEAL),
        ("Actif net patrimonial", _e(bilan.actif_net),
         C_GREEN if bilan.actif_net >= 0 else C_DRED),
    ]
    w = 190 // 3
    pdf.set_x(10)
    for lbl, val, bg in kpis:
        pdf.set_fill_color(*bg); pdf.set_text_color(*C_WHITE)
        pdf.set_font("Helvetica","",7)
        pdf.cell(w, 5, "  {}".format(lbl), border=0, fill=True)
    pdf.ln()
    pdf.set_x(10)
    for lbl, val, bg in kpis:
        pdf.set_fill_color(*bg); pdf.set_text_color(*C_WHITE)
        pdf.set_font("Helvetica","B",10)
        pdf.cell(w, 8, "  {}".format(val), border=1, fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    pdf.set_x(20); pdf.set_font("Helvetica","",8)
    pdf.set_text_color(110,110,110)
    pdf.cell(170, 5,
        "Revenus annuels : {}  |  Capacite d epargne : {}/mois  |  Taux d endettement : {:.1f} %".format(
        _e(bilan.revenus_annuels_total), _e(bilan.capacite_epargne_mensuelle), bilan.taux_endettement), ln=True)
    pdf.set_text_color(0,0,0)

    # ─────────────────────────────────────────────────────────────────────────
    #  H1 — RAPPEL DE VOTRE SITUATION
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Rappel de votre situation")

    # H2 — Votre famille
    _h2(pdf, "Votre famille")

    age1 = _age_str(dob1)
    if age1 or prof1:
        line = "Vous avez {}".format(age1) if age1 else "Vous etes"
        if prof1:
            line += " et vous etes {}".format(prof1)
        if emb1:
            line += " depuis le {}".format(emb1)
        _bullet(pdf, line + ".")
    if has_cj and nom_ccj:
        age2 = _age_str(dob2)
        lc = "Votre conjoint(e) est {}".format(prof2) if prof2 else "Votre conjoint(e) {}".format(nom_ccj)
        if age2:
            lc += " et a {}".format(age2)
        if emb2:
            lc += ", en poste depuis le {}".format(emb2)
        _bullet(pdf, lc + ".")
    if sit:
        ls = "Vous etes {}".format(sit.lower())
        if unio:
            ls += " depuis le {}".format(unio)
        if reg and reg != "Sans objet":
            ls += " sous le {}".format(reg)
        _bullet(pdf, ls + ".")
    if nb_enf > 0:
        _bullet(pdf, "Votre structure familiale est la suivante :")
        if enf:
            _th(pdf, ["Prenom","Date de naissance","Charge fiscale"], [65,65,60])
            _tr(pdf, [(e.get("prenom",""), e.get("date_naissance",""), e.get("charge","")) for e in enf], [65,65,60])
    pdf.ln(4)

    # H2 — Votre carrière
    _h2(pdf, "Votre carriere")

    # H3 — Carrière client
    _h3_axa(pdf, "Carriere {}".format(nom_c.split()[0] if nom_c else "Thomas"))
    pdf.set_font("Helvetica","",8.5); pdf.set_x(18)
    if prof1 or emb1:
        lines_car = ["Vous avez exerce ou vous exercez les activites professionnelles suivantes :"]
        if emb1 and prof1 and fin1:
            lines_car.append("Du {} au {} : {}".format(emb1, fin1, prof1))
        elif emb1 and prof1:
            lines_car.append("Du {} : {}".format(emb1, prof1))
        elif prof1:
            lines_car.append(prof1)
        if date_ret1:
            lines_car.append("Vous envisagez de partir a la retraite le {}{}.".format(
                date_ret1, ", a {} ans".format(age_ret) if age_ret else ""))
        elif age_ret:
            lines_car.append("Vous envisagez de partir a la retraite a {} ans.".format(age_ret))
        for l in lines_car:
            pdf.set_x(18); pdf.multi_cell(172, 6, l)

    if has_cj and nom_ccj:
        pdf.ln(2)
        _h3_axa(pdf, "Carriere {}".format(nom_ccj.split()[0] if nom_ccj else "Pascale"))
        pdf.set_font("Helvetica","",8.5); pdf.set_x(18)
        if prof2 or emb2:
            lines_cj = ["Vous avez exerce ou vous exercez les activites professionnelles suivantes :"]
            if emb2 and prof2 and fin2:
                lines_cj.append("Du {} au {} : {}".format(emb2, fin2, prof2))
            elif emb2 and prof2:
                lines_cj.append("Du {} : {}".format(emb2, prof2))
            elif prof2:
                lines_cj.append(prof2)
            if date_ret2:
                lines_cj.append("Vous envisagez de partir a la retraite le {}.".format(date_ret2))
            for l in lines_cj:
                pdf.set_x(18); pdf.multi_cell(172, 6, l)
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Vos actifs
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Rappel de votre situation (suite)")
    _h2(pdf, "Vos actifs")

    # H3 — Vos actifs au [date]
    _h3_axa(pdf, "Vos actifs au {}".format(today))

    _important(pdf,
        "Votre actif net (difference entre vos actifs et vos passifs) est de {}.".format(_e(bilan.actif_net)))
    pdf.set_x(10); pdf.set_font("Helvetica","",8.5)
    pdf.cell(190, 5, "Le total de votre actif brut est de {}.".format(_e(bilan.actif_brut)), ln=True)
    pdf.ln(3)

    det_map = {"Pleine propriete":"PP","Pleine propriété":"PP",
               "Nue-propriete":"NP","Nue-propriété":"NP",
               "Usufruit":"USF","Indivision":"IND","SCI":"SCI"}

    cw_a = [56,22,22,34,28,18,10]
    _th(pdf, ["Categorie / Bien", nm1, nm2, "Communaute","Acquisition","Det.","(1)"], cw_a)

    def _arow(lbl, vm, vf, vc, acq, det, qp="", bold=False):
        pdf.set_x(10)
        pdf.set_fill_color(*(C_MGREY if bold else (C_LGREY if pdf.page%2==0 else C_WHITE)))
        pdf.set_fill_color(*(C_MGREY if bold else C_LGREY))
        pdf.set_font("Helvetica","B" if bold else "",7.5)
        for val, w in zip([lbl,vm,vf,vc,acq,det,qp], cw_a):
            s = str(val)
            is_n = s.replace(" ","").replace("EUR","").replace("-","").isdigit()
            al = "R" if (is_n and val not in [lbl,acq,det,qp]) else "L"
            pdf.cell(w, 6, ("  {}".format(s) if al=="L" else s), border=1, fill=True, align=al)
        pdf.ln()
        pdf.set_font("Helvetica","",7.5)

    # Biens d'usage
    if val_usage > 0:
        _arow("Biens d usage : {}".format(_e(val_usage)),"","","","","","",bold=True)
        for b in immo_usage:
            det = det_map.get(b.get("mode_detention","Pleine propriete"),"PP")
            _arow("  {}".format(b.get("description","")[:28]),"","",_e(b.get("valeur_actuelle",0)),
                  str(b.get("annee_acquisition","")),det,"PP")

    # Immobilier de rapport
    if val_loc > 0:
        _arow("Immobilier de rapport : {}".format(_e(val_loc)),"","","","","","",bold=True)
        for b in immo_loc:
            det = det_map.get(b.get("mode_detention","Pleine propriete"),"PP")
            _arow("  {}".format(b.get("description","")[:28]),"","",_e(b.get("valeur_actuelle",0)),
                  str(b.get("annee_acquisition","")),det,"PP")

    # Assurance vie
    if val_av > 0:
        _arow("Assurance vie : {}".format(_e(val_av)),"","","","","","",bold=True)
        for a in av_list:
            _arow("  {}".format(a.get("description","")[:28]),"",_e(a.get("valeur_actuelle",0)),"",
                  a.get("date_souscription",""),"","")

    # Épargne retraite
    if val_per > 0:
        _arow("Epargne retraite et salariale : {}".format(_e(val_per)),"","","","","","",bold=True)
        for a in per_list:
            _arow("  {}".format(a.get("description","")[:28]),"",_e(a.get("valeur_actuelle",0)),"",
                  a.get("date_souscription",""),"","")

    # Disponibilités
    if bilan.actif_tresorerie > 0:
        _arow("Disponibilites : {}".format(_e(bilan.actif_tresorerie)),"","","","","","",bold=True)
        for lbl_t, key_t in [
            ("Comptes sur livret (CSL)","autres_livrets"),
            ("Livret de developpement durable (LDDS)","ldds"),
            ("Livrets A","livret_a"),
            ("Compte courant","compte_courant_disponible"),
            ("Autres liquidites","autres_liquidites"),
        ]:
            v = tres.get(key_t, 0)
            if v > 0:
                _arow("  {}".format(lbl_t),"","",_e(v),"","PP","")

    _arow("Total de vos actifs","","",_e(bilan.actif_brut),"","","",bold=True)
    pdf.ln(2)
    _legende(pdf,
        "(1) Mode de detention des actifs : PP signifie Pleine Propriete, "
        "NP Nue-Propriete et USF Usufruit. Selon le mode de detention, la valorisation "
        "indiquee correspond a la pleine-propriete, la nue-propriete ou l usufruit du bien.")
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Vos passifs (nouvelle page)
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Rappel de votre situation (suite)")
    _h2(pdf, "Vos passifs")

    # H3 — Votre passif : [montant]
    _h3_axa(pdf, "Votre passif : {}".format(_e(bilan.passif_total)))

    cw_p = [52,20,20,30,24,22,12,10]
    _th(pdf, ["Credit / Dette","Thomas","Pascale","Communaute","CRD","Mensualite","Debut","Fin"], cw_p)
    rows_p = []
    for cr in cred:
        dp = cr.get("detenu_par","Commun")
        crd = _e(cr.get("capital_restant_du",0))
        mens= _e(cr.get("mensualite",0))
        deb = cr.get("date_debut","")
        fin = str(cr.get("annee_fin",""))
        desc= cr.get("description","Credit")[:24]
        if "seul" in dp.lower() and nm1.split()[0].lower() in dp.lower():
            rows_p.append((desc,crd,"","",crd,mens,deb,fin))
        elif "seul" in dp.lower():
            rows_p.append((desc,"",crd,"",crd,mens,deb,fin))
        else:
            rows_p.append((desc,"","",crd,crd,mens,deb,fin))
    rows_p.append(("Total de vos passifs","","",_e(bilan.passif_total),_e(bilan.passif_total),"","",""))
    if rows_p:
        _tr(pdf, rows_p, cw_p, bold_last=True)
    else:
        pdf.set_font("Helvetica","I",8); pdf.set_x(10)
        pdf.cell(190,7,"  Aucun passif renseigne.",ln=True)
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Votre budget
    # ─────────────────────────────────────────────────────────────────────────
    _h2(pdf, "Votre budget")

    # H3 — Votre budget sur l'année [N]
    _h3_axa(pdf, "Votre budget sur l annee {}".format(yr))

    rev_items, cha_items = [], []
    if rev_sal:    rev_items.append(("Revenus d activite",       _e(rev_sal)))
    if rev_cj:     rev_items.append(("Revenus activite conjoint",_e(rev_cj)))
    if rev_immo_:  rev_items.append(("Revenus immobiliers",      _e(rev_immo_)))
    if rev_fin_:   rev_items.append(("Revenus financiers",       _e(rev_fin_)))
    if rev_pen:    rev_items.append(("Pensions / retraites",     _e(rev_pen)))
    if ir_ann:     cha_items.append(("Impots et taxes",          _e(ir_ann)))
    if bilan.charges_annuelles_courantes:
        cha_items.append(("Epargne",_e(bilan.charges_annuelles_courantes)))
    if bilan.charges_annuelles_credits:
        cha_items.append(("Charges d emprunt",_e(bilan.charges_annuelles_credits)))
    scol = ch.get("scolarite_annuel",0)
    if scol:
        cha_items.append(("Charges sur immeubles",_e(scol)))

    pdf.set_x(10); pdf.set_fill_color(*C_NAVY); pdf.set_text_color(*C_WHITE)
    pdf.set_font("Helvetica","B",8)
    pdf.cell(95,7,"  Revenus",border=1,fill=True)
    pdf.cell(95,7,"  Charges",border=1,fill=True,ln=True)
    pdf.set_text_color(0,0,0)

    for i in range(max(len(rev_items),len(cha_items),1)):
        fill = (i%2==0)
        pdf.set_fill_color(*C_LGREY) if fill else pdf.set_fill_color(*C_WHITE)
        pdf.set_font("Helvetica","",7.5); pdf.set_x(10)
        if i < len(rev_items):
            pdf.cell(60,6,"  {}".format(rev_items[i][0]),border=1,fill=fill)
            pdf.cell(35,6,rev_items[i][1],border=1,fill=fill,align="R")
        else:
            pdf.cell(95,6,"",border=1,fill=fill)
        if i < len(cha_items):
            pdf.cell(60,6,"  {}".format(cha_items[i][0]),border=1,fill=fill)
            pdf.cell(35,6,cha_items[i][1],border=1,fill=fill,align="R")
        else:
            pdf.cell(95,6,"",border=1,fill=fill)
        pdf.ln()

    pdf.set_x(10); pdf.set_font("Helvetica","B",7.5)
    pdf.set_fill_color(*C_MGREY)
    pdf.cell(60,7,"  Total des revenus",border=1,fill=True)
    pdf.cell(35,7,_e(bilan.revenus_annuels_total),border=1,fill=True,align="R")
    pdf.set_fill_color(255,220,220)
    pdf.cell(60,7,"  Total des charges",border=1,fill=True)
    pdf.cell(35,7,_e(bilan.charges_annuelles_total),border=1,fill=True,align="R")
    pdf.ln()
    pdf.set_x(10)
    pdf.set_fill_color(*(C_GREEN if solde_bud>=0 else C_DRED))
    pdf.set_text_color(*C_WHITE); pdf.set_font("Helvetica","B",9)
    pdf.cell(190,9,"  Solde budgetaire annuel : {}".format(_e(solde_bud)),border=1,fill=True,ln=True)
    pdf.set_text_color(0,0,0)
    pdf.ln(2)
    pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
    pdf.multi_cell(190,6,
        "En fin d annee vous disposerez d un solde budgetaire (difference entre vos revenus et "
        "vos charges) de {}, soit une capacite d epargne mensuelle de {}.".format(
        _e(solde_bud), _e(bilan.capacite_epargne_mensuelle)))

    # ─────────────────────────────────────────────────────────────────────────
    #  H1 — ANALYSE DE VOTRE SITUATION
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation")

    # H2 — Analyse de structure
    _h2(pdf, "Analyse de structure")
    # H3 — Répartition par famille
    _h3_axa(pdf, "Repartition par famille")

    cats_d = [
        ("Biens d usage",         val_usage),
        ("Immobilier de rapport", val_loc),
        ("Assurance vie",         val_av),
        ("Epargne retraite",      val_per),
        ("Disponibilites",        bilan.actif_tresorerie),
    ]
    rep_l = [l for l,v in cats_d if v>0]
    rep_v = [v for l,v in cats_d if v>0]
    rep_c = AXA_DONUT_FAMILLE[:len(rep_l)]
    img_struct = _donut_axa(rep_l, rep_v, rep_c) if rep_v else b""
    _insert_img(pdf, img_struct, "/tmp/g_struct.png", w=155, h=100)
    pdf.ln(3)

    # H2 — Analyse économique (nouvelle page)
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Analyse economique")
    # H3 — Répartition par horizon de placement
    _h3_axa(pdf, "Repartition par horizon de placement")

    hor = {"Court terme": bilan.actif_tresorerie, "Moyen terme": 0.0, "Long terme": val_usage+val_loc}
    for a in afin:
        t = a.get("type_actif","")
        if any(x in t for x in ["PEA","Assurance","PER","PEE","Compte-titres","Crypto"]):
            hor["Long terme"] = hor.get("Long terme",0) + a.get("valeur_actuelle",0)
        else:
            hor["Court terme"] = hor.get("Court terme",0) + a.get("valeur_actuelle",0)
    hl = [k for k,v in hor.items() if v>0]
    hv = [v for k,v in hor.items() if v>0]
    img_hor = _donut_axa(hl, hv, AXA_DONUT_HORIZON[:len(hl)]) if hv else b""
    _insert_img(pdf, img_hor, "/tmp/g_hor.png", w=155, h=100)
    pdf.ln(3)

    # H2 — Analyse financière (nouvelle page)
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Analyse financiere")
    # H3 — Répartition par rendement/risque
    _h3_axa(pdf, "Repartition par rendement/risque")

    ris = {"Sans risque": bilan.actif_tresorerie, "Defensif": val_usage+val_loc, "Dynamique": 0.0}
    for a in afin:
        t = a.get("type_actif","")
        if any(x in t for x in ["PEA","Compte-titres","Crypto"]):
            ris["Dynamique"] = ris.get("Dynamique",0) + a.get("valeur_actuelle",0)
        elif any(x in t for x in ["Assurance","PER"]):
            ris["Defensif"] = ris.get("Defensif",0) + a.get("valeur_actuelle",0)
        else:
            ris["Sans risque"] = ris.get("Sans risque",0) + a.get("valeur_actuelle",0)
    rl = [k for k,v in ris.items() if v>0]
    rv = [v for k,v in ris.items() if v>0]
    img_ris = _donut_axa(rl, rv, AXA_DONUT_RISQUE[:len(rl)]) if rv else b""
    _insert_img(pdf, img_ris, "/tmp/g_ris.png", w=155, h=100)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Évolution du patrimoine
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Evolution du patrimoine")

    projection = projeter_patrimoine(data, bilan, nb_annees=20)
    img_proj = _courbe_patrimoine_axa(projection)
    _insert_img(pdf, img_proj, "/tmp/g_proj.png", w=185, h=72)

    cw_pt = [22,22,44,38,38,26]
    _th(pdf, ["Annee","Age","Actif brut","Passif","Actif net","Epargne cum."], cw_pt)
    rows_pt = []
    for an in [0,5,10,15,20]:
        if an < len(projection):
            p = projection[an]
            rows_pt.append((str(p.annee), "{} ans".format(p.age_client),
                            _e(p.actif_brut), _e(p.passif),
                            _e(p.actif_net), _e(p.epargne_cumul)))
    _tr(pdf, rows_pt, cw_pt)
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Analyse fiscale et budgétaire (nouvelle page)
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Analyse fiscale et budgetaire")

    # H3 — Fiscalité
    _h3_axa(pdf, "Fiscalite")
    cw_f = [100,46,44]
    _th(pdf, ["Designation","Montant annuel","Taux Marginal d Imposition"], cw_f)
    rows_f = []
    if ir_ann:  rows_f.append(("Impot sur le Revenu", _e(ir_ann), tmi))
    if ps_ann:  rows_f.append(("Contributions sociales", _e(ps_ann), "-"))
    tf_ann = sum(b.get("taxe_fonciere",0) for b in immo)
    if tf_ann:  rows_f.append(("Taxes foncieres et taxes annexes", _e(tf_ann), "-"))
    if ifi_ann: rows_f.append(("IFI", _e(ifi_ann),
                               "{:.2f} %".format(ifi_ann/bilan.actif_net*100) if bilan.actif_net>0 else "-"))
    total_imp = ir_ann + ps_ann + (tf_ann or 0) + (ifi_ann or 0)
    rows_f.append(("Total de vos impots", _e(total_imp), ""))
    _tr(pdf, rows_f, cw_f, bold_last=True)
    pdf.ln(3)

    # H3 — Ratios
    _h3_axa(pdf, "Ratios")
    rat = []
    if bilan.taux_endettement > 0:
        rat.append(("Charges d endettement", "{:.2f} %".format(bilan.taux_endettement)))
    if total_imp > 0 and bilan.revenus_annuels_total > 0:
        rat.append(("Pression fiscale (en % des revenus)", "{:.2f} %".format(total_imp/bilan.revenus_annuels_total*100)))
    if bilan.taux_epargne > 0:
        rat.append(("Taux d epargne programme", "{:.2f} %".format(bilan.taux_epargne)))
    cw_r2 = [140,50]
    _th(pdf, ["Designation","Valeur"], cw_r2, bg=C_TEAL)
    _tr(pdf, [(d,v) for d,v in rat], cw_r2)
    pdf.ln(3)

    # H2 — Évolution du budget
    _h2(pdf, "Evolution du budget")
    img_bud = _courbe_budget_axa(bilan.revenus_annuels_total,
                                  bilan.charges_annuelles_total,
                                  bilan.capacite_epargne_mensuelle, int(yr))
    _insert_img(pdf, img_bud, "/tmp/g_bud.png", w=170, h=62)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Impôt sur le revenu
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse fiscale et budgetaire (suite)")
    _h2(pdf, "Impot sur le revenu")

    img_ir = _bareme_ir_axa(rfr, parts)
    _insert_img(pdf, img_ir, "/tmp/g_ir.png", w=160, h=30)

    if rfr and parts:
        qf = rfr / parts
        bornes_ir = [11497,27703,75539,281275]
        for b in bornes_ir:
            if qf < b:
                marge = (b - qf) * parts
                pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
                pdf.multi_cell(190, 6,
                    "Le seuil de votre tranche d imposition c est-a-dire le montant en dessous "
                    "duquel vous serez taxe dans la tranche inferieure est de {:,.0f} EUR. "
                    "Vous disposez d une marge de {:,.0f} EUR.".format(b*parts, marge).replace(",", " "))
                break
    pdf.ln(2)

    cw_ir2 = [130, 60]
    _th(pdf, ["Designation","Montant"], cw_ir2)
    rows_ir2 = []
    rows_ir2.append(("Nombre de parts", "{:.2f}".format(parts)))
    if rfr: rows_ir2.append(("Revenus declares", _e(rfr)))
    rows_ir2.append(("Revenu Brut Global", _e(rfr)))
    rows_ir2.append(("Base imposable apres application des abattements specifiques", _e(rfr)))
    rows_ir2.append(("Charges deductibles du revenu global", "0 EUR"))
    rows_ir2.append(("Revenu net imposable (Code General des Impots)", _e(rfr)))
    rows_ir2.append(("Revenu fiscal de reference", _e(rfr)))
    if ir_ann: rows_ir2.append(("Impot sur les revenus soumis au bareme", _e(ir_ann)))
    rows_ir2.append(("Reductions d impot", "0 EUR"))
    rows_ir2.append(("Prelevements sociaux", _e(ps_ann)))
    rows_ir2.append(("Impot sur le revenu et prelevements sociaux dus", _e(ir_ann + ps_ann)))
    _tr(pdf, rows_ir2, cw_ir2)
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Prélèvements sociaux
    # ─────────────────────────────────────────────────────────────────────────
    _h2(pdf, "Prelevements sociaux")
    pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
    pdf.multi_cell(190,6,"Les prelevements sociaux de 17,20 % se repartissent ainsi :")
    pdf.ln(2)

    img_ps = _ps_axa(base_ps)
    _insert_img(pdf, img_ps, "/tmp/g_ps.png", w=175, h=58)
    pdf.ln(2)

    cw_ps2 = [80,30,30,30]
    _th(pdf, ["Au titre des revenus {}".format(int(yr)-1), "CSG", "CRDS", "Prel. solidarite"], cw_ps2, bg=C_TEAL)
    _tr(pdf, [
        ("Base imposable", _e(base_ps), _e(base_ps), _e(base_ps)),
        ("Taux de l imposition", "9,20 %", "0,50 %", "7,50 %"),
        ("Montant de l imposition",
         _e(base_ps*0.092), _e(base_ps*0.005), _e(base_ps*0.075)),
        ("Total des prelevements sociaux", _e(ps_ann), "", ""),
        ("CSG deductible pour revenus {}".format(yr), _e(base_ps*0.068), "", ""),
    ], cw_ps2)
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — IFI à payer
    # ─────────────────────────────────────────────────────────────────────────
    _h2(pdf, "IFI a payer")
    actif_ifi = max(0, bilan.actif_immobilier - bilan.passif_total)
    if ifi_bool or ifi_ann > 0:
        pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
        pdf.multi_cell(190,6,
            "Votre actif net au 1er janvier {} est de {}. La valeur nette de votre "
            "patrimoine taxable depassant 1 300 000 EUR, vous devez le declarer a l IFI.".format(
            yr, _e(actif_ifi)))
        pdf.ln(2)
        cw_ifi=[130,60]; _th(pdf, ["Designation","Montant"], cw_ifi)
        _tr(pdf, [
            ("Actif net imposable", _e(actif_ifi)),
            ("IFI brut avant decote", _e(ifi_ann)),
            ("Decote", "0 EUR"),
            ("IFI a payer", _e(ifi_ann)),
            ("Taux marginal d imposition de l IFI",
             "{:.2f} %".format(ifi_ann/actif_ifi*100) if actif_ifi>0 else "—"),
        ], cw_ifi)
    else:
        pdf.set_font("Helvetica","I",8.5); pdf.set_x(10)
        pdf.cell(190,6,"Non assujetti a l IFI (patrimoine immobilier net < 1 300 000 EUR).",ln=True)
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Pression fiscale
    # ─────────────────────────────────────────────────────────────────────────
    _h2(pdf, "Pression fiscale")
    pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
    pdf.multi_cell(190,6,
        "La pression fiscale indique la part des revenus consacree aux impots "
        "(IR, prelevements sociaux, IFI...).")
    pdf.ln(2)
    cw_pf=[130,60]; _th(pdf, ["Designation","Montant"], cw_pf)
    rev_ref = rfr if rfr else bilan.revenus_annuels_total
    total_imp2 = ir_ann + ps_ann + (ifi_ann or 0)
    _tr(pdf, [
        ("Total des revenus disponibles avant impots", _e(rev_ref)),
        ("Total des impots et taxes", _e(total_imp2)),
        ("Pression fiscale globale (part des revenus declares consacree aux impots)",
         "{:.2f} %".format(total_imp2/rev_ref*100) if rev_ref>0 else "—"),
        ("Actifs bruts (y compris abattements et exonerations)", _e(bilan.actif_brut)),
        ("Taux d imposition du patrimoine (Impots/Actifs bruts)",
         "{:.2f} %".format(total_imp2/bilan.actif_brut*100) if bilan.actif_brut>0 else "—"),
    ], cw_pf)
    pdf.ln(3)
    img_pf = _pression_fiscale_axa(ir_ann, ps_ann, ifi_ann, rev_ref)
    _insert_img(pdf, img_pf, "/tmp/g_pf.png", w=185, h=54)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Analyse de votre retraite
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Analyse de votre retraite")

    # H3 — Vos pensions selon la date de retraite
    _h3_axa(pdf, "Vos pensions (regimes obligatoires) selon la date de votre retraite")
    pdf.ln(2)

    if pen_est and age_ret:
        rev_m = bilan.revenus_annuels_client/12 if bilan.revenus_annuels_client>0 else 1
        taux_base = pen_est/rev_m*100 if rev_m>0 else 60
        rows_ages = _retraite_multi_ages(pen_est, taux_base, age_ret)

        cw_ages = [56,26,26,28,26,24]
        hdrs_ages = [nm1[:14], "65 ans","66 ans",
                     "{} ans *".format(age_ret),"68 ans","69 ans"]

        pdf.set_x(10); pdf.set_fill_color(*C_TEAL); pdf.set_text_color(*C_WHITE)
        pdf.set_font("Helvetica","B",7.5)
        for h, w in zip(hdrs_ages, cw_ages):
            pdf.cell(w, 7, "  {}".format(h), border=1, fill=True)
        pdf.ln(); pdf.set_text_color(0,0,0)
        _tr(pdf, [
            ["Retraites nettes mensuelles (1)"] + [_e(r[1]) for r in rows_ages],
            ["Taux de remplacement (2)"]        + ["{:.0f} %".format(r[2]) for r in rows_ages],
        ], cw_ages)
        pdf.ln(3)

        if has_cj and nom_ccj and bilan.revenus_annuels_conjoint > 0:
            pen_cj = pen_est * 0.43
            taux_cj = pen_cj/(bilan.revenus_annuels_conjoint/12)*100 if bilan.revenus_annuels_conjoint>0 else 55
            rows_cj = _retraite_multi_ages(pen_cj, taux_cj, age_ret)
            hdrs_cj = [nm2[:14],"65 ans","66 ans",
                       "{} ans *".format(age_ret),"68 ans","69 ans"]
            pdf.set_x(10); pdf.set_fill_color(*C_TEAL); pdf.set_text_color(*C_WHITE)
            pdf.set_font("Helvetica","B",7.5)
            for h,w in zip(hdrs_cj, cw_ages):
                pdf.cell(w,7,"  {}".format(h),border=1,fill=True)
            pdf.ln(); pdf.set_text_color(0,0,0)
            _tr(pdf, [
                ["Retraites nettes mensuelles (1)"] + [_e(r[1]) for r in rows_cj],
                ["Taux de remplacement (2)"]        + ["{:.0f} %".format(r[2]) for r in rows_cj],
            ], cw_ages)
            pdf.ln(3)

        _legende(pdf,
            "(1) Retraites nettes mensuelles servies par les regimes obligatoires et "
            "issues des contrats collectifs et personnels.\n"
            "(2) Ce taux de remplacement n integre pas les pensions et rentes epargne "
            "retraite dont les montants ne sont pas connus pour un depart en retraite "
            "different de celui fixe.")
    else:
        pdf.set_font("Helvetica","I",8.5); pdf.set_x(10)
        pdf.multi_cell(190,6,
            "Informations retraite non renseignees. Veuillez renseigner l age "
            "de retraite et la pension estimee dans l onglet Prevoyance.")
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Analyse de votre prévoyance décès
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Analyse de votre prevoyance deces")

    besoin_cap  = bilan.revenus_annuels_client * 3
    besoin_rev  = bilan.revenus_annuels_client
    pen_cj_est  = pen_est * 0.1 if pen_est else 0

    # H3 — Garanties décès de [client] au [date]
    _h3_axa(pdf, "Garanties deces de {} au {}".format(nom_c, today))

    if besoin_cap > 0:
        gap_cap = max(0, besoin_cap - cap_deces)
        # H4 — Besoin à couvrir en capital
        _h4_axa(pdf, "Besoin a couvrir en capital : {}".format(_e(gap_cap)))
        img_dc1 = _prev_deces_barre_axa(besoin_cap, cap_deces, "Capitaux deces",
                                         "Capital — {}".format(nom_c))
        _insert_img(pdf, img_dc1, "/tmp/g_dc1.png", w=160, h=26)
        _legende(pdf,
            "Le besoin en capital est estime a 3 ans de revenus nets, soit {}. "
            "Il est couvert a hauteur de {}. "
            "Des capitaux deces seront verses au titre des regimes obligatoires et "
            "contrats individuels.".format(_e(besoin_cap), _e(cap_deces)))
        pdf.ln(3)

    if besoin_rev > 0:
        gap_rev = max(0, besoin_rev - pen_cj_est)
        # H4 — Besoin à couvrir en revenus
        _h4_axa(pdf, "Besoin a couvrir en revenus : {}".format(_e(gap_rev)))
        img_dc2 = _prev_deces_barre_axa(besoin_rev, pen_cj_est, "Pension de conjoint",
                                         "Revenus — {}".format(nom_c))
        _insert_img(pdf, img_dc2, "/tmp/g_dc2.png", w=160, h=26)
        _legende(pdf,
            "Le besoin en revenus est estime a 100% du revenu net annuel, soit {}. "
            "Il est couvert a hauteur de {} bruts par an. "
            "Des pensions de conjoint seront versees au titre des regimes obligatoires.".format(
            _e(besoin_rev), _e(pen_cj_est)))
        pdf.ln(3)

    # H3 — Garanties décès conjoint
    if has_cj and nom_ccj and bilan.revenus_annuels_conjoint > 0:
        besoin_cap_cj = bilan.revenus_annuels_conjoint * 3
        besoin_rev_cj = bilan.revenus_annuels_conjoint
        gap_cap_cj = max(0, besoin_cap_cj - cap_deces_cj)

        _h3_axa(pdf, "Garanties deces de {} au {}".format(nom_ccj, today))

        # H4
        _h4_axa(pdf, "Besoin a couvrir en capital : {}".format(_e(gap_cap_cj)))
        img_dc3 = _prev_deces_barre_axa(besoin_cap_cj, cap_deces_cj, "Capitaux deces",
                                         "Capital — {}".format(nom_ccj))
        _insert_img(pdf, img_dc3, "/tmp/g_dc3.png", w=160, h=26)
        _legende(pdf,
            "Le besoin en capital est estime a 3 ans de revenus nets, soit {}. "
            "Il est couvert a hauteur de {}.".format(_e(besoin_cap_cj), _e(cap_deces_cj)))
        pdf.ln(2)

        _h4_axa(pdf, "Besoin a couvrir en revenus : {}".format(_e(besoin_rev_cj)))
        img_dc4 = _prev_deces_barre_axa(besoin_rev_cj, 0, "Garanties",
                                         "Revenus — {}".format(nom_ccj))
        _insert_img(pdf, img_dc4, "/tmp/g_dc4.png", w=160, h=26)
        _legende(pdf,
            "Le besoin en revenus de {} est estime a 100% du revenu net annuel, "
            "soit {}.".format(nom_ccj, _e(besoin_rev_cj)))
    pdf.ln(3)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Analyse de votre prévoyance incapacité
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Analyse de votre prevoyance incapacite")

    g_j1_j3   = rev_j * 0.9
    g_j4_j363 = rev_j * 0.5
    g_j364    = 0.0

    # H3 — Garanties incapacité de [client] au [date]
    _h3_axa(pdf, "Garanties incapacite de {} au {}".format(nom_c, today))

    img_inc1 = _incapacite_courbe_axa(rev_j, nom_c, g_j1_j3, g_j4_j363, g_j364)
    _insert_img(pdf, img_inc1, "/tmp/g_inc1.png", w=170, h=70)

    cw_ic = [46,34,34,36]
    _th(pdf, [" ","Du 1er au 3eme jour","Du 4eme au 363eme jour","Du 364eme au 1095eme jour"],
        cw_ic, bg=C_TEAL)
    _tr(pdf, [
        ("Indemnites journalieres brutes", _e(g_j1_j3), _e(g_j4_j363), "0 EUR"),
        ("Regime professionnel obligatoire", "0 EUR", _e(rev_j*0.05), "0 EUR"),
        ("Maintien de salaire (1)", _e(g_j1_j3), _e(g_j4_j363-rev_j*0.05), "0 EUR"),
        ("Indemnites journalieres nettes", _e(g_j1_j3*0.9), _e(g_j4_j363*0.9), "0 EUR"),
        ("Besoin en revenus (2)", _e(rev_j), _e(rev_j), _e(rev_j)),
        ("Besoin a couvrir", _e(max(0,rev_j-g_j1_j3)), _e(max(0,rev_j-g_j4_j363)), _e(rev_j)),
    ], cw_ic)
    _legende(pdf,
        "(1) Le maintien de salaire correspond au complement de salaire legal, augmente "
        "le cas echeant des prestations versees dans le cadre d un accord collectif.\n"
        "(2) Le besoin en revenu de {} est estime a 100 % du revenu journalier, "
        "soit {}.".format(nom_c, _e(rev_j)))
    pdf.ln(3)

    if has_cj and nom_ccj and rev_j_cj > 0:
        g_cj_j1  = rev_j_cj * 0.5
        g_cj_j4  = rev_j_cj * 0.35
        # H3 — Garanties incapacité conjoint
        _h3_axa(pdf, "Garanties incapacite de {} au {}".format(nom_ccj, today))
        img_inc2 = _incapacite_courbe_axa(rev_j_cj, nom_ccj, g_cj_j1, g_cj_j4, 0)
        _insert_img(pdf, img_inc2, "/tmp/g_inc2.png", w=170, h=70)
        _th(pdf, [" ","Du 1er au 3eme jour","Du 4eme au 363eme jour","Du 364eme au 1095eme jour"],
            cw_ic, bg=C_TEAL)
        _tr(pdf, [
            ("Indemnites journalieres brutes", _e(g_cj_j1), _e(g_cj_j4), "0 EUR"),
            ("Regime professionnel obligatoire", "0 EUR", _e(g_cj_j4), "0 EUR"),
            ("Indemnites journalieres nettes", _e(g_cj_j1*0.9), _e(g_cj_j4*0.9), "0 EUR"),
            ("Besoin en revenus (1)", _e(rev_j_cj), _e(rev_j_cj), _e(rev_j_cj)),
            ("Besoin a couvrir",
             _e(max(0,rev_j_cj-g_cj_j1)), _e(max(0,rev_j_cj-g_cj_j4)), _e(rev_j_cj)),
        ], cw_ic)
        _legende(pdf,
            "(1) Le besoin en revenu de {} est estime a 100 % du revenu journalier, "
            "soit {}.".format(nom_ccj, _e(rev_j_cj)))
    pdf.ln(3)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Analyse de votre prévoyance invalidité
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Analyse de votre situation (suite)")
    _h2(pdf, "Analyse de votre prevoyance invalidite")

    def _inv_g(rev_ann, ind_m):
        ind_a = ind_m * 12 if ind_m else 0
        return (0, rev_ann*0.121+ind_a, rev_ann*0.202+ind_a, rev_ann*0.338+ind_a)

    g33, g66, g100, gptia = _inv_g(bilan.revenus_annuels_client, ind_inv)

    # H3 — Garanties invalidité de [client] au [date]
    _h3_axa(pdf, "Garanties invalidite de {} au {}".format(nom_c, today))
    img_inv1 = _invalidite_barres_axa(bilan.revenus_annuels_client, nom_c, g33, g66, g100, gptia)
    _insert_img(pdf, img_inv1, "/tmp/g_inv1.png", w=170, h=76)

    cw_inv = [52,30,32,32,24]
    _th(pdf, [" ","Invalidite > 33 %","Invalidite > 66 % (2)","Invalidite 100 % (2)","Perte autonomie"],
        cw_inv, bg=C_TEAL)
    _tr(pdf, [
        ("Rente annuelle brute", _e(g33), _e(g66), _e(g100), _e(gptia)),
        ("Regimes obligatoires", _e(g33), _e(g66), _e(g100), _e(gptia)),
        ("Rente annuelle nette", _e(g33*0.9), _e(g66*0.9), _e(g100*0.9), _e(gptia*0.9)),
        ("Besoin en revenus (1)", _e(bilan.revenus_annuels_client),"","",""),
        ("Besoin a couvrir",
         _e(max(0,bilan.revenus_annuels_client-g33)),
         _e(max(0,bilan.revenus_annuels_client-g66)),
         _e(max(0,bilan.revenus_annuels_client-g100)),
         _e(max(0,bilan.revenus_annuels_client-gptia))),
    ], cw_inv)
    _legende(pdf,
        "(1) Le besoin en revenu de {} est estime a 100% du revenu annuel, soit {}.\n"
        "(2) Les garanties correspondant aux invalidites de 1ere et 2eme categorie de la "
        "Securite sociale sont respectivement presentees dans les colonnes Invalidite > 66 % "
        "et Invalidite 100 %.\n"
        "(3) Un assure est considere en Perte Totale et Irreversible d Autonomie (PTIA) "
        "s il ne peut effectuer seul au moins 4 actes de la vie quotidienne.".format(
        nom_c, _e(bilan.revenus_annuels_client)))
    pdf.ln(3)

    if has_cj and nom_ccj and bilan.revenus_annuels_conjoint > 0:
        g33c, g66c, g100c, gptiac = _inv_g(bilan.revenus_annuels_conjoint, 0)
        # H3 — Garanties invalidité conjoint
        _h3_axa(pdf, "Garanties invalidite de {} au {}".format(nom_ccj, today))
        img_inv2 = _invalidite_barres_axa(bilan.revenus_annuels_conjoint, nom_ccj,
                                           g33c, g66c, g100c, gptiac)
        _insert_img(pdf, img_inv2, "/tmp/g_inv2.png", w=170, h=76)
        _th(pdf, [" ","Invalidite > 33 %","Invalidite > 66 % (2)","Invalidite 100 % (2)","Perte autonomie"],
            cw_inv, bg=C_TEAL)
        _tr(pdf, [
            ("Rente annuelle brute", _e(g33c), _e(g66c), _e(g100c), _e(gptiac)),
            ("Besoin en revenus (1)", _e(bilan.revenus_annuels_conjoint),"","",""),
            ("Besoin a couvrir",
             _e(max(0,bilan.revenus_annuels_conjoint-g33c)),
             _e(max(0,bilan.revenus_annuels_conjoint-g66c)),
             _e(max(0,bilan.revenus_annuels_conjoint-g100c)),
             _e(max(0,bilan.revenus_annuels_conjoint-gptiac))),
        ], cw_inv)
        _legende(pdf,
            "(1) Le besoin en revenu de {} est estime a 100% du revenu annuel, "
            "soit {}.".format(nom_ccj, _e(bilan.revenus_annuels_conjoint)))
    pdf.ln(3)

    # ─────────────────────────────────────────────────────────────────────────
    #  H2 — Analyse successorale
    # ─────────────────────────────────────────────────────────────────────────
    if nb_enf > 0:
        pdf.add_page(); _footer(pdf, today)
        _h1(pdf, "Analyse de votre situation (suite)")
        _h2(pdf, "Analyse successorale")
        _legende(pdf,
            "Simulation basee sur le droit successoral francais en vigueur. "
            "Abattements : 100 000 EUR par enfant (renouvele tous les 15 ans). "
            "Conjoint survivant : totalement exonere. "
            "Cette simulation est indicative — consultez un notaire.")
        pdf.ln(2)

        try:
            scenarios = simuler_succession(data, bilan.actif_net)
        except Exception:
            scenarios = []

        cw_sc = [38,28,26,22,22,24,20]
        hdrs_sc = ["Heritier","Heritage brut","Abattement","Base taxable",
                   "Droits","Cap. deces","Transm. nette"]

        for sc in scenarios:
            # H3 — Décès de [personne] puis de [autre]
            _h3_axa(pdf, "Deces de {}".format(sc.scenario))

            # H4 — Première transmission
            _h4_axa(pdf, "Succession de {} (premiere transmission) — masse : {}".format(
                sc.scenario.split(" puis")[0], _e(sc.masse_successorale_1)))
            pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
            pdf.multi_cell(190,6,
                "Nous avons suppose que le conjoint survivant recevrait la totalite de "
                "la masse successorale en usufruit.")
            pdf.ln(2)
            _th(pdf, hdrs_sc, cw_sc)
            rows_sc = []
            for h in sc.heritiers_1:
                rows_sc.append((h.nom[:16], _e(h.heritage_brut), _e(h.abattement),
                                _e(h.base_taxable), _e(h.droits),
                                _e(h.capitaux_deces) if hasattr(h,"capitaux_deces") and h.capitaux_deces else "—",
                                _e(h.transmission_nette)))
            rows_sc.append(("Total","","","",_e(sc.total_droits_1),"",_e(sc.total_transmission_1)))
            _tr(pdf, rows_sc, cw_sc, bold_last=True)
            pdf.ln(3)

            if sc.heritiers_2:
                # H4 — Seconde transmission
                _h4_axa(pdf, "Succession du survivant (seconde transmission) — masse : {}".format(
                    _e(sc.masse_successorale_2)))
                _th(pdf, hdrs_sc, cw_sc)
                rows_sc2 = []
                for h in sc.heritiers_2:
                    rows_sc2.append((h.nom[:16], _e(h.heritage_brut), _e(h.abattement),
                                     _e(h.base_taxable), _e(h.droits),
                                     _e(h.capitaux_deces) if hasattr(h,"capitaux_deces") and h.capitaux_deces else "—",
                                     _e(h.transmission_nette)))
                rows_sc2.append(("Total","","","",_e(sc.total_droits_2),"",_e(sc.total_transmission_2)))
                _tr(pdf, rows_sc2, cw_sc, bold_last=True)
                pdf.ln(4)

        # ─────────────────────────────────────────────────────────────────────
        #  H2 — Comparaison des donations au dernier vivant
        # ─────────────────────────────────────────────────────────────────────
        if has_cj and scenarios:
            pdf.add_page(); _footer(pdf, today)
            _h1(pdf, "Analyse de votre situation (suite)")
            _h2(pdf, "Comparaison des donations au dernier vivant")
            _legende(pdf,
                "PP = Pleine Propriete | USF = Usufruit | NP = Nue-Propriete. "
                "Le droit legal au conjoint survivant est la totalite en usufruit. "
                "Une donation entre epoux doit etre etablie par acte notarie.")
            pdf.ln(3)

            sc0   = scenarios[0]
            masse = sc0.masse_successorale_1
            nb_e  = max(1, nb_enf)

            def _don_opt(masse, nb_e, option):
                if option in ("tout_usf","tout_usf_don"):
                    dr = sum(h.droits for h in sc0.heritiers_1 if getattr(h,"lien","") == "enfant")
                    te = sum(h.transmission_nette for h in sc0.heritiers_1 if getattr(h,"lien","") == "enfant")
                    tc = masse - sum(h.heritage_brut for h in sc0.heritiers_1 if getattr(h,"lien","") == "enfant")
                    return dr, tc, te
                elif option == "quart_pp":
                    pc = masse*0.25; pe = masse*0.75/nb_e; dr=0; te=0
                    for _ in range(nb_e):
                        b=max(0,pe-100000); dr+=_droits_ligne_directe(b); te+=pe-_droits_ligne_directe(b)
                    return dr, pc, te
                elif option == "quotite_disp":
                    frac = 0.5 if nb_e==1 else (1/3 if nb_e==2 else 0.25)
                    pc=masse*frac; pe=masse*(1-frac)/nb_e; dr=0; te=0
                    for _ in range(nb_e):
                        b=max(0,pe-100000); dr+=_droits_ligne_directe(b); te+=pe-_droits_ligne_directe(b)
                    return dr, pc, te
                elif option == "trois_quarts_usf":
                    pc=masse*0.75; pe=masse*0.25/nb_e; dr=0; te=0
                    for _ in range(nb_e):
                        b=max(0,pe-100000); dr+=_droits_ligne_directe(b); te+=pe-_droits_ligne_directe(b)
                    return dr, pc, te
                return 0, 0, 0

            options_don = [
                ("Droit legal — Totalite en USF", "tout_usf"),
                ("1/4 en PP", "quart_pp"),
                ("Totalite en USF (donation)", "tout_usf_don"),
                ("Quotite disponible en PP", "quotite_disp"),
                ("3/4 en USF et 1/4 en PP", "trois_quarts_usf"),
            ]

            # Tableau sur 2 colonnes : Transmission 1er décès + 2ème décès
            cw_don = [54,28,32,32,26,18]
            _th(pdf, [" ","Droits enf.","Part conjoint","Part enfants","Transm. nette","Cov."], cw_don)
            rows_don = []
            for lbl, opt in options_don:
                dr, cj, enf_v = _don_opt(masse, nb_e, opt)
                tn = cj + enf_v - dr
                cov = "> 100 %" if cap_deces >= dr else ("{:.0f} %".format(cap_deces/dr*100) if dr>0 else "0 %")
                rows_don.append((lbl, _e(dr), _e(cj), _e(enf_v), _e(tn), cov))
            _tr(pdf, rows_don, cw_don)
            pdf.ln(2)
            _legende(pdf, "PP signifie Pleine Propriete, NP Nue-Propriete et USF Usufruit.")
            pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  Recommandations
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Recommandations")
    _h2(pdf, "Points forts")
    for pt in bilan.points_forts:
        pdf.set_x(14); pdf.set_font("Helvetica","B",9)
        pdf.set_text_color(*C_TEAL); pdf.cell(5,6,"+")
        pdf.set_font("Helvetica","",9); pdf.set_text_color(0,0,0)
        pdf.multi_cell(171,6,pt)
    pdf.ln(3)

    _h2(pdf, "Points de vigilance")
    for pt in (bilan.points_vigilance or []):
        pdf.set_x(14); pdf.set_font("Helvetica","B",9)
        pdf.set_text_color(*C_RED); pdf.cell(5,6,"!")
        pdf.set_font("Helvetica","",9); pdf.set_text_color(0,0,0)
        pdf.multi_cell(171,6,pt)
    if not bilan.points_vigilance:
        pdf.set_x(14); pdf.set_font("Helvetica","I",9)
        pdf.cell(176,6,"Aucun point de vigilance majeur identifie.",ln=True)
    pdf.ln(3)

    _h2(pdf, "Recommandations prioritaires")
    for i, reco in enumerate(bilan.recommandations, 1):
        pdf.set_x(14); pdf.set_font("Helvetica","B",9)
        pdf.set_text_color(*C_NAVY); pdf.cell(7,6,"{}.".format(i))
        pdf.set_font("Helvetica","",9); pdf.set_text_color(0,0,0)
        pdf.multi_cell(169,6,reco)
    pdf.ln(3)

    od = data.get("objectifs",{})
    if od.get("objectifs"):
        _h2(pdf, "Profil et objectifs patrimoniaux declares")
        pdf.set_x(10); pdf.set_font("Helvetica","",8.5)
        pdf.cell(95,6,"Profil de risque : {}".format(od.get("profil_risque","N/R")))
        pdf.cell(95,6,"Horizon : {}".format(od.get("horizon_investissement","N/R")),ln=True)
        for o in od.get("objectifs",[]):
            pdf.set_x(14); pdf.cell(176,5,"- {}".format(o),ln=True)
        pdf.ln(2)

    if od.get("commentaires","").strip():
        _h2(pdf, "Commentaires et remarques du conseiller")
        pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
        pdf.multi_cell(190,6,od["commentaires"])
    pdf.ln(4)

    # ─────────────────────────────────────────────────────────────────────────
    #  H1 — ANNEXES
    # ─────────────────────────────────────────────────────────────────────────
    pdf.add_page(); _footer(pdf, today)
    _h1(pdf, "Annexes")

    # H2 — Plafonnement du quotient familial
    _h2(pdf, "Plafonnement du quotient familial")

    # H3 — Situation de [client] et [conjoint]
    nom_et = "{} et {}".format(nom_c, nom_ccj) if has_cj and nom_ccj else nom_c
    _h3_axa(pdf, "Situation de {}".format(nom_et))

    pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
    pdf.multi_cell(190,6,
        "L avantage fiscal lie au quotient familial est limite par un mecanisme de "
        "plafonnement. Dans ce cas, le Taux Marginal d Imposition reel peut etre plus "
        "eleve que celui calcule precedemment.")
    pdf.ln(3)

    if rfr and ir_ann:
        ir_avant = ir_ann * 0.932
        plaf_qf  = ir_ann - ir_avant
        cw_qf = [130,60]
        _th(pdf, ["Designation","Montant"], cw_qf)
        _tr(pdf, [
            ("Impot brut avant plafonnement du quotient familial", _e(ir_avant)),
            ("Plafonnement du quotient familial", _e(plaf_qf)),
            ("Impot brut apres effet du plafonnement du quotient familial", _e(ir_ann)),
            ("Reduction d impot et autres imputations", "0 EUR"),
            ("Impot sur le revenu", _e(ir_ann)),
            ("Retenue a la source et acomptes payes", _e(-ir_ann)),
            ("Solde de l impot sur les revenus {}".format(int(yr)-1), "0 EUR"),
            ("Contributions sociales", _e(ps_ann)),
            ("Solde de contributions sociales {}".format(int(yr)-1), "0 EUR"),
            ("Taux moyen d imposition (administration fiscale)",
             "{:.2f} %".format(ir_ann/rfr*100) if rfr else "—"),
            ("Taux Marginal d Imposition (TMI)", tmi),
        ], cw_qf)
    pdf.ln(4)

    # H2 — Impôt brut et barème
    _h2(pdf, "Impot brut et bareme")

    # H3 — Situation de [client]
    _h3_axa(pdf, "Situation de {}".format(nom_et))

    pdf.set_font("Helvetica","",8.5); pdf.set_x(10)
    pdf.multi_cell(190,6,
        "L impot sur le revenu se calcule sur la base du Revenu Net Imposable : on retranche "
        "aux differents revenus nets categoreis les charges deductibles du revenu global. "
        "Ce revenu net est ensuite divise par le nombre de parts, fixe d apres la situation "
        "et les charges de famille : c est le systeme du quotient familial.")
    pdf.ln(3)

    if rfr:
        qf = rfr / parts if parts > 0 else rfr
        cw_b = [130,60]
        _th(pdf, ["Designation","Montant"], cw_b)
        _tr(pdf, [
            ("Revenu Net Imposable", _e(rfr)),
            ("Nombre de parts", "{:.2f}".format(parts)),
            ("Quotient familial", _e(qf)),
        ], cw_b)
        pdf.ln(3)

        # Tableau barème
        cw_bar = [60,32,18,30]
        _th(pdf, ["Tranche","Montant","Taux *","Impot brut"], cw_bar)
        rows_bar = []
        TRANCHES = [(11497,0.0),(16206,0.11),(47836,0.30),(205736,0.41),(999999999,0.45)]
        prev_plaf = 0
        ir_calc = 0
        for plaf, taux in TRANCHES:
            part_tranche = min(qf, plaf) - prev_plaf
            if part_tranche <= 0:
                prev_plaf = min(qf, plaf)
                continue
            imp = part_tranche * taux
            ir_calc += imp * parts
            if prev_plaf == 0:
                lbl = "Jusqu a {:,.0f} EUR".format(min(qf,plaf)*parts).replace(",", " ")
            else:
                lbl = "De {:,.0f} EUR a {:,.0f} EUR".format(
                    prev_plaf*parts, min(qf,plaf)*parts).replace(",", " ")
            rows_bar.append((lbl,
                             _e(part_tranche*parts),
                             "{:.2f} %".format(taux*100),
                             _e(imp*parts)))
            prev_plaf = min(qf, plaf)
            if qf <= plaf:
                break
        rows_bar.append(("Total", _e(rfr), "", _e(ir_ann or ir_calc)))
        _tr(pdf, rows_bar, cw_bar, bold_last=True)
        pdf.ln(2)
        _legende(pdf,
            "(*) Le taux applique au dernier euro declare sur la derniere tranche "
            "represente votre Taux Marginal d Imposition (TMI) en l absence de "
            "plafonnement du quotient familial.")

        # Image barème
        img_bar = _bareme_ir_axa(rfr, parts)
        _insert_img(pdf, img_bar, "/tmp/g_bar.png", w=160, h=30)

    pdf.ln(4)

    # Mention légale finale
    pdf.set_draw_color(*C_RED); pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.set_line_width(0.2); pdf.set_draw_color(0,0,0)
    pdf.ln(4)
    _legende(pdf,
        "Document confidentiel etabli a titre informatif uniquement. "
        "Ne constitue pas un conseil en investissement financier au sens de la directive MIF2. "
        "Les informations sont basees sur les elements declares par le client lors de "
        "l entretien du {}. "
        "Les rendements passes ne prejugent pas des rendements futurs. "
        "My Campus Patrimoine — www.mycampuspatrimoine.fr".format(today))

    return bytes(pdf.output())
