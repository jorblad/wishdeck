#!/usr/bin/env node
/**
 * Package the browser extension into a distributable zip.
 *
 * Usage: node build.js
 * Output: dist/wishdeck-extension.zip
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const files = [
  'manifest.json',
  'background.js',
  'options.html',
  'options.js',
  'README.md',
  'icon16.png',
  'icon48.png',
  'icon128.png',
];

const distDir = path.resolve(__dirname, 'dist');
const outFile = path.join(distDir, 'wishdeck-extension.zip');

fs.mkdirSync(distDir, { recursive: true });

const existingFiles = files.filter((f) => fs.existsSync(path.resolve(__dirname, f)));
if (!existingFiles.length) {
  console.error('No extension files found.');
  process.exit(1);
}

// Remove old package if it exists.
if (fs.existsSync(outFile)) {
  fs.unlinkSync(outFile);
}

const fileList = existingFiles.map((f) => `"${f}"`).join(' ');
execSync(`zip -j "${outFile}" ${fileList}`, { cwd: __dirname, stdio: 'inherit' });
console.log(`Created ${outFile} (${existingFiles.length} files)`);
