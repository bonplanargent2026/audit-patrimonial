"""
app.py — Application Streamlit d'audit patrimonial.

Lancement :
    streamlit run app.py

Navigation par onglets :
    1. Identité            6. Patrimoine immobilier
    2. Situation familiale  7. Patrimoine financier
    3. Personnes à charge   8. Trésorerie
    4. Revenus              9. Crédits et dettes
    5. Charges             10. Fiscalité
                           11. Objectifs & risque
                           📊  Bilan patrimonial
"""
import json
import streamlit as st
from datetime import date

from calculations import calculer_bilan
from models import (
    HORIZONS_INVESTISSEMENT,
    LIENS_PERSONNES_CHARGE,
    OBJECTIFS_LISTE,
    PROFILS_RISQUE,
    REGIMES_MATRIMONIAUX,
    SITUATIONS_FAMILIALES,
    STATUTS_PROFESSIONNELS,
    TRANCHES_MARGINALES,
    TYPES_ACTIFS_FINANCIERS,
    TYPES_BIENS_IMMOBILIERS,
    TYPES_CREDITS,
)
from report import afficher_rapport_streamlit, generer_pdf

# ─────────────────────────────────────────────
#  Configuration de la page
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Audit Patrimonial",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
#  CSS personnalisé
# ─────────────────────────────────────────────

