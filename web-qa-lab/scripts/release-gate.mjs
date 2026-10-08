import fs from 'node:fs';

const resultPath = 'artifacts/results.json';
const outputPath = 'artifacts/QA_REPORT.md';

if (!fs.existsSync(resultPath)) {
  console.error('Missing artifacts/results.json. Run npm run qa first.');
  process.exit(2);
}

const raw = JSON.parse(fs.readFileSync(resultPath, 'utf8'));
const suites = raw.suites || [];
const specs = [];

function walk(items) {
  for (const suite of items || []) {
    for (const spec of suite.specs || []) specs.push(spec);
    walk(suite.suites);
  }
}
walk(suites);

let passed = 0;
let failed = 0;
for (const spec of specs) {
  const ok = (spec.tests || []).every(t => (t.results || []).some(r => r.status === 'passed'));
  if (ok) passed++;
  else failed++;
}

const gate = failed === 0 ? 'READY FOR PHYSICAL TEST' : 'FAIL — FIX BEFORE DELIVERY';
const report = [
  '# Web QA Lab — Release Gate',
  '',
  `- Total checks: ${passed + failed}`,
  `- Passed: ${passed}`,
  `- Failed: ${failed}`,
  `- Recommendation: **${gate}**`,
  '',
  '## Failed checks',
  ''
];

const failedSpecs = specs.filter(spec => !(spec.tests || []).every(t => (t.results || []).some(r => r.status === 'passed')));
if (!failedSpecs.length) report.push('None.');
else failedSpecs.forEach(spec => report.push(`- ${spec.title}`));

report.push('', '## Required human/agent review', '', '- Review screenshots at desktop/tablet/mobile.', '- Review spacing, hierarchy, contrast, density, focus state and data legibility.', '- Compare critical flows against the current LKG before release.', '');

fs.mkdirSync('artifacts', { recursive: true });
fs.writeFileSync(outputPath, report.join('\n'));
console.log(report.join('\n'));
process.exit(failed ? 1 : 0);
