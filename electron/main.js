import { app, BrowserWindow, shell } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow = null;
let serverProcess = null;

// Start internal Web API server in background if not already running
async function startBackendServer() {
  try {
    const res = await fetch('http://localhost:3100/api/health', { signal: AbortSignal.timeout(1000) });
    if (res.ok) {
      console.log('Server is already running on port 3100.');
      return;
    }
  } catch (e) {
    // Server not running, proceed to spawn
  }

  const serverPath = path.join(__dirname, '../server/index.js');
  serverProcess = spawn(process.execPath, [serverPath], {
    env: { ...process.env, PORT: '3100' },
    stdio: 'ignore'
  });

  serverProcess.on('error', (err) => {
    console.error('Failed to start backend server process:', err);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1240,
    height: 840,
    minWidth: 800,
    minHeight: 600,
    title: 'ZeroAI Desk - 極輕量多模型 AI 桌面工作站',
    backgroundColor: '#0b0f19',
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Open external links in default system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Load from local web server or file fallback
  const loadApp = async () => {
    for (let i = 0; i < 15; i++) {
      try {
        const res = await fetch('http://localhost:3100/api/health', { signal: AbortSignal.timeout(500) });
        if (res.ok) {
          mainWindow.loadURL('http://localhost:3100');
          return;
        }
      } catch (err) {}
      await new Promise(r => setTimeout(r, 200));
    }
    
    // Static file fallback
    const distPath = path.join(__dirname, '../dist/index.html');
    mainWindow.loadFile(distPath);
  };

  loadApp();

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  await startBackendServer();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (serverProcess) {
    serverProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
