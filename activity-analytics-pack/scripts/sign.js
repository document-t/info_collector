const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

function findSigntool() {
  for (const kit of ['10', '11']) {
    const base = `C:\\Program Files (x86)\\Windows Kits\\${kit}\\bin`;
    if (!fs.existsSync(base)) continue;
    const dirs = fs.readdirSync(base).sort().reverse();
    for (const d of dirs) {
      const p = path.join(base, d, 'x64', 'signtool.exe');
      if (fs.existsSync(p)) return `"${p}"`;
    }
  }
  throw new Error('signtool.exe not found');
}

const signtoolPath = findSigntool();
const args = process.argv.slice(2);
const params = {};
for (let i = 0; i < args.length; i += 2) {
  const key = args[i].replace(/^--/, '');
  params[key] = args[i + 1];
}

if (!params.certificate || !params.password) {
  console.error('Usage: npm run sign -- --certificate=path/to/cert.p12 --password=your-password');
  process.exit(1);
}

const filesToSign = [
  path.join(__dirname, '../dist/win-unpacked/activity-analytics-hybrid.exe'),
  path.join(__dirname, '../dist/win-unpacked/resources/native/x64/Release/monitor.exe'),
  path.join(__dirname, '../dist/win-unpacked/resources/native/x64/Release/monitor.dll'),
  path.join(__dirname, '../dist/activity-analytics-hybrid-setup.exe')
];

const signCommand = `${signtoolPath} sign /f ${params.certificate} /p ${params.password} /t http://timestamp.digicert.com /fd SHA256`;

filesToSign.forEach(file => {
  if (fs.existsSync(file)) {
    console.log(`Signing ${file}...`);
    try {
      execSync(`${signCommand} "${file}"`, { stdio: 'inherit' });
      console.log(`Successfully signed ${file}`);
    } catch {
      console.error(`Failed to sign ${file}`);
      process.exit(1);
    }
  } else {
    console.warn(`File not found: ${file} - skipping`);
  }
});

console.log('Signing completed successfully');