/* =========================================================
   3deBlock · PoW Lab
   Frontend controller (ES module).
   Vendored libs are loaded locally — no CDN.
   ========================================================= */

import autoAnimate from "./vendor/auto-animate.js";


// -----------------------------------------------------
// ESTADO LOCAL
// -----------------------------------------------------

let fetching = false;
let lastMining = false;
let lastNodeIds = [];
let lastCompactIds = [];
let lastConfigSignature = "";
let chainRefreshing = false;

let logKeys = new Set();


// -----------------------------------------------------
// HELPERS
// -----------------------------------------------------

const $ = (id) => document.getElementById(id);


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}


function fmtHash(hash) {

    if (!hash) {
        return "—";
    }

    return hash.slice(0, 8) + "…";
}


function fmtAttempts(value) {

    const n = Number(value) || 0;

    if (n >= 1000000) {
        return (n / 1000000).toFixed(1) + "M";
    }

    if (n >= 1000) {
        return (n / 1000).toFixed(1) + "k";
    }

    return String(n);
}


function fmtTime(ts) {

    if (typeof ts !== "number") {
        return "--:--:--";
    }

    const d = new Date(ts * 1000);
    const pad = (n) => String(n).padStart(2, "0");

    return (
        pad(d.getHours()) + ":" +
        pad(d.getMinutes()) + ":" +
        pad(d.getSeconds())
    );
}


function statusClass(status) {

    if (!status) {
        return "st-idle";
    }

    const s = String(status).toLowerCase();

    if (
        s === "minando" ||
        s === "mining" ||
        s === "preparando"
    ) {
        return "st-mining";
    }

    if (
        s === "ganador" ||
        s === "winner" ||
        s === "won"
    ) {
        return "st-won";
    }

    return "st-idle";
}


function nodeTone(status, isWinner) {

    if (isWinner) {
        return "won";
    }

    const cls = statusClass(status);

    if (cls === "st-mining") {
        return "mining";
    }

    if (cls === "st-won") {
        return "won";
    }

    return "idle";
}


function setConn(online) {

    const el = $("conn-indicator");

    if (!el) {
        return;
    }

    el.classList.toggle("online", !!online);
    el.classList.toggle("offline", !online);
    el.title = online ? "Conectado" : "Sin conexión";
}


function setInlineError(id, message) {

    const el = $(id);

    if (!el) {
        return;
    }

    el.textContent = message || "";
    el.classList.toggle("visible", Boolean(message));
}


// -----------------------------------------------------
// RENDER · NODOS (tabla detalle)
// -----------------------------------------------------

function renderNodes(nodes, winner) {

    const tbody = $("nodes-body");

    if (!tbody) {
        return;
    }

    const ids = nodes.map((n) => n.id);

    const sameOrder =
        ids.length === lastNodeIds.length &&
        ids.every((id, i) => id === lastNodeIds[i]);

    if (!sameOrder) {

        tbody.innerHTML = "";

        nodes.forEach((n) => {

            const tr = document.createElement("tr");
            tr.dataset.id = n.id;

            for (let i = 0; i < 9; i += 1) {
                tr.appendChild(document.createElement("td"));
            }

            tbody.appendChild(tr);
        });

        lastNodeIds = ids.slice();
    }

    nodes.forEach((n) => {

        const tr = tbody.querySelector(
            `tr[data-id="${CSS.escape(n.id)}"]`
        );

        if (!tr) {
            return;
        }

        const isWinner = winner === n.id;

        tr.classList.toggle("winner-row", isWinner);

        const cells = tr.children;

        cells[0].innerHTML =
            (isWinner ? CROWN_ICON : "") + escapeHtml(n.id);

        cells[0].classList.toggle("node-id", isWinner);

        cells[1].textContent =
            (n.attempts || 0).toLocaleString();

        cells[2].innerHTML =
            '<code class="hash" data-hash="' +
                escapeHtml(n.last_hash || "") +
            '" title="' +
                escapeHtml(n.last_hash || "") +
            '">' + escapeHtml(fmtHash(n.last_hash)) +
            COPY_ICON + "</code>";

        cells[3].textContent =
            n.status || "—";

        cells[3].className =
            statusClass(n.status);

        cells[4].textContent =
            n.height;

        cells[5].textContent =
            n.mempool;

        cells[6].textContent =
            Number(n.balance_available || 0).toFixed(2);

        cells[7].textContent =
            Number(n.balance_pending || 0).toFixed(2);

        cells[8].innerHTML =
            n.valid ? TICK_SMALL : ALERT_SMALL;

        cells[8].className =
            n.valid ? "st-ok" : "st-bad";
    });
}


