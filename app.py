from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

import scrapers as sc

# liens des formulaires
KOBO_URL = "https://ee.kobotoolbox.org/x/gfUgReva"
GOOGLE_FORMS_URL = "https://forms.gle/fyppdTMwt9dAbLwa7"

RAW_DIR = sc.DATA_DIR / "raw"
CLEAN_DIR = sc.DATA_DIR / "clean"

SOURCES = {
    "books": {"nom": "Books to Scrape", "texte": "Librairie en ligne : prix, notes, stock, catégories.",
              "scrape": sc.scrape_books, "clean": sc.clean_books, "raw_csv": "books_webscraper.csv"},
    "gaaraas": {"nom": "Gaaraas (voitures)", "texte": "Annonces de voitures de l'annonceur Dakar auto.",
                "scrape": sc.scrape_gaaraas, "clean": sc.clean_gaaraas, "raw_csv": "gaaraas_webscraper.csv"},
    "motos": {"nom": "Dakar-Auto (motos)", "texte": "Motos et scooters à vendre au Sénégal.",
              "scrape": sc.scrape_motos, "clean": sc.clean_motos, "raw_csv": "motos_webscraper.csv"},
}
NOMS = {"books": "Livres", "gaaraas": "Voitures", "motos": "Motos", "bulletins": "Bulletins climat"}

COULEURS = ["#1fa294", "#c98500", "#5a8df0", "#e0607e"]
ABREGE = dict(zip(sc.MOIS, ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]))
ECHELLE = ["#33301c", "#7d5c12", "#c98500", "#ffd98a"]

st.set_page_config(page_title="My Data Collection App", layout="wide")
st.html("<style>" + (sc.BASE_DIR / "style.css").read_text(encoding="utf-8") + "</style>")


# chargement des données
@st.cache_data
def load_clean(source):
    try:
        return sc.load_from_db(sc.TABLES[source])
    except Exception:
        return pd.read_csv(CLEAN_DIR / f"{source}_clean.csv")


@st.cache_data
def load_raw_webscraper(fichier):
    return pd.read_csv(RAW_DIR / fichier)


@st.cache_data(show_spinner="Lecture des 11 bulletins PDF...")
def load_bulletins_raw():
    return sc.extract_bulletins()


# fonctions d'affichage
def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def nombre(x, unite="", decimales=0):
    if pd.isna(x):
        return "-"
    return f"{x:,.{decimales}f}".replace(",", chr(160)).replace(".", ",") + (f" {unite}" if unite else "")


def section(titre, texte=""):
    st.html(f"<div class='section'><h2>{escape(titre)}</h2>" + (f"<p>{escape(texte)}</p>" if texte else "") + "</div>")


def carte(icone, titre, texte, chiffre):
    st.html(f"<div class='carte-icone ic-{icone}'></div><div class='carte-titre'>{escape(titre)}</div>"
            f"<p class='carte-texte'>{escape(texte)}</p><div class='carte-chiffre'>{escape(chiffre)}</div>")


def kpis(valeurs):
    st.html("<div class='kpis'>" + "".join(
        f"<div class='kpi'><div class='kpi-nom'>{escape(n)}</div><div class='kpi-valeur'>{escape(str(v))}</div>"
        f"<div class='kpi-note'>{escape(p)}</div></div>" for n, v, p in valeurs) + "</div>")


def afficher(colonne, cle, fig, hauteur=360):
    fig.update_layout(
        height=hauteur, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#d5e6e4", size=13),
        title=dict(font=dict(family="Sora, sans-serif", size=16, color="#ffffff"), x=0, xanchor="left"),
        margin=dict(l=8, r=24, t=56, b=8), bargap=0.28, separators=", ",
        legend=dict(title_text="", orientation="h", y=-0.2, yanchor="top", x=0, xanchor="left"),
        hoverlabel=dict(bgcolor="#06262c", bordercolor="#f4b942", font=dict(color="#ffffff")),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor="rgba(255,255,255,.08)", zeroline=False, automargin=True)
    if fig.data and getattr(fig.data[0], "orientation", None) == "h":
        fig.update_yaxes(showgrid=False)
    with colonne.container(key=f"graphe_{cle}"):
        st.plotly_chart(fig, width="stretch", theme=None, key=f"plot_{cle}", config={"displayModeBar": False})


