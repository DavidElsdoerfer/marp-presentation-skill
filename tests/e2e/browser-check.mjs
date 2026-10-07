// Browser-Prüfung mit puppeteer-core (kommt mit marp-cli im npx-Cache).
//   node browser-check.mjs <puppeteer-core-dir> <chrome> live <md-datei> <url> <suchtext> <ersatz>
//   node browser-check.mjs <puppeteer-core-dir> <chrome> html <html-datei>
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const [, , pptrDir, chrome, mode, ...rest] = process.argv;
const puppeteer = (await import(pathToFileURL(`${pptrDir}/lib/esm/puppeteer/puppeteer-core.js`).href)).default;
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--no-sandbox'] });
const out = {};
try {
  const page = await browser.newPage();
  if (mode === 'live') {
    const [mdFile, url, search, replace] = rest;
    await page.goto(url, { waitUntil: 'networkidle0' });
    out.before = await page.$eval('h1', (e) => e.textContent);
    fs.writeFileSync(mdFile, fs.readFileSync(mdFile, 'utf8').replace(search, replace));
    await new Promise((r) => setTimeout(r, 4000));
    out.after = await page.$eval('h1', (e) => e.textContent);
  } else if (mode === 'html') {
    const [file] = rest;
    const failed = [];
    page.on('requestfailed', (r) => failed.push(r.url().slice(0, 80)));
    await page.goto('file://' + file, { waitUntil: 'networkidle0' });
    out.imagesLoaded = await page.$$eval('img', (els) => els.every((e) => e.complete && e.naturalWidth > 0));
    out.failedRequests = failed;
    await page.bringToFront();
    await page.keyboard.press('p');
    await new Promise((r) => setTimeout(r, 3000));
    const urls = browser.targets().filter((t) => t.type() === 'page').map((t) => t.url());
    const presenter = (await browser.pages()).find((p) => p.url().includes('view=presenter'));
    out.presenterUrl = urls.find((u) => u.includes('view=presenter')) || null;
    out.presenterTitle = presenter ? await presenter.title() : null;
  }
} finally {
  await browser.close();
}
console.log(JSON.stringify(out));
