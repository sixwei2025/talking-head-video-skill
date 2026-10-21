#!/usr/bin/env node
// Optional HTML renderer (HyperFrames-style): loads templates/vertical.html in
// headless Chrome, steps a deterministic clock frame by frame, screenshots,
// and pipes PNGs into ffmpeg with the narration track.
//
// usage: node scripts/render_html.mjs --captions build/captions.json \
//          --segments segments.json --audio build/voice/voice.wav --out build/render.mp4
// env:   CHROME_PATH=/path/to/chrome  (required; puppeteer-core does not ship a browser)
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const here = path.dirname(fileURLToPath(import.meta.url));
const tpl = arg('template', path.join(here, '..', 'templates', 'vertical.html'));
const fps = Number(arg('fps', 30));
const captions = JSON.parse(readFileSync(arg('captions', 'build/captions.json'), 'utf8'));
const segments = JSON.parse(readFileSync(arg('segments', 'segments.json'), 'utf8'));
const timing = JSON.parse(readFileSync(arg('timing', 'build/voice/timing.json'), 'utf8'));
const audio = arg('audio', 'build/voice/voice.wav');
const out = arg('out', 'build/render.mp4');
const maxSec = Number(arg('max-seconds', 0));
if (!process.env.CHROME_PATH) { console.error('Set CHROME_PATH to a Chrome/Chromium binary'); process.exit(2); }

const { default: puppeteer } = await import('puppeteer-core');
const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH, headless: true,
  args: ['--no-sandbox', '--hide-scrollbars', '--force-device-scale-factor=1'] });
const page = await browser.newPage();
await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.resolve(tpl)).href);
await page.evaluate((d) => window.THV.load(d), { captions, segments, timing });
let dur = Math.max(...timing.map((t) => t.end)) + 0.15;
if (maxSec) dur = Math.min(dur, maxSec);
const n = Math.round(dur * fps);
const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-', '-i', audio,
  '-t', dur.toFixed(3), '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p',
  '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
for (let i = 0; i < n; i++) {
  await page.evaluate((f, r) => window.THV.seek(f, r), i, fps);
  const png = await page.screenshot({ type: 'png' });
  if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
  if (i % (fps * 5) === 0) console.log(`frame ${i}/${n}`);
}
ff.stdin.end();
await browser.close();
await new Promise((r, j) => ff.on('close', (c) => (c === 0 ? r() : j(new Error('ffmpeg ' + c)))));
console.log('rendered', out);