// -----------------------------------------------------
// RENDER · LOG (incremental, newest first)
// -----------------------------------------------------

function logEntryHtml(e) {

    return (
        '<div class="log-entry">' +
            '<span class="log-time">' +
                escapeHtml(fmtTime(e.ts)) +
            "</span>" +
            '<span class="log-kind">' +
                "[" + escapeHtml(e.kind || "info") + "]" +
            "</span>" +
            '<span class="log-msg">' +
                escapeHtml(e.msg || "") +
            "</span>" +
        "</div>"
    );
}


function renderLog(entries) {

    const list = $("log-list");

    if (!list) {
        return;
    }

    const slice = (entries || []).slice(-30).reverse();

    if (slice.length === 0) {

        if (list.children.length === 0) {
            list.innerHTML = logEntryHtml({
                ts: null,
                kind: "info",
                msg: "Sin eventos todavía.",
            });
        }

        return;
    }

    const keys = slice.map(
        (e) => e.ts + "|" + (e.kind || "") + "|" + (e.msg || "")
    );

    const newOnes = slice.filter((e, i) => !logKeys.has(keys[i]));

    if (newOnes.length === 0 && list.children.length === slice.length) {
        return;
    }

    if (list.children.length === 0 || logKeys.size === 0) {

        list.innerHTML = slice.map(logEntryHtml).join("");
    }
    else {

        newOnes.reverse().forEach((e) => {
            list.insertAdjacentHTML("afterbegin", logEntryHtml(e));
        });
    }

    while (list.children.length > 30) {
        list.removeChild(list.lastChild);
    }

    logKeys = new Set(keys);
}


// -----------------------------------------------------
// RENDER · CONSTELACIÓN
// -----------------------------------------------------

const VBW = 1160;
const VBH = 300;

function line(x1, y1, x2, y2) {
    return (
        `<line class="link" x1="${x1.toFixed(1)}" y1="${y1.toFixed(1)}" ` +
        `x2="${x2.toFixed(1)}" y2="${y2.toFixed(1)}" />`
    );
}


function renderConstellation(nodes, winner) {

    const host = $("constellation");

    if (!host) {
        return;
    }

    const list = nodes || [];

    if (list.length === 0) {
        host.innerHTML =
            '<div class="empty-state" style="display:block">' +
            "Sin nodos.</div>";
        return;
    }

    const cx = VBW / 2;
    const cy = 112;
    const rx = 500;
    const ry = 82;
    const n = list.length;
    const r = n <= 12 ? 20 : (n <= 16 ? 17 : 14);
    const showSub = n <= 14;

    const pos = list.map((_, i) => {

        const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;

        return {
            x: cx + rx * Math.cos(a),
            y: cy + ry * Math.sin(a),
        };
    });

    const anchor = { x: cx, y: VBH - 26 };

    let svg = "";

    for (let i = 0; i < n; i += 1) {

        const j = (i + 1) % n;
        const k = (i + 2) % n;

        svg += line(pos[i].x, pos[i].y, pos[j].x, pos[j].y);
        svg += line(pos[i].x, pos[i].y, pos[k].x, pos[k].y);
    }

    if (winner) {

        const idx = list.findIndex((nd) => nd.id === winner);

        if (idx >= 0) {
            svg +=
                '<path class="link--active" fill="none" d="M' +
                pos[idx].x.toFixed(1) + " " + pos[idx].y.toFixed(1) +
                " Q " + cx + " " + (VBH - 96) +
                " " + anchor.x + " " + anchor.y + '" />';
        }
    }

    list.forEach((nd, i) => {

        const isWinner = winner === nd.id;
        const tone = nodeTone(nd.status, isWinner);

        svg +=
            `<g class="node node--${tone}">` +
                "<title>" +
                    escapeHtml(
                        "Nodo " + nd.id +
                        " · altura " + (nd.height ?? "—") +
                        " · intentos " + (nd.attempts || 0) +
                        (isWinner
                            ? " · ganador de la última ronda · " +
                              "recompensa a las 6 confirmaciones"
                            : "")
                    ) +
                "</title>" +
                `<circle class="node-halo" cx="${pos[i].x.toFixed(1)}" ` +
                    `cy="${pos[i].y.toFixed(1)}" r="${r + 5}" />` +
                `<circle class="node-ring" cx="${pos[i].x.toFixed(1)}" ` +
                    `cy="${pos[i].y.toFixed(1)}" r="${r}" />` +
                `<text class="node-label" x="${pos[i].x.toFixed(1)}" ` +
                    `y="${pos[i].y.toFixed(1)}">` +
                    escapeHtml(nd.id) +
                "</text>" +
                (showSub
                    ? `<text class="node-sub" x="${pos[i].x.toFixed(1)}" ` +
                        `y="${(pos[i].y + r + 12).toFixed(1)}">` +
                        escapeHtml(fmtAttempts(nd.attempts)) +
                      "</text>"
                    : "") +
            "</g>";
    });

    svg +=
        `<g class="anchor">` +
            `<circle class="anchor-ring" cx="${anchor.x}" ` +
                `cy="${anchor.y}" r="15" />` +
            `<text class="anchor-label" x="${anchor.x}" ` +
                `y="${anchor.y}">cadena</text>` +
        "</g>";

    host.innerHTML =
        `<svg viewBox="0 0 ${VBW} ${VBH}" ` +
        'preserveAspectRatio="xMidYMid meet">' + svg + "</svg>";

    const meta = $("constellation-meta");

    if (meta) {
        meta.textContent = winner
            ? "ganador " + winner
            : (lastMining ? "minando" : "idle");
    }
}


