#!/usr/bin/env node
// Optional: prepare a 视频号 (WeChat Channels) post in a browser YOU already logged in to.
// This script stores no account or login state. Start your own Chrome with
//   chrome --remote-debugging-port=9222 --user-data-dir=<your own profile dir>
// log in to the creator platform manually, then run:
//   CDP_URL=http://127.0.0.1:9222 node scripts/upload_channels_cdp.mjs --video deliver/x.mp4 --desc "..."
// It opens the post page, attaches the video and fills the description, then STOPS.
// A human reviews and clicks 发表. Selectors change often; adjust UPLOAD_URL / selectors.
import path from 'node:path';
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const CDP_URL = process.env.CDP_URL || 'http://127.0.0.1:9222';
const UPLOAD_URL = process.env.CHANNELS_UPLOAD_URL || 'https://channels.weixin.qq.com/platform/post/create';
const video = arg('video'); const desc = arg('desc', '');
if (!video) { console.error('--video required'); process.exit(2); }
const { default: puppeteer } = await import('puppeteer-core');
const browser = await puppeteer.connect({ browserURL: CDP_URL, defaultViewport: null });
const page = await browser.newPage();
await page.goto(UPLOAD_URL, { waitUntil: 'networkidle2' });
if (/login/i.test(page.url())) { console.error('Not logged in: log in manually in this browser first'); process.exit(3); }
const input = await page.waitForSelector('input[type=file]', { timeout: 30000 });
await input.uploadFile(path.resolve(video));
if (desc) {
  const box = await page.waitForSelector('[contenteditable], textarea', { timeout: 30000 });
  await box.click(); await page.keyboard.type(desc, { delay: 20 });
}
console.log('Video attached and description filled. Review in the browser and publish manually.');
browser.disconnect();
