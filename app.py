"""
MY DATA COLLECTION APP — Projet de fin d'année Data Collection

Options :
    1. Scraper des données sur plusieurs pages (BeautifulSoup, code du cours)
    2. Télécharger les données brutes (Web Scraper no-code) + données des bulletins PDF
    3. Dashboard des données nettoyées (une source à la fois)
    4. Formulaires d'évaluation (Kobo + Google Forms)
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import scrapers as sc

# ----------------------------------------------------------------------------------
# LIENS DES FORMULAIRES — à remplacer par tes propres liens une fois les formulaires créés
# ----------------------------------------------------------------------------------
KOBO_URL = "https://ee.kobotoolbox.org/x/gfUgReva"
GOOGLE_FORMS_URL = "https://forms.gle/fyppdTMwt9dAbLwa7"

RAW_DIR = sc.DATA_DIR / "raw"
CLEAN_DIR = sc.DATA_DIR / "clean"

SOURCES = {
    "books": {"nom": "Books to Scrape", "url": "https://books.toscrape.com/",
              "scrape": sc.scrape_books, "clean": sc.clean_books, "raw_csv": "books_webscraper.csv"},
    "gaaraas": {"nom": "Gaaraas — Dakar auto (voitures)", "url": "https://www.gaaraas.com/fr/users/dakar-auto",
                "scrape": sc.scrape_gaaraas, "clean": sc.clean_gaaraas, "raw_csv": "gaaraas_webscraper.csv"},
    "motos": {"nom": "Dakar-Auto — Motos & scooters", "url": "https://dakar-auto.com/senegal/motos-and-scooters-3",
              "scrape": sc.scrape_motos, "clean": sc.clean_motos, "raw_csv": "motos_webscraper.csv"},
}

COULEUR = "#1f6f8b"
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = [COULEUR, "#e07a5f", "#81b29a", "#f2cc8f", "#3d405b", "#9c89b8"]

st.set_page_config(page_title="My Data Collection App", page_icon="📊", layout="wide")

st.markdown("""
<style>
div.stButton > button, div.stDownloadButton > button, a[data-testid="stBaseLinkButton-secondary"] {
    width: 100%; font-size: 15px; height: 3em;
}
[data-testid="stMetricValue"] { font-size: 1.6rem; }
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------------
# Chargement des données (mis en cache pour ne pas relire la base à chaque clic)
# ----------------------------------------------------------------------------------
@st.cache_data
def load_clean(source):
    """Lit les données nettoyées dans la base SQLite (ou dans le CSV si la base est absente)."""
    try:
        return sc.load_from_db(sc.TABLES[source])
    except Exception:
        return pd.read_csv(CLEAN_DIR / f"{source}_clean.csv")


@st.cache_data
def load_raw_webscraper(fichier):
    return pd.read_csv(RAW_DIR / fichier)


@st.cache_data
def load_bulletins_raw():
    return sc.extract_bulletins()


def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def fcfa(x):
    return "—" if pd.isna(x) else f"{x:,.0f} F CFA".replace(",", " ")


# ----------------------------------------------------------------------------------
# En-tête et barre latérale
# ----------------------------------------------------------------------------------
st.markdown("<h1 style='text-align: center;'>MY DATA COLLECTION APP</h1>", unsafe_allow_html=True)
st.markdown("""
Cette application permet de **scraper** des données sur plusieurs pages, de **télécharger** les données brutes
collectées sans code (Web Scraper) et les données des bulletins climatologiques, de **visualiser** un dashboard
des données nettoyées et d'**évaluer** l'application.
* **Librairies Python :** requests, BeautifulSoup, pdfplumber, pandas, sqlite3, plotly, streamlit
* **Sources :** [Books to Scrape](https://books.toscrape.com/) — [Gaaraas](https://www.gaaraas.com/fr/users/dakar-auto)
  — [Dakar-Auto](https://dakar-auto.com/senegal/motos-and-scooters-3) — Bulletins climatologiques 2020-2021 (PDF)
""")

st.sidebar.header("Paramètres")
option = st.sidebar.selectbox("Options", [
    "Scraper des données",
    "Télécharger les données brutes",
    "Dashboard des données",
    "Évaluer l'application",
])

