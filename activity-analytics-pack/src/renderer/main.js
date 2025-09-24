import 'chart.js/auto';
import './style.css';
import Chart from 'chart.js/auto';

/* ---------- 主题切换 ---------- */
const html = document.documentElement;
const themeBtn = document.getElementById('themeToggle');
themeBtn?.addEventListener('click', () => html.classList.toggle('dark'));

/* ---------- 图表初始化 ---------- */
const sysCfg = {
  type: 'line',
  data: { labels: [], datasets: [
    { label: 'CPU %', data: [], borderColor: '#3b82f6', tension: 0.3, fill: false },
    { label: 'Mem %', data: [], borderColor: '#10b981', tension: 0.3, fill: false }
  ]},
  options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }
};
const inputCfg = {
  type: 'bar',
  data: { labels: [], datasets: [
    { label: 'KB', data: [], backgroundColor: '#8b5cf6' },
    { label: 'Mouse', data: [], backgroundColor: '#f59e0b' }
  ]},
  options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
};

const sysChart = new Chart(document.getElementById('sysChart'), sysCfg);
const inputChart = new Chart(document.getElementById('inputChart'), inputCfg);

/* ---------- 卡片 ---------- */
const statCards = document.getElementById('statCards');
const processTable = document.getElementById('processTable');
const monitorBtn = document.getElementById('monitorToggle');

const cardData = [
  { icon: 'fa-window-maximize', title: 'Active Window', id: 'title', unit: '' },
  { icon: 'fa-microchip', title: 'CPU', id: 'cpu', unit: '%' },
  { icon: 'fa-memory', title: 'Memory', id: 'mem', unit: '%' },
  { icon: 'fa-keyboard', title: 'Keyboard', id: 'kb', unit: '' },
  { icon: 'fa-mouse', title: 'Mouse', id: 'mouse', unit: '' },
  { icon: 'fa-microphone', title: 'Mic dB', id: 'dB', unit: 'dB' }
];

function renderCards(data) {
  statCards.innerHTML = cardData.map(c => `
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 flex items-center gap-4">
      <i class="fa ${c.icon} text-2xl text-blue-500"></i>
      <div>
        <div class="text-sm text-gray-500">${c.title}</div>
        <div class="text-xl font-bold">${data[c.id] ?? 0}${c.unit}</div>
      </div>
    </div>`).join('');
}

function updateCharts(data) {
  const now = new Date().toLocaleTimeString();
  // CPU / Mem
  sysCfg.data.labels.push(now);
  sysCfg.data.datasets[0].data.push(+data.cpu);
  sysCfg.data.datasets[1].data.push(+data.mem);
  if (sysCfg.data.labels.length > 20) {
    sysCfg.data.labels.shift();
    sysCfg.data.datasets.forEach(d => d.data.shift());
  }
  sysChart.update('none');
  // Input
  inputCfg.data.labels.push(now);
  inputCfg.data.datasets[0].data.push(+data.kb);
  inputCfg.data.datasets[1].data.push(+data.mouse);
  if (inputCfg.data.labels.length > 20) {
    inputCfg.data.labels.shift();
    inputCfg.data.datasets.forEach(d => d.data.shift());
  }
  inputChart.update('none');
}

/* ---------- 进程：去重 + 最近 10 条 ---------- */
const processMap = new Map();   // key = pid
const MAX_PROCESS = 10;

function updateTable(data) {
  
  processMap.set(data.pid, data);
 
  const list = Array.from(processMap.values())
                   .sort((a, b) => b.timestamp - a.timestamp)
                   .slice(0, MAX_PROCESS);

  const html = list.map(d => `
    <tr class="border-b dark:border-gray-700">
      <td class="py-2">${d.exe.split('\\').pop()}</td>
      <td class="py-2 truncate max-w-xs">${d.title}</td>
      <td class="py-2">${d.cpu.toFixed(1)}%</td>
      <td class="py-2">${d.mem.toFixed(0)}</td>
      <td class="py-2 text-xs">${new Date(d.timestamp).toLocaleTimeString()}</td>
    </tr>`).join('');
  document.getElementById('processTable').innerHTML = html;
}

/* ---------- 开关 ---------- */
let isRunning = true;
monitorBtn?.addEventListener('click', () => {
  isRunning = !isRunning;
  window.electronAPI.toggleMonitor(isRunning);
  monitorBtn.innerHTML = `<i class="fa fa-${isRunning ? 'pause' : 'play'} mr-2"></i><span>${isRunning ? '暂停' : '继续'}</span>`;
});

/* ---------- 接收数据 ---------- */
window.electronAPI.onRealtime((rows) => {
  if (!isRunning) return;
  const d = rows[0];
  renderCards(d);
  updateCharts(d);
  updateTable(d);
});
