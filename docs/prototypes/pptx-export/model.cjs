// Prototyp: Marp-Markdown -> JSON-Modell (Folien, Direktiven, Blöcke, Inline-Läufe, Notizen, Frontmatter).
//
//   MARP_CORE=<pfad zu @marp-team/marp-core> node model.cjs deck.md > model.json
//
// marp-core liefert marp-cli mit (npx-Cache: ~/.npm/_npx/<hash>/node_modules/@marp-team/marp-core). Ohne MARP_CORE wird dort gesucht.
// Tokenfolge von marp.markdown.parse(md, {}) je Folie: marpit_slide_open (meta.marpitDirectives = Direktiven wie {class: "title"}),
// front_matter (nur Folie 1), marpit_comment (meta.marpitParsedDirectives leer = Sprechernotiz, sonst Direktive), heading_*, paragraph_*,
// bullet_list_*/ordered_list_* (Verschachtelung über open/close zählen), table_*, fence, html_block, inline (children = Inline-Tokens).
const fs = require('fs');
const path = require('path');

function findMarpCore() {
  if (process.env.MARP_CORE) return process.env.MARP_CORE;
  const root = path.join(process.env.HOME || '', '.npm', '_npx');
  for (const h of fs.existsSync(root) ? fs.readdirSync(root) : []) {
    const p = path.join(root, h, 'node_modules', '@marp-team', 'marp-core');
    if (fs.existsSync(p)) return p;
  }
  throw new Error('marp-core nicht gefunden (MARP_CORE setzen oder einmal `npx @marp-team/marp-cli@4.1.2 --version` ausführen)');
}
const { Marp } = require(findMarpCore());

const md = fs.readFileSync(process.argv[2], 'utf8');
const marp = new Marp({ html: true });
const tokens = marp.markdown.parse(md, {});

// Inline-Token -> Läufe {t, b, i, s, code, link} bzw. {image: {src, alt}}
function runs(inline) {
  const out = [];
  let st = { b: false, i: false, s: false, link: null };
  for (const c of inline.children || []) {
    if (c.type === 'text') out.push({ t: c.content, ...st });
    else if (c.type === 'softbreak' || c.type === 'hardbreak') out.push({ t: '\n', ...st });
    else if (c.type === 'code_inline') out.push({ t: c.content, ...st, code: true });
    else if (c.type === 'strong_open') st = { ...st, b: true };
    else if (c.type === 'strong_close') st = { ...st, b: false };
    else if (c.type === 'em_open') st = { ...st, i: true };
    else if (c.type === 'em_close') st = { ...st, i: false };
    else if (c.type === 's_open') st = { ...st, s: true };
    else if (c.type === 's_close') st = { ...st, s: false };
    else if (c.type === 'link_open') st = { ...st, link: c.attrGet('href') };
    else if (c.type === 'link_close') st = { ...st, link: null };
    else if (c.type === 'image') out.push({ image: { src: c.attrGet('src'), alt: c.content } });   // alt enthält Marp-Schlüsselwörter (w:300, bg, left)
    else if (c.type === 'html_inline' && /^<br\s*\/?>/i.test(c.content)) out.push({ t: '\n', ...st });
  }
  return out;
}

const slides = [];
let cur = null, slot = null, table = null, row = null, quote = 0;
const listStack = [];
let frontmatter = '';
for (let i = 0; i < tokens.length; i++) {
  const t = tokens[i];
  if (t.type === 'marpit_slide_open') { cur = { index: t.meta.marpitSlide, directives: t.meta.marpitDirectives || {}, notes: [], blocks: [] }; slides.push(cur); slot = null; continue; }
  if (t.type === 'marpit_slide_close') { cur = null; continue; }
  if (t.type === 'front_matter') { frontmatter = typeof t.meta === 'string' ? t.meta : (t.content || ''); continue; }   // YAML-Text der Frontmatter (nur Folie 1)
  if (!cur) continue;
  const push = (b) => { b.slot = slot; cur.blocks.push(b); };
  if (t.type === 'marpit_comment') {   // Kommentar ohne geparste Direktive = Sprechernotiz
    const d = t.meta && t.meta.marpitParsedDirectives;
    if (!d || !Object.keys(d).length) cur.notes.push(t.content.trim());
    continue;
  }
  if (t.type === 'heading_open') { push({ type: 'heading', level: +t.tag[1], runs: runs(tokens[i + 1]) }); i += 2; continue; }
  if (t.type === 'paragraph_open' && listStack.length === 0 && !table) {
    const r = runs(tokens[i + 1]);
    if (r.length === 1 && r[0].image) push({ type: 'image', ...r[0].image });
    else push({ type: quote ? 'quote' : 'paragraph', runs: r });
    i += 2; continue;
  }
  if (t.type === 'blockquote_open') { quote++; continue; }
  if (t.type === 'blockquote_close') { quote--; continue; }
  if (t.type === 'bullet_list_open' || t.type === 'ordered_list_open') {
    listStack.push({ ordered: t.type === 'ordered_list_open' });
    if (listStack.length === 1) push({ type: 'list', ordered: t.type === 'ordered_list_open', items: [] });   // Unterlisten werden Einträge mit level
    continue;
  }
  if (t.type === 'bullet_list_close' || t.type === 'ordered_list_close') { listStack.pop(); continue; }
  if (t.type === 'paragraph_open' && listStack.length) {
    const lst = cur.blocks[cur.blocks.length - 1];
    lst.items.push({ level: listStack.length - 1, ordered: listStack[listStack.length - 1].ordered, runs: runs(tokens[i + 1]) });
    i += 2; continue;
  }
  if (t.type === 'table_open') { table = { type: 'table', rows: [], header: true }; continue; }
  if (t.type === 'tr_open') { row = []; continue; }
  if (t.type === 'tr_close') { table.rows.push(row); continue; }
  if (t.type === 'th_open' || t.type === 'td_open') { row.push(runs(tokens[i + 1])); i += 2; continue; }
  if (t.type === 'table_close') { push(table); table = null; continue; }
  if (t.type === 'fence' || t.type === 'code_block') { push({ type: 'code', lang: t.info, text: t.content }); continue; }
  if (t.type === 'html_block') {
    // Spalten/Slots: <div> ohne Klasse. Ein html_block kann "</div>\n<div>" zugleich schließen und öffnen (daher erst das </div> entfernen).
    const rest = t.content.replace(/^\s*<\/div>\s*/i, '');
    const m = rest.match(/^\s*<div([^>]*)>/i);
    if (m && !/class=/.test(m[1])) { slot = slot === null ? 0 : slot + 1; continue; }
    if (rest.trim() === '') continue;
    // alles andere (Komponenten wie <div class="flow-3">) wird als HTML-Block mitgegeben und ist nicht direkt abbildbar
    push({ type: 'html', html: rest.trim(), classes: (rest.match(/class="([^"]+)"/) || [, ''])[1].split(/\s+/).filter(Boolean),
           text: rest.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() });
    continue;
  }
}
console.log(JSON.stringify({ frontmatter, slides }, null, 1));