# ==================================================================================
# OPTION 1 — SCRAPER
# ==================================================================================
if option == "Scraper des données":
    source = st.sidebar.selectbox("Source", list(SOURCES), format_func=lambda k: SOURCES[k]["nom"])
    max_pages = sc.MAX_PAGES[source]
    nb_pages = st.sidebar.selectbox("Nombre de pages", list(range(1, max_pages + 1)), index=0)

    st.subheader(f"Scraper : {SOURCES[source]['nom']}")
    st.caption(f"Source : {SOURCES[source]['url']} — {max_pages} pages disponibles. "
               + ("Chaque livre ouvre sa page détail : compter ~10 secondes par page." if source == "books" else ""))

    if st.button(f"Lancer le scraping sur {nb_pages} page(s)"):
        barre = st.progress(0.0, text="Scraping en cours...")
        df_raw = SOURCES[source]["scrape"](
            nb_pages, progress=lambda i, n: barre.progress(i / n, text=f"Page {i}/{n}"))
        barre.empty()
        if df_raw.empty:
            st.error("Aucune donnée récupérée. Le site est peut-être indisponible.")
        else:
            st.session_state["scrape"] = (source, df_raw, SOURCES[source]["clean"](df_raw))

    if "scrape" in st.session_state and st.session_state["scrape"][0] == source:
        _, df_raw, df_clean = st.session_state["scrape"]
        st.success(f"{df_clean.shape[0]} lignes et {df_clean.shape[1]} colonnes après nettoyage.")
        onglet_clean, onglet_raw = st.tabs(["Données nettoyées", "Données brutes"])
        with onglet_clean:
            st.dataframe(df_clean, width="stretch")
        with onglet_raw:
            st.dataframe(df_raw, width="stretch")
        c1, c2 = st.columns(2)
        c1.download_button("Télécharger les données nettoyées (CSV)", csv_bytes(df_clean),
                           f"{source}_scraping.csv", "text/csv")
        if c2.button("Enregistrer dans la base de données"):
            nouvelles = sc.add_to_db(df_clean, sc.TABLES[source])
            load_clean.clear()
            st.success(f"Table « {sc.TABLES[source]} » mise à jour : {nouvelles} nouvelle(s) ligne(s) ajoutée(s), "
                       "les lignes déjà présentes ont été actualisées.")

# ==================================================================================
# OPTION 2 — DONNÉES BRUTES
# ==================================================================================
elif option == "Télécharger les données brutes":
    st.subheader("Données brutes (non nettoyées)")
    st.markdown("Données collectées avec l'extension Chrome **Web Scraper** (sans code), puis données extraites "
                "des **bulletins climatologiques** avec pdfplumber.")

    for source, infos in SOURCES.items():
        fichier = RAW_DIR / infos["raw_csv"]
        if st.button(infos["nom"], key=f"raw_{source}"):
            st.session_state["raw_affiche"] = source
            st.rerun()  # réaffiche la page pour ne montrer que les données choisies
        if st.session_state.get("raw_affiche") == source:
            if fichier.exists():
                df = load_raw_webscraper(infos["raw_csv"])
                st.write(f"Dimension des données : {df.shape[0]} lignes et {df.shape[1]} colonnes.")
                st.dataframe(df, width="stretch")
                st.download_button("Télécharger (CSV)", csv_bytes(df), infos["raw_csv"], "text/csv",
                                   key=f"dl_{source}")
            else:
                st.warning(f"Le fichier `data/raw/{infos['raw_csv']}` n'a pas encore été ajouté.")

    if st.button("Bulletins climatologiques (PDF)", key="raw_bulletins"):
        st.session_state["raw_affiche"] = "bulletins"
        st.rerun()
    if st.session_state.get("raw_affiche") == "bulletins":
        df = load_bulletins_raw()
        c1, c2 = st.columns(2)
        annees = c1.multiselect("Année", sorted(df["annee"].unique()), default=sorted(df["annee"].unique()))
        mois_dispo = [m for m in sc.MOIS if m in df["mois"].unique()]
        mois = c2.multiselect("Mois", mois_dispo, default=mois_dispo)
        df = df[df["annee"].isin(annees) & df["mois"].isin(mois)]
        st.write(f"Dimension des données : {df.shape[0]} lignes et {df.shape[1]} colonnes "
                 "(tableau de la page 8 de chaque bulletin, valeurs brutes).")
        st.dataframe(df, width="stretch")
        st.download_button("Télécharger (CSV)", csv_bytes(df), "bulletins_bruts.csv", "text/csv")