// -----------------------------------------------------
// RENDER · NODOS (tabla compacta)
// -----------------------------------------------------

const CHECK_ICON =
    '<svg class="node-check" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="10"></circle>' +
    '<path d="m16 9-5.5 5.5L8 12"></path></svg>';

const CROWN_ICON =
    '<svg class="crown-icon" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 ' +
    '1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-' +
    '.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l' +
    '4.276 3.664a1 1 0 0 0 1.516-.294z"></path>' +
    '<path d="M5 21h14"></path></svg>';

const TICK_SMALL =
    '<svg class="cell-icon ok" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M20 6 9 17l-5-5"></path></svg>';

const ALERT_SMALL =
    '<svg class="cell-icon bad" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 ' +
    '2 0 0 0 1.73-3"></path><path d="M12 9v4"></path>' +
    '<path d="M12 17h.01"></path></svg>';

const COPY_ICON =
    '<svg class="copy-icon" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect>' +
    '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2">' +
    "</path></svg>";

const PICKAXE_ICON =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" ' +
    'aria-hidden="true">' +
    '<path d="m14 13-8.381 8.38a1 1 0 0 1-3.001-3L11 9.999"></path>' +
    '<path d="M15.973 4.027A13 13 0 0 0 5.902 2.373c-1.398.342-1.092 ' +
    '2.158.277 2.601a19.9 19.9 0 0 1 5.822 3.024"></path>' +
    '<path d="M16.001 11.999a19.9 19.9 0 0 1 3.024 5.824c.444 1.369 ' +
    '2.26 1.676 2.603.278A13 13 0 0 0 20 8.069"></path>' +
    '<path d="M18.352 3.352a1.205 1.205 0 0 0-1.704 0l-5.296 5.296a1.205 ' +
    '1.205 0 0 0 0 1.704l2.296 2.296a1.205 1.205 0 0 0 1.704 0l5.296-' +
    '5.296a1.205 1.205 0 0 0 0-1.704z"></path></svg>';




