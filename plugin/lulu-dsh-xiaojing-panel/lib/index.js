/**
 * dsh-xiaojing-panel —— 小鲸控制台（宿主侧）v0.3（防御式）
 *
 * 与 dsh-onebot-qq 并存：QQ 传输仍由它负责；本插件只做：
 *   1) 本机 HTTP API（默认 127.0.0.1:9877，占用自动顺延）：人设/曲库/音色/表情包/定时/服务；
 *   2) 定时任务调度（文本 或 脚本）；
 *   3) 表情包自动收录（扫描入站媒体目录，去重后进「收录」）。
 *
 * 稳定性约定（防止宿主崩溃）：
 *   - 本模块 apply() 内部全部 try/catch，任何异常只打印不抛；
 *   - HTTP server 监听失败（端口占用）自动换端口，绝不 uncaught；
 *   - 所有定时器回调都包 try/catch；
 *   - 不注册全局 process 监听、不改宿主状态。
 */
import { spawn } from 'node:child_process';
import { readFile, writeFile, readdir, mkdir, rename, unlink, copyFile, stat, open } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import { join, dirname, extname } from 'node:path';

export const name = 'lulu-dsh-xiaojing-panel';
export const inject = [];

const DEFAULT_CONFIG = {
    host: '127.0.0.1',
    port: 9877,
    workspaceDir: 'D:\\software\\QQBot\\workspace',
    voiceDir: 'D:\\software\\Voice',
    musicDirsFile: 'D:\\software\\QQBot\\曲库目录.txt',
    schedulesFile: 'D:\\software\\QQBot\\schedules.json',
    rvcModelFile: 'D:\\software\\Voice\\rvc_model.txt',
    napcatApi: 'http://127.0.0.1:13200',
    rvcRepo: 'D:\\software\\Voice\\cover\\rvc_pack\\Retrieval-based-Voice-Conversion-WebUI-main',
    python: 'D:\\software\\Voice\\py310\\python.exe',
    napcatLauncher: 'D:\\software\\QQBot\\run-napcat-log.bat',
    mediaDir: 'D:\\software\\QQBot\\media',
    corpusDir: 'D:\\software\\QQBot\\workspace\\语料库',
    paramsFile: 'D:\\software\\Voice\\params.json',
    profilePatch: '',   // 留空自动用 %USERPROFILE%\\.dsh\\profiles\\desktop\\cordis.patch.yml
    autoCollectMinutes: 5,
};

const IMAGE_EXT = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']);
const MIME = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp' };

const cfg = (config) => ({ ...DEFAULT_CONFIG, ...(config ?? {}) });

const readText = async (p, fallback = '') => {
    try { return await readFile(p, 'utf8'); }
    catch { return fallback; }
};
const writeText = async (p, text) => {
    await mkdir(dirname(p), { recursive: true });
    await writeFile(p, text, 'utf8');
};

let netMod = null;
async function portOpen(port) {
    try {
        if (netMod === null) netMod = await import('node:net');
        const { connect } = netMod;
        return await new Promise((resolve) => {
            const socket = connect({ port, host: '127.0.0.1' });
            const done = (v) => { try { socket.destroy(); } catch { } resolve(v); };
            socket.setTimeout(700);
            socket.once('connect', () => done(true));
            socket.once('timeout', () => done(false));
            socket.once('error', () => done(false));
        });
    }
    catch { return false; }
}

async function listImages(dir) {
    try {
        const names = await readdir(dir);
        const out = [];
        for (const n of names) {
            if (!IMAGE_EXT.has(extname(n).toLowerCase())) continue;
            const p = join(dir, n);
            try {
                const st = await stat(p);
                if (!st.isFile()) continue;
                out.push({ name: n, size: st.size, mtime: Math.floor(st.mtimeMs / 1000) });
            }
            catch { }
        }
        out.sort((a, b) => b.mtime - a.mtime);
        return out;
    }
    catch { return []; }
}

function safeJoin(dir, name) {
    if (!name || name.includes('/') || name.includes('\\') || name.includes('..')) return null;
    return join(dir, name);
}

