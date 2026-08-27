# OpenForge

**Le Git des artefacts vérifiables.**

OpenForge versionne des connaissances, données, modèles, preuves, expériences et décisions. Chaque artefact conserve son manifeste, ses fichiers, ses empreintes d'intégrité, ses évaluations et sa provenance.

## À quoi ça sert

OpenForge permet de :

- conserver un dossier chronologique et immuable ;
- vérifier l'intégrité des fichiers avec SHA-256 ;
- rendre les résultats reproductibles et auditables ;
- détecter les preuves, sources ou dépendances manquantes ;
- comparer des versions sans réécrire l'historique ;
- publier des résultats explicables, sans transformer une hypothèse en certification.

## Les produits Forge

- **KnowledgeForge** : affirmations sourcées, versions, preuves et contradictions.
- **DataForge** : jeux de données versionnés, traçables et reproductibles.
- **ModelForge** : versions de modèles, artefacts, benchmarks et dérive.
- **ProofForge** : preuves formelles, dépendances et vérification automatique.
- **DecisionForge** : hypothèses, alternatives, décisions et résultats observés.
- **ExperimentForge** : expériences, paramètres, résultats et réplications.
- **SimulationForge** : simulations, scénarios, hypothèses et sorties vérifiables.
- **MOS Hub** : intégration quantitative optionnelle pour les stratégies et backtests.

Chaque produit peut fonctionner séparément. OpenForge fournit le socle commun ; aucun produit n'est requis pour utiliser les autres.

## Principe

Chaque dépôt d'artefact contient :

1. un manifeste standard ;
2. des fichiers versionnés par Git ;
3. des empreintes d'intégrité ;
4. des évaluations automatisées ;
5. une provenance vérifiable ;
6. des résultats rejouables.

## Démarrage rapide sous Windows / PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./bootstrap.ps1
./run.ps1
```

API locale : `http://127.0.0.1:8000`. Documentation : `docs/ARCHITECTURE.md`.

## Parcours type

1. Créer un dépôt d'artefact et son manifeste.
2. Ajouter les fichiers et leurs sources.
3. Valider le manifeste et calculer les empreintes.
4. Exécuter les évaluations adaptées au type d'artefact.
5. Publier un rapport reproductible.
6. Comparer ou forker une version sans effacer l'historique.

## Structure

```text
openforge-starter/
├── backend/     # API FastAPI de validation et d'intégrité
├── cli/         # CLI OpenForge
├── docs/        # architecture, usages et feuille de route
├── examples/    # manifestes d'exemple
├── schemas/     # schémas JSON
├── bootstrap.ps1
└── run.ps1
```

## Limites

OpenForge prouve l'intégrité et la traçabilité des éléments enregistrés. Il ne prouve pas à lui seul la vérité d'une affirmation, la qualité scientifique d'un seuil ou la pertinence d'une décision. Les validations et activations sensibles restent soumises à une revue humaine.

## Documentation

- [Présentation complète](docs/PRESENTATION.md)
- [Exemples d'utilisation](docs/USAGE_EXAMPLES.md)
- [Contribution](CONTRIBUTING.md)
- [Licence MIT](LICENSE)