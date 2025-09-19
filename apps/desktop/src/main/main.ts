import { app, BrowserWindow, shell } from 'electron';
import { join } from 'node:path';

import { registerIpcHandlers } from './ipc';
import { URLValidator } from './url-validator';

const isMac = process.platform === 'darwin';
let mainWindow: BrowserWindow | null = null;

/**
 * Securely opens an external URL after validation
 */
function openExternalURLSecurely(url: string): Promise<void> {
  const validationResult = URLValidator.validateURL(url);
  
  if (!validationResult.isValid) {
    console.error(`[SECURITY] Blocked attempt to open URL: ${url}. Reason: ${validationResult.reason}`);
    throw new Error(`Security violation: ${validationResult.reason}`);
  }

  console.log(`[SECURITY] Opening validated URL: ${url}`);
  return shell.openExternal(url);
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1120,
    minHeight: 700,
    title: 'EcoCode',
    webPreferences: {
      preload: join(__dirname, 'preload.js'),
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false,
    },
    backgroundColor: '#07090c',
  });

  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    await mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    await mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    try {
      openExternalURLSecurely(url);
    } catch (error) {
      console.error(`[SECURITY] Failed to open URL securely: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
    return { action: 'deny' };
  });
}

app.on('window-all-closed', () => {
  if (!isMac) {
    app.quit();
  }
});

app.on('activate', async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    await createWindow();
  }
});

app.whenReady().then(async () => {
  registerIpcHandlers();
  await createWindow();
});

// Export the secure URL opening function for use by IPC handlers
export { openExternalURLSecurely };
