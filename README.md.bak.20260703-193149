# Acceler8

This repository contains the generated public proofsheet output for Acceler8-ai and the related landing-page assets that are published through GitHub and Cloudflare Pages.

## Canonical Proofsheet Workflow

- Canonical stock photo processor: `python3 /Users/jkbrookspersonal/LocalSiteBuildFiles/00_SCRIPTS/a8_stock_photo_processor_v3.py`
- Shell aliases that should point to that processor: `proofsheet` and `Proofsheet`
- Photo staging folder: `/Users/jkbrookspersonal/JBLocal Files/PhotoStaging`
- Canonical stock photo folder: `/Users/jkbrookspersonal/Library/CloudStorage/GoogleDrive-jb@acceler8-ai.com/My Drive/a8_Root/06a8_Marketing_Promotion/03_Brand_Assets/Stock_Photos`
- Naming convention: `XXX.a8Stock.BUCKET.ext`
- Approved buckets: `TEAMS`, `SYSTEMS`, `REVENUE`, `DATA-VIZ`, `GRAPHIC-ELEMENTS`
- R2 bucket: `proofsheetbucketb`
- R2 public base URL: `https://pub-906aebdaaf22471faa576c94c2cdf07b.r2.dev`
- Proofsheet GitHub output: `/Users/jkbrookspersonal/Projects/acceler8/public/proofsheet/index.html`
- Proofsheet live URL: `https://proofsheet.acceler8-ai.com`
- Google service account JSON: `/Users/jkbrookspersonal/.config/acceler8-ai/google/service-account.json`
- Recommended environment variable: `GOOGLE_APPLICATION_CREDENTIALS=/Users/jkbrookspersonal/.config/acceler8-ai/google/service-account.json`

## Landing Page Image Rule

When the Acceler8-ai landing page uses stock photography, the public source and built output must reference the R2 public URLs directly. Do not use local Mac paths in public code, and do not assume local build success is enough for a GitHub-backed deploy.

## Safe Verification

```bash
alias proofsheet 2>/dev/null || true
alias Proofsheet 2>/dev/null || true

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
- `NoSuchBucket`: confirm the bucket is `proofsheetbucketb`, not `proofsheetbucket`.
- Live page shows filenames but not images: verify the R2 URLs return HTTP 200 and check the deployed HTML, not just the local build.
- `GOOGLE_APPLICATION_CREDENTIALS` points to an old path: reset it to `/Users/jkbrookspersonal/.config/acceler8-ai/google/service-account.json`.

