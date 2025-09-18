import { spawn, ChildProcess } from 'node:child_process';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { context } from 'esbuild';
import waitOn from 'wait-on';

const require = createRequire(import.meta.url);
const electronBinary: string = require('electron');

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const mainEntry = resolve(projectRoot, 'src/main/main.ts');
const preloadEntry = resolve(projectRoot, 'src/main/preload.ts');
const outDir = resolve(projectRoot, 'dist/main');
const mainBundle = resolve(outDir, 'main.js');

let electronProcess: ChildProcess | null = null;

async function createBuilder() {
  const buildContext = await context({
    entryPoints: [mainEntry, preloadEntry],
    bundle: true,
    platform: 'node',
    target: ['node20'],
    outdir: outDir,
    sourcemap: 'inline',
    external: ['electron'],
  });

  await buildContext.watch({
    onRebuild(error) {
      if (error) {
        console.error('Electron main process build failed:', error.message);
        return;
      }
      console.log('[esbuild] main process rebuilt');
      restartElectron();
    },
  });

  await buildContext.rebuild();
  return buildContext;
}

function launchElectron() {
  if (electronProcess) {
    return;
  }

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

  electronProcess.on('exit', (code) => {
    if (code !== null && code !== 0) {
      console.error(`Electron exited with code ${code}`);
    }
    electronProcess = null;
  });
}

function restartElectron() {
  if (!electronProcess) {
    launchElectron();
    return;
  }
  electronProcess.removeAllListeners('exit');
  electronProcess.kill('SIGTERM');
  electronProcess.once('exit', () => {
    electronProcess = null;
    launchElectron();
  });
}

async function main() {
  const buildContext = await createBuilder();
  process.on('SIGINT', async () => {
    if (electronProcess) {
      electronProcess.kill('SIGTERM');
    }
    await buildContext.dispose();
    process.exit(0);
  });
  process.on('SIGTERM', async () => {
    if (electronProcess) {
      electronProcess.kill('SIGTERM');
    }
    await buildContext.dispose();
    process.exit(0);
  });

  await waitOn({
    resources: [process.env.VITE_DEV_SERVER_URL ?? 'http://127.0.0.1:5173'],
    timeout: 30000,
  });

  launchElectron();
}

main().catch((error) => {
  console.error('Failed to start Electron dev runner:', error);
  process.exit(1);
});
