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

## Problèmes réglés (détaillés)
- **Artefact sans preuve opposable** → chaque dossier expose obligations, fournisseurs, ratios de couverture, hash SHA-256
- **Certification qui ne rejoue pas indépendamment du client** → serveur recharge et recalcule, jamais dans l'ordre client
- **Preuve qui expire sans alerte** → stabilité chronologique mesurée (STABLE/REGRESSED/RECOVERED/INSUFFICIENT/INCOMPATIBLE)
- **Verdict déclaratif sans justification** → le dossier est immuable, déterministe et audit public

## Scénarios d'utilisation (réels)
- **MOS Hub** → paquet de preuves rejouable avec 14 gates et hash d'intégrité
- **Diplôme / attestation** → preuve ancrée, opposable, portable entre institutions
- **Supply chain** → artefacts versionnés et traçables par provenance fermée

## À quoi ça pourrait servir (futur / possibilités)
- Blockchain de preuves
- Certification continue
- Portefeuille de preuves portable

## Pour qui ?
Devs, auditeurs, ops, chercheurs — qui ont besoin d'une preuve opposable, pas d'un verdict déclaratif.