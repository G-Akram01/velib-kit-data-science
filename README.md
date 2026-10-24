# Vélib' Métropole — Kit Data Science (DATA-IA-EXE710)

Projet de groupe · Télécom Paris · Année 2026-2027

**Question :** une station Vélib' sera-t-elle vide dans 30 minutes ?

## Objectif de collecte (48 heures minimum, puis 7 jours souhaités)

- **Toutes les stations** : aucune sélection géographique ni échantillonnage ; on conserve tous les champs bruts renvoyés par `station_status.json` à chaque passage.
- **Toutes les 5 minutes environ**, sans interruption programmée après 48 h (288 passages/jour ; 576 passages théoriques en 48 h).
- **Référentiel complet** `station_information.json` rechargé une fois par jour (localisation, capacité, noms).
- **Données conservées** : `data/raw/YYYY-MM-DD/*.json.gz` et contrôle de complétude/fraîcheur dans `data/quality/YYYY-MM-DD.csv`.
- **Audit** : `python -m src.audit_collection --hours 48` calcule le taux de relevés, le nombre de stations, les trous de collecte, et un indicateur `complete_48h`.
- **Seuil de qualité** : un flux de moins de 1 000 stations ou avec identifiants répétés est refusé. Ce seuil est une alerte prudente, et non une garantie de couverture 100 %. Il est configurable via `VELIB_MIN_STATIONS`.

Le script n'arrête **pas** la collecte à la fin de 48 h : elle continue tant que le workflow reste activé. L'indicateur de validation des 48 h exige 95 % des créneaux théoriques, un intervalle historique de 48 h minimum et aucun trou mesuré au-delà de 15 min. Les retards manquants ne peuvent pas être reconstruits a posteriori depuis ce flux instantané.


Le flux Vélib' publie une photographie de l'état courant, pas un historique. Notre pipeline collecte donc des instantanés JSON GBFS toutes les 5 minutes **environ**, depuis GitHub Actions, avec un horodatage UTC. Chaque exécution enregistre un fichier compressé et conserve la date de remontée du flux source quand elle existe.

## Contenu

- `src/collect_velib.py` : collecte API, retry HTTP, sauvegarde JSON gzip.
- `.github/workflows/collect-velib.yml` : planification et commit automatique.
- `data/raw/YYYY-MM-DD/` : instantanés horodatés et compressés (ne pas supprimer).
- `data/reference/` : caractéristiques des stations, rafraîchies quotidiennement quand la source répond.
- `data/quality/YYYY-MM-DD.csv` : métriques par relevé (nombre de stations, retard des signalements, stations vides...).
- `src/audit_collection.py` : bilan automatique de la fenêtre glissante de 48 heures.
- `notebooks/01_exploration_velib.ipynb` : notebook Colab, qualité, EDA et cible +30 min.
- `tests/` : tests unitaires sans connexion réseau.

## Démarrage

Créer et publier le dépôt avec GitHub CLI :

```bash
cd velib-kit-data-science
git init -b main
git add .
git commit -m "Initialiser le projet Kit Data Science - Velib"
gh repo create velib-kit-data-science --public --source=. --remote=origin --push
```

> Utiliser `--private` si votre groupe souhaite limiter l'accès ; les étapes Colab devront alors être autorisées avec votre compte GitHub.

Sur GitHub, ouvrir **Actions > Collecte Vélib toutes les 5 minutes > Run workflow** pour la première collecte. Vérifier ensuite les fichiers sous `data/raw/`. Le workflow programmé devra figurer sur la branche par défaut `main`. Si le commit échoue avec des droits insuffisants, vérifier les permissions GitHub Actions du dépôt et les règles de la branche.

Localement (optionnel) :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.collect_velib
python -m src.audit_collection --hours 48
```

## Google Colab

Pour un dépôt public, ouvrir :

`https://colab.research.google.com/github/<UTILISATEUR>/velib-kit-data-science/blob/main/notebooks/01_exploration_velib.ipynb`

Dans le notebook, remplacer `GITHUB_OWNER` si nécessaire, puis exécuter les cellules.
Chaque membre peut exécuter le notebook et contribuer au même dépôt via branches/pull requests. Pour partager une version modifiable via Google Drive, dans Colab utiliser **Fichier > Enregistrer une copie dans Drive > Partager** ; attention aux copies divergentes, privilégier GitHub pour les versions officielles.

## Origine des données

- Documentation Vélib' : https://www.velib-metropole.fr/fr/donnees-open-data-gbfs-du-service-velib-metropole
- Station status : `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json`
- Station information : `https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json`

Les variables `is_installed`, `is_renting`, `is_returning` du flux GBFS Vélib sont documentées sous forme de 0/1 ; vérifier la distribution réelle avant conversion. Le schéma peut varier selon les générations GBFS ; le notebook gère plusieurs noms usuels de compteurs de vélos.

## Limites et prudence

- `cron` GitHub Actions accepte un intervalle minimal de 5 minutes mais certaines exécutions peuvent être retardées ou ignorées. Vérifier la couverture temporelle avant toute analyse de séries temporelles.
- La collecte est exécutée **sur les serveurs GitHub** : aucun Mac à garder allumé.
- Les commits fréquents (288/jour théoriques) augmentent la taille du dépôt. Cette approche convient au devoir de quelques jours ; pour plusieurs semaines/mois, migrer l'historique vers un stockage objet ou une base dédiée.
- Un historique court ne permet pas de tirer des conclusions fiables sur les saisons ; la prédiction +30 minutes doit être présentée comme exploration/baseline et ne doit pas être évaluée par découpage aléatoire qui fuit des informations temporelles.
- « Station vide » = `num_bikes_available == 0` parmi les stations en service (`is_renting == 1`), pas simplement une station fermée.
- Mesurer le décalage entre collecte et dernier signalement station (`last_reported`) ; les stations ne sont pas toujours mises à jour simultanément.

## Répartition proposée

- Collecte, contrôle qualité, reproductibilité : groupe 1.
- Préparation, jointure métadonnées, EDA : groupe 2.
- Cible +30 min, baseline, évaluation temporelle, restitution : groupe 3.

## Livrable

Code GitHub + notebook exécutable + graphiques commentés + limites du jeu de données + sources et méthode de collecte. Date de remise annoncée par la fiche du module : **26 octobre 2026 à 18h**.
