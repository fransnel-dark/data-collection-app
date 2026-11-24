# My Data Collection App

Collecte, nettoyage, stockage et visualisation de **4 sources de données**, avec une application Streamlit.

| # | Source | Méthode | Volume |
|---|---|---|---|
| 1 | [Books to Scrape](https://books.toscrape.com/) | requests + BeautifulSoup (page liste + page détail) | 50 pages, 1 000 livres |
| 2 | [Gaaraas (Dakar auto)](https://www.gaaraas.com/fr/users/dakar-auto) | requests + BeautifulSoup | 13 pages, 245 voitures |
| 3 | [Dakar-Auto (motos et scooters)](https://dakar-auto.com/senegal/motos-and-scooters-3) | requests + BeautifulSoup | 55 pages, 1 089 annonces (1 078 sans doublons) |
| 4 | Bulletins climatologiques 2020-2021 (PDF) | pdfplumber | 11 bulletins, 258 lignes |

## Liens

- Application : https://data-collection-app-jean-fransnel-ebata-djounde.streamlit.app/
- Vidéo : _à compléter_

## Fonctionnalités de l'application

1. **Scraper des données** sur le nombre de pages choisi, pour chaque source web. Les données sont nettoyées automatiquement, téléchargeables et peuvent être enregistrées dans la base SQLite.
2. **Télécharger les données brutes** : exports non nettoyés de l'extension Web Scraper (no-code) et données extraites des bulletins PDF, filtrables par année et par mois.
3. **Dashboard** des données nettoyées, une source à la fois.
4. **Évaluer l'application** : formulaires Kobo et Google Forms.

## Organisation du dépôt

```
Projet_Data_Collection.ipynb   notebook : collecte + nettoyage + stockage des 4 sources
app.py                         application Streamlit
style.css                      design de l'application
scrapers.py                    fonctions de scraping / nettoyage / base de données (utilisées par l'appli)
data/
  bulletins/2020, 2021/        bulletins PDF
  raw/                         données brutes Web Scraper (no-code)
  clean/                       données nettoyées (CSV)
  projet_data_collection.db    base SQLite : books, gaaraas_voitures, dakar_auto_motos, bulletins_climato
forms/                         formulaire Kobo (XLSForm) + script Google Forms
webscraper_sitemaps/           sitemaps de l'extension Web Scraper
```

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Remarques sur les données

- **Gaaraas** : le sujet parle de 100 pages, mais l'annonceur n'a que 13 pages d'annonces. Le scraper s'arrête à la première page vide.
- **Dakar-Auto** : le site renvoie une erreur 404 après la page 55. Le nom et le téléphone des vendeurs ne sont pas collectés (données personnelles).
- **Bulletins** : les noms de stations sont harmonisés (Thies → Thiès, Stlouis → Saint-Louis…). Les « NP » (Non Parvenu) et 3 valeurs aberrantes (Bambey 01/2020, Koungheul 02/2020, Fatick 01/2021) sont remplacés par la médiane de la station si elle a au moins 6 mesures ; sinon ils restent vides (Tmax de Goudiry, Tmin de Kédougou). La colonne `valeur_imputee` signale les 7 lignes concernées.
