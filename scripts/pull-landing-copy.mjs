#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const ROOT = path.resolve(new URL('.', import.meta.url).pathname, '..');
const EXPORT_PATH = '/tmp/canonical_acceler8_landing_sheet_export.txt';
const PULL_LAND = process.env.PULL_LAND_BIN || 'PullLand';
const SHEET_ID = '1P_yEIR9u9LWoow8q6MB9h5o37N3bOCALUepZsw-zP3U';
const OUTPUT_PATH = path.join(ROOT, 'src/data/a8LandingCopy.ts');

function die(message) {
  console.error(`ERROR: ${message}`);
  process.exit(1);
}

function runPullLand() {
  const result = spawnSync(PULL_LAND, [SHEET_ID], {
    encoding: 'utf8',
    stdio: 'inherit',
  });

  if (result.status !== 0) {
    die(`PullLand failed with exit code ${result.status ?? 'unknown'}`);
  }
}

function parseExport(text) {
  const lines = text.split(/\r?\n/);
  const tabs = new Map();
  let currentTab = null;
  let mode = null;

  for (const line of lines) {
    const tabMatch = line.match(/^===== TAB: (.+) =====$/);
    if (tabMatch) {
      currentTab = tabMatch[1];
      tabs.set(currentTab, { headers: [], rows: [] });
      mode = null;
      continue;
    }

    if (!currentTab) continue;
    if (line === 'HEADERS:') {
      mode = 'headers';
      continue;
    }
    if (line === 'ALL DATA INCLUDING HEADER:') {
      mode = 'data';
      continue;
    }
    if (line.startsWith('Grid Rows:') || line.startsWith('Grid Columns:') || line.startsWith('Used Rows Pulled:') || line.startsWith('Header Count:') || line.startsWith('DATA ROW COUNT EXCLUDING HEADER:')) {
      continue;
    }
    if (!line.trim()) continue;

    const tab = tabs.get(currentTab);
    if (!tab) continue;

    const cells = line.split('\t');
    if (mode === 'headers' && tab.headers.length === 0) {
      tab.headers = cells;
      continue;
    }
    if (mode === 'data') {
      tab.rows.push(cells);
    }
  }

  return tabs;
}

function rowToObject(headers, row) {
  const out = {};
  headers.forEach((header, index) => {
    out[header] = row[index] ?? '';
  });
  return out;
}

function clean(value) {
  return String(value ?? '').trim();
}

function resolveCopy(row) {
  const updated = clean(row['Updated Copy']);
  const current = clean(row['Current Copy']);

  if (updated === 'REMOVE') return null;
  if (updated) return updated;
  return current || null;
}

function main() {
  runPullLand();

  if (!fs.existsSync(EXPORT_PATH)) {
    die(`Expected export artifact not found: ${EXPORT_PATH}`);
  }

  const exportText = fs.readFileSync(EXPORT_PATH, 'utf8');
  const tabs = parseExport(exportText);
  const copyTab = tabs.get('a8_Landing_Copy');
  const rulesTab = tabs.get('RULES');

  if (!copyTab) die('Missing a8_Landing_Copy tab in export.');
  if (!rulesTab) die('Missing RULES tab in export.');

  const rows = copyTab.rows.map((row) => rowToObject(copyTab.headers, row));
  const values = {};
  const removed = [];

  for (const row of rows) {
    const sectionId = clean(row['Section ID']);
    if (!sectionId || sectionId === 'Section ID') continue;

    const resolved = resolveCopy(row);
    if (resolved === null) {
      removed.push(sectionId);
      continue;
    }
    values[sectionId] = resolved;
  }

  const ruleRows = rulesTab.rows
    .map((row) => rowToObject(rulesTab.headers, row))
    .map((row) => clean(row[Object.keys(row)[1]] || row[Object.keys(row)[0]]))
    .filter(Boolean);

  const sheetTitleMatch = exportText.match(/Spreadsheet Title:\s*(.+)/);
  const sheetIdMatch = exportText.match(/Spreadsheet ID:\s*(.+)/);
  const pulledAtMatch = exportText.match(/Pulled At:\s*(.+)/);
  const tabCountMatch = exportText.match(/Tab Count:\s*(\d+)/);
  const tabNamesMatch = exportText.match(/Tab Names:\s*(.+)/);

  const payload = {
    spreadsheetTitle: sheetTitleMatch?.[1] || 'a8_LandingPage_CANONICAL',
    spreadsheetId: sheetIdMatch?.[1] || SHEET_ID,
    pulledAt: pulledAtMatch?.[1] || new Date().toISOString(),
    tabCount: Number(tabCountMatch?.[1] || 0),
    tabNames: tabNamesMatch?.[1]?.split(' | ') || ['NOTES_DO_NOT_USE', 'a8_Landing_Copy', 'RULES'],
    rules: ruleRows,
    removed,
    values,
  };

  const fileContents = `// Generated from ${EXPORT_PATH} by scripts/pull-landing-copy.mjs.\n` +
    `// Source of truth: Google Sheet ID ${SHEET_ID}.\n\n` +
    `export const landingCopy = ${JSON.stringify(payload, null, 2)} as const;\n`;

  fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
  fs.writeFileSync(OUTPUT_PATH, fileContents, 'utf8');

  console.log(`Wrote ${OUTPUT_PATH}`);
  console.log(`Sheet ID: ${SHEET_ID}`);
  console.log(`Removed sections: ${removed.length}`);
  console.log(`Rendered copy entries: ${Object.keys(values).length}`);
}

main();
