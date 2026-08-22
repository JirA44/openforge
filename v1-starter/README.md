# OpenForge V1.04 Starter / MOS Hub

Version interne : `1.0.4`.

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

Le scénario de démonstration n'invente pas de PASS : il crée d'abord les objets du Registry, fige une version, puis soumet des preuves explicites au moteur déterministe. Modifiez une valeur sous un seuil pour constater le blocage.

## Tests

```powershell
./scripts/Test.ps1
```

## Structure

- `apps/api` : API FastAPI, Registry SQLite local et moteur de certification.
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

## Persistance

Par défaut, l'API crée `openforge.db` dans le projet. Pour choisir un autre emplacement :

```powershell
$env:OPENFORGE_DB = "D:\OpenForge\data\openforge.db"
./scripts/Start.ps1
```

Les versions de stratégie sont immuables : un même numéro de version ne peut pas être réécrit.

## Runs reproductibles

Un run lie explicitement une version de stratégie, ses hashes code/configuration, une version de dataset, un runner, ses paramètres, sa seed et ses observations. Le manifeste canonique et le résultat sont hashés. `POST /v1/runs/{id}/replay` recalcule le résultat et signale `REPLAY_MATCH` ou `REPLAY_MISMATCH`.

## Certification depuis un run

`POST /v1/certifications/from-run` dérive automatiquement RR, Profit Factor net, expectancy, échantillon, drawdown et hashes depuis le run persisté. Ces champs ne peuvent donc plus être saisis manuellement dans ce parcours. Les attestations OOS, walk-forward, paper, shadow et sécurité restent exigées séparément.

## Paper et shadow vérifiés

Les routes `/v1/validations` enregistrent des sessions paper/shadow et leurs observations. La validation finale contrôle le volume minimal, l'écart d'exécution moyen et le taux de rejet. La certification depuis un run exige désormais les identifiants de deux sessions finalisées ; un simple booléen ne suffit plus.

## Live sécurisé, encore verrouillé

Un déploiement canari exige une stratégie `READY_FOR_LIVE`, des limites explicites et deux confirmations humaines : armement puis activation. Les violations de perte, drawdown, fiabilité des données ou du connecteur déclenchent `SUSPENDED`. En V1.04, `gateway_locked` reste toujours à `true` : aucun adaptateur ne peut transmettre d’ordre réel.