async function sendImage(res, path) {
    try {
        const st = await stat(path);
        const fh = await open(path, 'r');
        res.writeHead(200, {
            'Content-Type': MIME[extname(path).toLowerCase()] ?? 'application/octet-stream',
            'Content-Length': st.size,
            'Cache-Control': 'no-store',
            'Access-Control-Allow-Origin': '*',
        });
        const stream = fh.createReadStream();
        stream.on('error', () => { try { res.end(); } catch { } });
        stream.pipe(res);
    }
    catch {
        try { res.writeHead(404, { 'Access-Control-Allow-Origin': '*' }); res.end('not found'); } catch { }
    }
}

async function readSchedules(path) {
    try {
        const arr = JSON.parse(await readText(path, '[]'));
        return Array.isArray(arr) ? arr : [];
    }
    catch { return []; }
}
const writeSchedules = (path, items) => writeText(path, JSON.stringify(items, null, 2));

function startDetached(program, args, cwd) {
    try {
        const child = spawn(program, args, { cwd, detached: true, stdio: 'ignore', windowsHide: true });
        child.on('error', () => { });
        child.unref();
        return child.pid ?? 0;
    }
    catch { return 0; }
}

function killByPort(port) {
    return new Promise((resolve) => {
        try {
            const ps = spawn('powershell', ['-NoProfile', '-Command',
                `$c = Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($c) { Stop-Process -Id $c.OwningProcess -Force; 'killed' } else { 'none' }`],
                { windowsHide: true });
            let out = '';
            ps.stdout.on('data', (d) => { out += String(d); });
            ps.on('close', () => resolve(out.trim()));
            ps.on('error', () => resolve('error'));
        }
        catch { resolve('error'); }
    });
}

function jsonResponse(res, code, obj) {
    try {
        const body = JSON.stringify(obj);
        res.writeHead(code, {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Cache-Control': 'no-store',
        });
        res.end(body);
    }
    catch { }
}

function readBody(req) {
    return new Promise((resolve) => {
        let data = '';
        req.on('data', (chunk) => { data += chunk; if (data.length > 20 * 1024 * 1024) req.destroy(); });
        req.on('end', () => resolve(data));
        req.on('error', () => resolve(''));
    });
}

async function napcatSend(config, target, text) {
    const payload = target.type === 'group'
        ? { group_id: Number(target.id), message: [{ type: 'text', data: { text } }] }
        : { user_id: Number(target.id), message: [{ type: 'text', data: { text } }] };
    const url = config.napcatApi + (target.type === 'group' ? '/send_group_msg' : '/send_private_msg');
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    return res.json().catch(() => ({}));
}

const nowHM = () => {
    const d = new Date();
    return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
};
const dayKey = (d = new Date()) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');

async function fileHash(path) {
    const buf = await readFile(path);
    return createHash('md5').update(buf).digest('hex');
}


// ---------- 长文字图卡片（dsh-onebot 配置项）读写 ----------
function patchPath(C) {
    if (C.profilePatch) return C.profilePatch;
    const home = process.env.USERPROFILE || process.env.HOME || '.';
    return join(home, '.dsh', 'profiles', 'desktop', 'cordis.patch.yml');
}

function onebotBlock(text) {
    const m = text.match(/(^|\n)(- id: dsh-onebot\s*\n[\s\S]*?)(?=\n- (?:id:|insert:)|$)/);
    return m ? { body: m[2], start: m.index + m[1].length, end: m.index + m[1].length + m[2].length } : null;
}

