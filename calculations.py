"""
calculations.py — Moteur de calcul patrimonial.

Toutes les fonctions sont pures : elles prennent un dictionnaire de données
(construit depuis le session_state Streamlit) et retournent des résultats
encapsulés dans un BilanPatrimonial.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ─────────────────────────────────────────────
#  Structure de résultat
# ─────────────────────────────────────────────

@dataclass
class BilanPatrimonial:
    """Tous les résultats issus des calculs patrimoniaux."""

    # ── Actif ──
    actif_immobilier: float = 0.0
    actif_financier: float = 0.0
    actif_tresorerie: float = 0.0
    actif_brut: float = 0.0

    # ── Passif ──
    passif_total: float = 0.0

    # ── Actif net ──
    actif_net: float = 0.0

    # ── Revenus annuels ──
    revenus_annuels_client: float = 0.0
    revenus_annuels_conjoint: float = 0.0
    revenus_annuels_total: float = 0.0

    # ── Charges annuelles ──
    charges_annuelles_courantes: float = 0.0
    charges_annuelles_credits: float = 0.0
    charges_annuelles_total: float = 0.0

    # ── Indicateurs clés ──
    capacite_epargne_annuelle: float = 0.0
    capacite_epargne_mensuelle: float = 0.0
    taux_endettement: float = 0.0       # en %
    taux_epargne: float = 0.0           # en %

    # ── Répartition du patrimoine (%) ──
    repartition_patrimoine: Dict[str, float] = field(default_factory=dict)

    # ── Analyse qualitative ──
    points_forts: List[str] = field(default_factory=list)
    points_vigilance: List[str] = field(default_factory=list)
    recommandations: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────
#  Fonction principale
# ─────────────────────────────────────────────

def calculer_bilan(data: dict) -> BilanPatrimonial:
    """
    Calcule l'ensemble du bilan patrimonial depuis les données du formulaire.

    Args:
        data: dict structuré collecté depuis st.session_state (voir app.py)

    Returns:
        BilanPatrimonial complet avec calculs et analyse qualitative
    """
    bilan = BilanPatrimonial()

    # ── Actif immobilier ──────────────────────────────────────────────────────
    bilan.actif_immobilier = sum(
        b.get("valeur_actuelle", 0.0)
        for b in data.get("immobilier", [])
    )

    # ── Actif financier ───────────────────────────────────────────────────────
    bilan.actif_financier = sum(
        a.get("valeur_actuelle", 0.0)
        for a in data.get("actifs_financiers", [])
    )

    # ── Trésorerie ────────────────────────────────────────────────────────────
    t = data.get("tresorerie", {})
    bilan.actif_tresorerie = (
        t.get("livret_a", 0.0)
        + t.get("ldds", 0.0)
        + t.get("livret_jeune", 0.0)
        + t.get("autres_livrets", 0.0)
        + t.get("compte_courant_disponible", 0.0)
        + t.get("autres_liquidites", 0.0)
    )

    # ── Actif brut ────────────────────────────────────────────────────────────
    bilan.actif_brut = (
        bilan.actif_immobilier
        + bilan.actif_financier
        + bilan.actif_tresorerie
    )

    # ── Passif ────────────────────────────────────────────────────────────────
    bilan.passif_total = sum(
        c.get("capital_restant_du", 0.0)
        for c in data.get("credits", [])
    )

    # ── Actif net ─────────────────────────────────────────────────────────────
    bilan.actif_net = bilan.actif_brut - bilan.passif_total

    # ── Revenus annuels ───────────────────────────────────────────────────────
    r = data.get("revenus", {})

    bilan.revenus_annuels_client = (
        r.get("salaire_net_mensuel", 0.0) * 12
        + r.get("primes_annuelles", 0.0)
        + r.get("revenus_fonciers_annuels", 0.0)
        + r.get("revenus_financiers_annuels", 0.0)
        + r.get("pensions_annuelles", 0.0)
        + r.get("revenus_independants_annuels", 0.0)
        + r.get("autres_revenus_annuels", 0.0)
    )

    bilan.revenus_annuels_conjoint = (
        r.get("salaire_net_mensuel_conjoint", 0.0) * 12
        + r.get("primes_annuelles_conjoint", 0.0)
        + r.get("pensions_annuelles_conjoint", 0.0)
        + r.get("autres_revenus_annuels_conjoint", 0.0)
    )

    bilan.revenus_annuels_total = (
        bilan.revenus_annuels_client + bilan.revenus_annuels_conjoint
    )

    # ── Charges annuelles ─────────────────────────────────────────────────────
    ch = data.get("charges", {})

    charges_mensuelles_courantes = (
        ch.get("loyer_mensuel", 0.0)
        + ch.get("charges_logement_mensuel", 0.0)
        + ch.get("alimentation_mensuel", 0.0)
        + ch.get("transport_mensuel", 0.0)
        + ch.get("assurances_mensuel", 0.0)
        + ch.get("loisirs_mensuel", 0.0)
        + ch.get("autres_charges_mensuel", 0.0)
    )

    bilan.charges_annuelles_courantes = (
        charges_mensuelles_courantes * 12
        + ch.get("scolarite_annuel", 0.0)
    )

    # Mensualités de crédits (× 12)
    mensualites_mensuelles = sum(
        c.get("mensualite", 0.0) for c in data.get("credits", [])
    )
    bilan.charges_annuelles_credits = mensualites_mensuelles * 12

    bilan.charges_annuelles_total = (
        bilan.charges_annuelles_courantes + bilan.charges_annuelles_credits
    )

    # ── Capacité d'épargne ────────────────────────────────────────────────────
    bilan.capacite_epargne_annuelle = (
        bilan.revenus_annuels_total - bilan.charges_annuelles_total
    )
    bilan.capacite_epargne_mensuelle = bilan.capacite_epargne_annuelle / 12

    # ── Taux d'endettement ────────────────────────────────────────────────────
    revenus_mensuels = bilan.revenus_annuels_total / 12
    if revenus_mensuels > 0:
        bilan.taux_endettement = (mensualites_mensuelles / revenus_mensuels) * 100

    # ── Taux d'épargne ────────────────────────────────────────────────────────
    if bilan.revenus_annuels_total > 0:
        bilan.taux_epargne = (
            bilan.capacite_epargne_annuelle / bilan.revenus_annuels_total * 100
        )

    # ── Répartition du patrimoine ─────────────────────────────────────────────
    if bilan.actif_brut > 0:
        bilan.repartition_patrimoine = {
            "Immobilier": round(
                bilan.actif_immobilier / bilan.actif_brut * 100, 1
            ),
            "Financier": round(
                bilan.actif_financier / bilan.actif_brut * 100, 1
            ),
            "Trésorerie": round(
                bilan.actif_tresorerie / bilan.actif_brut * 100, 1
            ),
        }

    # ── Analyse qualitative ───────────────────────────────────────────────────
    (
        bilan.points_forts,
        bilan.points_vigilance,
        bilan.recommandations,
    ) = _analyser_situation(data, bilan, charges_mensuelles_courantes)

    return bilan


# ─────────────────────────────────────────────
#  Analyse qualitative
# ─────────────────────────────────────────────

def _analyser_situation(
    data: dict,
    bilan: BilanPatrimonial,
    charges_mensuelles_courantes: float,
) -> Tuple[List[str], List[str], List[str]]:
    """
    Génère les points forts, points de vigilance et recommandations
    à partir des indicateurs calculés.
    """
    points_forts: List[str] = []
    points_vigilance: List[str] = []
    recommandations: List[str] = []

    rep = bilan.repartition_patrimoine
    objectifs_data = data.get("objectifs", {})
    objectifs_list = objectifs_data.get("objectifs", [])
    fiscalite = data.get("fiscalite", {})

    # ── Points forts ──────────────────────────────────────────────────────────

    if bilan.actif_net > 0:
        points_forts.append(
            f"Patrimoine net positif ({_fmt(bilan.actif_net)} €) — "
            "situation patrimoniale globalement saine."
        )

    if 0 < bilan.taux_endettement <= 33:
        points_forts.append(
            f"Taux d'endettement maîtrisé ({bilan.taux_endettement:.1f} %) — "
            "capacité d'emprunt préservée (seuil bancaire : 35 %)."
        )

    if bilan.capacite_epargne_mensuelle > 0:
        points_forts.append(
            f"Capacité d'épargne positive : {_fmt(bilan.capacite_epargne_mensuelle)} €/mois "
            "— marge disponible pour investir ou se constituer une réserve."
        )

    if bilan.taux_epargne >= 15:
        points_forts.append(
            f"Excellent taux d'épargne ({bilan.taux_epargne:.1f} %) — "
            "effort financier significatif."
        )

    if rep.get("Financier", 0) >= 20 and bilan.actif_brut > 0:
        points_forts.append(
            "Bonne diversification : part significative d'actifs financiers "
            f"({rep.get('Financier', 0):.1f} % du patrimoine)."
        )

    # Épargne de précaution : au moins 3 mois de charges courantes
    if charges_mensuelles_courantes > 0:
        mois_reserve = (
            bilan.actif_tresorerie / charges_mensuelles_courantes
            if charges_mensuelles_courantes > 0
            else 0
        )
        if mois_reserve >= 3:
            points_forts.append(
                f"Épargne de précaution suffisante ({mois_reserve:.1f} mois de charges "
                "disponibles en liquidités)."
            )

    # ── Points de vigilance ───────────────────────────────────────────────────

    if bilan.taux_endettement > 35:
        points_vigilance.append(
            f"Taux d'endettement élevé ({bilan.taux_endettement:.1f} %) — "
            "au-dessus du seuil bancaire de 35 %. Toute demande de crédit sera difficile."
        )
    elif bilan.taux_endettement > 33:
        points_vigilance.append(
            f"Taux d'endettement proche du seuil bancaire ({bilan.taux_endettement:.1f} %) — "
            "vigilance avant tout nouvel emprunt."
        )

    if bilan.capacite_epargne_mensuelle < 0:
        points_vigilance.append(
            f"Déficit mensuel de {_fmt(abs(bilan.capacite_epargne_mensuelle))} € — "
            "les charges dépassent les revenus. Situation financière fragile."
        )
    elif bilan.taux_epargne < 5 and bilan.revenus_annuels_total > 0:
        points_vigilance.append(
            f"Taux d'épargne très faible ({bilan.taux_epargne:.1f} %) — "
            "marge de manœuvre insuffisante en cas d'imprévu."
        )

    if rep.get("Immobilier", 0) > 80 and bilan.actif_brut > 50_000:
        points_vigilance.append(
            f"Forte concentration immobilière ({rep.get('Immobilier', 0):.1f} % "
            "de l'actif brut) — risque de manque de liquidité et de diversification."
        )

    if charges_mensuelles_courantes > 0:
        mois_reserve = bilan.actif_tresorerie / charges_mensuelles_courantes
        if mois_reserve < 3:
            points_vigilance.append(
                f"Épargne de précaution insuffisante ({mois_reserve:.1f} mois de charges) — "
                "vulnérabilité en cas d'accident de la vie (objectif : 3 à 6 mois)."
            )

    if "Préparer la retraite" in objectifs_list:
        actifs_fin = data.get("actifs_financiers", [])
        has_retraite = any(
            a.get("type_actif", "") in [
                "PER (Plan d'Épargne Retraite)",
                "Assurance-vie (fonds euros)",
                "Assurance-vie (unités de compte)",
                "PEE / PERCO (Épargne salariale)",
            ]
            for a in actifs_fin
        )
        if not has_retraite:
            points_vigilance.append(
                "Objectif retraite déclaré mais aucun dispositif dédié identifié "
                "(PER, assurance-vie, épargne salariale)."
            )

    # ── Recommandations ───────────────────────────────────────────────────────

    if charges_mensuelles_courantes > 0 and bilan.capacite_epargne_mensuelle > 0:
        mois_reserve = bilan.actif_tresorerie / charges_mensuelles_courantes
        if mois_reserve < 6:
            recommandations.append(
                "Constituer ou renforcer l'épargne de précaution : viser 3 à 6 mois "
                "de charges sur un livret accessible (Livret A, LDDS)."
            )

    if rep.get("Immobilier", 0) > 70 and bilan.actif_brut > 100_000:
        recommandations.append(
            "Diversifier le patrimoine vers des actifs financiers (assurance-vie, PEA) "
            "pour rééquilibrer la répartition et améliorer la liquidité."
        )

    if bilan.taux_endettement > 25 and data.get("credits"):
        recommandations.append(
            "Étudier les opportunités de renégociation ou de rachat de crédits "
            "pour optimiser les mensualités et réduire le coût total du financement."
        )

    tmi = fiscalite.get("tranche_marginale_imposition", "")
    if tmi in ["30 %", "41 %", "45 %"]:
        recommandations.append(
            "Optimisation fiscale : envisager des dispositifs adaptés à votre tranche "
            f"({tmi}) — PER (déduction des versements), déficit foncier, "
            "investissement en groupement foncier, etc."
        )

    if "Préparer la retraite" in objectifs_list:
        recommandations.append(
            "Mettre en place ou abonder un Plan d'Épargne Retraite (PER) — "
            "les versements sont déductibles du revenu imposable selon votre TMI."
        )

    if "Transmettre un patrimoine" in objectifs_list:
        recommandations.append(
            "Anticiper la transmission : donation-partage, démembrement de propriété "
            "ou clause bénéficiaire de l'assurance-vie selon la configuration familiale."
        )

    if "Investir dans l'immobilier" in objectifs_list and bilan.taux_endettement < 30:
        recommandations.append(
            "Capacité d'endettement disponible pour un projet immobilier. "
            "Étudier les dispositifs fiscaux (LMNP, Pinel+, Malraux…) en fonction "
            "de votre fiscalité et de votre horizon."
        )

    # Valeurs par défaut si aucune analyse générée
    if not points_forts:
        points_forts.append(
            "Complétez l'ensemble du questionnaire pour obtenir une analyse personnalisée."
        )
    if not recommandations:
        recommandations.append(
            "Renseignez les sections revenus, charges et patrimoine pour recevoir "
            "des recommandations ciblées."
        )

    return points_forts, points_vigilance, recommandations


# ─────────────────────────────────────────────
#  Utilitaire de formatage interne
# ─────────────────────────────────────────────

def _fmt(valeur: float) -> str:
    """Formate un montant avec séparateur de milliers (style français)."""
    return f"{valeur:,.0f}".replace(",", "\u202f")  # espace fine insécable
