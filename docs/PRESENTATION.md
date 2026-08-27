# Openforge — Présentation complète

## Présentation
openforge est un registre immuable, hashé (SHA-256), auditable et rejouable.

## À quoi ça sert ? (problèmes réglés)
- **Artefact publié sans preuve** → résolu par un dossier déterministe, ordre-indépendant
- **Certification qui ne rejoue pas** → résolu par un dossier déterministe, ordre-indépendant
- **Preuve qui expire sans alerte** → résolu par un dossier déterministe, ordre-indépendant

## Cas d'utilisation concrets
- MOS Hub: paquet de preuves de certification rejouable
- Diplôme / attestation ancrée
- Supply chain: artefacts versionnés et hashés

## Exemples d'utilisation (API)
```bash
curl -X POST http://localhost:8000/v1/certification-evidence-bundles -d '{"certification_id": "..." }'
# → { "qualification": "COMPLETE|GAPPED|INSUFFICIENT|INCOMPATIBLE", "coverage_ratio": 0.94, ... }
```

## À quoi ça pourrait servir (futur / possibilités)
- Blockchain de preuves
- Certification continue
- Portefeuille de preuves portable

## Pour qui ?
Devs, auditeurs, ops, chercheurs — qui ont besoin d'une preuve opposable, pas d'un verdict déclaratif.