function renderCompactNodes(nodes, winner) {

    const tbody = $("nodes-compact-body");

    if (!tbody) {
        return;
    }

    const ids = nodes.map((n) => n.id);

    const sameOrder =
        ids.length === lastCompactIds.length &&
        ids.every((id, i) => id === lastCompactIds[i]);

    if (!sameOrder) {

        tbody.innerHTML = "";

        nodes.forEach((n) => {

            const tr = document.createElement("tr");
            tr.dataset.id = n.id;

            for (let i = 0; i < 6; i += 1) {
                tr.appendChild(document.createElement("td"));
            }

            tbody.appendChild(tr);
        });

        lastCompactIds = ids.slice();
    }

    nodes.forEach((n) => {

        const tr = tbody.querySelector(
            `tr[data-id="${CSS.escape(n.id)}"]`
        );

        if (!tr) {
            return;
        }

        const isWinner = winner === n.id;

        tr.classList.toggle("winner-row", isWinner);

        const cells = tr.children;

        cells[0].innerHTML =
            '<span class="node-cell">' +
                (isWinner ? CHECK_ICON : "") +
                '<span class="node-id">' + escapeHtml(n.id) + "</span>" +
            "</span>";

        cells[1].textContent = n.status || "—";
        cells[1].className = statusClass(n.status);

        cells[2].textContent =
            Number(n.attempts || 0).toLocaleString();

        cells[3].textContent = n.height;

        cells[4].textContent =
            Number(n.balance_available || 0).toFixed(2);

        cells[5].textContent =
            Number(n.balance_pending || 0).toFixed(2);
    });
}


// -----------------------------------------------------
// ESTADO · APLICAR
// -----------------------------------------------------

// -----------------------------------------------------
// RENDER · STATS STRIP + MINI PANEL
// -----------------------------------------------------

function setText(id, value) {

    const el = $(id);

    if (el) {
        el.textContent = value == null ? "—" : String(value);
    }
}


function updateNetParams(cfg) {

    const el = $("net-params");

    if (!el) {
        return;
    }

    el.textContent =
        "N = " + (cfg.num_nodes ?? "—") +
        " · dificultad = " + (cfg.difficulty ?? "—") +
        " · recompensa = 50 · maduración = 6 bloques";
}


function updateStats(data, cfg) {

    const nodes = data.nodes || [];

    const height = nodes.reduce(
        (max, n) => Math.max(max, Number(n.height) || 0),
        0
    );

    const mempool = nodes.reduce(
        (sum, n) => sum + (Number(n.mempool) || 0),
        0
    );

    setText("stat-height", height);
    setText("stat-nodes", cfg.num_nodes != null ? cfg.num_nodes : nodes.length);
    setText("stat-difficulty", cfg.difficulty != null ? cfg.difficulty : "—");
    setText("stat-mode", (cfg.mode || "pow").toUpperCase());
    setText("stat-mempool", mempool);
    setText(
        "stat-winner",
        data.winner || (data.mining ? "…" : "—")
    );
}


function updateMiniPanel(data, cfg) {

    const connEl = $("conn-indicator");
    const online = connEl
        ? connEl.classList.contains("online")
        : navigator.onLine;

    setText("mini-conn", online ? "en línea" : "sin conexión");

    const valid = document
        .getElementById("chain-status")
        ?.classList.contains("valid");

    setText("mini-chain", valid ? "válida" : "alterada");

    setText(
        "mini-lastblock",
        data.last_block_hash ? fmtHash(data.last_block_hash) : "—"
    );

    setText("mini-winner", data.winner || "—");
    setText("mini-mining", data.mining ? "minando" : "detenida");
}


function applyEstado(data) {

    const cfg = data.config || {};

    const signature =
        cfg.mode + "|" + cfg.num_nodes + "|" + cfg.difficulty;

    if (signature !== lastConfigSignature) {

        lastConfigSignature = signature;

        const modeSel = $("cfg-mode");
        const nodesInp = $("cfg-nodes");
        const diffInp = $("cfg-diff");

        if (modeSel && document.activeElement !== modeSel) {
            modeSel.value = cfg.mode || "pow";
        }

        if (nodesInp && document.activeElement !== nodesInp) {
            nodesInp.value = cfg.num_nodes;
        }

        if (diffInp && document.activeElement !== diffInp) {
            diffInp.value = cfg.difficulty;
        }
    }

    const posPanel = $("pos-panel");

    if (posPanel) {
        posPanel.hidden = cfg.mode !== "pos";
    }

    populateSenderReceiver(data.nodes || []);
    populatePosStakes(data.nodes || []);

    renderNodes(data.nodes || [], data.winner);
    renderCompactNodes(data.nodes || [], data.winner);
    renderLog(data.log || []);
    renderConstellation(data.nodes || [], data.winner);

    updateStats(data, cfg);
    updateMiniPanel(data, cfg);

    const modeChip = $("mode-chip");

    if (modeChip) {
        modeChip.textContent = cfg.mode || "pow";
    }

    const button = $("mine-button");

    if (button) {

        button.disabled = !!data.mining;

        button.innerHTML = PICKAXE_ICON +
            (data.mining ? "Minando…" : "Iniciar minería");
    }

    updateNetParams(cfg);

    if (lastMining && !data.mining) {
        refreshChainTable();
    }

    lastMining = !!data.mining;
}