def classement(serie, titre, unite="annonces", couleur=COULEURS[0]):
    d = serie.sort_values().reset_index()
    d.columns = ["nom", "valeur"]
    d["texte"] = d["valeur"].apply(nombre)
    fig = px.bar(d, x="valeur", y="nom", orientation="h", title=titre, text="texte")
    fig.update_traces(marker=dict(color=couleur, cornerradius=4), textposition="outside", cliponaxis=False,
                      textfont_color="#f1f7f6", hovertemplate="%{y} : %{text} " + unite + "<extra></extra>")
    fig.update_xaxes(title="", showticklabels=False, showgrid=False)
    fig.update_yaxes(title="", type="category", ticksuffix="  ")
    return fig


def colonnes_verticales(d, x, y, titre, nom_x, nom_y, couleur=COULEURS[0], fmt=",.0f"):
    fig = px.bar(d, x=x, y=y, title=titre, labels={x: nom_x, y: nom_y}, text_auto=fmt)
    fig.update_traces(marker=dict(color=couleur, cornerradius=4), textposition="outside", cliponaxis=False)
    return fig


def histogramme(d, x, titre, nom_x, nom_y, couleur=COULEURS[0]):
    fig = px.histogram(d, x=x, nbins=25, title=titre, labels={x: nom_x})
    fig.update_traces(marker=dict(color=couleur, line=dict(color="#0e353c", width=2)),
                      hovertemplate=nom_x + " : %{x}<br>" + nom_y + " : %{y}<extra></extra>")
    fig.update_layout(bargap=0)
    return fig.update_yaxes(title=nom_y)


def prix_par_annee(df):
    d = df.dropna(subset=["annee", "prix"]).groupby("annee")["prix"].agg(["median", "count"]).reset_index()
    d = d[d["count"] >= 3]
    fig = px.line(d, x="annee", y="median", markers=True, title="Prix médian selon l'année du véhicule",
                  labels={"annee": "Année", "median": "Prix médian (F CFA)"}, custom_data=["count"])
    fig.update_traces(line=dict(color=COULEURS[1], width=2), marker_size=8,
                      hovertemplate="%{x} : %{y:,.0f} F CFA (%{customdata[0]} annonces)<extra></extra>")
    return fig


st.sidebar.html("<div class='marque'><div class='marque-logo'>DC</div><div class='marque-nom'>Data Collection</div></div>")
OPTIONS = {
    "Scraper des données": ":material/travel_explore:",
    "Télécharger les données brutes": ":material/download:",
    "Dashboard des données": ":material/monitoring:",
    "Évaluer l'application": ":material/rate_review:",
}
option = st.sidebar.radio("Options", list(OPTIONS), format_func=lambda o: f"{OPTIONS[o]}  {o}")
if option == "Scraper des données":
    st.sidebar.divider()
    nb_pages = st.sidebar.selectbox("Nombre de pages à scraper", list(range(1, max(sc.MAX_PAGES.values()) + 1)))
    st.sidebar.caption("Si un site a moins de pages, le scraping s'arrête à la dernière.")

