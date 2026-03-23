# Suivi de cave V2

Version V2 de l'application web partagée de suivi de cave.

## Fonctions incluses
- dashboard métier
- plan de cave par zones
- ordre des zones et des cuves conforme au fichier Excel
- lots éditables
- mouvements complets
- entrée raisin avec :
  - poids du raisin
  - lecture brute du mustimètre
  - température
  - calcul de la M.V. corrigée
  - sucres g/L
  - TAV probable
  - rendement en L / kg
  - rendement en %
- calendrier en vue mensuelle avec filtres
- historique
- alertes
- remise à zéro par cuve
- logique automatique :
  - cuve inox + lot blanc vidé → à nettoyer
  - cuve inox + lot rosé ou rouge vidé → à dérougir
  - blocage uniquement sur le statut à dérougir

## Utilisateurs initiaux
- pierre / Pierre2026!
- jean-michel / JeanMichel2026!
- sylvain / Sylvain2026!

## Cuverie importée
- source : `Cuverie  (2).xlsx`
- nombre total de contenants : 110
- capacité totale : 6908.25 hL

### Répartition par zone
- A: 12 contenants, 1082.00 hL
- BETON: 15 contenants, 888.00 hL
- C: 15 contenants, 1183.00 hL
- CHAI A BARRIQUES: 25 contenants, 56.25 hL
- CHAPEAU FLOTTANT: 9 contenants, 180.00 hL
- EXTERIEUR: 5 contenants, 1250.00 hL
- FOUDRE: 10 contenants, 615.00 hL
- GARDE VIN BLEU: 2 contenants, 6.00 hL
- LIES: 4 contenants, 120.00 hL
- OEUFS BETON: 4 contenants, 27.00 hL
- S: 9 contenants, 1501.00 hL

## Lancer en local
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Puis ouvrir `http://localhost:8000`

## Déploiement Render
Le fichier `render.yaml` crée :
- un web service Python
- une base PostgreSQL Render
- les variables d'environnement nécessaires

Étapes :
1. pousser ce dossier dans un dépôt GitHub
2. dans Render, choisir **New + > Blueprint**
3. connecter le dépôt et valider le `render.yaml`
4. attendre le premier déploiement

## Remarques
- Les matériaux des cuves sont utilisés en logique interne mais ne sont pas affichés dans l'interface.
- Si une base existante doit être mise à jour, il est souvent plus simple de repartir d'une base propre après changement du seed ou du schéma.
