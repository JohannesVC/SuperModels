//            TOP TIPS
//         -----------------
// 1. ctrl + F5 to start debugging (launch.json)
// 2. npx electron-packager . electronChat --platform=win32 --arch=x64 --out=dist --overwrite

import { app, BrowserWindow, ipcMain } from 'electron';
import path, { dirname } from 'path';
import { fileURLToPath } from 'url';
import { spawn  } from 'child_process';

import { createRequire } from 'module';
const require = createRequire(import.meta.url);

const __dirname = dirname(fileURLToPath(import.meta.url));
const htmlPath = path.join(__dirname, '../renderer/index.html');

let win;

function createWindow() {
  if (require('electron-squirrel-startup')) return;

  win = new BrowserWindow({
    fullscreen: false,
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#262626',
      symbolColor: '#FFFFFF',
      height: 60
    },
    fullscreenable: false,
    autoHideMenuBar: true,
    icon: path.join(__dirname, '../renderer/icons/favicon.ico'),
    width: 800,
    height: 1000,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: true, // secure: true      
      // enableRemoteModule: true,
      preload: path.join(__dirname, 'preload.mjs'),
      // devTools: false, // use this to disable
    }
  });

  // win.webContents.openDevTools()
  win.loadFile(htmlPath);
}
app.whenReady().then(createWindow);

// python integration
let pythonExe;
let mainPy;
let cleanupPy;

if (app.isPackaged) {
  const basePath = process.resourcesPath;
  pythonExe = path.join(basePath, 'python', 'miniconda', 'envs', 'supmodenv', 'python.exe');
  mainPy = path.join(basePath, 'python', 'main.py');
  cleanupPy = path.join(basePath, 'python', 'cleanup.py');
} else {
  pythonExe = path.join(__dirname, "../../python/miniconda/envs/supmodenv/python.exe");
  mainPy = path.join(__dirname, '../../python/main.py');
  cleanupPy = path.join(__dirname, '../../python/cleanup.py');
}

ipcMain.on('run-python-script', (event, args) => {
  const pythonProcess = spawn(pythonExe, [mainPy, args]);

  // console.log("pythonExe path is:", pythonExe)

  // to the python
  pythonProcess.stdin.write(args + '\n');
  pythonProcess.stdin.end();

  // from python back
  pythonProcess.stdout.on('data', (data) => {
    event.sender.send(`python-output`, data.toString());
  });

  pythonProcess.stderr.on('data', (data) => {
    event.sender.send('python-error', data.toString());
  });

  pythonProcess.on('close', (code) => {
    event.sender.send('python-exit', code);
  });
});

let isQuitting = false;
let cleanupDone = false; 

app.on('before-quit', (event) => {
  console.log("Received 'before-quit' event.");
  if (isQuitting && cleanupDone) {
    console.log("Cleanup already completed. Allowing app to quit.");
    return; // Allow the app to quit
  }

  if (!isQuitting) {
    console.log("First time 'before-quit' event. Preventing default and starting cleanup.");
    event.preventDefault(); // Prevent the default quit behavior the first time
    isQuitting = true;      // Set the flag to indicate that quitting process has started

    const cleanupProcess = spawn(pythonExe, [cleanupPy], {
      stdio: 'ignore',
      shell: true,
      windowsHide: true
    });

    cleanupProcess.on('close', (code) => {
      console.log(`Cleanup process exited with code ${code}`);
      cleanupDone = true; // Set cleanup done flag
      app.quit();  // Try quitting the app again
    });

    cleanupProcess.on('error', (error) => {
      console.error('Error with the cleanup process:', error);
      cleanupDone = true; // Set cleanup done flag
      app.quit();  // Try quitting the app again, even if cleanup failed
    });
  } else {
    console.log("Cleanup in progress. Preventing app from quitting again.");
    event.preventDefault(); // Prevent quitting while cleanup is in progress
  }
});



ipcMain.on('open-external', (event, url) => {
  shell.openExternal(url);
});

// function createPopupWindow() {
//   popup = new BrowserWindow({
//     width: 750,
//     height: 900,
//     autoHideMenuBar: true,
//     parent: win,
//     titleBarStyle: 'hidden',
//     titleBarOverlay: {
//       color: '#262626',
//       symbolColor: '#FFFFFF',
//       height: 60
//     },
//     // modal: true,
//     webPreferences: {
//       nodeIntegration: true,
//       contextIsolation: true,
//       // enableRemoteModule: true,
//       preload: path.join(__dirname, 'preload.mjs'),
//       // You can also set a separate preload script for popup if needed
//     }
//   });
//   popup.webContents.openDevTools()

//   popup.loadFile(modalPath);
// }



// ipcMain.on('open-popup', () => {
//   createPopupWindow();
// });

// ipcMain.on('close-popup', (event, arg) => {
//   if (popup) {
//     console.log('closing popup')
//     popup.close();
//     popup = null;
//   }
// });
