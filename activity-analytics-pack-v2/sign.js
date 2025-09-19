const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// 解析命令行参数
const args = process.argv.slice(2);
const params = {};

for (let i = 0; i < args.length; i += 2) {
  const key = args[i].replace(/^--/, '');
  params[key] = args[i + 1];
}

// 检查必要参数
if (!params.certificate || !params.password) {
  console.error('Usage: npm run sign -- --certificate=path/to/cert.p12 --password=your-password');
  process.exit(1);
}

// 检查签名工具是否存在
const signtoolPath = '"C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.19041.0\\x64\\signtool.exe"';
try {
  execSync(`${signtoolPath} /?`, { stdio: 'ignore' });
} catch (error) {
  console.error('signtool.exe not found. Please install Windows SDK or update the path in sign.js');
  process.exit(1);
}

// 需要签名的文件
const filesToSign = [
  path.join(__dirname, '../dist/win-unpacked/activity-analytics-hybrid.exe'),
  path.join(__dirname, '../dist/win-unpacked/resources/native/x64/Release/monitor.exe'),
  path.join(__dirname, '../dist/win-unpacked/resources/native/x64/Release/monitor.dll'),
  path.join(__dirname, '../dist/activity-analytics-hybrid-setup.exe')
];

// 签名命令
const signCommand = `${signtoolPath} sign /f ${params.certificate} /p ${params.password} /t http://timestamp.digicert.com /fd SHA256`;

// 对每个文件进行签名
filesToSign.forEach(file => {
  if (fs.existsSync(file)) {
    console.log(`Signing ${file}...`);
    try {
      execSync(`${signCommand} "${file}"`, { stdio: 'inherit' });
      console.log(`Successfully signed ${file}`);
    } catch (error) {
      console.error(`Failed to sign ${file}`);
      process.exit(1);
    }
  } else {
    console.warn(`File not found: ${file} - skipping`);
  }
});

console.log('Signing completed successfully');