# ==================================================================================
# OPTION 3 — DASHBOARD
# ==================================================================================
elif option == "Dashboard des données":
    choix = {"books": "Books to Scrape", "gaaraas": "Gaaraas — voitures",
             "motos": "Dakar-Auto — motos & scooters", "bulletins": "Bulletins climatologiques"}
    source = st.sidebar.selectbox("Source", list(choix), format_func=choix.get)
    df = load_clean(source)
    st.subheader(f"Dashboard — {choix[source]}")
    st.caption(f"Données nettoyées : {df.shape[0]} lignes, table SQLite « {sc.TABLES[source]} ».")

    # ---------------------------------------------------------------- BOOKS
    if source == "books":
        categories = st.sidebar.multiselect("Catégories", sorted(df["categorie"].unique()))
        if categories:
            df = df[df["categorie"].isin(categories)]
        k = st.columns(4)
        k[0].metric("Livres", f"{len(df)}")
        k[1].metric("Prix moyen", f"£{df['prix'].mean():.2f}")
        k[2].metric("Note moyenne", f"{df['note'].mean():.2f} / 5")
        k[3].metric("Exemplaires en stock", f"{df['nb_produits'].sum()}")
        c1, c2 = st.columns(2)
        top = df["categorie"].value_counts().head(15).sort_values()
        c1.plotly_chart(px.bar(top, orientation="h", title="Catégories les plus représentées",
                               labels={"value": "Nombre de livres", "categorie": ""}).update_layout(showlegend=False),
                        width="stretch")
        c2.plotly_chart(px.histogram(df, x="prix", nbins=30, title="Distribution des prix",
                                     labels={"prix": "Prix (£)"}), width="stretch")
        c3, c4 = st.columns(2)
        notes = df.groupby("note", as_index=False).agg(nb=("titre", "count"), prix_moyen=("prix", "mean"))
        c3.plotly_chart(px.bar(notes, x="note", y="nb", title="Nombre de livres par note",
                               labels={"note": "Note (étoiles)", "nb": "Livres"}), width="stretch")
        c4.plotly_chart(px.bar(notes, x="note", y="prix_moyen", title="Prix moyen selon la note",
                               labels={"note": "Note (étoiles)", "prix_moyen": "Prix moyen (£)"}),
                        width="stretch")

    # ---------------------------------------------------------------- GAARAAS
    elif source == "gaaraas":
        marques = st.sidebar.multiselect("Marques", sorted(df["marque"].unique()))
        if marques:
            df = df[df["marque"].isin(marques)]
        k = st.columns(4)
        k[0].metric("Annonces", f"{len(df)}")
        k[1].metric("Prix médian", fcfa(df["prix"].median()))
        k[2].metric("Kilométrage médian", f"{df['kilometrage'].median():,.0f} km".replace(",", " "))
        k[3].metric("Année médiane", f"{df['annee'].median():.0f}")
        c1, c2 = st.columns(2)
        top = df["marque"].value_counts().head(12).sort_values()
        c1.plotly_chart(px.bar(top, orientation="h", title="Marques les plus présentes",
                               labels={"value": "Annonces", "marque": ""}).update_layout(showlegend=False),
                        width="stretch")
        c2.plotly_chart(px.scatter(df, x="annee", y="prix", color="boite_vitesse", hover_data=["marque", "modele"],
                                   title="Prix selon l'année",
                                   labels={"annee": "Année", "prix": "Prix (F CFA)", "boite_vitesse": "Boîte"}),
                        width="stretch")
        c3, c4 = st.columns(2)
        c3.plotly_chart(px.histogram(df, x="boite_vitesse", color="carburant", barmode="group",
                                     title="Boîte de vitesses et carburant",
                                     labels={"boite_vitesse": "Boîte de vitesses", "carburant": "Carburant"}),
                        width="stretch")
        prix_marque = (df.groupby("marque")["prix"].median().sort_values(ascending=False).head(12)
                       .sort_values().reset_index())
        c4.plotly_chart(px.bar(prix_marque, x="prix", y="marque", orientation="h",
                               title="Prix médian par marque", labels={"prix": "Prix médian (F CFA)", "marque": ""}),
                        width="stretch")

    # ---------------------------------------------------------------- MOTOS
    elif source == "motos":
        categories = st.sidebar.multiselect("Catégorie", sorted(df["categorie"].dropna().unique()))
        if categories:
            df = df[df["categorie"].isin(categories)]
        k = st.columns(4)
        k[0].metric("Annonces", f"{len(df)}")
        k[1].metric("Prix médian", fcfa(df["prix"].median()))
        k[2].metric("Part de neufs", f"{(df['etat'] == 'Neuf').mean():.0%}")
        k[3].metric("Marques différentes", f"{df['marque'].nunique()}")
        c1, c2 = st.columns(2)
        top = df["marque"].value_counts().head(12).sort_values()
        c1.plotly_chart(px.bar(top, orientation="h", title="Marques les plus présentes",
                               labels={"value": "Annonces", "marque": ""}).update_layout(showlegend=False),
                        width="stretch")
        c2.plotly_chart(px.histogram(df, x="categorie", color="etat", barmode="group",
                                     title="Catégorie et état", labels={"categorie": "", "etat": "État"}),
                        width="stretch")
        c3, c4 = st.columns(2)
        c3.plotly_chart(px.box(df.dropna(subset=["prix"]), x="categorie", y="prix", color="etat",
                               title="Prix selon la catégorie et l'état",
                               labels={"categorie": "", "prix": "Prix (F CFA)", "etat": "État"}),
                        width="stretch")
        quartiers = df["quartier"].value_counts().head(12).sort_values()
        c4.plotly_chart(px.bar(quartiers, orientation="h", title="Quartiers où l'on vend le plus",
                               labels={"value": "Annonces", "quartier": ""}).update_layout(showlegend=False),
                        width="stretch")

    # ---------------------------------------------------------------- BULLETINS
    else:
        stations = st.sidebar.multiselect("Stations", sorted(df["station"].unique()),
                                          default=["Dakar", "Saint-Louis", "Tambacounda", "Ziguinchor"])
        k = st.columns(4)
        k[0].metric("Bulletins", f"{df.groupby(['annee', 'mois']).ngroups}")
        k[1].metric("Stations", f"{df['station'].nunique()}")
        k[2].metric("Record de chaleur", f"{df['tmax_maxmax'].max():.1f} °C",
                    df.loc[df['tmax_maxmax'].idxmax(), 'station'], delta_color="off")
        k[3].metric("Minimum le plus bas", f"{df['tmin_minmin'].min():.1f} °C",
                    df.loc[df['tmin_minmin'].idxmin(), 'station'], delta_color="off")
        df["periode"] = df["mois"].str.capitalize() + " " + df["annee"].astype(str)
        df = df.sort_values(["annee", "mois_num"])
        sel = df[df["station"].isin(stations)] if stations else df
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.line(sel, x="periode", y="tmax_maxmax", color="station", markers=True,
                                title="Température maximale absolue par mois",
                                labels={"periode": "", "tmax_maxmax": "Tmax maxmax (°C)", "station": "Station"}),
                        width="stretch")
        c2.plotly_chart(px.line(sel, x="periode", y="tmin_minmin", color="station", markers=True,
                                title="Température minimale absolue par mois",
                                labels={"periode": "", "tmin_minmin": "Tmin minmin (°C)", "station": "Station"}),
                        width="stretch")
        carte = df.pivot_table(index="station", columns="periode", values="tmax_maxmax", sort=False)
        st.plotly_chart(px.imshow(carte, aspect="auto", color_continuous_scale="OrRd",
                                  title="Tmax maxmax (°C) par station et par mois",
                                  labels={"x": "", "y": "", "color": "°C"}), width="stretch")

    with st.expander("Voir les données nettoyées"):
        st.dataframe(df, width="stretch")
        st.download_button("Télécharger (CSV)", csv_bytes(df), f"{source}_clean.csv", "text/csv")

# ==================================================================================
# OPTION 4 — FORMULAIRES
# ==================================================================================
else:
    st.subheader("Donnez votre avis sur l'application")
    st.markdown("Le même questionnaire existe en deux versions. Choisissez celle que vous préférez :")
    c1, c2 = st.columns(2)
    c1.link_button("Formulaire Kobo", KOBO_URL)
    c2.link_button("Formulaire Google Forms", GOOGLE_FORMS_URL)
    if "REMPLACER" in KOBO_URL + GOOGLE_FORMS_URL:
        st.info("Les liens des formulaires ne sont pas encore configurés (variables KOBO_URL et "
                "GOOGLE_FORMS_URL en haut de app.py).")
