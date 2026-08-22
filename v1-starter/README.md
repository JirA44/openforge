# OpenForge V1 / MOS Hub

Starter exécutable du noyau OpenForge et de son premier produit MOS Hub.

## Démarrage Windows PowerShell

```powershell
./scripts/Setup.ps1
./scripts/Start.ps1
```

Ouvrir ensuite `http://127.0.0.1:8000/docs`.

## Test vertical

```powershell
./scripts/Demo-Certification.ps1
```

Le scénario de démonstration n'invente pas de PASS : il soumet des preuves explicites au moteur déterministe. Modifiez une valeur sous un seuil pour constater le blocage.

## Tests

```powershell
./scripts/Test.ps1
```

## Structure

- `apps/api` : API FastAPI et moteur de certification.
- `packages/contracts` : contrat OpenAPI.
- `packages/database` : schéma PostgreSQL initial.
- `policies` : politique MOS Hub versionnée.
- `examples` : requête de certification démonstrative.
- `scripts` : commandes PowerShell.

## Règles initiales

- RR planifié >= 3.0
- Profit Factor net >= 1.5
- Expectancy nette > 0
- OOS, walk-forward, paper et shadow obligatoires
- provenance, reproductibilité et sécurité obligatoires
- aucune activation live automatique

