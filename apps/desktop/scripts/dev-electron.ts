import { spawn, ChildProcess } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { context } from 'esbuild';
import waitOn from 'wait-on';

interface ProcessError extends Error {
  code?: string | number;
  signal?: string;
  killed?: boolean;
}

const require = createRequire(import.meta.url);
const electronBinary: string = require('electron');

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const mainEntry = resolve(projectRoot, 'src/main/main.ts');
const preloadEntry = resolve(projectRoot, 'src/main/preload.ts');
const outDir = resolve(projectRoot, 'dist/main');
const mainBundle = resolve(outDir, 'main.js');

let electronProcess: ChildProcess | null = null;
let buildContext: Awaited<ReturnType<typeof context>> | null = null;
let isShuttingDown = false;
let restartAttempts = 0;
const MAX_RESTART_ATTEMPTS = 5;
const RESTART_DELAY = 2000;

async function createBuilder() {
  try {
    buildContext = await context({
      entryPoints: [mainEntry, preloadEntry],
      bundle: true,
      platform: 'node',
      target: ['node20'],
      outdir: outDir,
      sourcemap: 'inline',
      external: ['electron'],
    });

    await buildContext.watch({
      onRebuild(error: any) {
        if (error) {
          console.error('Electron main process build failed:', error.message);
          logProcessEvent('build-error', { error: error.message });
          return;
        }
        console.log('[esbuild] main process rebuilt');
        logProcessEvent('build-success');
        restartElectron();
      },
    });

    await buildContext.rebuild();
    logProcessEvent('build-initial-success');
    return buildContext;
  } catch (error) {
    const err = error as ProcessError;
    console.error('Failed to create build context:', err.message);
    logProcessEvent('build-context-error', { error: err.message, code: err.code });
    throw err;
  }
}

function launchElectron() {
  if (electronProcess || isShuttingDown) {
    return;
  }

  try {
    logProcessEvent('electron-launch-attempt', { attempt: restartAttempts + 1 });
    
    electronProcess = spawn(
      electronBinary,
      [mainBundle],
      {
        stdio: 'inherit',
        env: {
          ...process.env,
          VITE_DEV_SERVER_URL: process.env.VITE_DEV_SERVER_URL ?? 'http://127.0.0.1:5173',
        },
      },
    );

    electronProcess.on('exit', (code, signal) => {
      logProcessEvent('electron-exit', { code, signal, killed: electronProcess?.killed });
      
      if (code !== null && code !== 0 && !isShuttingDown) {
        console.error(`Electron exited with code ${code}${signal ? ` (signal: ${signal})` : ''}`);
        
        if (restartAttempts < MAX_RESTART_ATTEMPTS) {
          restartAttempts++;
          console.log(`Attempting to restart Electron (attempt ${restartAttempts}/${MAX_RESTART_ATTEMPTS})...`);
          
          setTimeout(() => {
            electronProcess = null;
            launchElectron();
          }, RESTART_DELAY);
        } else {
          console.error('Max restart attempts reached. Please check the logs and restart manually.');
          logProcessEvent('electron-max-restarts-reached');
        }
      } else {
        restartAttempts = 0; // Reset on successful exit
      }
      
      electronProcess = null;
    });

    electronProcess.on('error', (error: ProcessError) => {
      console.error('Electron process error:', error.message);
      logProcessEvent('electron-process-error', { 
        error: error.message, 
        code: error.code,
        signal: error.signal 
      });
      
      electronProcess = null;
      
      if (!isShuttingDown && restartAttempts < MAX_RESTART_ATTEMPTS) {
        restartAttempts++;
        console.log(`Restarting Electron after error (attempt ${restartAttempts}/${MAX_RESTART_ATTEMPTS})...`);
        
        setTimeout(() => {
          launchElectron();
        }, RESTART_DELAY);
      }
    });

    electronProcess.on('spawn', () => {
      console.log('Electron process spawned successfully');
      logProcessEvent('electron-spawn-success');
      restartAttempts = 0; // Reset on successful spawn
    });

  } catch (error) {
    const err = error as ProcessError;
    console.error('Failed to launch Electron:', err.message);
    logProcessEvent('electron-launch-error', { error: err.message, code: err.code });
    
    electronProcess = null;
    
    if (!isShuttingDown && restartAttempts < MAX_RESTART_ATTEMPTS) {
      restartAttempts++;
      setTimeout(() => {
        launchElectron();
      }, RESTART_DELAY);
    }
  }
}

