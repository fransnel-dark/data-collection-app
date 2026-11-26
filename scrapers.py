import time
import sqlite3
from pathlib import Path

import pandas as pd
from requests import get
from bs4 import BeautifulSoup as bs

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PAUSE = 0.5

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "projet_data_collection.db"

MAX_PAGES = {"books": 50, "gaaraas": 13, "motos": 55}


# page HTML, 3 essais
def get_soup(url, essais=3):
    for _ in range(essais):
        try:
            page_source = get(url, headers=HEADERS, timeout=30)
            if page_source.status_code == 404:
                return None
            if page_source.status_code == 200:
                return bs(page_source.content, "html.parser")
        except Exception:
            pass
        time.sleep(2)
    raise ConnectionError(f"Page inaccessible après {essais} essais : {url}")


NOTES = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


# Books to Scrape
def scrape_books(nb_pages=50, progress=None):
    df = pd.DataFrame()
    for index_page in range(1, nb_pages + 1):
        url = f"https://books.toscrape.com/catalogue/page-{index_page}.html"
        soup_page = get_soup(url)
        if soup_page is None:
            break
        containers = soup_page.find_all("li", "col-xs-6 col-sm-4 col-md-3 col-lg-3")
        data = []
        for container in containers:
            try:
                note = container.find("p", "star-rating")["class"][1]
                url_container = "https://books.toscrape.com/catalogue/" + container.find("a")["href"]
                soup_container = get_soup(url_container)
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
    df = df.copy()
    df["prix"] = df["prix"].str.replace("£", "").str.replace("Â", "").astype(float)
    df["taxe"] = df["taxe"].str.replace("£", "").str.replace("Â", "").astype(float)
    df["nb_produits"] = df["disponibilite"].str.split("(").str[1].str.split(" ").str[0]
    df["nb_produits"] = df["nb_produits"].fillna(0).astype(int)
    df["disponibilite"] = df["disponibilite"].str.split("(").str[0].str.strip()
    df["note"] = df["note"].replace(NOTES).astype(int)
    df["nb_reviews"] = df["nb_reviews"].astype(int)
    df["description"] = df["description"].fillna("").str.strip()
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)
    colonnes = ["titre", "prix", "disponibilite", "nb_produits", "note",
                "nb_reviews", "description", "categorie", "taxe", "url"]
    return df[colonnes]


MARQUES_DEUX_MOTS = ["Land Rover", "Alfa Romeo", "Great Wall", "Aston Martin", "Rolls Royce"]


# Gaaraas
def scrape_gaaraas(nb_pages=13, progress=None):
    df = pd.DataFrame()
    for index_page in range(1, nb_pages + 1):
        url = f"https://www.gaaraas.com/fr/users/dakar-auto?page={index_page}"
        soup_page = get_soup(url)
        if soup_page is None:
            break
        containers = soup_page.find_all("a", "common-ad-card")
        if len(containers) == 0:
            break
        data = []
        for container in containers:
            try:
                prix = container.find("div", "ad-vehicle-price")
                kilometrage = container.find("div", "ad-vehicle-mileage")
                dic = {
                    "titre": container.find("h4").text,
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


def clean_gaaraas(df):
    df = df.copy()
    df["titre"] = df["titre"].str.strip().str.replace("‒", "-").str.replace("–", "-")
    avec_annee = df["titre"].str[:4].str.isnumeric()
    df["annee"] = pd.to_numeric(df["titre"].str[:4], errors="coerce").astype("Int64")
    nom = df["titre"].where(~avec_annee, df["titre"].str[5:])
    df["marque"] = nom.str.split(" ").str[0]
    df["modele"] = nom.str.split(" ", n=1).str[1].fillna("")
    for marque in MARQUES_DEUX_MOTS:
        ligne = nom.str.startswith(marque)
        df.loc[ligne, "marque"] = marque
        df.loc[ligne, "modele"] = nom[ligne].str[len(marque):].str.strip()
    df["prix"] = df["prix"].str.replace("CFA", "").str.replace(" ", "").str.replace("\xa0", "")
    df["prix"] = pd.to_numeric(df["prix"], errors="coerce")
    df["kilometrage"] = df["kilometrage"].str.replace("km", "").str.replace(" ", "").str.replace("\xa0", "")
    df["kilometrage"] = pd.to_numeric(df["kilometrage"], errors="coerce")
    df.loc[df["kilometrage"] == 0, "kilometrage"] = None
    df["boite_vitesse"] = df["boite_vitesse"].str.strip()
    df["region"] = df["region"].str.strip()
    df["carburant"] = df["carburant"].str.split("(").str[1].str.replace(")", "").str.strip()
    df["statut"] = df["statut"].str.strip()
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)
    colonnes = ["marque", "modele", "annee", "prix", "kilometrage", "boite_vitesse",
                "region", "carburant", "statut", "url"]
    return df[colonnes]


