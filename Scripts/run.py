from pathlib import Path
from loguru import logger as log
import asyncio
import json
import instagram
from datetime import datetime
import openpyxl
import pandas as pd
import os

# Patch temporaire d'un bug qui existe en python 3.12 qui marque dans le terminal : Exception ignored in: <function _DeleteDummyThreadOnDel.__del__>
import threading
threading._DummyThread.__del__ = lambda self: None

# Le chemin du fichier où vont finir les résultats
output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

# Le chemin du fichier où vont finir les posts
output_posts = Path(__file__).parent / "posts_folder"
output_posts.mkdir(exist_ok=True)


async def run():

    # Enable Scrapfly cache and debug mode
    instagram.BASE_CONFIG["cache"] = True
    instagram.BASE_CONFIG["debug"] = True

    log.info(f"Scrapping Instagram des {NUM_POSTS} derniers posts de {INSTAGRAM_USER} et enregistrement des résultats dans le dossier ./results")

    # Scrape user posts, limited to NUM_POSTS posts
    # On scrappe un compte précis pour récupérer les infos des x derniers posts
    posts_all = []
    async for post in instagram.scrape_user_posts(INSTAGRAM_USER, page_size = 1, max_pages = NUM_POSTS):
        posts_all.append(post)
    log.success(f"Checkpoint : Bien réussi à scrapper {len(posts_all)} posts")
    output.joinpath(f"{INSTAGRAM_USER}_all-user-posts.json").write_text(json.dumps(posts_all, indent=2, ensure_ascii=False), encoding='utf-8')
    log.success(f"Checkpoint : Le fichier {INSTAGRAM_USER}_all-user-posts.json a bien été écrit")

    # Chargement et extraction des shortcodes
    log.success(f"Checkpoint : On va extraire les shortcodes des posts scrappés")
    posts_data = instagram.load_posts_json(INSTAGRAM_USER, output)
    shortcodes = instagram.extract_shortcodes(posts_data)
    log.success(f"Checkpoint : J'ai bien récupéré {len(shortcodes)} shortcodes")

    # Scraping des commentaires par shortcode
    log.success(f"Checkpoint : On va extraire les commentaires des posts")
    all_comments = []
    for shortcode in shortcodes:
        log.success(f"Checkpoint : On va scrapper les commentaires du shortcode {shortcode}")
        comments = await instagram.scrape_post(f"https://www.instagram.com/p/{shortcode}/")
        output_posts.joinpath(f"post_{shortcode}.json").write_text(json.dumps(comments, indent=2, ensure_ascii=False), encoding='utf-8')
        log.success(f"Checkpoint : Les commentaires du shortcode {shortcode} ont bien été scrappés et écrits dans post_{shortcode}.json")
        all_comments.append(comments)
    log.success(f"Checkpoint : Bien réussi à scrapper {len(all_comments)} posts")

    # Sauvegarde avant flatten
    output_posts.joinpath(f"{INSTAGRAM_USER}_{NUM_POSTS}_last_posts_BRUT.json").write_text(json.dumps(all_comments, indent=2, ensure_ascii=False), encoding='utf-8')
    log.success(f"Checkpoint : Le fichier {INSTAGRAM_USER}_{NUM_POSTS}_last_posts_BRUT.json a bien été écrit")

    # Flatten les commentaires (ça a sorti une erreur mais bien fonctionné quand même !)
    log.success(f"Checkpoint : Aplatir les commentaires des posts scrappés")
    flattened_all_comments = instagram.flatten_comments(all_comments)

    # Export des commentaires à plats
    output_posts.joinpath(f"{INSTAGRAM_USER}_{NUM_POSTS}_last_posts.json").write_text(json.dumps(flattened_all_comments, indent=2, ensure_ascii=False), encoding='utf-8')
    log.success(f"Checkpoint : Le fichier {INSTAGRAM_USER}_{NUM_POSTS}_last_posts.json a bien été écrit")



     # Convertir en DataFrame Pandas
    df = pd.json_normalize(flattened_all_comments)

    # Afficher les 5 premières lignes du DataFrame, vérif
    print(df.head())


    # Trouver les ambassadeurs du compte ! (les comptes qui ont commentés le plus de posts différents)
    # On vérifie que df contient bien ces colonnes : 'comment_owner', 'shortcode', 'comment_likes'
    # 1. Nombre de posts différents commentés par chaque compte
    posts_commented = df.groupby('comment_owner')['shortcode'].nunique().reset_index()
    posts_commented.rename(columns={'shortcode': 'nb_posts_commented'}, inplace=True)

    # 2. Nombre total de commentaires de chaque compte
    total_comments = df.groupby('comment_owner').size().reset_index(name='nb_comments')

    # 3. Nombre total de likes reçus sur leurs commentaires
    total_likes = df.groupby('comment_owner')['comment_likes'].sum().reset_index()

    # 4. Merge des 3 résultats
    summary = posts_commented.merge(total_comments, on='comment_owner') \
                            .merge(total_likes, on='comment_owner')

    # 5. Trier par nombre de posts différents commentés (top contributeurs en reach)
    top_n_ambassadeurs = summary.sort_values(by='nb_posts_commented', ascending=False).head(NB_AMBASSADEURS)

    print(top_n_ambassadeurs)


    # Export des résulats

    # Ajoute la date au format YYYYMMDD
    date_str = datetime.now().strftime("%Y%m%d")

    # Prépare le chemin du dossier d'export
    base_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(base_dir, "results_ambassadeur")
    os.makedirs(results_dir, exist_ok=True)

    # Prépare les noms de fichiers avec la date
    top_n_ambassadeurs_file = os.path.join(results_dir, f"top{NB_AMBASSADEURS}_ambassadeurs_{date_str}.xlsx")
    summary_file = os.path.join(results_dir, f"ambassadeurs_summary_complet_{date_str}.xlsx")

    # Trie et exporte si les DataFrames ne sont pas vides
    summary_sorted = summary.sort_values(by="nb_posts_commented", ascending=False)

    if not top_n_ambassadeurs.empty:
        top_n_ambassadeurs.to_excel(top_n_ambassadeurs_file, index=False, sheet_name=f"Top {NB_AMBASSADEURS}")
        print(f"✅ Top {NB_AMBASSADEURS} exporté : {top_n_ambassadeurs_file}")
    else:
        print(f"⚠️ Le DataFrame top{NB_AMBASSADEURS} est vide, aucun export effectué pour le Top {NB_AMBASSADEURS}.")

    if not summary_sorted.empty:
        summary_sorted.to_excel(summary_file, index=False, sheet_name="Summary")
        print(f"✅ Résumé complet exporté : {summary_file}")
    else:
        print("⚠️ Le DataFrame summary est vide, aucun export effectué pour le résumé.")

if __name__ == "__main__":
    asyncio.run(run())
