# MOS Hub — Spécification

## Fichiers d'un dépôt de stratégie

```text
strategy/
├── openforge.yaml
├── strategy.py
├── parameters.yaml
├── requirements.lock
├── tests/
├── data/
├── reports/
└── attestations/
```

## Métriques minimales

- rendement total ;
- CAGR ;
- volatilité annualisée ;
- Sharpe ;
- Sortino ;
- Calmar ;
- max drawdown ;
- taux de réussite ;
- profit factor ;
- expectancy ;
- turnover ;
- exposition ;
- frais ;
- slippage.

## Anti-triche

- données figées par hash ;
- séparation in-sample / out-of-sample ;
- tests walk-forward ;
- coûts de transaction obligatoires ;
- publication du nombre d'essais ;
- détection de look-ahead bias ;
- seed déclarée ;
- runner déterministe.

## Score MOS

Le score ne doit jamais être une simple moyenne.

Exemple :

```text
MOS Score =
qualité des données
× reproductibilité
× robustesse
× performance ajustée du risque
× pénalité de complexité
× pénalité de surapprentissage
```
