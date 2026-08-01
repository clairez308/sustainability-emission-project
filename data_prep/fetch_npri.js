const fs = require('fs');

const OUT = process.argv[2];
const PAGE_SIZE = 5000;

function csvField(v) {
  if (v === null || v === undefined) return '';
  const s = String(v);
  if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

async function main() {
  const header = [
    'npri_id', 'ghgrp_id', 'year', 'company', 'facility_name', 'city',
    'province', 'naics_code', 'naics_description', 'report_type',
    'has_p2_plan', 'has_p2_activity'
  ];
  const rows = [header.join(',')];

  let start = 0;
  let total = null;
  while (total === null || start < total) {
    const url = `https://pollution-waste.canada.ca/sradapi/v2/npri/Search?fromYear=2004&toYear=2024&direction=ascending&order=NPRI_Id&language=en&start=${start}&length=${PAGE_SIZE}&window=10&draw=1`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status} at start=${start}`);
    const json = await resp.json();
    total = json.recordsTotal;
    for (const r of json.data) {
      rows.push([
        csvField(r.npriID),
        csvField(r.ghgrpID),
        csvField(r.year),
        csvField(r.company),
        csvField(r.facility),
        csvField(r.city),
        csvField(r.province ? r.province.en : ''),
        csvField(r.naics ? r.naics.id : ''),
        csvField(r.naics ? r.naics.en : ''),
        csvField(r.reportType ? r.reportType.en : ''),
        csvField(r.hasP2Plan),
        csvField(r.hasP2Activity),
      ].join(','));
    }
    process.stderr.write(`fetched ${Math.min(start + PAGE_SIZE, total)}/${total}\n`);
    start += PAGE_SIZE;
  }

  fs.writeFileSync(OUT, rows.join('\n') + '\n', 'utf-8');
  process.stderr.write(`wrote ${rows.length - 1} rows to ${OUT}\n`);
}

main().catch(e => { console.error(e); process.exit(1); });