// -----------------------------------------------------
// FETCH · /estado
// -----------------------------------------------------

async function fetchEstado() {

    if (fetching) {
        return;
    }

    fetching = true;

    try {

        const res = await fetch("/estado", { cache: "no-store" });

        if (!res.ok) {
            throw new Error("HTTP " + res.status);
        }

        const data = await res.json();

        setConn(true);
        applyEstado(data);
    }
    catch (err) {

        setConn(false);
        console.error("No se pudo consultar /estado:", err);
    }
    finally {

        fetching = false;
    }
}


// -----------------------------------------------------
// REFRESH · /  (fila de bloques + estado de cadena)
// -----------------------------------------------------

async function refreshChainTable() {

    if (chainRefreshing) {
        return;
    }

    chainRefreshing = true;

    try {

        const res = await fetch("/", { cache: "no-store" });

        if (!res.ok) {
            return;
        }

        const html = await res.text();

        const doc = new DOMParser()
            .parseFromString(html, "text/html");

        const freshBody = doc.getElementById("chain-row");
        const curBody = $("chain-row");

        if (freshBody && curBody) {
            curBody.innerHTML = freshBody.innerHTML;
        }

        const freshStatus = doc.getElementById("chain-status");
        const curStatus = $("chain-status");

        if (freshStatus && curStatus) {
            curStatus.className = freshStatus.className;
            curStatus.innerHTML = freshStatus.innerHTML;
        }
    }
    catch (err) {

        console.error("No se pudo refrescar la cadena:", err);
    }
    finally {

        chainRefreshing = false;
    }
}


// -----------------------------------------------------
// DROPDOWNS DINÁMICOS
// -----------------------------------------------------

function syncSelectOptions(select, options, keepValue) {

    if (!select) {
        return;
    }

    const currentValues = Array.from(select.options)
        .map((o) => o.value);

    const same =
        currentValues.length === options.length &&
        currentValues.every((v, i) => v === options[i]);

    if (same) {
        return;
    }

    const previous = keepValue ? select.value : null;

    select.innerHTML = "";

    options.forEach((opt) => {

        const el = document.createElement("option");
        el.value = opt;
        el.textContent = opt;
        select.appendChild(el);
    });

    if (previous && options.includes(previous)) {
        select.value = previous;
    }
}


function populateSenderReceiver(nodes) {

    const ids = (nodes || []).map((n) => n.id);

    syncSelectOptions($("tx-sender"), ids, true);
    syncSelectOptions($("tx-receiver"), ids, true);
}


function populatePosStakes(nodes) {

    const container = $("pos-stakes");

    if (!container) {
        return;
    }

    const ids = (nodes || []).map((n) => n.id);

    const existing = Array.from(
        container.querySelectorAll("input[data-node]")
    ).map((i) => i.dataset.node);

    const same =
        existing.length === ids.length &&
        existing.every((v, i) => v === ids[i]);

    if (same) {
        return;
    }

    const previous = {};

    Array.from(
        container.querySelectorAll("input[data-node]")
    ).forEach((inp) => {
        previous[inp.dataset.node] = inp.value;
    });

    container.innerHTML = "";

    ids.forEach((id) => {

        const label = document.createElement("label");
        label.className = "pos-stake";

        const span = document.createElement("span");
        span.textContent = id;

        const input = document.createElement("input");
        input.type = "number";
        input.min = "0";
        input.step = "0.01";
        input.value = previous[id] || "0";
        input.dataset.node = id;

        label.appendChild(span);
        label.appendChild(input);
        container.appendChild(label);
    });
}


// -----------------------------------------------------
// CLICK-TO-COPY · hashes
// -----------------------------------------------------

function installCopyHandler() {

    document.addEventListener("click", (event) => {

        const code = event.target.closest("code.hash[data-hash]");

        if (!code) {
            return;
        }

        const value = code.dataset.hash;

        if (!value || !navigator.clipboard) {
            return;
        }

        navigator.clipboard.writeText(value).then(() => {

            code.classList.add("copied");

            window.setTimeout(() => {
                code.classList.remove("copied");
            }, 900);
        }).catch(() => { /* clipboard denied — ignore */ });
    });
}


