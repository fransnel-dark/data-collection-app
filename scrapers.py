"""
scrapers.py — Collecte et nettoyage des 4 sources du projet Data Collection.

Sources :
    1. Books to Scrape        (BeautifulSoup, page liste + page détail de chaque livre)
    2. Gaaraas - Dakar auto   (BeautifulSoup, annonces voitures)
    3. Dakar-Auto motos       (BeautifulSoup, annonces motos & scooters)
    4. Bulletins climato PDF  (pdfplumber, tableau des températures par station)

Le code suit la méthode du cours :
    get(url) -> BeautifulSoup -> containers -> boucle + try/except -> dict -> DataFrame -> concat
Les fonctions `scrape_*` renvoient les données BRUTES (texte tel qu'affiché sur le site),
les fonctions `clean_*` renvoient les données NETTOYÉES (types numériques, colonnes séparées...).
"""

import re
import time
import sqlite3
from pathlib import Path

import pandas as pd
from requests import Session
from bs4 import BeautifulSoup as bs

# En-tête HTTP envoyé avec chaque requête (certains sites refusent les requêtes sans navigateur)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
# Une session réutilise la même connexion : c'est plus rapide pour les 1 000 pages de livres
session = Session()
# Pause entre deux pages, pour ne pas surcharger les sites
PAUSE = 0.5

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "projet_data_collection.db"

# Nombre maximum de pages disponibles sur chaque site (vérifié le 23/11/2026)
MAX_PAGES = {"books": 50, "gaaraas": 13, "motos": 55}


def get_soup(url, essais=3):
    """Récupère le code source d'une page et le renvoie sous forme d'objet BeautifulSoup.
    En cas de coupure réseau, on réessaie jusqu'à 3 fois."""
    for _ in range(essais):
        try:
            page_source = session.get(url, headers=HEADERS, timeout=30)
            if page_source.status_code == 404:  # page inexistante (ex : après la dernière page)
                return None
            if page_source.status_code == 200:
                return bs(page_source.content, "html.parser")
        except Exception:
            pass
        time.sleep(2)
    # on préfère une erreur visible à des données incomplètes
    raise ConnectionError(f"Page inaccessible après {essais} essais : {url}")


# =====================================================================================
# 1. BOOKS TO SCRAPE
# =====================================================================================
NOTES = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def scrape_books(nb_pages=50, progress=None):
    """Scrape les livres des pages 1 à nb_pages (20 livres par page).
    Pour chaque livre, on ouvre sa page détail pour la description, la catégorie, la taxe, etc."""
    df = pd.DataFrame()
    for index_page in range(1, nb_pages + 1):
        url = f"https://books.toscrape.com/catalogue/page-{index_page}.html"
        soup_page = get_soup(url)
        if soup_page is None:
            break
        # récupération des conteneurs (un conteneur = un livre)
        containers = soup_page.find_all("li", "col-xs-6 col-sm-4 col-md-3 col-lg-3")
        data = []
        for container in containers:
            try:
                # note du produit : elle est dans la classe CSS, ex "star-rating Three"
                note = container.find("p", "star-rating")["class"][1]
                # page détail du livre
                url_container = "https://books.toscrape.com/catalogue/" + container.find("a")["href"]
                soup_container = get_soup(url_container)
                # tableau "Product Information" -> dictionnaire {UPC: ..., Tax: ..., ...}
                infos = {row.th.text: row.td.text for row in soup_container.find("table").find_all("tr")}
                description = soup_container.find("div", id="product_description")
                dic = {
                    "titre": soup_container.find("h1").text,
                    "prix": soup_container.find("p", "price_color").text,
                    "disponibilite": infos.get("Availability"),
                    "note": note,
                    "nb_reviews": infos.get("Number of reviews"),
                    "description": description.find_next_sibling("p").text if description else None,
                    "categorie": soup_container.find("ul", "breadcrumb").find_all("li")[2].text.strip(),
                    "taxe": infos.get("Tax"),
                    "url": url_container,
                }
                data.append(dic)
            except Exception as erreur:
                print("élément ignoré :", url, erreur)
        DF = pd.DataFrame(data)
        df = pd.concat([df, DF], axis=0).reset_index(drop=True)
        if progress:
            progress(index_page, nb_pages)
    return df


