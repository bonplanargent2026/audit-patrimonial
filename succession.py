"""
succession.py — Calculs de succession, projection patrimoine et graphiques PDF.
Utilisé par report.py pour enrichir le bilan patrimonial.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import math


# ─────────────────────────────────────────────
#  BARÈME DROITS DE SUCCESSION 2024 (France)
# ─────────────────────────────────────────────

# Abattements légaux (en euros)
ABATTEMENTS = {
    "conjoint":   500_000,  # Totalement exonéré (mais on garde pour calcul enfants)
    "enfant":     100_000,
    "petit_enfant": 1_594,
    "frere_soeur": 15_932,
    "neveu_niece": 7_967,
    "autre":       1_594,
}

# Barème progressif enfants / en ligne directe
BAREME_LIGNE_DIRECTE = [
    (8_072,    0.05),
    (12_109,   0.10),
    (15_932,   0.15),
    (552_324,  0.20),
    (902_838,  0.30),
    (1_805_677, 0.40),
    (float('inf'), 0.45),
]

# Barème frères/sœurs
BAREME_FRERE_SOEUR = [
    (24_430, 0.35),
    (float('inf'), 0.45),
]

# Barème autres (neveux, non-parents)
BAREME_AUTRE = [(float('inf'), 0.60)]


def _droits_ligne_directe(base: float) -> float:
    """Calcule les droits de succession en ligne directe après abattement."""
    if base <= 0:
        return 0.0
    droits = 0.0
    precedent = 0.0
    for plafond, taux in BAREME_LIGNE_DIRECTE:
        tranche = min(base, precedent + plafond) - precedent
        if tranche <= 0:
            break
        droits += tranche * taux
        precedent += plafond
        if precedent >= base:
            break
    return round(droits, 2)


def _droits_par_lien(base: float, lien: str) -> float:
    if base <= 0:
        return 0.0
    if lien in ("conjoint", "partenaire_pacs"):
        return 0.0  # Totalement exonéré
    elif lien == "enfant":
        return _droits_ligne_directe(base)
    elif lien in ("frere", "soeur"):
        d = 0.0
        for plafond, taux in BAREME_FRERE_SOEUR:
            t = min(base, plafond)
            d += t * taux
            base -= t
            if base <= 0:
                break
        return round(d, 2)
    else:
        return round(base * 0.60, 2)


def _abattement(lien: str) -> float:
    mapping = {
        "conjoint": 0,          # exonéré totalement
        "partenaire_pacs": 0,
        "enfant": 100_000,
        "petit_enfant": 1_594,
        "frere": 15_932,
        "soeur": 15_932,
        "neveu": 7_967,
        "niece": 7_967,
    }
    return mapping.get(lien, 1_594)


# ─────────────────────────────────────────────
#  SIMULATION SUCCESSION
# ─────────────────────────────────────────────

@dataclass
class HeritierResult:
    nom:              str
    lien:             str
    heritage_brut:    float
    abattement:       float
    base_taxable:     float
    droits:           float
    capitaux_deces:   float
    reunion_usufruit: float
    transmission_nette: float


@dataclass
class SuccessionResult:
    scenario:              str
    premier_deces:         str
    second_deces:          str
    masse_successorale_1:  float
    masse_successorale_2:  float
    heritiers_1:           List[HeritierResult]
    heritiers_2:           List[HeritierResult]
    total_droits_1:        float
    total_droits_2:        float
    total_transmission_1:  float
    total_transmission_2:  float


def _valeur_usufruit(age: int) -> float:
    """Table fiscale usufruit/nue-propriété (article 669 CGI)."""
    table = [
        (21,  0.90), (31, 0.80), (41, 0.70), (51, 0.60),
        (61,  0.50), (71, 0.40), (81, 0.30), (91, 0.20),
        (float('inf'), 0.10)
    ]
    for age_max, val in table:
        if age < age_max:
            return val
    return 0.10


def simuler_succession(data: dict, bilan_actif_net: float) -> List[SuccessionResult]:
    """
    Simule 2 scénarios de succession :
    - Scénario 1 : décès du client en premier, puis du conjoint
    - Scénario 2 : décès du conjoint en premier, puis du client
    """
    ide   = data.get("identite", {})
    sfam  = data.get("situation_familiale", {})
    prev  = data.get("prevoyance", {})
    enfants = sfam.get("enfants", [])
    a_conjoint = ide.get("a_conjoint", False)

    prenom1 = ide.get("prenom", "Client")
    prenom2 = ide.get("prenom_conjoint", "Conjoint") if a_conjoint else ""

    # Capitaux décès assurance vie
    cap_deces = prev.get("capital_deces", 0.0)
    # On suppose 50/50 si couple
    cap_dec_1 = cap_deces if not a_conjoint else cap_deces / 2
    cap_dec_2 = cap_deces / 2 if a_conjoint else 0

    # Âge pour calcul usufruit
    def _get_age_num(dob_str: str) -> int:
        try:
            p = dob_str.strip().split("/")
            if len(p) == 3:
                from datetime import date
                d = date(int(p[2]), int(p[1]), int(p[0]))
                return (date.today() - d).days // 365
        except Exception:
            pass
        return 55

    age1 = _get_age_num(ide.get("dob", ""))
    age2 = _get_age_num(ide.get("dob_conjoint", "")) if a_conjoint else 0

    # Masse successorale simplifiée
    # En communauté : 50% à la succession + biens propres
    regime = sfam.get("regime_matrimonial", "")
    if a_conjoint and "communauté" in regime.lower():
        masse_base = bilan_actif_net / 2
    else:
        masse_base = bilan_actif_net

    nb_enfants = max(sfam.get("nb_enfants", 0), len(enfants))
    noms_enfants = [e.get("prenom", f"Enfant {i+1}") for i, e in enumerate(enfants)]
    if len(noms_enfants) < nb_enfants:
        noms_enfants += [f"Enfant {i+1}" for i in range(len(noms_enfants), nb_enfants)]

    resultats = []

    for scenario_num in range(1 if not a_conjoint else 2):
        if scenario_num == 0:
            # Décès client en premier
            premier  = prenom1
            second   = prenom2 if a_conjoint else "—"
            masse_1  = masse_base
            age_surv = age2
        else:
            # Décès conjoint en premier
            premier  = prenom2
            second   = prenom1
            masse_1  = masse_base
            age_surv = age1

        # ── PREMIÈRE TRANSMISSION ────────────────────────────────────────────
        heritiers_1: List[HeritierResult] = []
        total_droits_1 = 0.0

        if a_conjoint and nb_enfants > 0:
            # Conjoint survivant reçoit totalité en usufruit (option classique)
            val_usuf = _valeur_usufruit(age_surv)
            heritage_conjoint = masse_1 * val_usuf
            heritage_enfants  = masse_1 * (1 - val_usuf)  # nue-propriété

            # Conjoint — exonéré
            hr_cj = HeritierResult(
                nom=second, lien="conjoint",
                heritage_brut=heritage_conjoint,
                abattement=heritage_conjoint,
                base_taxable=0,
                droits=0,
                capitaux_deces=cap_dec_2 if scenario_num == 0 else cap_dec_1,
                reunion_usufruit=0,
                transmission_nette=heritage_conjoint + (cap_dec_2 if scenario_num==0 else cap_dec_1),
            )
            heritiers_1.append(hr_cj)

            # Enfants — nue-propriété
            if nb_enfants > 0:
                part_par_enfant = heritage_enfants / nb_enfants
                cap_enf = 0  # capitaux décès en nue-propriété = 0 ici
                for nom_e in noms_enfants:
                    abatt = _abattement("enfant")
                    base  = max(0, part_par_enfant - abatt)
                    droit = _droits_par_lien(base, "enfant")
                    total_droits_1 += droit
                    hr_e = HeritierResult(
                        nom=nom_e, lien="enfant",
                        heritage_brut=part_par_enfant,
                        abattement=min(abatt, part_par_enfant),
                        base_taxable=base,
                        droits=droit,
                        capitaux_deces=cap_enf,
                        reunion_usufruit=0,
                        transmission_nette=part_par_enfant - droit + cap_enf,
                    )
                    heritiers_1.append(hr_e)

        elif not a_conjoint and nb_enfants > 0:
            # Célibataire — tout aux enfants
            part_par_enfant = masse_1 / nb_enfants
            for nom_e in noms_enfants:
                abatt = _abattement("enfant")
                base  = max(0, part_par_enfant - abatt)
                droit = _droits_par_lien(base, "enfant")
                total_droits_1 += droit
                hr_e = HeritierResult(
                    nom=nom_e, lien="enfant",
                    heritage_brut=part_par_enfant,
                    abattement=min(abatt, part_par_enfant),
                    base_taxable=base,
                    droits=droit,
                    capitaux_deces=cap_dec_1/nb_enfants if nb_enfants else 0,
                    reunion_usufruit=0,
                    transmission_nette=part_par_enfant - droit,
                )
                heritiers_1.append(hr_e)
        else:
            # Pas d'héritiers connus
            hr = HeritierResult(
                nom="Heritiers non definis", lien="autre",
                heritage_brut=masse_1, abattement=0,
                base_taxable=masse_1,
                droits=_droits_par_lien(masse_1, "autre"),
                capitaux_deces=0, reunion_usufruit=0,
                transmission_nette=masse_1 - _droits_par_lien(masse_1, "autre"),
            )
            total_droits_1 += hr.droits
            heritiers_1.append(hr)

        total_transm_1 = sum(h.transmission_nette for h in heritiers_1)

        # ── DEUXIÈME TRANSMISSION (conjoint → enfants) ────────────────────────
        heritiers_2: List[HeritierResult] = []
        total_droits_2 = 0.0

        if a_conjoint and nb_enfants > 0:
            # Masse 2 = actif conjoint survivant + réunion usufruit
            val_usuf = _valeur_usufruit(age_surv)
            masse_usuf_reunie = masse_1 * val_usuf  # l'usufruit se réunit à la NP sans droits
            # Mais la succession du conjoint inclut sa propre part
            masse_2 = masse_base + masse_usuf_reunie  # succession du 2ème conjoint

            part_par_enfant_2 = masse_2 / nb_enfants
            # Abattement déjà utilisé en partie — on applique l'abattement résiduel (100k - déjà utilisé)
            # Simplification : on réapplique l'abattement complet (légalement correct si >15 ans entre donations)
            for i, nom_e in enumerate(noms_enfants):
                abatt = _abattement("enfant")
                base  = max(0, part_par_enfant_2 - abatt)
                droit = _droits_par_lien(base, "enfant")
                total_droits_2 += droit
                hr_e2 = HeritierResult(
                    nom=nom_e, lien="enfant",
                    heritage_brut=part_par_enfant_2,
                    abattement=min(abatt, part_par_enfant_2),
                    base_taxable=base,
                    droits=droit,
                    capitaux_deces=cap_dec_2/nb_enfants if scenario_num==0 else cap_dec_1/nb_enfants,
                    reunion_usufruit=masse_usuf_reunie / nb_enfants,
                    transmission_nette=part_par_enfant_2 - droit,
                )
                heritiers_2.append(hr_e2)

        total_transm_2 = sum(h.transmission_nette for h in heritiers_2)

        sc_label = f"Deces de {premier} en premier" + (f", puis {second}" if second != "—" else "")
        resultats.append(SuccessionResult(
            scenario=sc_label,
            premier_deces=premier,
            second_deces=second,
            masse_successorale_1=masse_1,
            masse_successorale_2=masse_base if a_conjoint else 0,
            heritiers_1=heritiers_1,
            heritiers_2=heritiers_2,
            total_droits_1=total_droits_1,
            total_droits_2=total_droits_2,
            total_transmission_1=total_transm_1,
            total_transmission_2=total_transm_2,
        ))

    return resultats


# ─────────────────────────────────────────────
#  PROJECTION PATRIMOINE
# ─────────────────────────────────────────────

@dataclass
class ProjectionAnnee:
    annee:          int
    age_client:     int
    actif_brut:     float
    passif:         float
    actif_net:      float
    epargne_cumul:  float
    capital_immo:   float
    capital_fin:    float


def projeter_patrimoine(data: dict, bilan, nb_annees: int = 20) -> List[ProjectionAnnee]:
    """
    Projette l'évolution du patrimoine sur nb_annees années.
    Hypothèses :
    - Immobilier : +2% / an (valorisation)
    - Actifs financiers : rendement moyen pondéré des actifs déclarés
    - Crédits : remboursement mensuel constant → capital restant dû décroît
    - Épargne mensuelle : placée sur actifs financiers
    """
    from datetime import date as dt

    ide   = data.get("identite", {})
    afin  = data.get("actifs_financiers", [])
    cred  = data.get("credits", [])
    prev  = data.get("prevoyance", {})

    # Âge client
    try:
        p = ide.get("dob","").strip().split("/")
        dob = dt(int(p[2]),int(p[1]),int(p[0]))
        age_base = (dt.today()-dob).days//365
    except Exception:
        age_base = 45

    # Rendement moyen actifs financiers
    if afin:
        rdt_moyen = sum(a.get("taux_rendement",2.0) for a in afin) / len(afin) / 100
    else:
        rdt_moyen = 0.02

    TAUX_IMMO    = 0.02   # revalorisation immobilier
    TAUX_INFLAT  = 0.02   # inflation approximative

    actif_immo_0  = bilan.actif_immobilier
    actif_fin_0   = bilan.actif_financier + bilan.actif_tresorerie
    passif_0      = bilan.passif_total
    epargne_m     = max(0, bilan.capacite_epargne_mensuelle)

    # Mensualités crédits totales
    mensualites   = sum(c.get("mensualite",0) for c in cred)

    # Calcul capital restant dû simplifié : décroissance linéaire sur durée restante
    credits_info = []
    annee_actu   = dt.today().year
    for cr in cred:
        ann_fin = cr.get("annee_fin", annee_actu+10)
        duree_rest = max(1, ann_fin - annee_actu)
        crd = cr.get("capital_restant_du", 0)
        credits_info.append({"crd": crd, "duree": duree_rest, "mens": cr.get("mensualite",0)})

    resultats: List[ProjectionAnnee] = []
    actif_immo = actif_immo_0
    actif_fin  = actif_fin_0
    passif     = passif_0
    epargne_c  = 0.0

    for an in range(nb_annees + 1):
        annee = dt.today().year + an
        age   = age_base + an

        actif_net = actif_immo + actif_fin - passif
        resultats.append(ProjectionAnnee(
            annee=annee, age_client=age,
            actif_brut=actif_immo+actif_fin,
            passif=passif,
            actif_net=actif_net,
            epargne_cumul=epargne_c,
            capital_immo=actif_immo,
            capital_fin=actif_fin,
        ))

        if an < nb_annees:
            # Mise à jour annuelle
            actif_immo = actif_immo * (1 + TAUX_IMMO)
            actif_fin  = actif_fin * (1 + rdt_moyen) + epargne_m * 12
            epargne_c += epargne_m * 12

            # Remboursement crédits
            remb_annuel = 0.0
            for cr_info in credits_info:
                if cr_info["duree"] > 0:
                    remb_ann = min(cr_info["mens"]*12, cr_info["crd"])
                    remb_annuel += remb_ann
                    cr_info["crd"] = max(0, cr_info["crd"] - remb_ann)
                    cr_info["duree"] -= 1
            passif = max(0, sum(ci["crd"] for ci in credits_info))

    return resultats


# ─────────────────────────────────────────────
#  GRAPHIQUES → PNG en mémoire (matplotlib)
# ─────────────────────────────────────────────

def _try_import_mpl():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        return plt, mpatches
    except ImportError:
        return None, None


def graphique_repartition(repartition: dict, actif_brut: float) -> bytes:
    """Camembert répartition patrimoine → PNG bytes."""
    plt, mp = _try_import_mpl()
    if plt is None:
        return b""
    fig, ax = plt.subplots(figsize=(5, 3.5), dpi=110)
    labels = list(repartition.keys())
    values = list(repartition.values())
    colors = ["#1e3a5f","#2c7a7b","#f6ad55"]
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=140,
        pctdistance=0.75, labeldistance=1.1,
        wedgeprops=dict(width=0.55)
    )
    for t in texts: t.set_fontsize(9)
    for at in autotexts: at.set_fontsize(8); at.set_color("white")
    ax.set_title(f"Repartition du patrimoine\nActif brut : {actif_brut:,.0f} EUR".replace(",", " "),
                 fontsize=10, fontweight="bold", color="#1e3a5f", pad=10)
    plt.tight_layout()
    buf = __import__("io").BytesIO()
    plt.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def graphique_revenus_charges(bilan) -> bytes:
    """Barres revenus vs charges → PNG bytes."""
    plt, mp = _try_import_mpl()
    if plt is None:
        return b""
    fig, ax = plt.subplots(figsize=(5, 3.5), dpi=110)
    categories = ["Revenus\nannuels", "Charges\ncourantes", "Mensualites\ncredits", "Epargne\nannuelle"]
    values = [
        bilan.revenus_annuels_total,
        bilan.charges_annuelles_courantes,
        bilan.charges_annuelles_credits,
        max(0, bilan.capacite_epargne_annuelle),
    ]
    colors_bar = ["#2c7a7b","#fc8181","#f6ad55","#68d391"]
    bars = ax.bar(categories, values, color=colors_bar, edgecolor="white", linewidth=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+max(values)*0.01,
                f"{val:,.0f}".replace(",", " "), ha="center", va="bottom", fontsize=7.5)
    ax.set_ylabel("EUR", fontsize=8)
    ax.set_title("Flux financiers annuels", fontsize=10, fontweight="bold", color="#1e3a5f")
    ax.yaxis.set_major_formatter(__import__("matplotlib").ticker.FuncFormatter(
        lambda x, _: f"{x:,.0f}".replace(",", " ")))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)
    plt.tight_layout()
    buf = __import__("io").BytesIO()
    plt.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def graphique_projection(projection: List[ProjectionAnnee]) -> bytes:
    """Courbe évolution patrimoine → PNG bytes."""
    plt, mp = _try_import_mpl()
    if plt is None:
        return b""
    annees   = [p.annee for p in projection]
    actif_n  = [p.actif_net/1000 for p in projection]
    actif_b  = [p.actif_brut/1000 for p in projection]
    passif   = [p.passif/1000 for p in projection]
    cap_fin  = [p.capital_fin/1000 for p in projection]

    fig, ax = plt.subplots(figsize=(8, 4), dpi=110)
    ax.fill_between(annees, actif_n, alpha=0.15, color="#1e3a5f")
    ax.plot(annees, actif_n,  color="#1e3a5f", linewidth=2,   label="Actif net", marker="o", markersize=3)
    ax.plot(annees, actif_b,  color="#2c7a7b", linewidth=1.5, label="Actif brut", linestyle="--")
    ax.plot(annees, passif,   color="#fc8181", linewidth=1.5, label="Passif (dettes)", linestyle=":")
    ax.plot(annees, cap_fin,  color="#f6ad55", linewidth=1.5, label="Actifs financiers", linestyle="-.")

    ax.set_xlabel("Annee", fontsize=9)
    ax.set_ylabel("Milliers EUR", fontsize=9)
    ax.set_title("Projection de l'evolution du patrimoine", fontsize=11, fontweight="bold", color="#1e3a5f")
    ax.legend(fontsize=8, loc="upper left")
    ax.yaxis.set_major_formatter(__import__("matplotlib").ticker.FuncFormatter(
        lambda x, _: f"{x:,.0f} k".replace(",", " ")))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.tick_params(labelsize=8)
    plt.tight_layout()
    buf = __import__("io").BytesIO()
    plt.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def graphique_succession_barres(resultats: List[SuccessionResult]) -> bytes:
    """Barres comparant droits vs transmission nette par héritier → PNG bytes."""
    plt, mp = _try_import_mpl()
    if plt is None or not resultats:
        return b""

    sc = resultats[0]
    heritiers = [h for h in sc.heritiers_1 if h.lien not in ("conjoint","partenaire_pacs")]
    if not heritiers:
        heritiers = sc.heritiers_1

    noms   = [h.nom for h in heritiers]
    transm = [h.transmission_nette/1000 for h in heritiers]
    droits = [h.droits/1000 for h in heritiers]

    x = range(len(noms))
    w = 0.35
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=110)
    b1 = ax.bar([i-w/2 for i in x], transm, w, label="Transmission nette (k EUR)", color="#2c7a7b")
    b2 = ax.bar([i+w/2 for i in x], droits, w, label="Droits de succession (k EUR)", color="#fc8181")
    ax.set_xticks(list(x))
    ax.set_xticklabels(noms, fontsize=9)
    ax.set_ylabel("Milliers EUR", fontsize=8)
    ax.set_title("Transmission nette vs Droits — 1er deces", fontsize=10, fontweight="bold", color="#1e3a5f")
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=8)
    plt.tight_layout()
    buf = __import__("io").BytesIO()
    plt.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