st.html("""
<div class='hero'>
  <h1 class='hero-titre'>MY <b>DATA</b> COLLECTION APP</h1>
  <p class='hero-texte'>Cette application permet de scraper des données sur plusieurs pages, de télécharger les données
  brutes et de voir les dashboards des données nettoyées.</p>
  <div class='puces'>
    <a class='puce' href='https://books.toscrape.com/' target='_blank' rel='noopener'>Books to Scrape</a>
    <a class='puce' href='https://www.gaaraas.com/fr/users/dakar-auto' target='_blank' rel='noopener'>Gaaraas</a>
    <a class='puce' href='https://dakar-auto.com/senegal/motos-and-scooters-3' target='_blank' rel='noopener'>Dakar-Auto</a>
    <span class='puce'>Bulletins climatologiques 2020-2021</span>
  </div>
  <div class='libs'>Python : requests, BeautifulSoup, pdfplumber, pandas, sqlite3, plotly, streamlit</div>
</div>
""")

# option 1 : scraper
if option == "Scraper des données":
    section("Scraper des données",
            "Choisissez le nombre de pages dans la barre latérale, puis la source à scraper.")
    clic = None
    for colonne, (source, infos) in zip(st.columns(3), SOURCES.items()):
        pages = min(nb_pages, sc.MAX_PAGES[source])
        with colonne.container(key=f"carte_scrape_{source}"):
            carte(source, infos["nom"], infos["texte"], f"{sc.MAX_PAGES[source]} pages disponibles")
            if st.button(f"Scraper {pages} page{'s' if pages > 1 else ''}", key=f"scrape_{source}",
                         icon=":material/play_arrow:", width="stretch"):
                clic = (source, pages)
    if nb_pages > 5:
        st.caption("Pour les livres, chaque fiche est ouverte une par une : comptez plusieurs secondes par page.")

    if clic:
        source, pages = clic
        st.session_state.pop("scrape", None)
        barre = st.progress(0.0, text="Connexion au site...")
        try:
            df_raw = SOURCES[source]["scrape"](
                pages, progress=lambda i, n: barre.progress(i / n, text=f"Page {i} sur {n}"))
            if df_raw.empty:
                st.error("Aucune donnée récupérée : la structure du site a peut-être changé.")
            else:
                st.session_state["scrape"] = (source, df_raw, SOURCES[source]["clean"](df_raw))
        except Exception as erreur:
            st.error(f"Le scraping n'a pas abouti. Le site est peut-être indisponible, réessayez plus tard. ({erreur})")
        barre.empty()

    if "scrape" in st.session_state:
        source, df_raw, df_clean = st.session_state["scrape"]
        with st.container(key="resultat"):
            section(f"Résultat : {SOURCES[source]['nom']}",
                    f"Dimension des données : {df_clean.shape[0]} lignes et {df_clean.shape[1]} colonnes.")
            onglet_clean, onglet_raw = st.tabs(["Données nettoyées", "Données brutes"])
            onglet_clean.dataframe(df_clean, width="stretch")
            onglet_raw.dataframe(df_raw, width="stretch")
            c1, c2 = st.columns(2)
            c1.download_button("Télécharger en CSV", csv_bytes(df_clean), f"{source}_scraping.csv", "text/csv",
                               icon=":material/download:", width="stretch")
            if c2.button("Enregistrer dans la base de données", icon=":material/database:", width="stretch"):
                nouvelles = sc.add_to_db(df_clean, sc.TABLES[source])
                load_clean.clear()
                st.success(f"Table « {sc.TABLES[source]} » mise à jour : {nouvelles} nouvelle(s) ligne(s), "
                           "les lignes déjà présentes ont été actualisées.")