def clean_books(df):
    """Nettoyage : prix et taxe en nombres, disponibilité découpée en statut + nombre de produits."""
    df = df.copy()
    df["prix"] = df["prix"].str.replace("£", "").str.replace("Â", "").astype(float)
    df["taxe"] = df["taxe"].str.replace("£", "").str.replace("Â", "").astype(float)
    # "In stock (22 available)" -> statut "In stock" / nombre de produits 22
    df["nb_produits"] = df["disponibilite"].str.extract(r"(\d+)").astype(float).fillna(0).astype(int)
    df["disponibilite"] = df["disponibilite"].str.replace(r"\s*\(.*\)", "", regex=True).str.strip()
    df["note"] = df["note"].map(NOTES).astype("Int64")
    df["nb_reviews"] = pd.to_numeric(df["nb_reviews"], errors="coerce").astype("Int64")
    df["description"] = df["description"].fillna("").str.strip()
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)
    colonnes = ["titre", "prix", "disponibilite", "nb_produits", "note",
                "nb_reviews", "description", "categorie", "taxe", "url"]
    return df[colonnes]


# =====================================================================================
# 2. GAARAAS - DAKAR AUTO (voitures)
# =====================================================================================
# Marques composées de deux mots : le premier mot seul ne suffit pas
MARQUES_DEUX_MOTS = ["Land Rover", "Alfa Romeo", "Great Wall", "Aston Martin", "Rolls Royce"]


def scrape_gaaraas(nb_pages=13, progress=None):
    """Scrape les annonces de l'annonceur 'Dakar auto' sur gaaraas.com."""
    df = pd.DataFrame()
    for index_page in range(1, nb_pages + 1):
        url = f"https://www.gaaraas.com/fr/users/dakar-auto?page={index_page}"
        soup_page = get_soup(url)
        if soup_page is None:
            break
        containers = soup_page.find_all("a", "common-ad-card")
        if len(containers) == 0:  # plus d'annonces : on a dépassé la dernière page
            break
        data = []
        for container in containers:
            try:
                # certaines annonces n'ont pas de prix ("Négociable") ou pas de kilométrage
                prix = container.find("div", "ad-vehicle-price")
                kilometrage = container.find("div", "ad-vehicle-mileage")
                dic = {
                    "titre": container.find("h4").text,                     # ex "2010 Dacia Sandero"
                    "prix": prix.find("div", "value").text if prix else None,
                    "kilometrage": kilometrage.find("div", "value").text if kilometrage else None,
                    "boite_vitesse": container.find("div", "transmission").text,
                    "region": container.find("div", "location").text,
                    "carburant": container.find("div", "engine-capacity").text,
                    "statut": container.find("div", "ribbon").text if container.find("div", "ribbon") else "Disponible",
                    "url": "https://www.gaaraas.com" + container["href"],
                }
                data.append(dic)
            except Exception as erreur:
                print("élément ignoré :", url, erreur)
        DF = pd.DataFrame(data)
        df = pd.concat([df, DF], axis=0).reset_index(drop=True)
        if progress:
            progress(index_page, nb_pages)
        time.sleep(PAUSE)
    return df


def separer_marque_modele(nom):
    """'Dacia Sandero' -> ('Dacia', 'Sandero') ; 'Land Rover Discovery' -> ('Land Rover', 'Discovery')."""
    for marque in MARQUES_DEUX_MOTS:
        if nom.lower().startswith(marque.lower()):
            return marque, nom[len(marque):].strip()
    morceaux = nom.split(" ", 1)
    return morceaux[0], (morceaux[1] if len(morceaux) > 1 else "")


def clean_gaaraas(df):
    """Nettoyage : séparation année / marque / modèle, prix et kilométrage en nombres."""
    df = df.copy()
    # le site utilise parfois un tiret spécial "‒" (Mercedes‒Benz) : on le remplace par "-"
    df["titre"] = df["titre"].str.strip().str.replace("‒", "-").str.replace("–", "-")
    df["annee"] = df["titre"].str.extract(r"^(\d{4})").astype(float).astype("Int64")
    nom = df["titre"].str.replace(r"^\d{4}\s+", "", regex=True)
    df["marque"] = nom.apply(lambda x: separer_marque_modele(x)[0])
    df["modele"] = nom.apply(lambda x: separer_marque_modele(x)[1])
    df["prix"] = pd.to_numeric(df["prix"].str.replace(r"\D", "", regex=True), errors="coerce")
    df["kilometrage"] = pd.to_numeric(df["kilometrage"].str.replace(r"\D", "", regex=True), errors="coerce")
    df.loc[df["kilometrage"] == 0, "kilometrage"] = float("nan")  # 0 km sur une occasion = non renseigné
    df["boite_vitesse"] = df["boite_vitesse"].str.strip()
    df["region"] = df["region"].str.strip()
    # "N/A (Essence)" -> "Essence"
    df["carburant"] = df["carburant"].str.extract(r"\((.*?)\)")[0].str.strip()
    df["statut"] = df["statut"].str.strip()
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)
    colonnes = ["marque", "modele", "annee", "prix", "kilometrage", "boite_vitesse",
                "region", "carburant", "statut", "url"]
    return df[colonnes]