// -----------------------------------------------------
// ACCIONES · CONFIG
// -----------------------------------------------------

async function applyConfig() {

    setInlineError("config-error", "");

    const num_nodes =
        parseInt($("cfg-nodes").value, 10);

    const difficulty =
        parseInt($("cfg-diff").value, 10);

    const mode =
        $("cfg-mode").value;

    try {

        const res = await fetch("/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                num_nodes: num_nodes,
                difficulty: difficulty,
                mode: mode
            })
        });

        let payload = {};

        try {
            payload = await res.json();
        }
        catch (_) {
            payload = {};
        }

        if (!res.ok || !payload.ok) {

            setInlineError(
                "config-error",
                payload.error || ("Error HTTP " + res.status)
            );

            return;
        }

        lastNodeIds = [];
        lastCompactIds = [];
        lastConfigSignature = "";
        logKeys = new Set();

        await fetchEstado();
        await refreshChainTable();
    }
    catch (err) {

        setInlineError(
            "config-error",
            "No se pudo aplicar la configuración: " + err.message
        );
    }
}


async function resetSim() {

    setInlineError("config-error", "");

    try {

        const res = await fetch("/reset", { method: "POST" });

        if (!res.ok) {

            setInlineError(
                "config-error",
                "Reset falló: HTTP " + res.status
            );

            return;
        }

        lastNodeIds = [];
        lastCompactIds = [];
        lastConfigSignature = "";
        logKeys = new Set();

        await fetchEstado();
        await refreshChainTable();
    }
    catch (err) {

        setInlineError(
            "config-error",
            "Reset falló: " + err.message
        );
    }
}


// -----------------------------------------------------
// ACCIONES · POS
// -----------------------------------------------------

async function runPosRound() {

    setInlineError("pos-error", "");

    const inputs = document.querySelectorAll(
        "#pos-stakes input[data-node]"
    );

    const stakes = {};

    inputs.forEach((inp) => {

        const value = parseFloat(inp.value);

        if (!Number.isNaN(value) && value > 0) {
            stakes[inp.dataset.node] = value;
        }
    });

    if (Object.keys(stakes).length === 0) {

        setInlineError(
            "pos-error",
            "Debe apostar al menos un validador con saldo."
        );

        return;
    }

    const posBtn = $("pos-run");
    const out = $("pos-output");

    if (posBtn) {
        posBtn.disabled = true;
    }

    try {

        const res = await fetch("/pos_round", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stakes: stakes })
        });

        let payload = {};

        try {
            payload = await res.json();
        }
        catch (_) {
            payload = {};
        }

        if (!res.ok || !payload.ok) {

            setInlineError(
                "pos-error",
                payload.error || ("Error HTTP " + res.status)
            );

            return;
        }

        const proposerId = payload.proposer_id;
        let V = payload.V || 0;
        let A = payload.A || 0;

        // Todos los nodos votan SÍ (voto honesto por defecto).
        // Los nodos fuera de la ronda devuelven error y se ignoran.
        for (const validatorId of Array.from(inputs).map(
            (inp) => inp.dataset.node
        )) {

            const voteRes = await fetch("/pos_vote", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    validator_id: validatorId,
                    yes: true
                })
            });

            let votePayload = {};

            try {
                votePayload = await voteRes.json();
            }
            catch (_) {
                votePayload = {};
            }

            if (voteRes.ok && votePayload.ok) {
                V = votePayload.V;
                A = votePayload.A;
            }

            if (out) {
                out.textContent = JSON.stringify(
                    {
                        proposer_id: proposerId,
                        state: "VOTACION",
                        A: A,
                        V: V
                    },
                    null,
                    2
                );
            }
        }

        const finRes = await fetch("/pos_finalize", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        let finPayload = {};

        try {
            finPayload = await finRes.json();
        }
        catch (_) {
            finPayload = {};
        }

        if (!finRes.ok || !finPayload.ok) {

            setInlineError(
                "pos-error",
                finPayload.error || ("Error HTTP " + finRes.status)
            );

            return;
        }

        if (out) {
            out.textContent = JSON.stringify(
                {
                    proposer_id: finPayload.proposer_id,
                    state: finPayload.state,
                    accepted: finPayload.accepted,
                    A: finPayload.A,
                    V: finPayload.V,
                    slashed: finPayload.slashed,
                    new_attempt_needed: finPayload.new_attempt_needed,
                    candidate_hash: finPayload.candidate_hash
                },
                null,
                2
            );
        }

        if (finPayload.accepted) {
            await fetchEstado();
            await refreshChainTable();
        }
        else {
            setInlineError(
                "pos-error",
                "Bloque rechazado. Proponente penalizado con " +
                    finPayload.slashed +
                    (finPayload.new_attempt_needed
                        ? ". Se requiere un nuevo intento."
                        : ".")
            );
        }
    }
    catch (err) {

        setInlineError(
            "pos-error",
            "No se pudo iniciar la ronda: " + err.message
        );
    }
    finally {

        if (posBtn) {
            posBtn.disabled = false;
        }
    }
}


