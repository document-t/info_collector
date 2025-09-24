
const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, '../src/worker');
const distDir = path.join(__dirname, '../dist/worker');

// 没有 worker 就跳过
if (!fs.existsSync(srcDir)) return;

fs.mkdirSync(distDir, { recursive: true });
fs.cpSync(srcDir, distDir, { recursive: true, force: true });
console.log('[copy-worker] copied -> dist/worker');