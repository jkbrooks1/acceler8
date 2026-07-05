# Acceler8-ai

This repository contains the public landing page and the proofsheet output used for Acceler8-ai publishing workflows.

## Canonical Proofsheet Workflow

- Canonical stock photo processor: use the current project-approved processor entry point
- Shell aliases that should point to that processor: `proofsheet` and `Proofsheet`
- Photo staging folder: local staging location used by the processor
- Canonical stock photo folder: Google Drive stock-photo source used by the processor
- Naming convention: `XXX.a8Stock.BUCKET.ext`
- Approved buckets: `TEAMS`, `SYSTEMS`, `REVENUE`, `DATA-VIZ`, `GRAPHIC-ELEMENTS`
- R2 bucket: `proofsheetbucketbb`
- R2 public base URL: `https://pub-906aebdaaf22471faa576c94c2cdf07b.r2.dev`
- Proofsheet GitHub output: `public/proofsheet/index.html`
- Proofsheet live URL: `https://proofsheet.acceler8-ai.com`
- Google service account JSON: local credential path managed in the developer environment
- Recommended environment variable: `GOOGLE_APPLICATION_CREDENTIALS`

## Landing Page Image Rule

When the Acceler8-ai landing page uses stock photography, the public source and built output must reference the R2 public URLs directly. Do not use local Mac paths in public code, and do not assume local build success is enough for a GitHub-backed deploy.

## Safe Verification

```bash
for v in R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY R2_ACCOUNT_ID R2_BUCKET_NAME R2_PUBLIC_URL; do
  if printenv "$v" >/dev/null; then
    echo "SET     $v"
  else
    echo "MISSING $v"
  fi
done

curl -fsSL https://proofsheet.acceler8-ai.com -o /tmp/proofsheet_live_doc_check.html
```

## Troubleshooting

- `proofsheet` command not found: confirm the shell alias resolves to the canonical processor path.
- Wrong alias path: both aliases should run the same Python script.
- Missing R2 env vars: load the required `R2_*` variables before running the processor.
- `NoSuchBucket`: confirm the bucket is `proofsheetbucketbb`, not `proofsheetbucketb`.
- Live page shows filenames but not images: verify the R2 URLs return HTTP 200 and check the deployed HTML, not just the local build.
