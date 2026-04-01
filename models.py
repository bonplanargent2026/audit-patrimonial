"""
models.py — Modèles de données pour l'audit patrimonial.
Utilise des dataclasses Python pour une structure claire et typée.
"""
from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────
#  Listes de référence (valeurs des selectbox)
# ─────────────────────────────────────────────

SITUATIONS_FAMILIALES = [
    "Célibataire",
    "Marié(e)",
    "Pacsé(e)",
    "En concubinage",
    "Divorcé(e)",
    "Veuf / Veuve",
]

REGIMES_MATRIMONIAUX = [
    "Sans objet",
    "Communauté réduite aux acquêts (régime légal)",
    "Séparation de biens",
    "Communauté universelle",
    "Participation aux acquêts",
]

STATUTS_PROFESSIONNELS = [
    "Salarié(e) du privé",
    "Fonctionnaire / Agent public",
    "Travailleur non salarié (TNS)",
    "Profession libérale",
    "Chef d'entreprise / Gérant",
    "Retraité(e)",
    "Sans activité professionnelle",
    "Étudiant(e)",
]

TYPES_BIENS_IMMOBILIERS = [
    "Résidence principale",
    "Résidence secondaire",
    "Investissement locatif",
    "SCPI / Pierre-papier",
    "Local professionnel",
    "Terrain / Autre",
]

TYPES_ACTIFS_FINANCIERS = [
    "Assurance-vie (fonds euros)",
    "Assurance-vie (unités de compte)",
    "PEA (Plan d'Épargne en Actions)",
    "Compte-titres ordinaire",
    "PER (Plan d'Épargne Retraite)",
    "PEE / PERCO (Épargne salariale)",
    "Plan d'Épargne Logement (PEL)",
    "Compte d'Épargne Logement (CEL)",
    "Cryptomonnaies",
    "Autre placement financier",
]

TYPES_CREDITS = [
    "Crédit immobilier (résidence principale)",
    "Crédit immobilier (investissement locatif)",
    "Crédit à la consommation",
    "Crédit automobile",
    "Crédit professionnel",
    "Autre dette",
]

TRANCHES_MARGINALES = ["0 %", "11 %", "30 %", "41 %", "45 %"]

OBJECTIFS_LISTE = [
    "Préparer la retraite",
    "Constituer un patrimoine",
    "Optimiser la fiscalité",
    "Transmettre un patrimoine",
    "Investir dans l'immobilier",
    "Protéger la famille",
    "Financer les études des enfants",
    "Développer mon entreprise",
    "Obtenir des revenus complémentaires",
    "Autre",
]

HORIZONS_INVESTISSEMENT = [
    "Court terme (moins de 3 ans)",
    "Moyen terme (3 à 8 ans)",
    "Long terme (plus de 8 ans)",
]

PROFILS_RISQUE = [
    "Prudent — capital garanti, rendement faible",
    "Équilibré — légères fluctuations acceptées",
    "Dynamique — fluctuations importantes acceptées",
    "Offensif — recherche de performance maximale",
]

LIENS_PERSONNES_CHARGE = ["Enfant", "Parent", "Autre personne à charge"]


# ─────────────────────────────────────────────
#  Dataclasses
# ─────────────────────────────────────────────

@dataclass
class Identite:
    """Identité du client (et de son conjoint si applicable)."""
    nom: str = ""
    prenom: str = ""
    date_naissance: str = ""
    profession: str = ""
    statut_professionnel: str = "Salarié(e) du privé"

    # Conjoint
    a_conjoint: bool = False
    nom_conjoint: str = ""
    prenom_conjoint: str = ""
    date_naissance_conjoint: str = ""
    profession_conjoint: str = ""
    statut_professionnel_conjoint: str = "Salarié(e) du privé"


@dataclass
class SituationFamiliale:
    """Situation familiale et régime matrimonial."""
    situation: str = "Célibataire"
    regime_matrimonial: str = "Sans objet"
    annee_union: Optional[int] = None


@dataclass
class PersonneCharge:
    """Une personne à charge du foyer."""
    lien: str = "Enfant"
    annee_naissance: int = 2010
    a_charge_fiscale: bool = True


