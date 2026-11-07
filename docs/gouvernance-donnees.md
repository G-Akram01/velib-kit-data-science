# Gouvernance et dictionnaire des données

**Projet :** Vélib’ Métropole — Kit Data Science · **version :** 7 novembre 2026  
**Périmètre analytique figé :** 25–30 octobre 2026, heure de Paris. Cette note décrit les données réellement utilisées par le notebook principal et les règles nécessaires à leur réutilisation.

## 1. Responsabilité, provenance et droits

Les données proviennent des flux publics GBFS `station_status.json` et `station_information.json` de Vélib’ Métropole, publiés par Smovengo/Syndicat Autolib’ Vélib’ Métropole. La [documentation de l’éditeur](https://www.velib-metropole.fr/fr/donnees-open-data-gbfs-du-service-velib-metropole) décrit les flux ; le [catalogue de Paris Data](https://opendata.paris.fr/explore/dataset/velib-disponibilite-en-temps-reel/information/) identifie le producteur et affiche la licence ODbL pour son jeu de données de disponibilité. Cette mention de licence concerne la fiche Paris Data ; avant toute réutilisation commerciale ou redistribution indépendante de l’API GBFS, vérifier les conditions applicables au flux source. Toute publication issue de ce dépôt doit conserver l’attribution « données Vélib’ Métropole / Smovengo / Syndicat Autolib’ Vélib’ Métropole », un lien vers la source et la date de consultation.

Le groupe est responsable des copies, transformations, analyses et conclusions de ce dépôt. Les fichiers ne contiennent pas de trajets individuels ni d’identifiant d’usager : ils décrivent des stations et des comptes agrégés. Les noms et coordonnées des stations sont publics. Ne pas enrichir ces données avec des traces individuelles dans ce dépôt sans nouvelle revue de gouvernance.

## 2. Inventaire et traçabilité

| Actif | Contenu et granularité | Chemin | Origine et horodatage |
| --- | --- | --- | --- |
| Statut brut | Une ligne par station dans chaque photographie du réseau | `data/raw/YYYY-MM-DD/*.json.gz` | URL source et `collected_at_utc` dans chaque fichier ; `source_last_updated` si fourni |
| Référentiel | Nom, coordonnées, capacité et code de station ; une copie par jour disponible | `data/reference/station_information_YYYY-MM-DD.json.gz` | URL source et `collected_at_utc` dans le fichier |
| Contrôle par passage | Nombre de stations, doublons, âge de `last_reported`, stations ouvertes sans vélo | `data/quality/YYYY-MM-DD.csv` | Une ligne par collecte réussie, heure UTC |
| Vue analytique | Jointure, nettoyage, cible future et variables historiques calculés à l’exécution | `notebooks/Analyse_velib_V_07_11.ipynb` | Référentiel du 25 octobre ; période fixée dans le code ; pas de fichier dérivé faisant autorité |
| Audit de couverture | Comptages et trous sur une fenêtre glissante | `src/audit_collection.py` | Recalculé sur les fichiers bruts |

Le collecteur préserve la réponse de chaque station et rejette un flux de moins de 1 000 stations ou comportant des identifiants dupliqués. Cette validation minimale ne garantit ni l’exhaustivité, ni la ponctualité du flux. Les instantanés sont append-only dans l’usage normal ; une correction doit être documentée, versionnée et accompagnée d’une comparaison avec les fichiers originaux.

## 3. Dictionnaire des variables décisives

| Variable | Sens et unité | Source / règle |
| --- | --- | --- |
| `station_id` | Identifiant technique de station, chaîne dans l’analyse | Flux statut et référentiel ; clé de jointure |
| `stationCode` | Code usuel affiché par Vélib’ | Flux brut ; utile pour rapprocher les annonces publiques, différent de `station_id` |
| `collected_at_utc` / `collecte` | Instant de notre collecte, UTC | Horloge du collecteur, pas heure de mise à jour de chaque station |
| `last_reported` | Dernier signalement de la station, secondes Unix | Flux statut ; son âge ne prouve pas seul que les compteurs sont périmés |
| `num_bikes_available` / `velos` | Vélos disponibles, nombre | Flux statut |
| `num_bikes_available_types` / `velos_meca`, `velos_elec` | Décompte par type, nombre | Flux statut ; valeur manquante conservée si détail absent |
| `num_docks_available` / `bornes_libres` | Bornes libres, nombre | Flux statut |
| `is_renting` / `en_service` | 1 si l’emprunt est autorisé, 0 sinon | Flux statut ; une valeur 0 n’identifie pas sa cause |
| `is_returning` | 1 si le dépôt est autorisé | Flux statut ; distinct de `is_renting` |
| `capacity` | Capacité officielle, bornes | Référentiel du 25 octobre ; peut différer des bornes effectivement utilisables |
| `lat`, `lon` | Coordonnées WGS84, degrés | Référentiel ; accès public à la position d’une station, pas d’une personne |
| `temps` | Créneau de cinq minutes le plus proche, heure de Paris | Arrondi de `collecte` ; doublons station-créneau résolus en gardant la dernière collecte |
| `vide` | 1 si `velos == 0` et `en_service == 1` | Variable descriptive ; une station fermée n’est pas comptée comme vide |
| `cible` | 1 si station ouverte et sans vélo exactement à +30 minutes | Étiquette créée uniquement lorsque l’observation future existe et que la station est en service à `t` et `t+30` |

## 4. Règles de qualité et de préparation

1. Convertir les heures UTC en heure de Paris avec fuseau explicite ; le 25 octobre 2026 comporte 25 heures, soit 300 créneaux théoriques de cinq minutes.
2. Vérifier les identifiants, le nombre de stations par relevé, les valeurs manquantes et les incohérences de capacité. Une capacité officielle ne doit pas être substituée automatiquement à `velos + bornes_libres`.
3. Conserver la fenêtre historique dense du 25 au 30 octobre : 1 736 créneaux observés sur 1 740 attendus après arrondi (99,8 %), quatre trous de dix minutes. Ne pas interpoler un état futur absent.
4. Exclure de l’analyse les 17 stations dont `last_reported` dépasse 24 heures au dernier relevé retenu ; garder trace de cette règle et du nombre écarté. Le seuil est un choix analytique, pas une preuve d’indisponibilité du service.
5. La cible de classification utilise une vraie observation à +30 minutes. Les données futures ne sont pas des variables explicatives ; un embargo de 30 minutes sépare entraînement, validation et test. Les statistiques historiques par station sont apprises sur l’entraînement seul.
6. Les valeurs manquantes des variations passées sont imputées à zéro dans le modèle actuel. Cela signifie « variation inconnue traitée comme nulle », et doit être considéré comme une limite, non comme une mesure observée.

L’audit récent du 7 novembre signalait seulement 9 relevés sur 576 attendus dans les 48 heures précédant son dernier instantané (1,56 %). Les jours récents ne sont donc pas substituables à la période dense dans l’évaluation. Le diagnostic se reproduit avec `python -m src.audit_collection --hours 48`, mais les résultats glissants peuvent changer lorsque de nouveaux fichiers sont collectés.

## 5. Événements externes et biais

La [Ville de Paris](https://www.paris.fr/?photo=26-12) indiquait 110 stations fermées pour les manifestations du 24 octobre, avec réouverture progressive dans la nuit du 25 au 26. [Vélib’ Métropole](https://blog.velib-metropole.fr/fermeture-temporaire-de-stations-velib-a-loccasion-des-manifestations-2/) annonçait 110 fermetures temporaires liées aux manifestations du 31 octobre, applicables dès le 30. Les instantanés du dépôt montrent environ 166 stations avec `is_renting != 1` le 25, environ 20 en milieu de semaine et jusqu’à 142 le 30 au soir. La concordance temporelle rend ce contexte pertinent, mais le flux GBFS ne fournit pas la cause individuelle de fermeture : ces chiffres ne mesurent pas directement le nombre de stations fermées à cause de la mobilisation.

Les stations fermées sont exclues des statistiques de « stations vides ». De plus, le jeu de classification écarte une station encore ouverte à `t` si elle est fermée à `t+30`. La mesure répond donc à une question **conditionnelle** — parmi les stations observées ouvertes aux deux instants, lesquelles sont vides à +30 minutes — et ne décrit pas tout le risque opérationnel de ne pas pouvoir emprunter un vélo. La période comprend la fin des fermetures du 24 et le début de celles du 31 ; elle ne représente pas un week-end ordinaire. La comparaison dimanche/jours ouvrés et la performance du modèle ne doivent pas être interprétées comme un effet causal des manifestations ou de la grève.

## 6. Accès, conservation, reproductibilité et revue

Les données sont publiques et versionnées dans ce dépôt pédagogique. L’écriture sur la branche de référence du rendu doit être réservée aux contributeurs ; une modification du code, des données ou du rapport doit passer par un commit identifiable. La branche `finalisation-remise-2026-11-08` fixe le rendu ; `main` reste distincte. Ne pas publier de clé, de jeton ou de fichier contenant des données personnelles.

Pour reproduire les résultats : cloner la branche de remise, installer `requirements.txt`, lancer les tests, exécuter le notebook principal dans l’ordre, puis comparer les chiffres de synthèse au rapport. Le rapport PDF est compilé depuis `docs/rapport-final.tex`. Le code, les paramètres, la période, le référentiel et les réserves méthodologiques doivent rester synchronisés. Toute prolongation de la collecte doit avoir une politique explicite de stockage, de durée et d’archivage : 288 instantanés théoriques par jour font croître Git rapidement. Aucun effacement automatique de l’historique n’est défini ici ; avant une conservation longue, déplacer les données brutes vers un stockage adapté et documenter la durée retenue.

**Revue avant diffusion :** vérifier attribution et licence à la source, intégrité des fichiers, état des tests, bornes temporelles, exclusions, liens de reproduction, noms des auteurs, et présence des limites dans la synthèse. L’enseignant et le groupe doivent encore valider l’envoi final par mail.

## 7. Responsabilités et critères de suivi

| Fonction | Responsable connu / décision restante | Contrôle attendu |
| --- | --- | --- |
| Production du flux source | Smovengo / Syndicat Autolib’ Vélib’ Métropole | Suivre la documentation et les changements du schéma source |
| Collecte, accès au dépôt et incidents | Équipe du projet ; référent individuel à désigner | Surveiller les exécutions GitHub Actions et les trous, sans confondre succès du workflow et cadence atteinte |
| Préparation et qualité analytique | Équipe du projet | Examiner les doublons, valeurs manquantes, incohérences, heures et exclusions avant chaque nouveau calcul |
| Validation scientifique | Quatre auteurs du rapport | Comparer les métriques aux baselines et relire les limites de généralisation |
| Publication et remise | Équipe du projet | Vérifier l’accord des membres et confirmer l’envoi par mail ; aucun envoi n’est présumé effectué |

Les données sont classées **publiques, agrégées par station** dans le périmètre actuel. La cible de qualité de collecte choisie par le projet est au moins 95 % des créneaux sur 48 h et aucun trou supérieur à 15 minutes ; elle n’est pas un engagement contractuel du producteur. Un échec de ce contrôle doit bloquer toute nouvelle affirmation sur la période récente, déclencher une enquête sur la planification et être enregistré avec sa date et sa résolution. Les seuils et exclusions analytiques doivent être revus si le schéma ou la cadence changent.

## 8. Registre des incidents pertinents pour ce rendu

| Date / période | Événement et preuve | Effet sur l’analyse | État |
| --- | --- | --- | --- |
| 24–26 octobre 2026 | 110 fermetures annoncées par la Ville de Paris ; niveau élevé de `is_renting != 1` observé le 25 | Dimanche non représentatif d’un service ordinaire ; stations fermées séparées des stations vides | Pris en compte dans notebook et rapport |
| 30 octobre–2 novembre 2026 | 110 fermetures annoncées par Vélib’ dès le 30 ; hausse observée de `is_renting != 1` en fin de journée | Fin du test chronologique perturbée ; les fermetures futures sont exclues de la cible | Pris en compte dans notebook et rapport |
| Après le 31 octobre 2026 | Audit récent : 9/576 relevés attendus sur 48 h au dernier instantané du 7 novembre | Données récentes inaptes à remplacer la fenêtre dense | Collecte à rétablir ; non résolu pour ce rendu |

La cause de chaque changement de `is_renting` n’est pas codée dans les instantanés. Les annonces externes et la série interne sont conservées comme deux sources distinctes, sans jointure causale automatique.
