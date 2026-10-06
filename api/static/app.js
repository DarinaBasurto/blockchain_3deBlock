/* =========================================================
   3deBlock · PoW Lab
   Frontend controller (vanilla JS, no frameworks)
   ========================================================= */

(function () {

    "use strict";


    // -----------------------------------------------------
    // ESTADO LOCAL
    // -----------------------------------------------------

    let fetching = false;
    let lastMining = false;
    let lastNodeIds = [];
    let lastConfigSignature = "";
    let chainRefreshing = false;


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
    // RENDER · NODOS
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

            cells[0].textContent =
                (isWinner ? "🏆 " : "") + n.id;

            cells[1].textContent =
                (n.attempts || 0).toLocaleString();

            cells[2].innerHTML =
                "<code>" + escapeHtml(fmtHash(n.last_hash)) + "</code>";

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

            cells[8].textContent =
                n.valid ? "✓" : "✕";

            cells[8].className =
                n.valid ? "st-ok" : "st-bad";
        });
    }


    // -----------------------------------------------------
    // RENDER · LOG
    // -----------------------------------------------------

    function renderLog(entries) {

        const list = $("log-list");

        if (!list) {
            return;
        }

        const slice = (entries || []).slice(-30).reverse();

        if (slice.length === 0) {
            list.innerHTML =
                '<div class="log-entry">' +
                '<span class="log-msg">Sin eventos todavía.</span>' +
                '</div>';
            return;
        }

        list.innerHTML = slice
            .map((e) => (
                '<div class="log-entry">' +
                    '<span class="log-time">' +
                        escapeHtml(fmtTime(e.ts)) +
                    '</span>' +
                    '<span class="log-kind">' +
                        "[" + escapeHtml(e.kind || "info") + "]" +
                    '</span>' +
                    '<span class="log-msg">' +
                        escapeHtml(e.msg || "") +
                    '</span>' +
                '</div>'
            ))
            .join("");
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
    // ESTADO · APLICAR
    // -----------------------------------------------------

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
        renderLog(data.log || []);

        const button = $("mine-button");

        if (button) {

            button.disabled = !!data.mining;

            button.textContent = data.mining
                ? "Minando…"
                : "Iniciar minería";
        }

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
    // REFRESH · /  (solo tablas)
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

            const freshBody = doc.getElementById("chain-body");
            const curBody = $("chain-body");

            if (freshBody && curBody) {
                curBody.innerHTML = freshBody.innerHTML;
            }

            const freshStatus = doc.getElementById("chain-status");
            const curStatus = $("chain-status");

            if (freshStatus && curStatus) {
                curStatus.className = freshStatus.className;
                curStatus.textContent = freshStatus.textContent;
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

            // Forzar reconstrucción de la tabla de nodos
            lastNodeIds = [];
            lastConfigSignature = "";

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
            lastConfigSignature = "";

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

            const out = $("pos-output");

            if (out) {

                out.textContent = JSON.stringify(
                    {
                        proposer_id: payload.proposer_id,
                        state: payload.state,
                        A: payload.A,
                        V: payload.V
                    },
                    null,
                    2
                );
            }
        }
        catch (err) {

            setInlineError(
                "pos-error",
                "No se pudo iniciar la ronda: " + err.message
            );
        }
    }


    // -----------------------------------------------------
    // INIT
    // -----------------------------------------------------

    function init() {

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

        fetchEstado();

        setInterval(fetchEstado, 400);
    }


    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    }
    else {
        init();
    }

})();