st.markdown(
    """
    <style>
        /* En-tête principal */
        .app-title {
            font-size: 2rem;
            font-weight: 700;
            color: #1e3a5f;
            margin-bottom: 0;
        }
        .app-subtitle {
            color: #718096;
            font-size: 1rem;
            margin-top: 0;
        }
        /* Séparateurs de section */
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #2c5282;
            border-left: 4px solid #2c7a7b;
            padding-left: 10px;
            margin: 1.2rem 0 0.8rem 0;
        }
        /* Bouton principal */
        div[data-testid="stButton"] > button[kind="primary"] {
            background-color: #1e3a5f;
            color: white;
            font-size: 1.05rem;
            padding: 0.6rem 2rem;
            border-radius: 6px;
        }
        /* Onglets */
        div[data-testid="stTabs"] button {
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
#  Initialisation du session_state
# ─────────────────────────────────────────────

def _init_state():
    """Initialise les clés de session nécessaires si elles n'existent pas."""
    defaults = {
        # Compteurs pour les listes dynamiques
        "nb_personnes_charge": 0,
        "nb_immobilier": 0,
        "nb_actifs_financiers": 0,
        "nb_credits": 0,
        # Résultats du bilan
        "bilan_calcule": False,
        "bilan_data": None,
        "bilan_result": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()

# ─────────────────────────────────────────────
#  En-tête
# ─────────────────────────────────────────────

st.markdown('<p class="app-title">💼 Audit Patrimonial</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">Questionnaire de découverte client — renseignez chaque section '
    "puis cliquez sur <strong>Calculer le bilan</strong> dans l'onglet 📊.</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ─────────────────────────────────────────────
#  Sauvegarde / Chargement de session
# ─────────────────────────────────────────────

_SKIP_KEYS = {"bilan_calcule", "bilan_data", "bilan_result"}

def _session_to_json() -> str:
    """Sérialise le session_state en JSON (valeurs primitives uniquement)."""
    data = {}
    for k, v in st.session_state.items():
        if k.startswith("_") or k in _SKIP_KEYS:
            continue
        if isinstance(v, (str, int, float, bool, list, dict, type(None))):
            data[k] = v
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)

col_save, col_load, _ = st.columns([1, 2, 3])

with col_save:
    st.download_button(
        label="💾 Sauvegarder ma progression",
        data=_session_to_json(),
        file_name=f"audit_{date.today().strftime('%Y%m%d')}.json",
        mime="application/json",
        help="Télécharge un fichier JSON pour reprendre plus tard",
    )

with col_load:
    uploaded_file = st.file_uploader(
        "📂 Reprendre une session sauvegardée",
        type="json",
        label_visibility="visible",
        key="_uploader",
    )
    if uploaded_file is not None and not st.session_state.get("_session_loaded"):
        try:
            loaded_data = json.loads(uploaded_file.read())
            for k, v in loaded_data.items():
                st.session_state[k] = v
            st.session_state["_session_loaded"] = True
            st.success("Session restaurée avec succès !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur lors du chargement : {e}")
    elif uploaded_file is None:
        st.session_state["_session_loaded"] = False

st.markdown("---")

# ─────────────────────────────────────────────
#  Onglets de navigation
# ─────────────────────────────────────────────

(
    tab_id,
    tab_famille,
    tab_charges_pers,
    tab_revenus,
    tab_charges,
    tab_immo,
    tab_financier,
    tab_tresorerie,
    tab_credits,
    tab_fiscalite,
    tab_prevoyance,
    tab_objectifs,
    tab_profil,
    tab_bilan,
) = st.tabs([
    "1 · Identité",
    "2 · Situation familiale",
    "3 · Personnes à charge",
    "4 · Revenus",
    "5 · Charges",
    "6 · Immobilier",
    "7 · Financier",
    "8 · Trésorerie",
    "9 · Crédits",
    "10 · Fiscalité",
    "11 · Prévoyance & Garanties",
    "12 · Objectifs & risque",
    "13 · Profil investisseur",
    "📊 Bilan",
])


# ─────────────────────────────────────────────
#  1 · IDENTITÉ
# ─────────────────────────────────────────────

with tab_id:
    st.markdown('<p class="section-title">Informations client</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.text_input("Nom", key="id_nom", placeholder="DUPONT")
        st.text_input("Date de naissance", key="id_dob", placeholder="15/03/1980")
        st.selectbox("Statut professionnel", STATUTS_PROFESSIONNELS, key="id_statut_pro")
        st.text_input("Employé(e) depuis (date d'embauche)", key="id_date_embauche", placeholder="01/09/2015")
        st.text_input("Date de fin d'activité prévue", key="id_date_fin_activite", placeholder="31/08/2046",
                      help="Date à laquelle le client cessera son activité (départ en retraite)")
        st.text_input("Date de départ en retraite (précise)", key="id_date_retraite", placeholder="1er septembre 2046",
                      help="Ex : 1er septembre 2046")
    with c2:
        st.text_input("Prénom", key="id_prenom", placeholder="Jean")
        st.text_input("Profession", key="id_profession", placeholder="Ingénieur")

    st.markdown('<p class="section-title">Conjoint / Partenaire</p>', unsafe_allow_html=True)
    st.checkbox("Ajouter les informations du conjoint / partenaire", key="id_a_conjoint")

    if st.session_state.get("id_a_conjoint"):
        c3, c4 = st.columns(2)
        with c3:
            st.text_input("Nom du conjoint", key="id_nom_conjoint")
            st.text_input("Date de naissance", key="id_dob_conjoint", placeholder="20/07/1982")
            st.selectbox(
                "Statut professionnel", STATUTS_PROFESSIONNELS,
                key="id_statut_pro_conjoint",
            )
            st.text_input("Employé(e) depuis (date d'embauche)", key="id_date_embauche_conjoint", placeholder="01/09/2015")
            st.text_input("Date de fin d'activité prévue — conjoint", key="id_date_fin_activite_conjoint",
                          placeholder="31/08/2045")
            st.text_input("Date de départ en retraite (précise) — conjoint", key="id_date_retraite_conjoint",
                          placeholder="1er septembre 2045")
        with c4:
            st.text_input("Prénom du conjoint", key="id_prenom_conjoint")
            st.text_input("Profession", key="id_profession_conjoint")


# ─────────────────────────────────────────────
#  2 · SITUATION FAMILIALE
# ─────────────────────────────────────────────

with tab_famille:
    st.markdown('<p class="section-title">Situation familiale</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Situation familiale", SITUATIONS_FAMILIALES, key="fam_situation")
    with c2:
        st.selectbox("Régime matrimonial", REGIMES_MATRIMONIAUX, key="fam_regime")

    situation = st.session_state.get("fam_situation", "Célibataire")
    if situation in ("Marié(e)", "Pacsé(e)", "En concubinage"):
        st.number_input(
            "Année d'union / mariage / PACS",
            min_value=1950, max_value=2025, value=2010, step=1,
            key="fam_annee_union",
        )

    st.markdown('<p class="section-title">Enfants du foyer</p>', unsafe_allow_html=True)
    st.number_input(
        "Nombre d'enfants", min_value=0, max_value=15, value=0, step=1,
        key="fam_nb_enfants",
    )

    for i in range(int(st.session_state.get("fam_nb_enfants", 0))):
        with st.expander(f"Enfant n° {i + 1}", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.text_input("Prénom", key=f"enf_{i}_prenom", placeholder="Ex : Léa")
            with c2:
                st.text_input(
                    "Date de naissance", key=f"enf_{i}_dob",
                    placeholder="JJ/MM/AAAA",
                )
            with c3:
                st.selectbox(
                    "Situation",
                    ["À charge fiscalement", "Majeur autonome", "Garde alternée"],
                    key=f"enf_{i}_charge",
                )


# ─────────────────────────────────────────────
#  3 · PERSONNES À CHARGE
# ─────────────────────────────────────────────

with tab_charges_pers:
    st.markdown('<p class="section-title">Personnes à charge du foyer</p>', unsafe_allow_html=True)
    st.info(
        "Renseignez ici les personnes à charge pour lesquelles vous souhaitez "
        "indiquer le détail (enfants, parents dépendants…)."
    )

    st.number_input(
        "Nombre de personnes à charge à détailler",
        min_value=0, max_value=10, step=1,
        key="nb_personnes_charge",
    )

    for i in range(int(st.session_state.nb_personnes_charge)):
        with st.expander(f"Personne à charge n° {i + 1}", expanded=(i == 0)):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.selectbox(
                    "Lien de parenté", LIENS_PERSONNES_CHARGE,
                    key=f"pc_{i}_lien",
                )
            with c2:
                st.number_input(
                    "Année de naissance",
                    min_value=1924, max_value=2024, value=2010, step=1,
                    key=f"pc_{i}_annee_naissance",
                )
            with c3:
                st.checkbox("À charge fiscalement", value=True, key=f"pc_{i}_charge_fiscale")


# ─────────────────────────────────────────────
#  4 · REVENUS
# ─────────────────────────────────────────────

with tab_revenus:
    st.markdown('<p class="section-title">Revenus du client</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.number_input(
            "Salaire net mensuel (€)", min_value=0.0, step=100.0, format="%.2f",
            key="rev_salaire_mensuel",
        )
        st.number_input(
            "Revenus fonciers bruts annuels (€)", min_value=0.0, step=100.0, format="%.2f",
            key="rev_fonciers_annuels",
            help="Loyers perçus avant déduction des charges",
        )
        st.number_input(
            "Pensions / retraites annuelles (€)", min_value=0.0, step=100.0, format="%.2f",
            key="rev_pensions_annuelles",
        )
        st.number_input(
            "Autres revenus annuels (€)", min_value=0.0, step=100.0, format="%.2f",
            key="rev_autres_annuels",
        )
    with c2:
        st.number_input(
            "Primes / bonus annuels (€)", min_value=0.0, step=100.0, format="%.2f",
            key="rev_primes_annuelles",
        )
        st.number_input(
            "Revenus financiers annuels (€)", min_value=0.0, step=100.0, format="%.2f",
            key="rev_financiers_annuels",
            help="Dividendes, intérêts, plus-values réalisées",
        )
        st.number_input(
            "Revenus indépendants / BIC / BNC annuels (€)",
            min_value=0.0, step=100.0, format="%.2f",
            key="rev_independants_annuels",
        )

    if st.session_state.get("id_a_conjoint"):
        st.markdown(
            '<p class="section-title">Revenus du conjoint / partenaire</p>',
            unsafe_allow_html=True,
        )
        c3, c4 = st.columns(2)
        with c3:
            st.number_input(
                "Salaire net mensuel — conjoint (€)",
                min_value=0.0, step=100.0, format="%.2f",
                key="rev_salaire_mensuel_conjoint",
            )
            st.number_input(
                "Pensions / retraites annuelles — conjoint (€)",
                min_value=0.0, step=100.0, format="%.2f",
                key="rev_pensions_annuelles_conjoint",
            )
        with c4:
            st.number_input(
                "Primes annuelles — conjoint (€)",
                min_value=0.0, step=100.0, format="%.2f",
                key="rev_primes_annuelles_conjoint",
            )
            st.number_input(
                "Autres revenus annuels — conjoint (€)",
                min_value=0.0, step=100.0, format="%.2f",
                key="rev_autres_annuels_conjoint",
            )
    else:
        # Initialise à 0 si pas de conjoint
        for k in [
            "rev_salaire_mensuel_conjoint", "rev_primes_annuelles_conjoint",
            "rev_pensions_annuelles_conjoint", "rev_autres_annuels_conjoint",
        ]:
            if k not in st.session_state:
                st.session_state[k] = 0.0


# ─────────────────────────────────────────────
#  5 · CHARGES
# ─────────────────────────────────────────────

with tab_charges:
    st.markdown(
        '<p class="section-title">Charges courantes mensuelles (hors remboursements de crédits)</p>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.number_input(
            "Loyer mensuel (€ — 0 si propriétaire)",
            min_value=0.0, step=50.0, format="%.2f",
            key="ch_loyer_mensuel",
        )
        st.number_input(
            "Alimentation mensuelle (€)",
            min_value=0.0, step=50.0, format="%.2f",
            key="ch_alimentation_mensuel",
        )
        st.number_input(
            "Assurances mensuelles (€) — hors crédits",
            min_value=0.0, step=20.0, format="%.2f",
            key="ch_assurances_mensuel",
        )
        st.number_input(
            "Autres charges mensuelles (€)",
            min_value=0.0, step=50.0, format="%.2f",
            key="ch_autres_mensuel",
        )
    with c2:
        st.number_input(
            "Charges logement mensuelles (€) — eau, énergie, internet…",
            min_value=0.0, step=20.0, format="%.2f",
            key="ch_charges_logement_mensuel",
        )
        st.number_input(
            "Transport mensuel (€) — carburant, transports en commun…",
            min_value=0.0, step=20.0, format="%.2f",
            key="ch_transport_mensuel",
        )
        st.number_input(
            "Loisirs / sorties mensuels (€)",
            min_value=0.0, step=20.0, format="%.2f",
            key="ch_loisirs_mensuel",
        )
        st.number_input(
            "Scolarité / garde d'enfants annuelle (€)",
            min_value=0.0, step=100.0, format="%.2f",
            key="ch_scolarite_annuel",
        )


# ─────────────────────────────────────────────
#  6 · PATRIMOINE IMMOBILIER
# ─────────────────────────────────────────────

with tab_immo:
    st.markdown(
        '<p class="section-title">Biens immobiliers détenus</p>',
        unsafe_allow_html=True,
    )

    st.number_input(
        "Nombre de biens immobiliers",
        min_value=0, max_value=15, step=1,
        key="nb_immobilier",
    )

    for i in range(int(st.session_state.nb_immobilier)):
        with st.expander(f"Bien immobilier n° {i + 1}", expanded=(i == 0)):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input(
                    "Description (ex : Appartement Lyon 3 pièces)",
                    key=f"immo_{i}_description",
                )
                st.selectbox(
                    "Type de bien", TYPES_BIENS_IMMOBILIERS,
                    key=f"immo_{i}_type",
                )
                st.number_input(
                    "Valeur actuelle estimée (€)",
                    min_value=0.0, step=1000.0, format="%.0f",
                    key=f"immo_{i}_valeur",
                )
                st.number_input(
                    "Valeur d'acquisition (€)",
                    min_value=0.0, step=1000.0, format="%.0f",
                    key=f"immo_{i}_valeur_acq",
                    help="Prix d'achat initial du bien",
                )
            with c2:
                st.number_input(
                    "Année d'acquisition",
                    min_value=1900, max_value=2025, value=2015, step=1,
                    key=f"immo_{i}_annee_acq",
                )
                st.number_input(
                    "Revenu locatif mensuel (€ — 0 si non loué)",
                    min_value=0.0, step=50.0, format="%.2f",
                    key=f"immo_{i}_loyer_mensuel",
                )
                st.selectbox(
                    "Mode de détention",
                    ["Pleine propriété", "Nue-propriété", "Usufruit", "Indivision", "SCI", "Autre"],
                    key=f"immo_{i}_detention",
                    help="Pleine propriété = détention complète ; Nue-propriété = sans droit d'usage",
                )
                # Quote-part si indivision ou nue-propriété
                detention_val = st.session_state.get(f"immo_{i}_detention", "Pleine propriété")
                if detention_val in ("Indivision", "Nue-propriété", "Usufruit"):
                    st.number_input(
                        "Quote-part détenue (%)",
                        min_value=1.0, max_value=100.0, value=50.0, step=1.0, format="%.0f",
                        key=f"immo_{i}_quote_part",
                        help="Ex : 50% si indivision entre deux personnes",
                    )
                st.text_input(
                    "Détenu par (préciser nom/prénom si tiers)",
                    key=f"immo_{i}_detenu_par_txt",
                    placeholder="Ex : M. Dupont seul / M. et Mme Dupont / SCI Famille",
                )
                st.selectbox(
                    "Dispositif fiscal",
                    ["Aucun", "Pinel", "Denormandie", "LMNP", "LMP", "Malraux",
                     "Monuments Historiques", "Nue-propriété (démembrement)", "Autre"],
                    key=f"immo_{i}_dispositif_fiscal",
                )
                st.number_input(
                    "Charges de copropriété annuelles (€)",
                    min_value=0.0, step=100.0, format="%.0f",
                    key=f"immo_{i}_charges_copro",
                )
                st.number_input(
                    "Taxe foncière annuelle (€)",
                    min_value=0.0, step=50.0, format="%.0f",
                    key=f"immo_{i}_taxe_fonciere",
                )


# ─────────────────────────────────────────────
#  7 · PATRIMOINE FINANCIER
# ─────────────────────────────────────────────

with tab_financier:
    st.markdown(
        '<p class="section-title">Actifs financiers (hors trésorerie)</p>',
        unsafe_allow_html=True,
    )

    st.number_input(
        "Nombre d'actifs financiers",
        min_value=0, max_value=20, step=1,
        key="nb_actifs_financiers",
    )

    for i in range(int(st.session_state.nb_actifs_financiers)):
        with st.expander(f"Actif financier n° {i + 1}", expanded=(i == 0)):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input(
                    "Description (ex : AV Cardif, PEA Bourse Direct…)",
                    key=f"af_{i}_description",
                )
                st.selectbox(
                    "Type d'actif", TYPES_ACTIFS_FINANCIERS,
                    key=f"af_{i}_type",
                )
                st.text_input(
                    "Date de souscription / ouverture",
                    key=f"af_{i}_date_souscription",
                    placeholder="JJ/MM/AAAA",
                    help="Permet de calculer l'ancienneté fiscale (ex : AV > 8 ans, PEA > 5 ans)",
                )
            with c2:
                st.number_input(
                    "Valeur actuelle (€)",
                    min_value=0.0, step=500.0, format="%.0f",
                    key=f"af_{i}_valeur",
                )
                st.number_input(
                    "Taux de rendement annuel estimé (%)",
                    min_value=0.0, max_value=30.0, value=0.0, step=0.1, format="%.2f",
                    key=f"af_{i}_taux_rendement",
                    help="Rendement net annuel constaté ou estimé",
                )
                st.number_input(
                    "Versement mensuel programmé (€)",
                    min_value=0.0, step=50.0, format="%.0f",
                    key=f"af_{i}_versement_mensuel",
                )


# ─────────────────────────────────────────────
#  8 · TRÉSORERIE
# ─────────────────────────────────────────────

with tab_tresorerie:
    st.markdown(
        '<p class="section-title">Liquidités et épargne de précaution</p>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.number_input(
            "Livret A (€)", min_value=0.0, step=100.0, format="%.0f",
            key="treso_livret_a",
        )
        st.number_input(
            "Livret Jeune (€)", min_value=0.0, step=100.0, format="%.0f",
            key="treso_livret_jeune",
        )
        st.number_input(
            "Compte courant disponible (épargne) (€)",
            min_value=0.0, step=100.0, format="%.0f",
            key="treso_cc_disponible",
        )
    with c2:
        st.number_input(
            "LDDS (€)", min_value=0.0, step=100.0, format="%.0f",
            key="treso_ldds",
        )
        st.number_input(
            "Autres livrets réglementés (€)",
            min_value=0.0, step=100.0, format="%.0f",
            key="treso_autres_livrets",
        )
        st.number_input(
            "Autres liquidités (€)", min_value=0.0, step=100.0, format="%.0f",
            key="treso_autres",
        )


# ─────────────────────────────────────────────
#  9 · CRÉDITS ET DETTES
# ─────────────────────────────────────────────

with tab_credits:
    st.markdown(
        '<p class="section-title">Crédits et dettes en cours</p>',
        unsafe_allow_html=True,
    )

    st.number_input(
        "Nombre de crédits / dettes",
        min_value=0, max_value=15, step=1,
        key="nb_credits",
    )

    for i in range(int(st.session_state.nb_credits)):
        with st.expander(f"Crédit / Dette n° {i + 1}", expanded=(i == 0)):
            c1, c2 = st.columns(2)
            with c1:
                st.text_input(
                    "Description (ex : Crédit immo BNP résidence principale)",
                    key=f"cr_{i}_description",
                )
                st.selectbox(
                    "Type de crédit", TYPES_CREDITS,
                    key=f"cr_{i}_type",
                )
                st.number_input(
                    "Capital restant dû (€)",
                    min_value=0.0, step=1000.0, format="%.0f",
                    key=f"cr_{i}_crd",
                )
            with c2:
                st.number_input(
                    "Mensualité (€)",
                    min_value=0.0, step=10.0, format="%.2f",
                    key=f"cr_{i}_mensualite",
                )
                st.number_input(
                    "Taux d'intérêt annuel (%)",
                    min_value=0.0, max_value=30.0, step=0.1, format="%.2f",
                    key=f"cr_{i}_taux",
                )
                st.text_input(
                    "Date de début du crédit",
                    key=f"cr_{i}_date_debut",
                    placeholder="MM/AAAA",
                )
                st.number_input(
                    "Année de fin de crédit",
                    min_value=2024, max_value=2060, value=2030, step=1,
                    key=f"cr_{i}_annee_fin",
                )
                st.number_input(
                    "Assurance emprunteur mensuelle (€)",
                    min_value=0.0, step=5.0, format="%.2f",
                    key=f"cr_{i}_assurance_emprunteur",
                    help="Coût mensuel de l'assurance liée à ce crédit",
                )


# ─────────────────────────────────────────────
#  10 · FISCALITÉ
# ─────────────────────────────────────────────

with tab_fiscalite:
    st.markdown(
        '<p class="section-title">Situation fiscale du foyer</p>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(
            "Tranche marginale d'imposition (TMI)",
            TRANCHES_MARGINALES,
            index=2,  # 30% par défaut
            key="fisc_tmi",
        )
        st.number_input(
            "Revenu fiscal de référence (RFR) annuel (€)",
            min_value=0.0, step=500.0, format="%.0f",
            key="fisc_rfr",
        )
    with c2:
        st.number_input(
            "Nombre de parts fiscales",
            min_value=1.0, max_value=10.0, value=1.0, step=0.5, format="%.1f",
            key="fisc_parts",
        )
        st.number_input(
            "Impôt sur le revenu annuel payé (€)",
            min_value=0.0, step=100.0, format="%.0f",
            key="fisc_ir_annuel",
        )

    st.markdown(
        '<p class="section-title">Impôt sur la Fortune Immobilière (IFI)</p>',
        unsafe_allow_html=True,
    )
    st.checkbox("Assujetti à l'IFI (patrimoine immobilier net > 1,3 M€)", key="fisc_ifi")
    if st.session_state.get("fisc_ifi"):
        st.number_input(
            "IFI à payer (montant annuel, €)",
            min_value=0.0, step=100.0, format="%.0f",
            key="fisc_ifi_annuel",
        )


# ─────────────────────────────────────────────
#  11 · PRÉVOYANCE & GARANTIES
# ─────────────────────────────────────────────

with tab_prevoyance:
    st.markdown(
        '<p class="section-title">Garanties personnelles (décès / invalidité / arrêt de travail)</p>',
        unsafe_allow_html=True,
    )
    st.info("Indiquez les contrats de prévoyance individuels (hors garanties collectives employeur).")

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(
            "Avez-vous une assurance décès individuelle ?",
            ["Non", "Oui — temporaire décès", "Oui — vie entière décès"],
            key="prev_deces",
        )
        st.number_input(
            "Capital décès assuré (€)",
            min_value=0.0, step=10000.0, format="%.0f",
            key="prev_capital_deces",
        )
        st.selectbox(
            "Garantie arrêt de travail / invalidité ?",
            ["Non", "Oui — contrat individuel", "Oui — via employeur (Art.83/Art.39)"],
            key="prev_arret_travail",
        )
        st.number_input(
            "Indemnité journalière ou rente invalidité mensuelle (€)",
            min_value=0.0, step=100.0, format="%.0f",
            key="prev_indemnite_invalidite",
        )
    with c2:
        st.selectbox(
            "Contrat de prévoyance dépendance ?",
            ["Non", "Oui"],
            key="prev_dependance",
        )
        st.number_input(
            "Rente dépendance mensuelle prévue (€)",
            min_value=0.0, step=100.0, format="%.0f",
            key="prev_rente_dependance",
        )
        st.selectbox(
            "Mutuelle / complémentaire santé ?",
            ["Non", "Oui — individuelle", "Oui — via employeur"],
            key="prev_mutuelle",
        )
        if st.session_state.get("id_a_conjoint"):
            st.number_input(
                "Capital décès assuré — conjoint (€)",
                min_value=0.0, step=10000.0, format="%.0f",
                key="prev_capital_deces_conjoint",
            )

    st.markdown(
        '<p class="section-title">Retraite — situation actuelle</p>',
        unsafe_allow_html=True,
    )
    c3, c4 = st.columns(2)
    with c3:
        st.number_input(
            "Âge de départ à la retraite envisagé",
            min_value=50, max_value=75, value=65, step=1,
            key="prev_age_retraite",
        )
        st.number_input(
            "Estimation de la pension retraite mensuelle (€)",
            min_value=0.0, step=100.0, format="%.0f",
            key="prev_pension_estimee",
            help="Estimation issue du relevé de carrière ou de la simulation retraite",
        )
    with c4:
        st.number_input(
            "Revenu mensuel souhaité à la retraite (€)",
            min_value=0.0, step=100.0, format="%.0f",
            key="prev_revenu_souhaite_retraite",
        )
        st.selectbox(
            "Avez-vous un Plan Épargne Retraite (PER) ?",
            ["Non", "Oui — PER individuel", "Oui — PERCO / PERE-CO (collectif)", "Oui — les deux"],
            key="prev_per",
        )
        if st.session_state.get("prev_per", "Non") != "Non":
            st.text_input(
                "Date d'ouverture du PER",
                key="prev_per_date_ouverture",
                placeholder="MM/AAAA",
            )
            st.number_input(
                "Encours actuel du PER (€)",
                min_value=0.0, step=500.0, format="%.0f",
                key="prev_per_encours",
            )
            st.number_input(
                "Versement mensuel sur le PER (€)",
                min_value=0.0, step=50.0, format="%.0f",
                key="prev_per_versement_mensuel",
            )
            st.number_input(
                "Taux de rendement estimé du PER (%)",
                min_value=0.0, max_value=20.0, value=0.0, step=0.1, format="%.2f",
                key="prev_per_rendement",
            )

    st.markdown(
        '<p class="section-title">Coûts des assurances personnelles</p>',
        unsafe_allow_html=True,
    )
    c7, c8 = st.columns(2)
    with c7:
        st.number_input(
            "Cotisation assurance décès mensuelle (€)",
            min_value=0.0, step=5.0, format="%.2f",
            key="prev_cout_deces",
        )
        st.number_input(
            "Cotisation mutuelle / complémentaire santé mensuelle (€)",
            min_value=0.0, step=5.0, format="%.2f",
            key="prev_cout_mutuelle",
        )
    with c8:
        st.number_input(
            "Assurance(s) consommation / vie mensuelle (€)",
            min_value=0.0, step=5.0, format="%.2f",
            key="prev_cout_consommation",
            help="Assurances liées à des crédits à la consommation, garantie revente, etc.",
        )
        st.number_input(
            "Autres cotisations prévoyance mensuelles (€)",
            min_value=0.0, step=5.0, format="%.2f",
            key="prev_cout_autres",
        )

    st.markdown(
        '<p class="section-title">Transmission & Libéralités</p>',
        unsafe_allow_html=True,
    )
    c5, c6 = st.columns(2)
    with c5:
        st.selectbox(
            "Avez-vous rédigé un testament ?",
            ["Non", "Oui — testament olographe", "Oui — testament notarié"],
            key="transm_testament",
        )
        st.selectbox(
            "Avez-vous effectué des donations ?",
            ["Non", "Oui — donation simple", "Oui — donation-partage", "Oui — donation entre époux"],
            key="transm_donations",
        )
        st.number_input(
            "Montant total des donations déjà effectuées (€)",
            min_value=0.0, step=1000.0, format="%.0f",
            key="transm_montant_donations",
        )
    with c6:
        st.selectbox(
            "Avez-vous une clause bénéficiaire d'assurance-vie optimisée ?",
            ["Non / ne sait pas", "Oui — clause standard", "Oui — clause sur mesure"],
            key="transm_clause_av",
        )
        st.text_area(
            "Souhaits de transmission particuliers",
            height=100,
            key="transm_souhaits",
            placeholder="Ex : protéger le conjoint, transmettre aux enfants, oeuvres caritatives...",
        )


# ─────────────────────────────────────────────
#  12 · OBJECTIFS & RISQUE
# ─────────────────────────────────────────────

with tab_objectifs:
    st.markdown(
        '<p class="section-title">Objectifs patrimoniaux</p>',
        unsafe_allow_html=True,
    )

    st.multiselect(
        "Sélectionnez vos objectifs principaux (plusieurs choix possibles)",
        OBJECTIFS_LISTE,
        key="obj_objectifs",
    )

    st.markdown(
        '<p class="section-title">Horizon et profil de risque</p>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(
            "Horizon d'investissement", HORIZONS_INVESTISSEMENT,
            index=1,
            key="obj_horizon",
        )
    with c2:
        st.selectbox(
            "Profil de risque", PROFILS_RISQUE,
            index=1,
            key="obj_profil_risque",
        )

    st.markdown(
        '<p class="section-title">Expérience financière</p>',
        unsafe_allow_html=True,
    )
    c3, c4 = st.columns(2)
    with c3:
        st.selectbox(
            "Connaissance des placements financiers",
            [
                "Placements bancaires traditionnels uniquement (livrets, comptes)",
                "Quelques placements (épargne, actions) — fluctuations connues",
                "Plusieurs catégories de placements, y compris spéculatifs",
                "Tous types de placements, y compris marchés financiers spéculatifs",
            ],
            key="obj_connaissance_placements",
        )
        st.selectbox(
            "Avez-vous réalisé des opérations financières dans les 12 derniers mois ?",
            ["Non", "Oui — souscription", "Oui — rachat", "Oui — versement complémentaire"],
            key="obj_operations_recentes",
        )
        if st.session_state.get("obj_operations_recentes", "Non") != "Non":
            st.number_input(
                "Montant de l'opération (€)",
                min_value=0.0, step=500.0, format="%.0f",
                key="obj_operations_montant",
            )
    with c4:
        st.selectbox(
            "Comportement en cas de perte importante",
            [
                "Je vends immédiatement pour limiter les pertes",
                "J'attends que ca remonte",
                "J'en profite pour racheter à la baisse",
            ],
            key="obj_comportement_perte",
        )
        st.number_input(
            "Capacité d'épargne mensuelle supplémentaire à investir (€)",
            min_value=0.0, step=50.0, format="%.0f",
            key="obj_epargne_supplementaire",
        )

    st.markdown(
        '<p class="section-title">Remarques libres</p>',
        unsafe_allow_html=True,
    )
    st.text_area(
        "Commentaires, contraintes particulières, projets en cours…",
        height=120,
        key="obj_commentaires",
        placeholder="Ex : projet d'achat immobilier dans 2 ans, départ à la retraite prévu en 2030…",
    )


# ─────────────────────────────────────────────
#  Collecte des données depuis session_state
# ─────────────────────────────────────────────

def _collect_data() -> dict:
    """
    Reconstruit le dictionnaire de données structuré
    depuis les valeurs stockées dans st.session_state.
    """
    ss = st.session_state

    # ── Identité ──────────────────────────────────────────────────────────────
    identite = {
        "nom": ss.get("id_nom", ""),
        "prenom": ss.get("id_prenom", ""),
        "date_naissance": ss.get("id_dob", ""),
        "profession": ss.get("id_profession", ""),
        "statut_professionnel": ss.get("id_statut_pro", ""),
        "date_embauche": ss.get("id_date_embauche", ""),
        "date_fin_activite": ss.get("id_date_fin_activite", ""),
        "date_retraite": ss.get("id_date_retraite", ""),
        "a_conjoint": ss.get("id_a_conjoint", False),
        "nom_conjoint": ss.get("id_nom_conjoint", ""),
        "prenom_conjoint": ss.get("id_prenom_conjoint", ""),
        "date_naissance_conjoint": ss.get("id_dob_conjoint", ""),
        "profession_conjoint": ss.get("id_profession_conjoint", ""),
        "statut_professionnel_conjoint": ss.get("id_statut_pro_conjoint", ""),
        "date_embauche_conjoint": ss.get("id_date_embauche_conjoint", ""),
        "date_fin_activite_conjoint": ss.get("id_date_fin_activite_conjoint", ""),
        "date_retraite_conjoint": ss.get("id_date_retraite_conjoint", ""),
    }

    # ── Situation familiale ───────────────────────────────────────────────────
    nb_enfants = int(ss.get("fam_nb_enfants", 0))
    enfants = [
        {
            "prenom": ss.get(f"enf_{i}_prenom", ""),
            "date_naissance": ss.get(f"enf_{i}_dob", ""),
            "charge": ss.get(f"enf_{i}_charge", "A charge fiscalement"),
        }
        for i in range(nb_enfants)
    ]
    situation_familiale = {
        "situation": ss.get("fam_situation", "Célibataire"),
        "regime_matrimonial": ss.get("fam_regime", "Sans objet"),
        "annee_union": ss.get("fam_annee_union", None),
        "nb_enfants": nb_enfants,
        "enfants": enfants,
    }

    # ── Personnes à charge ────────────────────────────────────────────────────
    personnes_charge = [
        {
            "lien": ss.get(f"pc_{i}_lien", "Enfant"),
            "annee_naissance": ss.get(f"pc_{i}_annee_naissance", 2010),
            "a_charge_fiscale": ss.get(f"pc_{i}_charge_fiscale", True),
        }
        for i in range(int(ss.get("nb_personnes_charge", 0)))
    ]

    # ── Revenus ───────────────────────────────────────────────────────────────
    revenus = {
        "salaire_net_mensuel": ss.get("rev_salaire_mensuel", 0.0),
        "primes_annuelles": ss.get("rev_primes_annuelles", 0.0),
        "revenus_fonciers_annuels": ss.get("rev_fonciers_annuels", 0.0),
        "revenus_financiers_annuels": ss.get("rev_financiers_annuels", 0.0),
        "pensions_annuelles": ss.get("rev_pensions_annuelles", 0.0),
        "revenus_independants_annuels": ss.get("rev_independants_annuels", 0.0),
        "autres_revenus_annuels": ss.get("rev_autres_annuels", 0.0),
        # Conjoint
        "salaire_net_mensuel_conjoint": ss.get("rev_salaire_mensuel_conjoint", 0.0),
        "primes_annuelles_conjoint": ss.get("rev_primes_annuelles_conjoint", 0.0),
        "pensions_annuelles_conjoint": ss.get("rev_pensions_annuelles_conjoint", 0.0),
        "autres_revenus_annuels_conjoint": ss.get("rev_autres_annuels_conjoint", 0.0),
    }

    # ── Charges ───────────────────────────────────────────────────────────────
    charges = {
        "loyer_mensuel": ss.get("ch_loyer_mensuel", 0.0),
        "charges_logement_mensuel": ss.get("ch_charges_logement_mensuel", 0.0),
        "alimentation_mensuel": ss.get("ch_alimentation_mensuel", 0.0),
        "transport_mensuel": ss.get("ch_transport_mensuel", 0.0),
        "assurances_mensuel": ss.get("ch_assurances_mensuel", 0.0),
        "loisirs_mensuel": ss.get("ch_loisirs_mensuel", 0.0),
        "autres_charges_mensuel": ss.get("ch_autres_mensuel", 0.0),
        "scolarite_annuel": ss.get("ch_scolarite_annuel", 0.0),
    }

    # ── Patrimoine immobilier ─────────────────────────────────────────────────
    immobilier = [
        {
            "description": ss.get(f"immo_{i}_description", f"Bien {i + 1}"),
            "type_bien": ss.get(f"immo_{i}_type", "Résidence principale"),
            "valeur_actuelle": ss.get(f"immo_{i}_valeur", 0.0),
            "valeur_acquisition": ss.get(f"immo_{i}_valeur_acq", 0.0),
            "annee_acquisition": ss.get(f"immo_{i}_annee_acq", 2020),
            "revenu_locatif_mensuel": ss.get(f"immo_{i}_loyer_mensuel", 0.0),
            "mode_detention": ss.get(f"immo_{i}_detention", "Pleine propriété"),
            "detenu_par": ss.get(f"immo_{i}_detenu_par", "M. et Mme (commun)"),
            "dispositif_fiscal": ss.get(f"immo_{i}_dispositif_fiscal", "Aucun"),
            "quote_part": ss.get(f"immo_{i}_quote_part", 100.0),
            "detenu_par_txt": ss.get(f"immo_{i}_detenu_par_txt", ""),
            "charges_copro": ss.get(f"immo_{i}_charges_copro", 0.0),
            "taxe_fonciere": ss.get(f"immo_{i}_taxe_fonciere", 0.0),
        }
        for i in range(int(ss.get("nb_immobilier", 0)))
    ]

    # ── Actifs financiers ─────────────────────────────────────────────────────
    actifs_financiers = [
        {
            "description": ss.get(f"af_{i}_description", f"Actif {i + 1}"),
            "type_actif": ss.get(f"af_{i}_type", "Assurance-vie (fonds euros)"),
            "valeur_actuelle": ss.get(f"af_{i}_valeur", 0.0),
            "date_souscription": ss.get(f"af_{i}_date_souscription", ""),
            "taux_rendement": ss.get(f"af_{i}_taux_rendement", 0.0),
            "versement_mensuel": ss.get(f"af_{i}_versement_mensuel", 0.0),
        }
        for i in range(int(ss.get("nb_actifs_financiers", 0)))
    ]

    # ── Trésorerie ────────────────────────────────────────────────────────────
    tresorerie = {
        "livret_a": ss.get("treso_livret_a", 0.0),
        "ldds": ss.get("treso_ldds", 0.0),
        "livret_jeune": ss.get("treso_livret_jeune", 0.0),
        "autres_livrets": ss.get("treso_autres_livrets", 0.0),
        "compte_courant_disponible": ss.get("treso_cc_disponible", 0.0),
        "autres_liquidites": ss.get("treso_autres", 0.0),
    }

    # ── Crédits ───────────────────────────────────────────────────────────────
    credits = [
        {
            "description": ss.get(f"cr_{i}_description", f"Crédit {i + 1}"),
            "type_credit": ss.get(f"cr_{i}_type", "Crédit immobilier (résidence principale)"),
            "capital_restant_du": ss.get(f"cr_{i}_crd", 0.0),
            "mensualite": ss.get(f"cr_{i}_mensualite", 0.0),
            "taux_annuel": ss.get(f"cr_{i}_taux", 0.0),
            "annee_fin": ss.get(f"cr_{i}_annee_fin", None),
            "date_debut": ss.get(f"cr_{i}_date_debut", ""),
            "assurance_emprunteur": ss.get(f"cr_{i}_assurance_emprunteur", 0.0),
        }
        for i in range(int(ss.get("nb_credits", 0)))
    ]

    # ── Fiscalité ─────────────────────────────────────────────────────────────
    fiscalite = {
        "tranche_marginale_imposition": ss.get("fisc_tmi", "30 %"),
        "revenu_fiscal_reference": ss.get("fisc_rfr", 0.0),
        "parts_fiscales": ss.get("fisc_parts", 1.0),
        "impot_revenu_annuel": ss.get("fisc_ir_annuel", 0.0),
        "assujetti_ifi": ss.get("fisc_ifi", False),
        "ifi_annuel": ss.get("fisc_ifi_annuel", 0.0) if ss.get("fisc_ifi") else 0.0,
    }

    # ── Prévoyance & Transmission ────────────────────────────────────────────
    prevoyance = {
        "assurance_deces": ss.get("prev_deces", "Non"),
        "capital_deces": ss.get("prev_capital_deces", 0.0),
        "capital_deces_conjoint": ss.get("prev_capital_deces_conjoint", 0.0),
        "arret_travail": ss.get("prev_arret_travail", "Non"),
        "indemnite_invalidite": ss.get("prev_indemnite_invalidite", 0.0),
        "dependance": ss.get("prev_dependance", "Non"),
        "rente_dependance": ss.get("prev_rente_dependance", 0.0),
        "mutuelle": ss.get("prev_mutuelle", "Non"),
        "age_retraite": ss.get("prev_age_retraite", 65),
        "pension_estimee": ss.get("prev_pension_estimee", 0.0),
        "revenu_souhaite_retraite": ss.get("prev_revenu_souhaite_retraite", 0.0),
        "per": ss.get("prev_per", "Non"),
        "per_date_ouverture": ss.get("prev_per_date_ouverture", ""),
        "per_encours": ss.get("prev_per_encours", 0.0),
        "per_versement_mensuel": ss.get("prev_per_versement_mensuel", 0.0),
        "per_rendement": ss.get("prev_per_rendement", 0.0),
        "cout_deces": ss.get("prev_cout_deces", 0.0),
        "cout_mutuelle": ss.get("prev_cout_mutuelle", 0.0),
        "cout_consommation": ss.get("prev_cout_consommation", 0.0),
        "cout_autres": ss.get("prev_cout_autres", 0.0),
        "testament": ss.get("transm_testament", "Non"),
        "donations": ss.get("transm_donations", "Non"),
        "montant_donations": ss.get("transm_montant_donations", 0.0),
        "clause_av": ss.get("transm_clause_av", "Non / ne sait pas"),
        "souhaits_transmission": ss.get("transm_souhaits", ""),
    }

    # ── Objectifs ─────────────────────────────────────────────────────────────
    objectifs = {
        "objectifs": ss.get("obj_objectifs", []),
        "horizon_investissement": ss.get("obj_horizon", "Moyen terme (3 à 8 ans)"),
        "profil_risque": ss.get("obj_profil_risque", "Équilibré — légères fluctuations acceptées"),
        "connaissance_placements": ss.get("obj_connaissance_placements", ""),
        "operations_recentes": ss.get("obj_operations_recentes", "Non"),
        "operations_montant": ss.get("obj_operations_montant", 0.0),
        "comportement_perte": ss.get("obj_comportement_perte", ""),
        "epargne_supplementaire": ss.get("obj_epargne_supplementaire", 0.0),
        "commentaires": ss.get("obj_commentaires", ""),
    }

    return {
        "identite": identite,
        "situation_familiale": situation_familiale,
        "personnes_charge": personnes_charge,
        "revenus": revenus,
        "charges": charges,
        "immobilier": immobilier,
        "actifs_financiers": actifs_financiers,
        "tresorerie": tresorerie,
        "credits": credits,
        "fiscalite": fiscalite,
        "prevoyance": prevoyance,
        "objectifs": objectifs,
    }


# ─────────────────────────────────────────────
#  📊 · BILAN PATRIMONIAL
# ─────────────────────────────────────────────

with tab_bilan:
    st.markdown(
        '<p class="section-title">Générer le bilan patrimonial</p>',
        unsafe_allow_html=True,
    )

    st.info(
        "Assurez-vous d'avoir renseigné les sections **Revenus**, **Charges**, "
        "**Patrimoine** et **Crédits** avant de calculer."
    )

    col_btn, col_spacer = st.columns([1, 3])
    with col_btn:
        if st.button("⚙️ Calculer le bilan patrimonial", type="primary", use_container_width=True):
            with st.spinner("Calcul en cours…"):
                data = _collect_data()
                bilan = calculer_bilan(data)
                st.session_state["bilan_calcule"] = True
                st.session_state["bilan_data"] = data
                st.session_state["bilan_result"] = bilan
            st.success("Bilan calculé avec succès !")

    # ── Affichage du rapport ──────────────────────────────────────────────────
    if st.session_state.get("bilan_calcule"):
        data = st.session_state["bilan_data"]
        bilan = st.session_state["bilan_result"]

        afficher_rapport_streamlit(data, bilan)

        # Bouton de téléchargement PDF
        st.markdown("---")
        st.markdown("### Télécharger le rapport")

        with st.spinner("Génération du PDF…"):
            pdf_bytes = generer_pdf(data, bilan)

        identite = data.get("identite", {})
        nom = identite.get("nom", "client").lower().replace(" ", "_")
        prenom = identite.get("prenom", "").lower().replace(" ", "_")
        filename = f"bilan_patrimonial_{prenom}_{nom}_{date.today().strftime('%Y%m%d')}.pdf"

        st.download_button(
            label="📄 Télécharger le rapport PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=False,
        )

        st.caption(
            "Le rapport PDF contient la synthèse patrimoniale, les tableaux actif/passif "
            "et revenus/charges, ainsi que l'analyse et les recommandations."
        )


# ─────────────────────────────────────────────
#  13 · PROFIL INVESTISSEUR
#  AMF + Finance durable + Score de risque
# ─────────────────────────────────────────────

with tab_profil:
    st.markdown(
        '<p class="section-title">Questionnaire Profil Investisseur</p>',
        unsafe_allow_html=True,
    )
    st.info(
        "Ce questionnaire combine le profil **AMF** (tolérance au risque financier), "
        "le profil **Finance durable** (préférences ESG/ISR) et génère un **score de risque 1→7** "
        "conforme MIF2 ainsi qu'un **profil d'allocation recommandé**."
    )

    # ══════════════════════════════════════════
    #  SECTION A — SITUATION & HORIZON
    # ══════════════════════════════════════════
    st.markdown('<p class="section-title">A — Situation & Horizon de placement</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        prf_age = st.selectbox(
            "A1. Votre âge",
            ["Moins de 35 ans", "35 à 49 ans", "50 à 59 ans", "60 ans et plus"],
            key="prf_age",
        )
        prf_horizon = st.selectbox(
            "A2. Horizon de placement pour ce projet",
            ["Moins de 2 ans", "2 à 5 ans", "5 à 10 ans", "Plus de 10 ans"],
            key="prf_horizon",
        )
    with c2:
        prf_situation_pro = st.selectbox(
            "A3. Situation professionnelle actuelle",
            ["Salarié(e) CDI / Fonctionnaire", "Indépendant(e) / TNS", "Retraité(e)", "Sans emploi / Autre"],
            key="prf_situation_pro",
        )
        prf_epargne_dispo = st.selectbox(
            "A4. Part du capital à investir par rapport à votre patrimoine total",
            ["Moins de 10%", "10% à 25%", "25% à 50%", "Plus de 50%"],
            key="prf_epargne_dispo",
        )

    # ══════════════════════════════════════════
    #  SECTION B — OBJECTIFS FINANCIERS
    # ══════════════════════════════════════════
    st.markdown('<p class="section-title">B — Objectifs financiers</p>', unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        prf_objectif_principal = st.selectbox(
            "B1. Objectif principal de ce placement",
            [
                "Préserver mon capital (pas de perte acceptable)",
                "Générer des revenus réguliers stables",
                "Faire croître mon capital à long terme",
                "Maximiser la performance, même avec risque élevé",
            ],
            key="prf_objectif_principal",
        )
        prf_besoin_liquidite = st.selectbox(
            "B2. Avez-vous besoin de pouvoir récupérer ce capital rapidement ?",
            [
                "Oui, à tout moment (besoin de liquidité immédiate)",
                "Oui, dans les 2 ans",
                "Non, pas avant 5 ans",
                "Non, je n'en aurai probablement jamais besoin à court terme",
            ],
            key="prf_besoin_liquidite",
        )
    with c4:
        prf_revenu_complementaire = st.selectbox(
            "B3. Souhaitez-vous percevoir des revenus complémentaires issus de ce placement ?",
            ["Non, je préfère la capitalisation", "Oui, occasionnellement", "Oui, régulièrement"],
            key="prf_revenu_complementaire",
        )
        prf_montant_investi = st.selectbox(
            "B4. Montant envisagé pour ce placement",
            ["Moins de 10 000 €", "10 000 € à 50 000 €", "50 000 € à 150 000 €", "Plus de 150 000 €"],
            key="prf_montant_investi",
        )

    # ══════════════════════════════════════════
    #  SECTION C — TOLÉRANCE AU RISQUE (AMF)
    # ══════════════════════════════════════════
    st.markdown('<p class="section-title">C — Tolérance au risque (profil AMF)</p>', unsafe_allow_html=True)

    c5, c6 = st.columns(2)
    with c5:
        prf_perte_max = st.selectbox(
            "C1. Quelle perte maximale sur 1 an seriez-vous prêt(e) à accepter ?",
            [
                "Aucune perte — je veux garantir mon capital",
                "Jusqu'à -5% (perte légère acceptable)",
                "Jusqu'à -15% (perte modérée acceptable)",
                "Jusqu'à -25% (perte significative acceptable)",
                "Plus de -25% si la performance à long terme est au rendez-vous",
            ],
            key="prf_perte_max",
        )
        prf_reaction_baisse = st.selectbox(
            "C2. Si votre placement perd 20% en 3 mois, vous :",
            [
                "Vendez immédiatement pour éviter d'autres pertes",
                "Attendez sans rien faire en espérant une remontée",
                "Analysez avant de décider",
                "Rachetez davantage pour profiter de la baisse",
            ],
            key="prf_reaction_baisse",
        )
        prf_volatilite = st.selectbox(
            "C3. Comment réagissez-vous aux fluctuations de valeur de vos placements ?",
            [
                "Cela me stress beaucoup, je préfère la stabilité absolue",
                "Je les accepte si elles restent limitées",
                "Je les accepte en gardant une vision long terme",
                "Elles ne me dérangent pas, c'est inhérent aux marchés",
            ],
            key="prf_volatilite",
        )
    with c6:
        prf_experience = st.selectbox(
            "C4. Quelle est votre expérience en matière de placements financiers ?",
            [
                "Aucune — je débute",
                "Limitée — livrets et fonds euros uniquement",
                "Moyenne — quelques placements en actions/obligations",
                "Confirmée — portefeuille diversifié, OPCVM, ETF",
                "Avancée — produits complexes, produits structurés, dérivés",
            ],
            key="prf_experience",
        )
        prf_connaissance_produits = st.multiselect(
            "C5. Quels types de placements connaissez-vous ? (plusieurs choix possibles)",
            [
                "Livrets réglementés (Livret A, LDDS)",
                "Fonds euros (assurance-vie)",
                "Obligations",
                "Actions cotées",
                "OPCVM / ETF / Trackers",
                "Immobilier (SCPI, OPCI)",
                "Produits structurés",
                "Private equity",
                "Cryptoactifs",
            ],
            key="prf_connaissance_produits",
        )
        prf_deja_perdu = st.selectbox(
            "C6. Avez-vous déjà subi une perte significative sur un placement ?",
            ["Non, jamais", "Oui, une perte légère (< 10%)", "Oui, une perte importante (> 10%)", "Oui et cela a modifié ma façon d'investir"],
            key="prf_deja_perdu",
        )

    # ══════════════════════════════════════════
    #  SECTION D — FINANCE DURABLE (ESG/ISR)
    # ══════════════════════════════════════════
    st.markdown('<p class="section-title">D — Préférences en matière de finance durable</p>', unsafe_allow_html=True)
    st.caption("Conformément à la réglementation MIF2 révisée (août 2022), nous devons recueillir vos préférences en matière d'investissement durable.")

    c7, c8 = st.columns(2)
    with c7:
        prf_esg_interet = st.selectbox(
            "D1. Êtes-vous sensible aux critères environnementaux, sociaux et de gouvernance (ESG) dans vos placements ?",
            [
                "Non, la performance financière est mon seul critère",
                "Légèrement — je préfère éviter les secteurs controversés",
                "Oui — j'intègre les critères ESG dans mes choix",
                "Oui, c'est une priorité — je veux un impact positif mesurable",
            ],
            key="prf_esg_interet",
        )
        prf_exclusions = st.multiselect(
            "D2. Souhaitez-vous exclure certains secteurs de vos investissements ?",
            [
                "Armement / Défense",
                "Tabac",
                "Énergies fossiles (charbon, pétrole, gaz)",
                "Jeux d'argent",
                "Alcool",
                "Industrie nucléaire",
                "Aucune exclusion particulière",
            ],
            key="prf_exclusions",
        )
        prf_taxonomie = st.selectbox(
            "D3. Souhaitez-vous qu'une part minimale de votre investissement soit alignée sur la taxonomie européenne (activités durables) ?",
            [
                "Non, pas de contrainte",
                "Oui, au moins 10% d'activités durables",
                "Oui, au moins 30% d'activités durables",
                "Oui, le maximum possible",
            ],
            key="prf_taxonomie",
        )
    with c8:
        prf_pai = st.selectbox(
            "D4. Souhaitez-vous que les impacts négatifs sur la durabilité (PAI) soient pris en compte dans la sélection des investissements ?",
            [
                "Non, pas nécessairement",
                "Oui, de manière partielle",
                "Oui, de manière systématique",
            ],
            key="prf_pai",
        )
        prf_impact = st.selectbox(
            "D5. Quel type d'impact durable vous tient le plus à cœur ?",
            [
                "Environnemental — climat, biodiversité, eau",
                "Social — emploi, égalité, droits humains",
                "Gouvernance — transparence, éthique des entreprises",
                "Les trois également",
                "Aucune préférence particulière",
            ],
            key="prf_impact",
        )
        prf_perf_vs_esg = st.selectbox(
            "D6. Si un fonds ISR/ESG performe légèrement moins qu'un fonds classique, vous :",
            [
                "Je préfère la performance — l'ESG n'est pas prioritaire",
                "J'accepte jusqu'à -0,5% de performance annuelle",
                "J'accepte jusqu'à -1% de performance annuelle",
                "J'accepte un écart de performance plus important pour l'impact",
            ],
            key="prf_perf_vs_esg",
        )

    # ══════════════════════════════════════════
    #  CALCUL AUTOMATIQUE DES PROFILS
    # ══════════════════════════════════════════

    st.markdown("---")
    if st.button("🎯 Calculer mon profil investisseur", type="primary", key="btn_calcul_profil"):

        # ── Score AMF (risque financier) : 0 à 100 pts ───────────────────────
        score_amf = 0

        # A1 — âge (moins d'années = plus de capacité à prendre des risques)
        score_amf += {"Moins de 35 ans": 12, "35 à 49 ans": 9, "50 à 59 ans": 5, "60 ans et plus": 2}.get(st.session_state.get("prf_age", ""), 0)

        # A2 — horizon
        score_amf += {"Moins de 2 ans": 0, "2 à 5 ans": 5, "5 à 10 ans": 10, "Plus de 10 ans": 15}.get(st.session_state.get("prf_horizon", ""), 0)

        # A4 — part investie
        score_amf += {"Moins de 10%": 8, "10% à 25%": 6, "25% à 50%": 3, "Plus de 50%": 1}.get(st.session_state.get("prf_epargne_dispo", ""), 0)

        # B1 — objectif
        score_amf += {
            "Préserver mon capital (pas de perte acceptable)": 0,
            "Générer des revenus réguliers stables": 5,
            "Faire croître mon capital à long terme": 10,
            "Maximiser la performance, même avec risque élevé": 15,
        }.get(st.session_state.get("prf_objectif_principal", ""), 0)

        # C1 — perte max
        score_amf += {
            "Aucune perte — je veux garantir mon capital": 0,
            "Jusqu'à -5% (perte légère acceptable)": 5,
            "Jusqu'à -15% (perte modérée acceptable)": 10,
            "Jusqu'à -25% (perte significative acceptable)": 15,
            "Plus de -25% si la performance à long terme est au rendez-vous": 20,
        }.get(st.session_state.get("prf_perte_max", ""), 0)

        # C2 — réaction baisse
        score_amf += {
            "Vendez immédiatement pour éviter d'autres pertes": 0,
            "Attendez sans rien faire en espérant une remontée": 3,
            "Analysez avant de décider": 7,
            "Rachetez davantage pour profiter de la baisse": 10,
        }.get(st.session_state.get("prf_reaction_baisse", ""), 0)

        # C3 — volatilité
        score_amf += {
            "Cela me stress beaucoup, je préfère la stabilité absolue": 0,
            "Je les accepte si elles restent limitées": 4,
            "Je les accepte en gardant une vision long terme": 8,
            "Elles ne me dérangent pas, c'est inhérent aux marchés": 12,
        }.get(st.session_state.get("prf_volatilite", ""), 0)

        # C4 — expérience
        score_amf += {
            "Aucune — je débute": 0,
            "Limitée — livrets et fonds euros uniquement": 2,
            "Moyenne — quelques placements en actions/obligations": 5,
            "Confirmée — portefeuille diversifié, OPCVM, ETF": 8,
            "Avancée — produits complexes, produits structurés, dérivés": 10,
        }.get(st.session_state.get("prf_experience", ""), 0)

        # ── Score ESG (finance durable) : 0 à 40 pts ─────────────────────────
        score_esg = 0

        score_esg += {
            "Non, la performance financière est mon seul critère": 0,
            "Légèrement — je préfère éviter les secteurs controversés": 5,
            "Oui — j'intègre les critères ESG dans mes choix": 12,
            "Oui, c'est une priorité — je veux un impact positif mesurable": 20,
        }.get(st.session_state.get("prf_esg_interet", ""), 0)

        score_esg += {
            "Non, pas de contrainte": 0,
            "Oui, au moins 10% d'activités durables": 3,
            "Oui, au moins 30% d'activités durables": 6,
            "Oui, le maximum possible": 10,
        }.get(st.session_state.get("prf_taxonomie", ""), 0)

        score_esg += {
            "Non, pas nécessairement": 0,
            "Oui, de manière partielle": 3,
            "Oui, de manière systématique": 6,
        }.get(st.session_state.get("prf_pai", ""), 0)

        score_esg += {
            "Je préfère la performance — l'ESG n'est pas prioritaire": 0,
            "J'accepte jusqu'à -0,5% de performance annuelle": 1,
            "J'accepte jusqu'à -1% de performance annuelle": 2,
            "J'accepte un écart de performance plus important pour l'impact": 4,
        }.get(st.session_state.get("prf_perf_vs_esg", ""), 0)

        # ── Score de risque MIF2 (1 à 7) ──────────────────────────────────────
        score_mif2 = max(1, min(7, round(score_amf / 87 * 6 + 1)))

        # ── Profil AMF ────────────────────────────────────────────────────────
        if score_amf <= 20:
            profil_amf = "🛡️ Défensif"
            desc_amf = "Priorité absolue à la préservation du capital. Placements peu risqués, faible volatilité."
            alloc_amf = {"Fonds euros / Monétaire": 70, "Obligations": 20, "Actions": 5, "Immobilier (SCPI)": 5}
            color_amf = "#c6f6d5"
        elif score_amf <= 45:
            profil_amf = "⚖️ Équilibré"
            desc_amf = "Recherche d'un équilibre entre sécurité et performance. Accepte une volatilité modérée."
            alloc_amf = {"Fonds euros / Monétaire": 35, "Obligations": 25, "Actions": 30, "Immobilier (SCPI)": 10}
            color_amf = "#bee3f8"
        elif score_amf <= 65:
            profil_amf = "📈 Dynamique"
            desc_amf = "Orientation performance à long terme. Accepte des fluctuations importantes sur la durée."
            alloc_amf = {"Fonds euros / Monétaire": 10, "Obligations": 15, "Actions": 60, "Immobilier (SCPI)": 15}
            color_amf = "#fefcbf"
        else:
            profil_amf = "🚀 Offensif"
            desc_amf = "Recherche de performance maximale. Accepte un risque élevé et une forte volatilité."
            alloc_amf = {"Fonds euros / Monétaire": 0, "Obligations": 5, "Actions": 80, "Immobilier (SCPI)": 15}
            color_amf = "#fed7d7"

        # ── Profil Finance Durable ────────────────────────────────────────────
        if score_esg <= 5:
            profil_esg = "🔵 Conventionnel"
            desc_esg = "Pas de contrainte ESG. Sélection basée uniquement sur les critères financiers."
        elif score_esg <= 15:
            profil_esg = "🟢 ISR — Investissement Socialement Responsable"
            desc_esg = "Intégration des critères ESG dans la sélection, exclusion des secteurs controversés."
        elif score_esg <= 28:
            profil_esg = "🌿 ESG Engagé"
            desc_esg = "Fort ancrage ESG avec alignement partiel sur la taxonomie européenne et prise en compte des PAI."
        else:
            profil_esg = "🌍 Transition / Impact"
            desc_esg = "Investisseur impact : priorité aux placements contribuant activement à la transition écologique et sociale."

        # ── Profil combiné & allocation ───────────────────────────────────────
        if score_esg > 15:
            suffixe_esg = " — Orientation durable"
            note_esg = "Filtrage ESG appliqué sur la sélection de fonds."
        else:
            suffixe_esg = ""
            note_esg = "Pas de contrainte ESG sur les supports proposés."

        profil_final = f"{profil_amf}{suffixe_esg}"

        # ── Sauvegarde dans session_state ─────────────────────────────────────
        st.session_state["profil_amf"] = profil_amf
        st.session_state["profil_esg"] = profil_esg
        st.session_state["score_mif2"] = score_mif2
        st.session_state["profil_final"] = profil_final
        st.session_state["alloc_amf"] = alloc_amf
        st.session_state["score_amf"] = score_amf
        st.session_state["score_esg"] = score_esg
        st.session_state["profil_calcule"] = True

    # ── Affichage des résultats ───────────────────────────────────────────────
    if st.session_state.get("profil_calcule"):

        profil_amf   = st.session_state["profil_amf"]
        profil_esg   = st.session_state["profil_esg"]
        score_mif2   = st.session_state["score_mif2"]
        profil_final = st.session_state["profil_final"]
        alloc_amf    = st.session_state["alloc_amf"]
        score_amf    = st.session_state["score_amf"]
        score_esg    = st.session_state["score_esg"]

        # ── Bandeau score MIF2 ────────────────────────────────────────────────
        mif2_colors = {1: "#276749", 2: "#276749", 3: "#2c7a7b", 4: "#d69e2e", 5: "#dd6b20", 6: "#c53030", 7: "#742a2a"}
        bg_mif2 = mif2_colors.get(score_mif2, "#2d3748")
        st.markdown(
            f'<div style="background:{bg_mif2};padding:16px 24px;border-radius:10px;text-align:center;margin:12px 0;">'
            f'<span style="color:white;font-size:1.1rem;font-weight:600;">Score de risque MIF2 : </span>'
            f'<span style="color:white;font-size:2rem;font-weight:800;">{score_mif2} / 7</span>'
            f'<br><span style="color:#e2e8f0;font-size:0.85rem;">Score brut AMF : {score_amf}/87 pts · Score ESG : {score_esg}/40 pts</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("### Résultats détaillés")
        r1, r2, r3 = st.columns(3)

        with r1:
            st.markdown(
                f'<div style="background:#edf2f7;padding:14px;border-radius:8px;text-align:center;">'
                f'<div style="font-size:0.8rem;color:#718096;font-weight:600;">PROFIL AMF</div>'
                f'<div style="font-size:1.3rem;font-weight:700;color:#1e3a5f;margin:6px 0;">{profil_amf}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with r2:
            st.markdown(
                f'<div style="background:#edf2f7;padding:14px;border-radius:8px;text-align:center;">'
                f'<div style="font-size:0.8rem;color:#718096;font-weight:600;">PROFIL FINANCE DURABLE</div>'
                f'<div style="font-size:1.1rem;font-weight:700;color:#276749;margin:6px 0;">{profil_esg}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with r3:
            st.markdown(
                f'<div style="background:#1e3a5f;padding:14px;border-radius:8px;text-align:center;">'
                f'<div style="font-size:0.8rem;color:#a0aec0;font-weight:600;">PROFIL COMBINÉ FINAL</div>'
                f'<div style="font-size:1rem;font-weight:700;color:white;margin:6px 0;">{profil_final}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Allocation recommandée ────────────────────────────────────────────
        st.markdown("### Allocation d'actifs recommandée")

        alloc_items = list(alloc_amf.items())
        cols_alloc = st.columns(len(alloc_items))
        colors_alloc = ["#2c7a7b", "#1e3a5f", "#e53e3e", "#d69e2e"]
        for idx, (classe, pct) in enumerate(alloc_items):
            with cols_alloc[idx]:
                st.markdown(
                    f'<div style="background:{colors_alloc[idx]};padding:12px;border-radius:8px;text-align:center;">'
                    f'<div style="color:rgba(255,255,255,0.8);font-size:0.75rem;">{classe}</div>'
                    f'<div style="color:white;font-size:1.8rem;font-weight:800;">{pct}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # ── Grille de risque MIF2 visuelle ────────────────────────────────────
        st.markdown("### Positionnement sur l'échelle de risque MIF2")
        mif2_html = '<div style="display:flex;gap:4px;margin:10px 0;">'
        labels = ["1\nTrès\nfaible", "2\nFaible", "3\nMod.\nfaible", "4\nModéré", "5\nMod.\nélevé", "6\nÉlevé", "7\nTrès\nélevé"]
        bg_colors = ["#276749","#2f855a","#2c7a7b","#d69e2e","#dd6b20","#c53030","#742a2a"]
        for n in range(1, 8):
            active = n == score_mif2
            border = "3px solid white" if active else "3px solid transparent"
            scale = "scale(1.15)" if active else "scale(1)"
            mif2_html += (
                f'<div style="flex:1;background:{bg_colors[n-1]};border:{border};'
                f'border-radius:6px;padding:10px 4px;text-align:center;'
                f'transform:{scale};transition:transform 0.2s;">'
                f'<div style="color:white;font-size:0.75rem;font-weight:{"800" if active else "500"};white-space:pre-line;">{labels[n-1]}</div>'
                f'</div>'
            )
        mif2_html += '</div>'
        st.markdown(mif2_html, unsafe_allow_html=True)

        # ── Note ESG ──────────────────────────────────────────────────────────
        st.markdown("### Préférences finance durable")
        note_esg = "Filtrage ESG appliqué sur la sélection de fonds." if score_esg > 15 else "Pas de contrainte ESG sur les supports proposés."
        st.markdown(
            f'<div style="background:#f0fff4;border-left:4px solid #38a169;padding:12px 16px;border-radius:0 8px 8px 0;">'
            f'<strong>{profil_esg}</strong><br>'
            f'<span style="font-size:0.9rem;color:#4a5568;">{note_esg}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Avertissement réglementaire ───────────────────────────────────────
        st.markdown("---")
        st.caption(
            "⚠️ Ce questionnaire est établi conformément aux exigences MIF2 et à la réglementation AMF. "
            "Les résultats constituent une recommandation indicative et ne se substituent pas à un conseil "
            "personnalisé fourni par un conseiller en investissements financiers (CIF) agréé. "
            "Le profil doit être revu au moins tous les 2 ans ou lors de tout changement de situation."
        )