# option 2 : données brutes
elif option == "Télécharger les données brutes":
    section("Données brutes, non nettoyées",
            "Collectées sans code avec l'extension Web Scraper, et extraites des bulletins PDF avec pdfplumber.")
    jeux = {s: (NOMS[s], "Export brut de l'extension Chrome Web Scraper.") for s, i in SOURCES.items()}
    jeux["bulletins"] = ("Bulletins climat", "Températures extraites des bulletins PDF.")
    for colonne, (source, (nom, texte)) in zip(st.columns(4), jeux.items()):
        with colonne.container(key=f"carte_raw_{source}"):
            carte(source, nom, texte, "11 bulletins PDF" if source == "bulletins" else "Fichier CSV")
            if st.button("Afficher", key=f"raw_{source}", icon=":material/table_view:", width="stretch"):
                st.session_state["raw_affiche"] = source

    choix = st.session_state.get("raw_affiche")
    if choix:
        with st.container(key="resultat"):
            if choix == "bulletins":
                df = load_bulletins_raw()
                c1, c2 = st.columns(2)
                toutes = sorted(df["annee"].unique())
                annees = c1.multiselect("Année", toutes, default=toutes)
                mois_dispo = [m for m in sc.MOIS if m in df["mois"].unique()]
                mois = c2.multiselect("Mois", mois_dispo, default=mois_dispo)
                df = df[df["annee"].isin(annees) & df["mois"].isin(mois)]
                contenu, fichier = csv_bytes(df), "bulletins_bruts.csv"
            else:
                fichier = SOURCES[choix]["raw_csv"]
                df = load_raw_webscraper(fichier)
                contenu = (RAW_DIR / fichier).read_bytes()
            section(jeux[choix][0], f"Dimension des données : {df.shape[0]} lignes et {df.shape[1]} colonnes.")
            st.dataframe(df, width="stretch")
            st.download_button("Télécharger en CSV", contenu, fichier, "text/csv",
                               icon=":material/download:", width="stretch")