# Dakar-Auto motos
def scrape_motos(nb_pages=55, progress=None):
    df = pd.DataFrame()
    for index_page in range(1, nb_pages + 1):
        url = f"https://dakar-auto.com/senegal/motos-and-scooters-3?page={index_page}"
        soup_page = get_soup(url)
        if soup_page is None:
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
                    "titre": container.find("h2", "listing-card__header__title").text,
                    "categorie": categorie.contents[0],
                    "etat": categorie.find("small").text if categorie.find("small") else None,
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
    df = df.copy()
    for col in ["titre", "categorie", "etat", "prix", "quartier", "ville", "kilometrage", "reference", "publication"]:
        df[col] = df[col].str.split().str.join(" ")
    mots = df["titre"].str.split(" ")
    dernier = mots.str[-1]
    df["annee"] = pd.to_numeric(dernier.where(dernier.str.len() == 4), errors="coerce").astype("Int64")
    a_enlever = (dernier == "0") | df["annee"].notna()
    nom = mots.where(~a_enlever, mots.str[:-1]).str.join(" ")
    df["marque"] = nom.str.split(" ").str[0].replace({"Bmw": "BMW"})
    df["modele"] = nom.str.split(" ", n=1).str[1]
    df["prix"] = pd.to_numeric(df["prix"].str.replace("F CFA", "").str.replace(" ", ""), errors="coerce")
    df.loc[df["prix"] < 10000, "prix"] = None
    df["kilometrage"] = pd.to_numeric(df["kilometrage"].str.replace("km", "").str.replace(" ", ""), errors="coerce")
    df.loc[(df["etat"] == "Occasion") & (df["kilometrage"] <= 10), "kilometrage"] = None
    df["kilometrage"] = df["kilometrage"].astype("Int64")
    df["reference"] = df["reference"].str.replace("Ref.", "").str.strip()
    df["quartier"] = df["quartier"].str.rstrip(",")
    df["publication"] = df["publication"].str.replace("Passée, ", "")
    df = df.drop_duplicates(subset=["reference"]).reset_index(drop=True)
    colonnes = ["marque", "modele", "annee", "categorie", "etat", "prix", "kilometrage",
                "quartier", "ville", "reference", "publication", "url"]
    return df[colonnes]


# Bulletins PDF
COLONNES_BULLETINS = ["station", "tmax_maxmax", "tmax_minmax", "tmin_maxmin", "tmin_minmin"]
MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
        "aout", "septembre", "octobre", "novembre", "decembre"]
NOMS_STATIONS = {
    "Cap": "Cap Skirring", "Tamba": "Tambacounda", "Kedougou": "Kédougou",
    "Linguere": "Linguère", "Ranerou": "Ranérou", "Stlouis": "Saint-Louis",
    "Saint Louis": "Saint-Louis", "Thies": "Thiès", "Nioro": "Nioro du Rip",
}


def extract_bulletins(dossier=DATA_DIR / "bulletins"):
    import pdfplumber

    df = pd.DataFrame()
    fichiers = sorted(Path(dossier).glob("*/*.pdf"))
    for fichier in fichiers:
        with pdfplumber.open(fichier) as pdf:
            page = pdf.pages[7]
            table = page.extract_tables()[0]
        DF = pd.DataFrame(table[2:], columns=COLONNES_BULLETINS)
        DF["annee"] = int(fichier.parent.name)
        DF["mois"] = fichier.stem.replace("climato_", "")
        df = pd.concat([df, DF], axis=0).reset_index(drop=True)
    return df


def clean_bulletins(df):
    df = df.copy()
    df["station"] = df["station"].str.strip().replace(NOMS_STATIONS)
    temperatures = COLONNES_BULLETINS[1:]
    for col in temperatures:
        df[col] = pd.to_numeric(df[col].str.replace(",", "."), errors="coerce")
    aberrant = (df["tmax_minmax"] < df["tmin_minmin"]) | (df["tmax_minmax"] > df["tmax_maxmax"])
    df.loc[aberrant, "tmax_minmax"] = None
    df.loc[df["tmin_maxmin"] > 35, "tmin_maxmin"] = None
    manquait = df[temperatures].isna()
    for col in temperatures:
        for station in df["station"].unique():
            ligne = df["station"] == station
            if df.loc[ligne, col].count() >= 6:
                df.loc[ligne, col] = df.loc[ligne, col].fillna(df.loc[ligne, col].median())
    df["valeur_imputee"] = (manquait & df[temperatures].notna()).any(axis=1).astype(int)
    df["mois_num"] = df["mois"].apply(lambda m: MOIS.index(m) + 1)
    df = df.sort_values(["annee", "mois_num", "station"]).reset_index(drop=True)
    return df[["annee", "mois", "mois_num", "station"] + temperatures + ["valeur_imputee"]]


# base SQLite
TABLES = {"books": "books", "gaaraas": "gaaraas_voitures",
          "motos": "dakar_auto_motos", "bulletins": "bulletins_climato"}


def save_to_db(df, table, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()


def add_to_db(df, table, cle="url", db_path=DB_PATH):
    try:
        existant = load_from_db(table, db_path)
    except Exception:
        existant = pd.DataFrame()
    total = pd.concat([df, existant], axis=0).drop_duplicates(subset=[cle], keep="first").reset_index(drop=True)
    save_to_db(total, table, db_path)
    return len(total) - len(existant)


def load_from_db(table, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df