function restartElectron() {
  if (isShuttingDown) {
    return;
  }

  if (!electronProcess) {
    launchElectron();
    return;
  }

  logProcessEvent('electron-restart-initiated');
  
  // Set a timeout to force kill if graceful shutdown fails
  const forceKillTimeout = setTimeout(() => {
    if (electronProcess && !electronProcess.killed) {
      console.warn('Electron process did not exit gracefully, force killing...');
      logProcessEvent('electron-force-kill');
      electronProcess.kill('SIGKILL');
    }
  }, 5000);

  electronProcess.removeAllListeners('exit');
  electronProcess.once('exit', (code, signal) => {
    clearTimeout(forceKillTimeout);
    logProcessEvent('electron-restart-exit', { code, signal });
    electronProcess = null;
    
    if (!isShuttingDown) {
      // Small delay to ensure clean restart
      setTimeout(() => {
        launchElectron();
      }, 500);
    }
  });

  try {
    electronProcess.kill('SIGTERM');
  } catch (error) {
    const err = error as ProcessError;
    console.error('Error killing Electron process:', err.message);
    logProcessEvent('electron-kill-error', { error: err.message });
    clearTimeout(forceKillTimeout);
    electronProcess = null;
    
    if (!isShuttingDown) {
      launchElectron();
    }
  }
}

function logProcessEvent(event: string, data?: Record<string, unknown>) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [DEV-ELECTRON] ${event}`, data ? JSON.stringify(data) : '');
}

async function gracefulShutdown(signal: string) {
  if (isShuttingDown) {
    return;
  }
  
  isShuttingDown = true;
  logProcessEvent('shutdown-initiated', { signal });
  
  console.log(`Received ${signal}, shutting down gracefully...`);
  
  // Kill Electron process first
  if (electronProcess && !electronProcess.killed) {
    try {
      electronProcess.kill('SIGTERM');
      
      // Wait for Electron to exit or force kill after timeout
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          if (electronProcess && !electronProcess.killed) {
            console.warn('Force killing Electron process...');
            electronProcess.kill('SIGKILL');
          }
          resolve();
        }, 3000);
        
        if (electronProcess) {
          electronProcess.once('exit', () => {
            clearTimeout(timeout);
            resolve();
          });
        } else {
          clearTimeout(timeout);
          resolve();
        }
      });
    } catch (error) {
      const err = error as ProcessError;
      console.error('Error during Electron shutdown:', err.message);
      logProcessEvent('shutdown-electron-error', { error: err.message });
    }
  }
  
  // Dispose build context
  if (buildContext) {
    try {
      await buildContext.dispose();
      logProcessEvent('build-context-disposed');
    } catch (error) {
      const err = error as ProcessError;
      console.error('Error disposing build context:', err.message);
      logProcessEvent('shutdown-build-error', { error: err.message });
    }
  }
  
  logProcessEvent('shutdown-complete');
  process.exit(0);
}

async function waitForDevServer() {
  const devServerUrl = process.env.VITE_DEV_SERVER_URL ?? 'http://127.0.0.1:5173';
  
  try {
    logProcessEvent('waiting-for-dev-server', { url: devServerUrl });
    
    await waitOn({
      resources: [devServerUrl],
      timeout: 30000,
      interval: 1000,
      window: 1000,
    });
    
    logProcessEvent('dev-server-ready', { url: devServerUrl });
  } catch (error) {
    const err = error as ProcessError;
    console.error('Dev server failed to start within timeout:', err.message);
    logProcessEvent('dev-server-timeout', { error: err.message, url: devServerUrl });
    throw new Error(`Development server at ${devServerUrl} is not responding. Please ensure Vite is running.`);
  }
}

async function main() {
  try {
    logProcessEvent('main-start');
    
    // Create build context
    await createBuilder();
    
    // Set up signal handlers for graceful shutdown
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));
    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    
    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
      console.error('Uncaught exception:', error);
      logProcessEvent('uncaught-exception', { error: error.message, stack: error.stack });
      gracefulShutdown('uncaughtException');
    });
    
    process.on('unhandledRejection', (reason, promise) => {
      console.error('Unhandled rejection at:', promise, 'reason:', reason);
      logProcessEvent('unhandled-rejection', { reason: String(reason) });
      gracefulShutdown('unhandledRejection');
    });

    // Wait for dev server to be ready
    await waitForDevServer();

    // Launch Electron
    launchElectron();
    
    logProcessEvent('main-complete');
  } catch (error) {
    const err = error as ProcessError;
    console.error('Failed to start development environment:', err.message);
    logProcessEvent('main-error', { error: err.message, stack: err.stack });
    process.exit(1);
  }
}

main().catch((error: ProcessError) => {
  console.error('Failed to start Electron dev runner:', error.message);
  logProcessEvent('main-catch-error', { error: error.message, stack: error.stack });
  process.exit(1);
});