# option 3 : dashboard
elif option == "Dashboard des données":
    section("Dashboard des données nettoyées")
    with st.container(key="choix_source"):
        source = st.radio("Source", list(NOMS), format_func=NOMS.get, horizontal=True, label_visibility="collapsed")
    df = load_clean(source)

    if source == "books":
        filtre = st.multiselect("Filtrer par catégorie", sorted(df["categorie"].unique()), placeholder="Toutes")
        if filtre:
            df = df[df["categorie"].isin(filtre)]
        kpis([("Livres", nombre(len(df)), f"{df['categorie'].nunique()} catégories"),
              ("Prix moyen", "£" + nombre(df["prix"].mean(), decimales=2),
               f"de £{nombre(df['prix'].min(), decimales=2)} à £{nombre(df['prix'].max(), decimales=2)}"),
              ("Note moyenne", nombre(df["note"].mean(), "/ 5", 2), "étoiles"),
              ("Exemplaires en stock", nombre(df["nb_produits"].sum()), "tous livres confondus")])
        notes = df.groupby("note", as_index=False).agg(nb=("titre", "count"), prix=("prix", "mean"))
        c1, c2 = st.columns(2)
        afficher(c1, "b1", classement(df["categorie"].value_counts().head(10), "Les 10 catégories les plus fournies", "livres"))
        afficher(c2, "b2", histogramme(df, "prix", "Distribution des prix", "Prix (£)", "Livres", COULEURS[1]))
        c1, c2 = st.columns(2)
        afficher(c1, "b3", colonnes_verticales(notes, "note", "nb", "Nombre de livres par note", "Note (étoiles)", "Livres"))
        afficher(c2, "b4", colonnes_verticales(notes, "note", "prix", "Prix moyen selon la note", "Note (étoiles)",
                                               "Prix moyen (£)", COULEURS[1], ".2f"))

    elif source == "gaaraas":
        filtre = st.multiselect("Filtrer par marque", sorted(df["marque"].unique()), placeholder="Toutes")
        if filtre:
            df = df[df["marque"].isin(filtre)]
        kpis([("Annonces", nombre(len(df)), f"{df['marque'].nunique()} marques"),
              ("Prix médian", nombre(df["prix"].median(), "F"), "francs CFA"),
              ("Kilométrage médian", nombre(df["kilometrage"].median(), "km"), "au compteur"),
              ("Année médiane", f"{df['annee'].median():.0f}" if df["annee"].notna().any() else "-", "mise en circulation")])
        c1, c2 = st.columns(2)
        afficher(c1, "g1", classement(df["marque"].value_counts().head(10), "Les 10 marques les plus présentes"))
        afficher(c2, "g2", prix_par_annee(df))
        c1, c2 = st.columns(2)
        fig = px.scatter(df.dropna(subset=["prix", "kilometrage"]), x="kilometrage", y="prix", color="boite_vitesse",
                         hover_name="marque", hover_data={"modele": True, "annee": True},
                         color_discrete_map={"Manuelle": COULEURS[0], "Automatique": COULEURS[1]},
                         title="Prix et kilométrage", labels={"kilometrage": "Kilométrage", "prix": "Prix (F CFA)",
                                                             "boite_vitesse": "Boîte", "modele": "Modèle", "annee": "Année"})
        fig.update_traces(marker=dict(size=9, line=dict(color="#0e353c", width=1.5)))
        afficher(c1, "g3", fig)
        d = df.groupby(["boite_vitesse", "carburant"]).size().reset_index(name="nb")
        fig = px.bar(d, x="boite_vitesse", y="nb", color="carburant", barmode="group", text_auto=True,
                     color_discrete_map={"Diesel": COULEURS[2], "Essence": COULEURS[3]}, title="Boîte de vitesses et carburant",
                     labels={"boite_vitesse": "", "nb": "Annonces", "carburant": "Carburant"})
        fig.update_traces(marker_cornerradius=4, textposition="outside", cliponaxis=False)
        afficher(c2, "g4", fig)

    elif source == "motos":
        filtre = st.multiselect("Filtrer par marque", sorted(df["marque"].unique()), placeholder="Toutes")
        if filtre:
            df = df[df["marque"].isin(filtre)]
        kpis([("Annonces", nombre(len(df)), f"{df['marque'].nunique()} marques"),
              ("Prix médian", nombre(df["prix"].median(), "F"), "francs CFA"),
              ("Occasion", f"{(df['etat'] == 'Occasion').mean():.0%}", "des annonces"),
              ("Scooters", f"{(df['categorie'] == 'Scooters').mean():.0%}", "selon le classement du site")])
        c1, c2 = st.columns(2)
        afficher(c1, "m1", classement(df["marque"].value_counts().head(10), "Les 10 marques les plus présentes"))
        afficher(c2, "m2", prix_par_annee(df))
        c1, c2 = st.columns(2)
        fig = px.box(df.dropna(subset=["prix"]), x="categorie", y="prix", title="Répartition des prix par catégorie",
                     labels={"categorie": "", "prix": "Prix (F CFA)"}, hover_data=["marque", "modele"])
        fig.update_traces(line=dict(color=COULEURS[0], width=2), fillcolor="rgba(31,162,148,.3)",
                          marker=dict(size=6, color=COULEURS[0]))
        afficher(c1, "m3", fig)
        afficher(c2, "m4", classement(df["quartier"].value_counts().head(10), "Les 10 quartiers les plus actifs", couleur=COULEURS[1]))

    else:
        kpis([("Bulletins", df.groupby(["annee", "mois"]).ngroups, "7 en 2020, 4 en 2021"),
              ("Stations", df["station"].nunique(), "au Sénégal"),
              ("Record de chaleur", nombre(df["tmax_maxmax"].max(), "°C", 1),
               f"{df.loc[df['tmax_maxmax'].idxmax(), 'station']}, {df.loc[df['tmax_maxmax'].idxmax(), 'mois']} {df.loc[df['tmax_maxmax'].idxmax(), 'annee']}"),
              ("Minimum le plus bas", nombre(df["tmin_minmin"].min(), "°C", 1),
               f"{df.loc[df['tmin_minmin'].idxmin(), 'station']}, {df.loc[df['tmin_minmin'].idxmin(), 'mois']} {df.loc[df['tmin_minmin'].idxmin(), 'annee']}")])
        stations = st.multiselect("Comparer des stations (4 au maximum)", sorted(df["station"].unique()),
                                  default=["Dakar", "Matam", "Saint-Louis", "Ziguinchor"], max_selections=4)
        couleurs = {s: c for s, c in st.session_state.get("couleurs_stations", {}).items() if s in stations}
        for s in stations:
            if s not in couleurs:
                couleurs[s] = [c for c in COULEURS if c not in couleurs.values()][0]
        st.session_state["couleurs_stations"] = couleurs
        df = df.sort_values(["annee", "mois_num"])
        df["date"] = pd.to_datetime(dict(year=df["annee"], month=df["mois_num"], day=1))
        calendrier = pd.date_range(df["date"].min(), df["date"].max(), freq="MS")
        if stations:
            courbes = pd.concat([df[df["station"] == s].set_index("date").reindex(calendrier).assign(station=s)
                                 for s in stations]).rename_axis("date").reset_index()
            for colonne, (cle, var, titre) in zip(st.columns(2), [("c1", "tmax_maxmax", "Température maximale du mois"),
                                                                 ("c2", "tmin_minmin", "Température minimale du mois")]):
                fig = px.line(courbes, x="date", y=var, color="station", markers=True, title=titre,
                              color_discrete_map=couleurs, labels={"date": "", var: "°C", "station": "Station"})
                fig.update_traces(line_width=2, marker_size=8, connectgaps=False, hovertemplate="%{y:.1f} °C")
                fig.update_layout(hovermode="x unified")
                fig.update_xaxes(tickformat="%m/%Y", hoverformat="%m/%Y")
                afficher(colonne, cle, fig, 400)
        c1, c2 = st.columns([3, 2])
        df["periode"] = df["mois"].map(ABREGE) + " " + df["annee"].astype(str)
        carte_chaleur = df.pivot_table(index="station", columns="periode", values="tmax_maxmax", sort=False).sort_index()
        fig = px.imshow(carte_chaleur, aspect="auto", color_continuous_scale=ECHELLE, title="Tmax par station et par mois (°C)",
                        labels={"x": "", "y": "", "color": "°C"})
        fig.update_traces(xgap=2, ygap=2, hovertemplate="%{y}, %{x} : %{z:.1f} °C<extra></extra>")
        fig.update_yaxes(dtick=1, showgrid=False).update_xaxes(showgrid=False)
        afficher(c1, "c3", fig, 620)
        chaudes = df.groupby("station")["tmax_maxmax"].max().nlargest(12).sort_values().reset_index()
        fig = px.scatter(chaudes, x="tmax_maxmax", y="station", text=chaudes["tmax_maxmax"].map(lambda v: nombre(v, decimales=1)),
                         title="Records de chaleur par station (°C)", labels={"tmax_maxmax": "", "station": ""})
        fig.update_traces(marker=dict(size=13, color=COULEURS[1]), textposition="middle right", cliponaxis=False,
                          hovertemplate="%{y} : %{x:.1f} °C<extra></extra>")
        afficher(c2, "c4", fig, 620)

    with st.expander("Voir les données nettoyées"):
        table = df.drop(columns=["date", "periode"], errors="ignore")
        st.dataframe(table, width="stretch")
        st.download_button("Télécharger en CSV", csv_bytes(table), f"{source}_clean.csv", "text/csv",
                           icon=":material/download:", width="stretch")

# option 4 : formulaires
else:
    section("Donnez votre avis", "Le même questionnaire existe en deux versions. Choisissez celle que vous préférez.")
    for colonne, (cle, nom, texte, url) in zip(st.columns(2), [
            ("kobo", "Formulaire Kobo", "Le niveau de satisfaction se calcule pendant la saisie.", KOBO_URL),
            ("google", "Formulaire Google Forms", "Un formulaire en plusieurs étapes, adapté au téléphone.", GOOGLE_FORMS_URL)]):
        with colonne.container(key=f"carte_form_{cle}"):
            carte(cle, nom, texte, "6 sections")
            st.link_button("Ouvrir le formulaire", url, icon=":material/open_in_new:", width="stretch")