// -----------------------------------------------------
// FORM · /transaccion (JSON, inline errors)
// -----------------------------------------------------

async function submitTransaction(event) {

    event.preventDefault();

    const form = event.currentTarget;
    const errorEl = $("tx-error");

    if (errorEl) {
        errorEl.hidden = true;
        errorEl.textContent = "";
    }

    const formData = new FormData(form);

    try {

        const res = await fetch("/transaccion", {
            method: "POST",
            headers: { "Accept": "application/json" },
            body: formData,
        });

        if (res.ok) {

            if (errorEl) {
                errorEl.hidden = true;
                errorEl.textContent = "";
            }

            fetchEstado();
            return;
        }

        let message = "No se pudo enviar la transacción.";

        try {

            const data = await res.json();

            if (data && data.error) {
                message = data.error;
            }
        }
        catch (parseErr) {
            // keep the default message
        }

        if (errorEl) {
            errorEl.textContent = message;
            errorEl.hidden = false;
        }
    }
    catch (err) {

        if (errorEl) {
            errorEl.textContent = "Error de red: " + err.message;
            errorEl.hidden = false;
        }
    }
}


// -----------------------------------------------------
// FORM · /alterar (JSON, inline errors)
// -----------------------------------------------------

async function submitAlter(event) {

    event.preventDefault();

    let errorEl = $("alter-error");

    if (!errorEl) {
        errorEl = document.createElement("div");
        errorEl.id = "alter-error";
        errorEl.className = "inline-error";
        event.currentTarget.appendChild(errorEl);
    }

    setInlineError("alter-error", "");

    try {

        const res = await fetch("/alterar", {
            method: "POST",
            headers: { "Accept": "application/json" },
        });

        if (!res.ok) {

            setInlineError(
                "alter-error",
                "No se pudo alterar la cadena: HTTP " + res.status
            );

            return;
        }

        await refreshChainTable();
        await fetchEstado();
    }
    catch (err) {

        setInlineError(
            "alter-error",
            "No se pudo alterar la cadena: " + err.message
        );
    }
}


// -----------------------------------------------------
// INIT
// -----------------------------------------------------

function init() {

    const txForm = $("tx-form");

    if (txForm) {
        txForm.addEventListener("submit", submitTransaction);
    }

    const alterForm = $("alter-form");

    if (alterForm) {
        alterForm.addEventListener("submit", submitAlter);
    }

    const applyBtn = $("cfg-apply");

    if (applyBtn) {
        applyBtn.addEventListener("click", applyConfig);
    }

    const resetBtn = $("cfg-reset");

    if (resetBtn) {
        resetBtn.addEventListener("click", resetSim);
    }

    const posBtn = $("pos-run");

    if (posBtn) {
        posBtn.addEventListener("click", runPosRound);
    }

    const nodesBody = $("nodes-body");
    const compactBody = $("nodes-compact-body");
    const logList = $("log-list");
    const chainRow = $("chain-row");

    if (nodesBody) {
        autoAnimate(nodesBody);
    }

    if (compactBody) {
        autoAnimate(compactBody);
    }

    if (logList) {
        autoAnimate(logList);
    }

    if (chainRow) {
        autoAnimate(chainRow);
    }

    installCopyHandler();

    fetchEstado();

    setInterval(fetchEstado, 400);
}


if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
}
else {
    init();
}