@dataclass
class Revenus:
    """Revenus annuels bruts du foyer (client + conjoint)."""
    # ── Client ──
    salaire_net_mensuel: float = 0.0        # × 12 pour annualiser
    primes_annuelles: float = 0.0
    revenus_fonciers_annuels: float = 0.0
    revenus_financiers_annuels: float = 0.0
    pensions_annuelles: float = 0.0
    revenus_independants_annuels: float = 0.0   # BIC / BNC
    autres_revenus_annuels: float = 0.0

    # ── Conjoint ──
    salaire_net_mensuel_conjoint: float = 0.0
    primes_annuelles_conjoint: float = 0.0
    pensions_annuelles_conjoint: float = 0.0
    autres_revenus_annuels_conjoint: float = 0.0


@dataclass
class Charges:
    """Charges courantes mensuelles du foyer (hors remboursements de crédits)."""
    loyer_mensuel: float = 0.0              # 0 si propriétaire
    charges_logement_mensuel: float = 0.0  # eau, élec, gaz, internet…
    alimentation_mensuel: float = 0.0
    transport_mensuel: float = 0.0          # carburant + transports
    assurances_mensuel: float = 0.0        # hors assurances crédits
    loisirs_mensuel: float = 0.0
    autres_charges_mensuel: float = 0.0
    scolarite_annuel: float = 0.0           # garde, scolarité (annuel)


@dataclass
class BienImmobilier:
    """Un bien immobilier détenu."""
    description: str = ""
    type_bien: str = "Résidence principale"
    valeur_actuelle: float = 0.0
    annee_acquisition: int = 2020
    revenu_locatif_mensuel: float = 0.0     # 0 si non locatif


@dataclass
class ActifFinancier:
    """Un actif financier (hors trésorerie)."""
    description: str = ""
    type_actif: str = "Assurance-vie (fonds euros)"
    valeur_actuelle: float = 0.0


@dataclass
class Tresorerie:
    """Liquidités et épargne de court terme."""
    livret_a: float = 0.0
    ldds: float = 0.0
    livret_jeune: float = 0.0
    autres_livrets: float = 0.0
    compte_courant_disponible: float = 0.0
    autres_liquidites: float = 0.0


@dataclass
class Credit:
    """Un crédit ou une dette en cours."""
    description: str = ""
    type_credit: str = "Crédit immobilier (résidence principale)"
    capital_restant_du: float = 0.0
    mensualite: float = 0.0
    taux_annuel: float = 0.0
    annee_fin: Optional[int] = None


@dataclass
class Fiscalite:
    """Situation fiscale du foyer."""
    tranche_marginale_imposition: str = "30 %"
    revenu_fiscal_reference: float = 0.0
    parts_fiscales: float = 1.0
    impot_revenu_annuel: float = 0.0
    assujetti_ifi: bool = False


@dataclass
class Objectifs:
    """Objectifs patrimoniaux et profil investisseur."""
    objectifs: List[str] = field(default_factory=list)
    horizon_investissement: str = "Moyen terme (3 à 8 ans)"
    profil_risque: str = "Équilibré — légères fluctuations acceptées"
    commentaires: str = ""


@dataclass
class QuestionnairePatrimonial:
    """Agrégat de toutes les données du questionnaire client."""
    identite: Identite = field(default_factory=Identite)
    situation_familiale: SituationFamiliale = field(default_factory=SituationFamiliale)
    personnes_charge: List[PersonneCharge] = field(default_factory=list)
    revenus: Revenus = field(default_factory=Revenus)
    charges: Charges = field(default_factory=Charges)
    immobilier: List[BienImmobilier] = field(default_factory=list)
    actifs_financiers: List[ActifFinancier] = field(default_factory=list)
    tresorerie: Tresorerie = field(default_factory=Tresorerie)
    credits: List[Credit] = field(default_factory=list)
    fiscalite: Fiscalite = field(default_factory=Fiscalite)
    objectifs: Objectifs = field(default_factory=Objectifs)