# =====================================================================================
# 3. DAKAR-AUTO - MOTOS & SCOOTERS
# =====================================================================================
def scrape_motos(nb_pages=55, progress=None):
    """Scrape les annonces motos & scooters de dakar-auto.com.
    Le nom et le téléphone du vendeur ne sont volontairement PAS collectés (données personnelles)."""
    df = pd.DataFrame()
    for index_page in range(1, nb_pages + 1):
        url = f"https://dakar-auto.com/senegal/motos-and-scooters-3?page={index_page}"
        soup_page = get_soup(url)
        if soup_page is None:  # le site renvoie une erreur 404 après la dernière page
            break
        containers = soup_page.find_all("div", "listing-card")
        if len(containers) == 0:
            break
        data = []
        for container in containers:
            try:
                categorie = container.find("h4", "listing-card__header__category")
                attributs = [li.text.strip() for li in container.find_all("li", "listing-card__attribute")]
                kilometrage = [a for a in attributs if a.endswith("km")]
                dic = {
                    "titre": container.find("h2", "listing-card__header__title").text,   # ex "Honda X-ADV 2024"
                    "categorie": categorie.contents[0],                                    # Motos / Scooters
                    "etat": categorie.find("small").text if categorie.find("small") else None,  # Occasion / Neuf
                    "prix": container.find("h3", "listing-card__header__price").text,
                    "quartier": container.find("span", "town-suburb").text if container.find("span", "town-suburb") else None,
                    "ville": container.find("span", "province").text,
                    "kilometrage": kilometrage[0] if kilometrage else None,
                    "reference": attributs[0] if attributs else None,
                    "publication": container.find("p", "time").text,
                    "url": "https://dakar-auto.com" + container.find("h2").find("a")["href"],
                }
                data.append(dic)
            except Exception as erreur:
                print("élément ignoré :", url, erreur)
        DF = pd.DataFrame(data)
        df = pd.concat([df, DF], axis=0).reset_index(drop=True)
        if progress:
            progress(index_page, nb_pages)
        time.sleep(PAUSE)
    return df


def clean_motos(df):
    """Nettoyage : séparation marque / modèle / année, prix et kilométrage en nombres."""
    df = df.copy()
    for col in ["titre", "categorie", "etat", "prix", "quartier", "ville", "kilometrage", "reference", "publication"]:
        df[col] = df[col].astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    # l'année est le dernier mot du titre ; quand elle est inconnue, le site affiche "0"
    df["annee"] = df["titre"].str.extract(r"\s(\d{4})$")[0].astype(float).astype("Int64")
    nom = df["titre"].str.replace(r"\s+(\d{4}|0)$", "", regex=True)
    df["marque"] = nom.str.split(" ").str[0]
    # même marque écrite différemment (BMW / Bmw) -> on garde l'écriture la plus fréquente
    df["marque"] = df.groupby(df["marque"].str.lower())["marque"].transform(lambda x: x.mode()[0])
    df["modele"] = nom.str.split(" ", n=1).str[1]
    df["prix"] = pd.to_numeric(df["prix"].str.replace(r"\D", "", regex=True), errors="coerce")
    # prix symboliques (ex : 450 F CFA) = prix non renseigné par le vendeur
    df.loc[df["prix"] < 10000, "prix"] = pd.NA
    df["kilometrage"] = pd.to_numeric(df["kilometrage"].str.replace(r"\D", "", regex=True), errors="coerce")
    # 0 à 10 km sur une moto d'occasion = kilométrage non renseigné
    df.loc[(df["etat"] == "Occasion") & (df["kilometrage"] <= 10), "kilometrage"] = pd.NA
    df["reference"] = df["reference"].str.replace(r"\D", "", regex=True)
    df["quartier"] = df["quartier"].str.rstrip(",")
    df["publication"] = df["publication"].str.replace("Passée, ", "", regex=False)
    df = df.drop_duplicates(subset=["reference"]).reset_index(drop=True)
    colonnes = ["marque", "modele", "annee", "categorie", "etat", "prix", "kilometrage",
                "quartier", "ville", "reference", "publication", "url"]
    return df[colonnes]


