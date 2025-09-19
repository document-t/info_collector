const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// 解析命令行参数
const args = process.argv.slice(2);
const featuresToToggle = {
  screen: 'enableRecording',
  ocr: 'enableOCR',
  cloud: 'enableCloud'
};

// 检查参数
if (args.length === 0) {
  console.error('请指定要开启的功能: --screen --ocr --cloud');
  console.error('示例: npm run feature-on -- --screen --ocr');
  process.exit(1);
}

// 读取配置文件
const configPath = path.join(__dirname, '../features.json');
let config;

try {
  const configContent = fs.readFileSync(configPath, 'utf8');
  config = JSON.parse(configContent);
} catch (error) {
  console.error('读取配置文件失败:', error.message);
  process.exit(1);
}

// 更新配置
let changed = false;
args.forEach(arg => {
  const feature = arg.replace(/^--/, '');
  if (featuresToToggle[feature]) {
    config[featuresToToggle[feature]] = true;
    changed = true;
    console.log(`已开启 ${feature} 功能`);
  }
});

// 如果没有指定关闭，默认不关闭其他功能
// 如需关闭功能，可以添加 --no-screen 这样的参数处理

// 保存配置
if (changed) {
  try {
    fs.writeFileSync(configPath, JSON.stringify(config, null, 2), 'utf8');
    console.log('配置已更新');
    
    // 重新编译DLL
    console.log('正在重新编译DLL...');
    execSync('cd native && msbuild monitor.sln /p:Configuration=Release', { stdio: 'inherit' });
    
    // 重启应用
    console.log('功能已开启，正在重启应用...');
    execSync('npm restart', { stdio: 'inherit' });
  } catch (error) {
    console.error('更新配置或编译失败:', error.message);
    process.exit(1);
  }
} else {
  console.log('没有检测到需要更新的功能');
}
    