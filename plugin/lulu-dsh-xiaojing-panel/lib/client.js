/**
 * dsh-xiaojing-panel — 客户端设置面板（「小鲸控制台」）v0.3
 *
 * 与宿主侧 lib/index.js 的本机 HTTP API 通信（默认 http://127.0.0.1:9877）。
 * 只依赖 react（宿主冻结模块），不注册 Typert Remote，避免宿主侧契约冲突。
 */
window.__ModuleLoader__.load({
    id: 'lulu-dsh-xiaojing-panel',
    factory: (require) => {
        const module = { exports: {} };
        const reactModule = require('react');
        const React = reactModule != null && typeof reactModule.createElement === 'function'
            ? reactModule
            : reactModule.default;
        if (React == null || typeof React.createElement !== 'function')
            throw new Error('dsh-xiaojing-panel client: react 不可用');

        const P = React.createElement;
        const API = 'http://127.0.0.1:9877';

        const S = {
            wrap: { padding: '4px 2px', color: 'inherit', font: 'inherit' },
            title: { fontSize: 18, fontWeight: 600, margin: '0 0 4px' },
            desc: { opacity: 0.65, fontSize: 12, margin: '0 0 14px' },
            tabs: { display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 },
            tab: { padding: '6px 12px', borderRadius: 8, border: '1px solid rgba(127,127,127,.35)', cursor: 'pointer', background: 'transparent', color: 'inherit' },
            tabOn: { padding: '6px 12px', borderRadius: 8, border: '1px solid #3b82f6', background: 'rgba(59,130,246,.15)', cursor: 'pointer', color: 'inherit' },
            card: { border: '1px solid rgba(127,127,127,.3)', borderRadius: 10, padding: 12, marginBottom: 12 },
            subTitle: { fontSize: 14, fontWeight: 600, margin: '4px 0 8px' },
            label: { fontSize: 13, fontWeight: 600, marginBottom: 6, display: 'block' },
            hint: { fontSize: 11, opacity: 0.6, margin: '4px 0 8px' },
            row: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginBottom: 8 },
            textarea: { width: '100%', minHeight: 260, fontFamily: 'ui-monospace,Consolas,monospace', fontSize: 12, padding: 8, borderRadius: 8, border: '1px solid rgba(127,127,127,.35)', background: 'rgba(127,127,127,.08)', color: 'inherit', resize: 'vertical' },
            input: { flex: 1, minWidth: 160, padding: '6px 8px', borderRadius: 8, border: '1px solid rgba(127,127,127,.35)', background: 'rgba(127,127,127,.08)', color: 'inherit' },
            btn: { padding: '6px 14px', borderRadius: 8, border: '1px solid rgba(127,127,127,.35)', cursor: 'pointer', background: 'transparent', color: 'inherit' },
            btnPrimary: { padding: '6px 14px', borderRadius: 8, border: '1px solid #3b82f6', cursor: 'pointer', background: 'rgba(59,130,246,.18)', color: 'inherit' },
            btnDanger: { padding: '6px 12px', borderRadius: 8, border: '1px solid #ef4444', cursor: 'pointer', background: 'rgba(239,68,68,.12)', color: 'inherit' },
            ok: { color: '#22c55e', fontSize: 12 },
            err: { color: '#ef4444', fontSize: 12, whiteSpace: 'pre-wrap' },
            dot: { width: 8, height: 8, borderRadius: 4, display: 'inline-block', marginRight: 6 },
            grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(104px,1fr))', gap: 8 },
            tile: { border: '1px solid rgba(127,127,127,.25)', borderRadius: 8, padding: 4, textAlign: 'center', cursor: 'pointer' },
            tileOn: { border: '2px solid #3b82f6', borderRadius: 8, padding: 3, textAlign: 'center', cursor: 'pointer' },
            thumb: { width: '100%', height: 72, objectFit: 'contain', background: 'rgba(127,127,127,.08)', borderRadius: 6 },
            cap: { fontSize: 10, opacity: 0.8, wordBreak: 'break-all', marginTop: 2 },
            small: { fontSize: 12 },
            schedCard: { border: '1px dashed rgba(127,127,127,.35)', borderRadius: 8, padding: 10, marginBottom: 10 },
        };

        async function api(path, opts) {
            const res = await fetch(API + path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts ?? {}));
            const data = await res.json().catch(() => ({}));
            if (!res.ok || data.ok === false) throw new Error(data.error || ('HTTP ' + res.status));
            return data;
        }

        const imgUrl = (kind, name) => API + '/img?kind=' + kind + '&name=' + encodeURIComponent(name);

        function Panel() {
            const [tab, setTab] = React.useState('persona');
            const [state, setState] = React.useState(null);
            const [busy, setBusy] = React.useState(false);
            const [msg, setMsg] = React.useState(null);
            const [persona, setPersona] = React.useState('');
            const [music, setMusic] = React.useState('');
            const [model, setModel] = React.useState('');
            const [saved, setSaved] = React.useState([]);
            const [collected, setCollected] = React.useState([]);
            const [picked, setPicked] = React.useState({});
            const [schedules, setSchedules] = React.useState([]);
            const [showJson, setShowJson] = React.useState(false);
            const [openSec, setOpenSec] = React.useState({ saved: true, collected: false });
            const [corpus, setCorpus] = React.useState({ dir: '', files: [] });
            const [corpusName, setCorpusName] = React.useState('');
            const [corpusText, setCorpusText] = React.useState('');
            const [params, setParams] = React.useState(null);
            const [bigImg, setBigImg] = React.useState(null);
            const [cardCfg, setCardCfg] = React.useState(null);
            const [kw, setKw] = React.useState({ saved: '', collected: '' });
            const [jsonText, setJsonText] = React.useState('[]');

            const load = React.useCallback(async () => {
                setBusy(true);
                try {
                    const st = await api('/state');
                    setState(st);
                    setMusic(st.musicDirs || '');
                    setModel(st.rvcModel || '');
                    setSchedules(st.schedules || []);
                    setJsonText(JSON.stringify(st.schedules || [], null, 2));
                    const p = await api('/persona');
                    setPersona(p.text || '');
                    const sk = await api('/stickers');
                    setSaved(sk.saved || []);
                    setCollected(sk.collected || []);
                    try { const cp = await api('/corpus'); setCorpus(cp); } catch { }
                    try { const pm = await api('/params'); setParams(pm.params || null); } catch { }
                    try { const cd = await api('/card'); setCardCfg(cd.config || null); } catch { }
                    setMsg(null);
                }
                catch (e) {
                    setMsg({ type: 'err', text: '连不上控制台服务（127.0.0.1:9877）。' + (e && e.message ? e.message : '') });
                }
                finally { setBusy(false); }
            }, []);

            React.useEffect(() => { load(); }, [load]);

            const run = async (fn, okText) => {
                setBusy(true);
                try {
                    await fn();
                    setMsg({ type: 'ok', text: okText });
                    await load();
                }
                catch (e) { setMsg({ type: 'err', text: (e && e.message) || String(e) }); }
                finally { setBusy(false); }
            };

            const toggle = (kind, name) => setPicked((prev) => {
                const next = Object.assign({}, prev);
                const set = Object.assign({}, next[kind] || {});
                if (set[name]) delete set[name];
                else set[name] = true;
                next[kind] = set;
                return next;
            });
            const pickedList = (kind) => Object.keys(picked[kind] || {});
            const clearPicked = (kind) => setPicked((prev) => Object.assign({}, prev, { [kind]: {} }));

            const renderStickerGrid = (kind, items) => {
                const selected = pickedList(kind);
                return P('div', null,
                    P('div', { style: S.grid }, items.map((it) => {
                        const on = !!(picked[kind] || {})[it.name];
                        return P('div', {
                            key: it.name,
                            style: on ? S.tileOn : S.tile,
                            title: it.name + '（' + Math.round(it.size / 1024) + 'KB）',
                            onClick: () => toggle(kind, it.name),
                        },
                            P('img', {
                                src: imgUrl(kind, it.name), style: S.thumb, loading: 'lazy', alt: it.name,
                                onClick: (ev) => { ev.stopPropagation(); setBigImg({ kind, name: it.name }); },
                                title: '点击查看大图',
                            }),
                            P('div', { style: S.cap }, it.name.replace(/\.(png|jpg|jpeg|gif|webp|bmp)$/i, '')));
                    })),
                    P('div', { style: S.row },
                        P('span', { style: S.small }, '已选 ' + selected.length + ' 张'),
                        P('button', {
                            style: S.btnDanger, disabled: busy || selected.length === 0, type: 'button', onClick: () => {
                                if (!window.confirm('删除选中的 ' + selected.length + ' 张？不可恢复')) return;
                                run(() => api('/stickers/delete', { method: 'POST', body: JSON.stringify({ kind, names: selected }) }), '已删除 ' + selected.length + ' 张').then(() => clearPicked(kind));
                            },
                        }, '删除选中'),
                        P('button', {
                            style: S.btn, disabled: busy || selected.length !== 1, type: 'button', onClick: () => {
                                const oldName = selected[0];
                                const next = window.prompt('新文件名（保持扩展名，如 36_生气.png）', oldName);
                                if (!next || next === oldName) return;
                                run(() => api('/stickers/rename', { method: 'POST', body: JSON.stringify({ kind, from: oldName, to: next }) }), '已重命名').then(() => clearPicked(kind));
                            },
                        }, '重命名'),
                        P('button', {
                            style: S.btn, disabled: busy || selected.length === 0, type: 'button', onClick: () => {
                                const prefix = window.prompt('给选中的 ' + selected.length + ' 张加前缀（如 75_新）：', '');
                                if (!prefix) return;
                                run(() => api('/stickers/prefix', { method: 'POST', body: JSON.stringify({ kind, names: selected, prefix }) }), '已加前缀').then(() => clearPicked(kind));
                            },
                        }, '批量加前缀'),
                        kind === 'collected' ? P('button', {
                            style: S.btnPrimary, disabled: busy || selected.length === 0, type: 'button', onClick: () => {
                                run(() => api('/stickers/promote', { method: 'POST', body: JSON.stringify({ names: selected }) }), '已移入收藏（小鲸现在能发了）').then(() => clearPicked(kind));
                            },
                        }, '移入收藏') : null,
                        P('button', { style: S.btn, type: 'button', onClick: load }, '刷新')));
            };

            if (state === null) {
                return P('div', { style: S.wrap },
                    P('h2', { style: S.title }, '小鲸控制台'),
                    P('p', { style: S.desc }, busy ? '正在读取…' : '未连接'),
                    msg ? P('div', { style: msg.type === 'err' ? S.err : S.ok }, msg.text) : null,
                    P('div', { style: S.row }, P('button', { style: S.btnPrimary, onClick: load, type: 'button' }, '重试连接')));
            }

            const svc = state.services || {};
            const svcRow = (key, label, port) => P('div', { style: S.row },
                P('span', { style: S.small },
                    P('span', { style: Object.assign({}, S.dot, { background: svc[key] ? '#22c55e' : '#ef4444' }) }),
                    label + '（:' + port + '）' + (svc[key] ? ' 运行中' : ' 未启动')),
                P('span', { style: { flex: 1 } }),
                P('button', { style: S.btn, disabled: busy || svc[key], onClick: () => run(() => api('/service', { method: 'POST', body: JSON.stringify({ name: key, action: 'start' }) }), label + ' 启动中（约 60~90 秒）'), type: 'button' }, '启动'),
                P('button', { style: S.btn, disabled: busy || !svc[key], onClick: () => run(() => api('/service', { method: 'POST', body: JSON.stringify({ name: key, action: 'stop' }) }), label + ' 已停止'), type: 'button' }, '停止'));

            const tabs = [
                ['persona', '人格人设'],
                ['stickers', '表情包'],
                ['music', '音乐库'],
                ['rvc', '音色模型'],
                ['schedule', '定时任务'],
                ['services', '服务管理'],
                ['corpus', '语料库'],
                ['card', '长文转图'],
                ['params', '语音/唱歌参数'],
                ['files', '配置文件'],
            ];

            const addSchedule = (preset) => {
                const base = { id: 'task_' + Date.now(), enabled: true, time: '19:00', days: [], targets: [], text: '' };
                if (preset === 'news') Object.assign(base, { id: 'news_daily', enabled: false, time: '19:00', script: 'news_push.py' });
                setSchedules([...(schedules || []), base]);
            };
            const updateSchedule = (idx, patch) => {
                const next = (schedules || []).slice();
                next[idx] = Object.assign({}, next[idx], patch);
                setSchedules(next);
            };
            const removeSchedule = (idx) => setSchedules((schedules || []).filter((_, i) => i !== idx));
            const saveSchedules = () => run(() => api('/schedules', { method: 'POST', body: JSON.stringify({ items: schedules }) }), '定时任务已保存（每 30 秒检查一次）');

            return P('div', { style: S.wrap },
                P('h2', { style: S.title }, '小鲸控制台'),
                P('p', { style: S.desc }, '管理人格、表情包、音乐库、音色、定时任务，以及 NapCat / RVC / TTS 服务。人格保存后需在 QQ 里发 /new 生效。'),
                P('div', { style: S.tabs }, tabs.map(([k, label]) => P('button', { key: k, type: 'button', style: tab === k ? S.tabOn : S.tab, onClick: () => setTab(k) }, label))),
                msg ? P('div', { style: msg.type === 'err' ? S.err : S.ok, role: 'alert' }, msg.text) : null,

                tab === 'persona' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '人格文件 AGENTS.md（' + state.personaLen + ' 字符）'),
                    P('p', { style: S.hint }, '这就是小鲸的性格。保存后发 /new 生效。'),
                    P('textarea', { style: S.textarea, value: persona, onChange: (e) => setPersona(e.target.value), spellCheck: false }),
                    P('div', { style: S.row },
                        P('button', { style: S.btnPrimary, disabled: busy, type: 'button', onClick: () => run(() => api('/persona', { method: 'POST', body: JSON.stringify({ text: persona }) }), '人格已保存（发 /new 生效）') }, '保存人格'),
                        P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: state.paths.workspaceDir + '\\AGENTS.md' }) }) }, '系统编辑器打开'),
                        P('button', { style: S.btn, type: 'button', onClick: load }, '重新读取'))) : null,

                tab === 'stickers' ? P('div', null,
                    ...['saved', 'collected'].map((kind) => {
                        const items = kind === 'saved' ? saved : collected;
                        const title = kind === 'saved'
                            ? '收藏（' + saved.length + ' 张）—— 小鲸现在能发的'
                            : '收录（' + collected.length + ' 张）—— 自动收藏的，待整理';
                        const isOpen = !!openSec[kind];
                        const keyword = (kw[kind] || '').trim().toLowerCase();
                        const filtered = keyword === '' ? items : items.filter((it) => it.name.toLowerCase().includes(keyword));
                        return P('div', { key: kind, style: S.card },
                            P('div', {
                                style: Object.assign({}, S.subTitle, { cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }),
                                onClick: () => setOpenSec((prev) => Object.assign({}, prev, { [kind]: !prev[kind] })),
                            },
                                P('span', null, isOpen ? '▾' : '▸'),
                                P('span', null, title),
                                P('span', { style: Object.assign({}, S.hint, { margin: 0 }) }, isOpen ? '（点击收起）' : '（点击展开）')),
                            P('p', { style: S.hint },
                                kind === 'saved'
                                    ? '文件名就是标签。点图选中（可多选），然后删除/重命名。'
                                    : '插件每 ' + (state.paths.autoCollectMinutes || 5) + ' 分钟扫描一次别人发的图片，去重后进这里。选中 → 重命名 → 移入收藏。'),
                            P('div', { style: S.row },
                                P('input', {
                                    style: Object.assign({}, S.input, { maxWidth: 280 }),
                                    value: kw[kind] || '',
                                    placeholder: '搜索文件名…',
                                    onChange: (e) => setKw((prev) => Object.assign({}, prev, { [kind]: e.target.value })),
                                }),
                                P('button', {
                                    style: S.btn, type: 'button', disabled: filtered.length === 0,
                                    onClick: () => {
                                        const all = {};
                                        for (const it of filtered) all[it.name] = true;
                                        setPicked((prev) => Object.assign({}, prev, { [kind]: all }));
                                    },
                                }, '全选'),
                                P('button', {
                                    style: S.btn, type: 'button',
                                    onClick: () => clearPicked(kind),
                                }, '清空选择'),
                                P('span', { style: S.small }, '共 ' + items.length + ' 张' + (keyword ? '，匹配 ' + filtered.length : '')),
                                kind === 'saved'
                                    ? P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: state.paths.workspaceDir + '\\stickers' }) }) }, '打开目录')
                                    : P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: state.paths.workspaceDir + '\\stickers\\inbox' }) }) }, '打开目录'),
                                kind === 'collected'
                                    ? P('button', { style: S.btn, disabled: busy, type: 'button', onClick: () => run(() => api('/stickers/collect', { method: 'POST', body: '{}' }), '已扫描并收录') }, '立即收录')
                                    : null),
                            isOpen ? renderStickerGrid(kind, filtered) : null);
                    })) : null,

                tab === 'music' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '曲库目录（一行一个文件夹）'),
                    P('p', { style: S.hint }, '点歌和聊天里唱歌都用它，保存立即生效。'),
                    P('textarea', { style: Object.assign({}, S.textarea, { minHeight: 120 }), value: music, onChange: (e) => setMusic(e.target.value), spellCheck: false }),
                    P('div', { style: S.row },
                        P('button', { style: S.btnPrimary, disabled: busy, type: 'button', onClick: () => run(() => api('/music', { method: 'POST', body: JSON.stringify({ text: music }) }), '曲库已保存') }, '保存曲库'),
                        P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: state.paths.musicDirsFile }) }) }, '打开配置文件'))) : null,

                tab === 'rvc' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '音色模型（当前：' + (state.rvcModel || '未设置') + '）'),
                    P('p', { style: S.hint }, '改完到「服务管理」停止再启动 RVC 服务生效。模型放在 ' + state.paths.rvcRepo + '\\assets\\weights。'),
                    P('div', { style: S.row },
                        P('select', { style: Object.assign({}, S.input, { padding: 8 }), value: model, onChange: (e) => setModel(e.target.value) },
                            (state.rvcModels || []).map((m) => P('option', { key: m, value: m }, m))),
                        P('button', { style: S.btnPrimary, disabled: busy, type: 'button', onClick: () => run(() => api('/rvc-model', { method: 'POST', body: JSON.stringify({ model }) }), '已设为默认，重启 RVC 服务后生效') }, '设为默认'),
                        P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: state.paths.rvcRepo + '\\assets\\weights' }) }) }, '打开模型目录'))) : null,

                tab === 'schedule' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '定时任务（' + schedules.length + ' 个）'),
                    P('p', { style: S.hint }, '时间 24 小时制 HH:MM；days 空=每天（0=周日）。文本任务发给 targets；脚本任务跑一次 python 脚本（新闻推送这类脚本自己发消息）。'),
                    P('div', { style: S.row },
                        P('button', { style: S.btn, type: 'button', onClick: () => addSchedule('news') }, '+ 每日新闻（19:00）'),
                        P('button', { style: S.btn, type: 'button', onClick: () => addSchedule('text') }, '+ 自定义文本'),
                        P('button', { style: S.btn, type: 'button', onClick: () => addSchedule('script') }, '+ 运行脚本')),
                    schedules.map((item, idx) => P('div', { key: (item.id || 't') + '_' + idx, style: S.schedCard },
                        P('div', { style: S.row },
                            P('input', { style: Object.assign({}, S.input, { maxWidth: 90 }), value: item.time || '19:00', onChange: (e) => updateSchedule(idx, { time: e.target.value }), placeholder: 'HH:MM' }),
                            P('input', { style: S.input, value: item.id || '', onChange: (e) => updateSchedule(idx, { id: e.target.value }), placeholder: '任务 id' }),
                            P('label', { style: S.small },
                                P('input', { type: 'checkbox', checked: item.enabled !== false, onChange: (e) => updateSchedule(idx, { enabled: e.target.checked }) }), ' 启用'),
                            P('button', {
                                style: S.btn, type: 'button', disabled: busy,
                                onClick: () => run(() => api('/schedules/test', { method: 'POST', body: JSON.stringify({ item }) }), '已测试发送（看对应聊天是否收到）'),
                            }, '测试发送'),
                            P('button', {
                                style: S.btn, type: 'button', disabled: busy,
                                onClick: () => setSchedules([...(schedules || []), Object.assign({}, item, { id: (item.id || 'task') + '_copy' + Date.now().toString().slice(-4) })]),
                            }, '复制'),
                            P('button', { style: S.btnDanger, type: 'button', onClick: () => removeSchedule(idx) }, '删除')),
                        P('div', { style: S.row },
                            P('input', { style: S.input, value: item.script || '', onChange: (e) => updateSchedule(idx, { script: e.target.value }), placeholder: '脚本任务：相对 workspace 的脚本名（如 news_push.py）；留空=文本任务' })),
                        item.script ? null : P('div', { style: S.row },
                            P('input', { style: S.input, value: item.text || '', onChange: (e) => updateSchedule(idx, { text: e.target.value }), placeholder: '要发送的文本' }),
                            P('input', {
                                style: Object.assign({}, S.input, { maxWidth: 280 }),
                                value: (item.targets || []).map((t) => t.type + ':' + t.id).join(','),
                                onChange: (e) => {
                                    const targets = e.target.value.split(',')
                                        .map((s) => s.trim()).filter(Boolean)
                                        .map((s) => {
                                            const [type, ...rest] = s.split(':');
                                            return { type: type === 'private' ? 'private' : 'group', id: rest.join(':').trim() };
                                        });
                                    updateSchedule(idx, { targets });
                                },
                                placeholder: '目标，如 group:123,private:456',
                            })))),
                    P('div', { style: S.row },
                        P('button', { style: S.btnPrimary, disabled: busy, type: 'button', onClick: saveSchedules }, '保存任务'),
                        P('button', { style: S.btn, type: 'button', onClick: () => setShowJson(!showJson) }, showJson ? '收起高级 JSON' : '高级 JSON'),
                        P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: state.paths.schedulesFile }) }) }, '打开任务文件')),
                    showJson ? P('div', null,
                        P('textarea', { style: Object.assign({}, S.textarea, { minHeight: 180 }), value: jsonText, onChange: (e) => setJsonText(e.target.value), spellCheck: false }),
                        P('div', { style: S.row }, P('button', {
                            style: S.btnPrimary, type: 'button', disabled: busy,
                            onClick: () => {
                                let items;
                                try { items = JSON.parse(jsonText); }
                                catch (e) { setMsg({ type: 'err', text: 'JSON 格式错误：' + e.message }); return; }
                                setSchedules(items);
                                run(() => api('/schedules', { method: 'POST', body: JSON.stringify({ items }) }), 'JSON 已保存');
                            },
                        }, '保存 JSON'))) : null) : null,

                tab === 'services' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '外部服务'),
                    P('p', { style: S.hint }, '启动后等 60~90 秒再刷新；停止会结束占用端口的进程。'),
                    svcRow('napcat', 'QQ / NapCat', 13200),
                    svcRow('rvc', 'RVC 音色服务', 9850),
                    svcRow('tts', 'GPT-SoVITS 语音服务', 9880),
                    P('div', { style: S.row }, P('button', { style: S.btn, type: 'button', onClick: load }, '刷新状态'))) : null,

                tab === 'card' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '长文字 → 图片卡片'),
                    P('p', { style: S.hint }, '回复很长时自动渲染成一张图片发出去，避免长文被 QQ 截断/刷屏。这是 dsh-onebot-qq 插件的配置，改完需要重启 DSH 生效。'),
                    cardCfg === null ? P('p', { style: S.err }, '还没读到配置') : P('div', null,
                        P('label', { style: S.small },
                            P('input', {
                                type: 'checkbox', checked: cardCfg.enabled !== false,
                                onChange: (e) => setCardCfg(Object.assign({}, cardCfg, { enabled: e.target.checked })),
                            }),
                            ' 开启（关闭后所有回复都发纯文字）'),
                        P('div', { style: S.row, marginTop: 10 },
                            P('label', { style: S.small }, '触发字数阈值：',
                                P('input', {
                                    type: 'number', min: 50, step: 10,
                                    style: Object.assign({}, S.input, { width: 100, display: 'inline-block' }),
                                    value: cardCfg.threshold ?? 200,
                                    onChange: (e) => setCardCfg(Object.assign({}, cardCfg, { threshold: Number(e.target.value) })),
                                }),
                                ' 字（超过就转图片；建议 150~300）')),
                        P('div', { style: S.row },
                            P('label', { style: S.small, flex: 1 }, '卡片页脚文字：',
                                P('input', {
                                    style: Object.assign({}, S.input, { maxWidth: 240 }),
                                    value: cardCfg.footer ?? '小鲸',
                                    onChange: (e) => setCardCfg(Object.assign({}, cardCfg, { footer: e.target.value })),
                                }))),
                        P('div', { style: S.row },
                            P('label', { style: S.small, flex: 1 }, '字体文件：',
                                P('input', {
                                    style: Object.assign({}, S.input, { maxWidth: 320 }),
                                    value: cardCfg.fontFile ?? 'C:\\Windows\\Fonts\\msyh.ttc',
                                    onChange: (e) => setCardCfg(Object.assign({}, cardCfg, { fontFile: e.target.value })),
                                })),
                            P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: 'C:\\Windows\\Fonts' }) }) }, '打开字体目录')),
                        P('p', { style: S.hint }, '字体建议用微软雅黑：C:\\Windows\\Fonts\\msyh.ttc（粗体 msyhbd.ttc）'),
                        P('div', { style: S.row },
                            P('button', {
                                style: S.btnPrimary, disabled: busy, type: 'button',
                                onClick: () => run(() => api('/card', { method: 'POST', body: JSON.stringify({ config: cardCfg }) }), '已保存到 DSH 配置，重启 DSH 后生效'),
                            }, '保存设置'),
                            P('button', { style: S.btn, type: 'button', onClick: () => api('/card').then((cd) => setCardCfg(cd.config || null)) }, '重新读取')))) : null,

                tab === 'corpus' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '语料库（' + (corpus.files || []).length + ' 个文件）'),
                    P('p', { style: S.hint }, '存放人设补充、话术、话题素材。目录：' + (corpus.dir || '')),
                    P('div', { style: S.row },
                        P('button', { style: S.btn, type: 'button', onClick: () => api('/corpus').then((cp) => setCorpus(cp)) }, '刷新列表'),
                        P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: corpus.dir }) }) }, '打开目录'),
                        P('input', { style: Object.assign({}, S.input, { maxWidth: 260 }), value: corpusName, placeholder: '新文件名（如 口头禅.md）', onChange: (e) => setCorpusName(e.target.value) }),
                        P('button', {
                            style: S.btnPrimary, type: 'button', disabled: busy || !corpusName.trim(),
                            onClick: () => run(() => api('/corpus/file', { method: 'POST', body: JSON.stringify({ name: corpusName.trim(), text: '' }) }), '已新建 ' + corpusName).then(() => setCorpusName('')),
                        }, '新建')),
                    P('div', { style: S.row },
                        P('select', {
                            style: Object.assign({}, S.input, { padding: 8 }), value: corpusName,
                            onChange: (e) => {
                                const name = e.target.value;
                                setCorpusName(name);
                                if (name) api('/corpus/file?name=' + encodeURIComponent(name)).then((r) => setCorpusText(r.text || '')).catch(() => setCorpusText(''));
                                else setCorpusText('');
                            },
                        }, [P('option', { key: '', value: '' }, '（选择文件）')].concat((corpus.files || []).map((f) => P('option', { key: f, value: f }, f)))),
                        P('button', {
                            style: S.btnDanger, type: 'button', disabled: busy || !corpusName,
                            onClick: () => {
                                if (!window.confirm('删除 ' + corpusName + '？')) return;
                                run(() => api('/corpus/delete', { method: 'POST', body: JSON.stringify({ name: corpusName }) }), '已删除').then(() => { setCorpusName(''); setCorpusText(''); });
                            },
                        }, '删除文件')),
                    P('textarea', { style: S.textarea, value: corpusText, onChange: (e) => setCorpusText(e.target.value), spellCheck: false, placeholder: '选中或新建文件后，在这里编辑内容…' }),
                    P('div', { style: S.row },
                        P('button', {
                            style: S.btnPrimary, disabled: busy || !corpusName, type: 'button',
                            onClick: () => run(() => api('/corpus/file', { method: 'POST', body: JSON.stringify({ name: corpusName, text: corpusText }) }), '语料已保存'),
                        }, '保存语料'))) : null,

                tab === 'params' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '语音 / 唱歌参数'),
                    P('p', { style: S.hint }, '看不懂没关系：下面每一个都写了「调大/调小会怎样」。改完点最下面的「保存参数」，下次生成语音/唱歌自动生效。'),
                    P('p', { style: Object.assign({}, S.hint, { color: '#f59e0b' }) },
                        '⚠️ 不知道改哪项时：先只动「人声音量」「伴奏音量」「响度」，其他保持默认。'),
                    params === null ? P('p', { style: S.err }, '还没读到参数') : P('div', null,

                        P('div', { style: S.subTitle }, '一、语音情绪（说话用）'),
                        P('p', { style: S.hint }, '每个格子三个数字：①语速 ②清晰度 ③嗓音高低。'),
                        P('div', { style: S.grid, gridTemplateColumns: 'repeat(auto-fill,minmax(170px,1fr))' }, Object.keys((params.voice || {}).emotions || {}).map((k) => {
                            const e = (params.voice.emotions)[k] || {};
                            const upd = (field, val) => {
                                const next = JSON.parse(JSON.stringify(params));
                                next.voice.emotions[k][field] = Number(val);
                                setParams(next);
                            };
                            const labelMap = { normal: '日常', sweet: '撒娇', gentle: '温柔深情', sad: '难过', tsundere: '傲娇', excited: '兴奋' };
                            return P('div', { key: k, style: S.tile },
                                P('div', { style: S.cap }, (labelMap[k] || k) + '（' + k + '）'),
                                P('div', { style: S.row },
                                    P('input', { type: 'number', step: '0.01', style: Object.assign({}, S.input, { minWidth: 0, width: 62 }), value: e.speed ?? '', onChange: (ev) => upd('speed', ev.target.value), title: '语速：1=正常；越小越慢，越大越快（0.8~1.3）' }),
                                    P('input', { type: 'number', step: '0.1', style: Object.assign({}, S.input, { minWidth: 0, width: 62 }), value: e.presence ?? '', onChange: (ev) => upd('presence', ev.target.value), title: '清晰度：越大咬字越清楚越亮（0~4）' }),
                                    P('input', { type: 'number', step: '1', style: Object.assign({}, S.input, { minWidth: 0, width: 54 }), value: e.pitch ?? '', onChange: (ev) => upd('pitch', ev.target.value), title: '嗓音高低：大=更高更嫩，小=更低更沉稳（-3~+3）' })),
                                P('div', { style: S.cap }, '语速 / 清晰度 / 高低'));
                        })),
                        P('p', { style: S.hint }, '语速：1=正常，0.9 更慢更柔，1.2 更活泼。清晰度：2.5 左右正常，觉得闷就加、觉得刺耳就减。高低：0 自然，-2 更低沉，+2 更高。'),

                        P('div', { style: S.subTitle }, '二、唱歌（cover.py 用）'),
                        P('div', { style: S.row }, (() => {
                            const cv = (params.cover || {});
                            const upd = (field, val) => {
                                const next = JSON.parse(JSON.stringify(params));
                                next.cover = Object.assign({}, next.cover, { [field]: Number(val) });
                                setParams(next);
                            };
                            const meta = [
                                ['targetHz', '目标音高(Hz)', '决定整体唱多高。声音闷/低 → 调大(300~310)；高音破音 → 调小(275~285)', '270~320'],
                                ['pitchMin', '音高下限', '自动定调最低能降几个半音（-2 正常）', '-4~0'],
                                ['pitchMax', '音高上限', '自动定调最高能升几个半音（6 正常；破音就降到 4~5）', '2~8'],
                                ['protect', '保护度', '越大越保留原唱气声/细节，越小越干净（0.35 正常）', '0.2~0.5'],
                                ['indexRate', '索引权重', '越大越像原唱音色，越小越像模型（0.5 中性）', '0~1'],
                                ['vocalVol', '人声音量', '人声多大。听不清唱什么就调大', '0.8~1.5'],
                                ['instVol', '伴奏音量', '伴奏多大。伴奏盖过人声就调小', '0.4~1.0'],
                                ['loudnessI', '整体响度', '成片多响。-16 偏小，-14 正常，-12 偏大（容易爆）', '-16~-12'],
                            ];
                            return meta.map(([field, label, tip, range]) => P('label', { key: field, style: { display: 'block', marginBottom: 10 } },
                                P('div', { style: S.small }, label + '（' + range + '）'),
                                P('input', {
                                    type: 'number', step: '0.01', title: tip,
                                    style: Object.assign({}, S.input, { width: 120, display: 'inline-block' }),
                                    value: cv[field] ?? '', onChange: (ev) => upd(field, ev.target.value),
                                }),
                                P('div', { style: Object.assign({}, S.hint, { margin: '2px 0 0' }) }, tip)));
                        })()),

                        P('div', { style: S.row, marginTop: 8 },
                            P('button', {
                                style: S.btnPrimary, disabled: busy, type: 'button',
                                onClick: () => run(() => api('/params', { method: 'POST', body: JSON.stringify({ params }) }), '参数已保存（下次生成生效）'),
                            }, '保存参数'),
                            P('button', {
                                style: S.btn, type: 'button',
                                onClick: () => {
                                    const next = JSON.parse(JSON.stringify(params));
                                    next.voice.emotions = {
                                        normal: { speed: 1.02, presence: 2.5, pitch: 0 }, sweet: { speed: 1.0, presence: 3.0, pitch: 1 },
                                        gentle: { speed: 0.92, presence: 2.0, pitch: -2 }, sad: { speed: 0.9, presence: 1.5, pitch: -2 },
                                        tsundere: { speed: 1.12, presence: 3.5, pitch: 1 }, excited: { speed: 1.2, presence: 3.0, pitch: 2 },
                                    };
                                    next.cover = { targetHz: 290.0, pitchMin: -2, pitchMax: 6, protect: 0.35, indexRate: 0.5, vocalVol: 1.2, instVol: 0.75, loudnessI: -14.0 };
                                    setParams(next);
                                    setMsg({ type: 'ok', text: '已恢复默认值，记得点「保存参数」' });
                                },
                            }, '恢复默认'),
                            P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: 'D:\\software\\Voice\\params.json' }) }) }, '打开 params.json')))) : null,

                tab === 'files' ? P('div', { style: S.card },
                    P('span', { style: S.label }, '常用配置文件'),
                    [
                        ['人格 AGENTS.md', state.paths.workspaceDir + '\\AGENTS.md'],
                        ['曲库目录', state.paths.musicDirsFile],
                        ['音色模型名', state.paths.rvcModelFile],
                        ['定时任务', state.paths.schedulesFile],
                        ['记忆库', state.paths.workspaceDir + '\\记忆库.md'],
                        ['表情包目录', state.paths.workspaceDir + '\\stickers'],
                        ['语音产物', state.paths.workspaceDir + '\\voice'],
                        ['声音工坊', state.paths.voiceDir],
                    ].map(([label, p]) => P('div', { key: label, style: S.row },
                        P('span', { style: { minWidth: 140, fontSize: 12 } }, label),
                        P('span', { style: Object.assign({}, S.small, { flex: 1, opacity: 0.65, wordBreak: 'break-all' }) }, p),
                        P('button', { style: S.btn, type: 'button', onClick: () => api('/open', { method: 'POST', body: JSON.stringify({ path: p }) }) }, '打开')))) : null,

                P('p', { style: Object.assign({}, S.hint, { marginTop: 16 }) },
                    '控制台服务：http://127.0.0.1:9877　｜　QQ 传输由 dsh-onebot-qq 负责，本面板不改它。'),
                bigImg === null ? null : P('div', {
                    style: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,.72)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'zoom-out' },
                    onClick: () => setBigImg(null),
                },
                    P('div', { style: { maxWidth: '86vw', maxHeight: '86vh', textAlign: 'center' } },
                        P('img', { src: imgUrl(bigImg.kind, bigImg.name), style: { maxWidth: '86vw', maxHeight: '78vh', objectFit: 'contain', borderRadius: 8 } }),
                        P('div', { style: { color: '#fff', fontSize: 12, marginTop: 6 } }, bigImg.name + '（点任意处关闭）'))));
        }

        const inject = ['slots'];
        function apply(ctx) {
            try {
                ctx.slots.inject('settings.section', () => ctx.slots.register(
                    { name: 'settings.section', id: 'xiaojing-panel', order: 40, label: () => '小鲸控制台', icon: 'settings' },
                    () => P(Panel)));
            }
            catch (error) {
                // eslint-disable-next-line no-console
                console.error('[xiaojing-panel] client apply failed (ignored):', error && error.message);
            }
        }

        module.exports = { inject, apply };
        return module.exports;
    },
});