function readCardConfig(text) {
    const block = onebotBlock(text);
    const body = block ? block.body : '';
    const num = (key, dflt) => {
        const m = body.match(new RegExp('(^|\\n)\\s*' + key + '\\s*:\\s*([-0-9.]+)'));
        return m ? Number(m[2]) : dflt;
    };
    const str = (key, dflt) => {
        const m = body.match(new RegExp('(^|\\n)\\s*' + key + '\\s*:\\s*[\'"]?([^\\n\'"]*)'));
        return m ? m[2].trim() : dflt;
    };
    const fontMatch = body.match(/(^|\n)\s*fontFiles\s*:\s*\[([^\]]*)\]/);
    let font = fontMatch ? (fontMatch[2].split(',')[0] || '').trim().replace(/^['"]|['"]$/g, '') : '';
    font = font.replace(/[\\\/]+/g, '/');
    font = font.replace(/^([A-Za-z]):\/?/, '$1:/');
    return {
        enabled: num('textImageThreshold', 200) > 0,
        threshold: num('textImageThreshold', 200),
        footer: str('cardFooter', '小鲸'),
        fontFile: font || 'C:\\Windows\\Fonts\\msyh.ttc',
        found: !!block,
    };
}

function writeCardConfig(text, cfg) {
    const block = onebotBlock(text);
    if (!block) return null;
    let body = block.body;
    const threshold = cfg.enabled ? Math.max(1, Number(cfg.threshold) || 200) : 0;
    const setKey = (key, line) => {
        const re = new RegExp('(^|\\n)(\\s*)' + key + '\\s*:[^\\n]*');
        if (re.test(body)) body = body.replace(re, '$1$2' + line);
        else body = body.replace(/\s*$/, '') + '\n    ' + line;
    };
    setKey('textImageThreshold', 'textImageThreshold: ' + threshold);
    setKey('cardFooter', "cardFooter: '" + String(cfg.footer || '小鲸').replace(/'/g, '') + "'");
    const fontPath = String(cfg.fontFile || 'C:/Windows/Fonts/msyh.ttc').replace(/\\/g, '/');
    setKey('fontFiles', "fontFiles: [ '" + fontPath + "' ]");
    setKey('fontFamilies', "fontFamilies: [ 'Microsoft YaHei' ]");
    return text.slice(0, block.start) + body + text.slice(block.end);
}

function buildHandler(C, dirs, state) {
    const { savedDir, collectDir } = dirs;

    async function collectOnce(force = false) {
        try {
            await mkdir(collectDir, { recursive: true });
            const existing = new Set();
            for (const item of await listImages(collectDir)) {
                try { existing.add(await fileHash(join(collectDir, item.name))); } catch { }
            }
            for (const item of await listImages(savedDir)) {
                try { existing.add(await fileHash(join(savedDir, item.name))); } catch { }
            }
            let files = [];
            try { files = await readdir(C.mediaDir); } catch { return { added: 0, skipped: 0 }; }
            const windowSec = force ? 3600 : Math.max(60, C.autoCollectMinutes * 60) * 2;
            const cutoff = Date.now() / 1000 - windowSec;
            let added = 0;
            let skipped = 0;
            for (const n of files) {
                if (!n.startsWith('media_') || !IMAGE_EXT.has(extname(n).toLowerCase())) continue;
                const p = join(C.mediaDir, n);
                try {
                    const st = await stat(p);
                    if (st.mtimeMs / 1000 < cutoff) continue;
                    const h = await fileHash(p);
                    if (existing.has(h)) { skipped++; continue; }
                    existing.add(h);
                    const ext = extname(n).toLowerCase();
                    const base = '收录_' + dayKey().replace(/-/g, '') + '_' + String(Date.now()).slice(-6) + ext;
                    await copyFile(p, join(collectDir, base));
                    added++;
                }
                catch { }
            }
            return { added, skipped };
        }
        catch { return { added: 0, skipped: 0 }; }
    }

    async function runTask(item) {
        try {
            if (item.script) {
                const scriptPath = item.script.startsWith(':') ? item.script.slice(1) : join(C.workspaceDir, item.script);
                return await new Promise((resolve) => {
                    try {
                        const child = spawn(C.python, [scriptPath, ...(Array.isArray(item.args) ? item.args : [])],
                            { cwd: C.workspaceDir, windowsHide: true, stdio: 'ignore' });
                        child.on('close', (code) => resolve({ ok: code === 0, code }));
                        child.on('error', () => resolve({ ok: false, code: -1 }));
                    }
                    catch { resolve({ ok: false, code: -1 }); }
                });
            }
            const targets = Array.isArray(item.targets) ? item.targets : [];
            for (const target of targets) {
                try { await napcatSend(C, target, String(item.text ?? '')); } catch { }
            }
            return { ok: true };
        }
        catch { return { ok: false }; }
    }

    async function handler(req, res) {
        try {
            const url = new URL(req.url ?? '/', 'http://127.0.0.1');
            if (req.method === 'OPTIONS') return jsonResponse(res, 204, {});

            if (url.pathname === '/ping') return jsonResponse(res, 200, { ok: true, name: 'xiaojing-panel', version: '0.4.1' });

            if (url.pathname === '/state') {
                const persona = await readText(join(C.workspaceDir, 'AGENTS.md'));
                const model = (await readText(C.rvcModelFile, '')).trim();
                let models = [];
                try { models = (await readdir(join(C.rvcRepo, 'assets', 'weights'))).filter((n) => n.toLowerCase().endsWith('.pth')); } catch { }
                return jsonResponse(res, 200, {
                    ok: true,
                    paths: C,
                    personaLen: persona.length,
                    musicDirs: await readText(C.musicDirsFile),
                    rvcModel: model,
                    rvcModels: models,
                    savedCount: (await listImages(savedDir)).length,
                    collectedCount: (await listImages(collectDir)).length,
                    schedules: await readSchedules(C.schedulesFile),
                    services: {
                        rvc: await portOpen(9850),
                        tts: await portOpen(9880),
                        napcat: await portOpen(13200),
                    },
                });
            }

            if (url.pathname === '/stickers')
                return jsonResponse(res, 200, { ok: true, saved: await listImages(savedDir), collected: await listImages(collectDir) });

            if (url.pathname === '/img') {
                const kind = url.searchParams.get('kind') === 'collected' ? 'collected' : 'saved';
                const name = url.searchParams.get('name') ?? '';
                const p = safeJoin(kind === 'collected' ? collectDir : savedDir, name);
                if (!p) return jsonResponse(res, 400, { ok: false, error: 'bad name' });
                return sendImage(res, p);
            }

            if (url.pathname === '/persona' && req.method === 'GET')
                return jsonResponse(res, 200, { ok: true, text: await readText(join(C.workspaceDir, 'AGENTS.md')) });
            if (url.pathname === '/persona' && req.method === 'POST') {
                const { text } = JSON.parse(await readBody(req) || '{}');
                if (typeof text !== 'string') return jsonResponse(res, 400, { ok: false, error: 'text required' });
                await writeText(join(C.workspaceDir, 'AGENTS.md'), text);
                return jsonResponse(res, 200, { ok: true, len: text.length });
            }

            if (url.pathname === '/music' && req.method === 'POST') {
                const { text } = JSON.parse(await readBody(req) || '{}');
                await writeText(C.musicDirsFile, String(text ?? ''));
                return jsonResponse(res, 200, { ok: true });
            }

            if (url.pathname === '/rvc-model' && req.method === 'POST') {
                const { model } = JSON.parse(await readBody(req) || '{}');
                if (!model) return jsonResponse(res, 400, { ok: false, error: 'model required' });
                await writeText(C.rvcModelFile, String(model));
                return jsonResponse(res, 200, { ok: true, model });
            }

            if (url.pathname === '/stickers/collect' && req.method === 'POST')
                return jsonResponse(res, 200, { ok: true, ...(await collectOnce(true)) });

            if (url.pathname === '/stickers/delete' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                const base = body.kind === 'collected' ? collectDir : savedDir;
                let n = 0;
                for (const name of body.names ?? []) {
                    const p = safeJoin(base, name);
                    if (p) { try { await unlink(p); n++; } catch { } }
                }
                return jsonResponse(res, 200, { ok: true, deleted: n });
            }

            if (url.pathname === '/stickers/rename' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                const base = body.kind === 'collected' ? collectDir : savedDir;
                const from = safeJoin(base, body.from);
                const to = safeJoin(base, body.to);
                if (!from || !to) return jsonResponse(res, 400, { ok: false, error: 'bad name' });
                await rename(from, to);
                return jsonResponse(res, 200, { ok: true });
            }

            if (url.pathname === '/stickers/promote' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                let n = 0;
                for (const name of body.names ?? []) {
                    const from = safeJoin(collectDir, name);
                    const target = safeJoin(savedDir, name);
                    if (!from || !target) continue;
                    try { await rename(from, target); n++; } catch { }
                }
                return jsonResponse(res, 200, { ok: true, moved: n });
            }

            if (url.pathname === '/schedules' && req.method === 'GET')
                return jsonResponse(res, 200, { ok: true, items: await readSchedules(C.schedulesFile) });
            if (url.pathname === '/schedules' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                if (!Array.isArray(body.items)) return jsonResponse(res, 400, { ok: false, error: 'items required' });
                await writeSchedules(C.schedulesFile, body.items);
                return jsonResponse(res, 200, { ok: true, count: body.items.length });
            }

            if (url.pathname === '/open' && req.method === 'POST') {
                const { path: target } = JSON.parse(await readBody(req) || '{}');
                if (!target) return jsonResponse(res, 400, { ok: false, error: 'path required' });
                startDetached('cmd', ['/c', 'start', '', target], C.workspaceDir);
                return jsonResponse(res, 200, { ok: true });
            }

            if (url.pathname === '/service' && req.method === 'POST') {
                const { name: svc, action } = JSON.parse(await readBody(req) || '{}');
                const table = {
                    rvc: { port: 9850, start: () => startDetached(C.python, [join(C.voiceDir, 'cover', 'rvc_server.py')], join(C.rvcRepo)) },
                    tts: { port: 9880, start: () => startDetached(C.python, [join(C.voiceDir, 'start-tts.py')], C.voiceDir) },
                    napcat: { port: 13200, start: () => startDetached('cmd', ['/c', C.napcatLauncher], C.workspaceDir) },
                };
                const item = table[svc];
                if (!item) return jsonResponse(res, 400, { ok: false, error: 'unknown service' });
                if (action === 'start') {
                    if (await portOpen(item.port)) return jsonResponse(res, 200, { ok: true, already: true });
                    item.start();
                    return jsonResponse(res, 200, { ok: true, starting: true });
                }
                if (action === 'stop') return jsonResponse(res, 200, { ok: true, out: await killByPort(item.port) });
                return jsonResponse(res, 400, { ok: false, error: 'action required' });
            }

            if (url.pathname === '/file') {
                const p = url.searchParams.get('path') ?? '';
                return jsonResponse(res, 200, { ok: true, path: p, text: (await readText(p, '')).slice(0, 200000) });
            }


            // ---------- 语料库 ----------
            if (url.pathname === '/corpus' && req.method === 'GET') {
                try { await mkdir(C.corpusDir, { recursive: true }); } catch { }
                let files = [];
                try {
                    const names = await readdir(C.corpusDir);
                    files = names.filter((n) => !n.startsWith('.')).sort();
                }
                catch { }
                return jsonResponse(res, 200, { ok: true, dir: C.corpusDir, files });
            }
            if (url.pathname === '/corpus/file' && req.method === 'GET') {
                const name = safeJoin(C.corpusDir, url.searchParams.get('name') ?? '');
                if (!name) return jsonResponse(res, 400, { ok: false, error: 'bad name' });
                return jsonResponse(res, 200, { ok: true, text: await readText(name, '') });
            }
            if (url.pathname === '/corpus/file' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                const target = safeJoin(C.corpusDir, body.name || '');
                if (!target) return jsonResponse(res, 400, { ok: false, error: 'bad name' });
                await writeText(target, String(body.text ?? ''));
                return jsonResponse(res, 200, { ok: true });
            }
            if (url.pathname === '/corpus/delete' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                const target = safeJoin(C.corpusDir, body.name || '');
                if (!target) return jsonResponse(res, 400, { ok: false, error: 'bad name' });
                try { await unlink(target); } catch { }
                return jsonResponse(res, 200, { ok: true });
            }

            // ---------- 语音/唱歌参数 ----------
            if (url.pathname === '/params' && req.method === 'GET') {
                let data = {};
                try { data = JSON.parse(await readText(C.paramsFile, '{}')); } catch { }
                return jsonResponse(res, 200, { ok: true, params: data, file: C.paramsFile });
            }
            if (url.pathname === '/params' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                if (typeof body.params !== 'object' || body.params === null)
                    return jsonResponse(res, 400, { ok: false, error: 'params required' });
                await writeText(C.paramsFile, JSON.stringify(body.params, null, 2));
                return jsonResponse(res, 200, { ok: true });
            }

            // ---------- 定时任务：立即测试发送 ----------
            if (url.pathname === '/schedules/test' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                const item = body.item || {};
                const result = [];
                if (item.script) {
                    const r = await runTask(item);
                    result.push({ script: item.script, ok: r.ok });
                }
                else {
                    for (const target of (Array.isArray(item.targets) ? item.targets : [])) {
                        try { const r = await napcatSend(C, target, String(item.text ?? '')); result.push({ target, ok: !!(r && (r.status === 'ok' || r.retcode === 0)) }); }
                        catch (e) { result.push({ target, ok: false, error: String(e) }); }
                    }
                }
                return jsonResponse(res, 200, { ok: true, result });
            }

            // ---------- 表情包批量加前缀 ----------
            if (url.pathname === '/stickers/prefix' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                const base = body.kind === 'collected' ? collectDir : savedDir;
                const prefix = String(body.prefix || '');
                let n = 0;
                for (const name of body.names ?? []) {
                    const from = safeJoin(base, name);
                    const to = safeJoin(base, prefix + name);
                    if (!from || !to) continue;
                    try { await rename(from, to); n++; } catch { }
                }
                return jsonResponse(res, 200, { ok: true, renamed: n });
            }


            // ---------- 长文字图卡片 ----------
            if (url.pathname === '/card' && req.method === 'GET') {
                const text = await readText(patchPath(C), '');
                return jsonResponse(res, 200, { ok: true, file: patchPath(C), config: readCardConfig(text) });
            }
            if (url.pathname === '/card' && req.method === 'POST') {
                const body = JSON.parse(await readBody(req) || '{}');
                const file = patchPath(C);
                const text = await readText(file, '');
                const next = writeCardConfig(text, body.config || {});
                if (next === null) return jsonResponse(res, 400, { ok: false, error: 'profile patch 里没找到 dsh-onebot 配置块' });
                await writeText(file, next);
                return jsonResponse(res, 200, { ok: true, needRestart: true });
            }

            return jsonResponse(res, 404, { ok: false, error: 'not found' });
        }
        catch (error) {
            try { jsonResponse(res, 500, { ok: false, error: error instanceof Error ? error.message : String(error) }); } catch { }
        }
    }

    return { handler, collectOnce, runTask };
}

export function apply(ctx, config) {
    try {
        const C = cfg(config);
        const savedDir = join(C.workspaceDir, 'stickers');
        const collectDir = join(savedDir, 'inbox');
        const state = { lastFired: new Map(), port: 0 };
        const api0 = buildHandler(C, { savedDir, collectDir }, state);
        const handler = api0.handler;
        const collectOnce = api0.collectOnce;
        const runTask = api0.runTask;

        const api = createServer((req, res) => { handler(req, res).catch(() => { }); });

        api.on('error', (error) => {
            try { console.error('[xiaojing-panel] server error:', error && error.message); } catch { }
        });

        const listenOn = (port, attempt) => {
            api.once('listening', () => {
                state.port = port;
                try { console.log('[xiaojing-panel] API on http://' + C.host + ':' + port); } catch { }
                setTimeout(() => { try { collectOnce(true).catch(() => { }); } catch { } }, 1500);
            });
            api.once('error', () => {
                if (attempt < 5) { try { api.close(); } catch { } setTimeout(() => listenOn(port + 1, attempt + 1), 300); }
            });
            try { api.listen(port, C.host); } catch { }
        };
        listenOn(C.port, 0);

        const collectTimer = setInterval(() => { try { collectOnce(false).catch(() => { }); } catch { } }, Math.max(1, C.autoCollectMinutes) * 60 * 1000);
        collectTimer.unref?.();

        const timer = setInterval(() => {
            (async () => {
                try {
                    const items = await readSchedules(C.schedulesFile);
                    const hm = nowHM();
                    const day = dayKey();
                    const weekday = new Date().getDay();
                    for (const item of items) {
                        if (!item || item.enabled === false) continue;
                        if (String(item.time ?? '') !== hm) continue;
                        if (Array.isArray(item.days) && item.days.length > 0 && item.days.includes(weekday) === false) continue;
                        if (state.lastFired.get(item.id) === day + '|' + hm) continue;
                        state.lastFired.set(item.id, day + '|' + hm);
                        try { await runTask(item); } catch { }
                    }
                }
                catch { }
            })().catch(() => { });
        }, 30000);
        timer.unref?.();

        try {
            ctx.effect?.(() => () => {
                try { clearInterval(timer); } catch { }
                try { clearInterval(collectTimer); } catch { }
                try { api.close(); } catch { }
            });
        }
        catch { }
    }
    catch (error) {
        try { console.error('[xiaojing-panel] apply failed (ignored):', error && error.message); } catch { }
    }
}
