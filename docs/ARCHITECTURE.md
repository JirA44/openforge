# Architecture

## Couche 1 — Git

Git reste la source de vérité pour l'historique, les branches et les forks.

## Couche 2 — Manifeste OpenForge

Chaque dépôt contient un fichier `openforge.yaml` décrivant :

- le type d'artefact ;
- sa version ;
- ses auteurs ;
- ses dépendances ;
- ses entrées et sorties ;
- ses règles d'évaluation ;
- sa licence ;
- sa provenance.

## Couche 3 — Runner reproductible

Le runner exécute les tests dans un environnement isolé et produit :

- logs ;
- métriques ;
- hashes ;
- rapport JSON ;
- attestation signée.

## Couche 4 — Registry

Le registry indexe les dépôts, versions, forks, scores et attestations.

## Couche 5 — Interface

Fonctions principales :

- explorer ;
- comparer ;
- forker ;
- exécuter ;
- vérifier ;
- classer ;
- suivre les versions.
