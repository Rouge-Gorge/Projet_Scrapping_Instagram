import os
from dotenv import load_dotenv

# Charge les variables d'environnement depuis un fichier .env
load_dotenv("variables.env")

# Variables sensibles (à mettre dans variables.env)
API_KEY = os.getenv("API_KEY")
NUM_POSTS = int(os.getenv("NUM_POSTS", 10))
NB_AMBASSADEURS = int(os.getenv("NB_AMBASSADEURS", 5))
INSTAGRAM_USER = os.getenv("INSTAGRAM_USER", "lacoste") #lacoste par défaut

print(f"API_KEY = {API_KEY}")
print(f"NUM_POSTS = {NUM_POSTS}")
print(f"NB_AMBASSADEURS = {NB_AMBASSADEURS}")
print(f"INSTAGRAM_USER = {INSTAGRAM_USER}")