# =====================================================================================
# 4. BULLETINS CLIMATOLOGIQUES (PDF)
# =====================================================================================
COLONNES_BULLETINS = ["station", "tmax_maxmax", "tmax_minmax", "tmin_maxmin", "tmin_minmin"]
MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]
# Un même lieu est écrit différemment selon les bulletins : on harmonise
NOMS_STATIONS = {
    "Cap": "Cap Skirring", "Tamba": "Tambacounda", "Kedougou": "Kédougou",
    "Linguere": "Linguère", "Ranerou": "Ranérou", "Stlouis": "Saint-Louis",
    "Saint Louis": "Saint-Louis", "Thies": "Thiès", "Nioro": "Nioro du Rip",
}


def extract_bulletins(dossier=DATA_DIR / "bulletins"):
    """Extrait le tableau des températures (page 8 de chaque bulletin) avec pdfplumber.
    Ajoute les variables 'annee' (nom du dossier) et 'mois' (nom du fichier)."""
    import pdfplumber

    df = pd.DataFrame()
    fichiers = sorted(Path(dossier).glob("*/*.pdf"))
    for fichier in fichiers:
        with pdfplumber.open(fichier) as pdf:
            page = pdf.pages[7]               # le tableau des températures est en page 8
            table = page.extract_tables()[0]
        DF = pd.DataFrame(table[2:], columns=COLONNES_BULLETINS)  # 2 lignes d'en-tête ignorées
        DF["annee"] = int(fichier.parent.name)                    # ex dossier "2020"
        DF["mois"] = fichier.stem.replace("climato_", "")         # ex "climato_janvier" -> "janvier"
        df = pd.concat([df, DF], axis=0).reset_index(drop=True)
    return df


def clean_bulletins(df):
    """Nettoyage : virgule -> point, conversion en nombres, noms de stations harmonisés,
    valeurs manquantes ("NP" = Non Parvenu) ou aberrantes remplacées par la médiane de la station,
    seulement si la station a au moins 6 mesures ; sinon la valeur reste manquante."""
    df = df.copy()
    df["station"] = df["station"].str.strip().replace(NOMS_STATIONS)
    temperatures = COLONNES_BULLETINS[1:]
    for col in temperatures:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".").str.strip(), errors="coerce")
    # Valeurs aberrantes : une Tmax ne peut pas être plus basse que la Tmin la plus basse du mois
    # (Bambey 01/2020 : 2.9 °C, Koungheul 02/2020 : 10 °C), et une Tmin ne dépasse pas 35 °C (Fatick 01/2021 : 38.5 °C)
    aberrant = (df["tmax_minmax"] < df["tmin_minmin"]) | (df["tmax_minmax"] > df["tmax_maxmax"])
    df.loc[aberrant, "tmax_minmax"] = float("nan")
    df.loc[df["tmin_maxmin"] > 35, "tmin_maxmin"] = float("nan")
    # valeurs manquantes -> médiane de la station, si elle a au moins 6 mesures sur 11 bulletins
    manquait = df[temperatures].isna()
    for col in temperatures:
        groupe = df.groupby("station")[col]
        mediane = groupe.transform("median").where(groupe.transform("count") >= 6)
        df[col] = df[col].fillna(mediane)
    # valeur_imputee = 1 si au moins une température de la ligne a été remplacée par la médiane
    df["valeur_imputee"] = (manquait & df[temperatures].notna()).any(axis=1).astype(int)
    df["mois_num"] = df["mois"].apply(lambda m: MOIS.index(m) + 1)
    df = df.sort_values(["annee", "mois_num", "station"]).reset_index(drop=True)
    return df[["annee", "mois", "mois_num", "station"] + temperatures + ["valeur_imputee"]]


# =====================================================================================
# BASE DE DONNÉES SQLITE
# =====================================================================================
TABLES = {"books": "books", "gaaraas": "gaaraas_voitures",
          "motos": "dakar_auto_motos", "bulletins": "bulletins_climato"}


def save_to_db(df, table, db_path=DB_PATH):
    """Enregistre un DataFrame dans une table de la base SQLite (la table est remplacée)."""
    conn = sqlite3.connect(db_path)
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()


def add_to_db(df, table, cle="url", db_path=DB_PATH):
    """Ajoute de nouvelles lignes à une table sans créer de doublons (la clé identifie une annonce / un livre).
    Les données déjà présentes sont conservées ; une annonce déjà connue est mise à jour."""
    try:
        existant = load_from_db(table, db_path)
    except Exception:
        existant = pd.DataFrame()
    total = pd.concat([df, existant], axis=0).drop_duplicates(subset=[cle], keep="first").reset_index(drop=True)
    save_to_db(total, table, db_path)
    return len(total) - len(existant)  # nombre de nouvelles lignes


def load_from_db(table, db_path=DB_PATH):
    """Lit une table de la base SQLite dans un DataFrame."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df
