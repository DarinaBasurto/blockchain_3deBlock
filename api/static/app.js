let wasMining = false;
let reloadScheduled = false;


async function updateState() {

    try {

        const response = await fetch("/estado");

        const data = await response.json();


        // -----------------------------------------
        // NODOS
        // -----------------------------------------

        data.nodes.forEach((node) => {

            const attempts =
                document.getElementById(
                    `node-${node.id}-attempts`
                );

            const hash =
                document.getElementById(
                    `node-${node.id}-hash`
                );

            const status =
                document.getElementById(
                    `node-${node.id}-status`
                );

            const reward =
                document.getElementById(
                    `node-${node.id}-reward`
                );

            const card =
                document.getElementById(
                    `node-${node.id}`
                );


            if (attempts) {
                attempts.textContent =
                    node.attempts.toLocaleString();
            }


            if (hash) {

                hash.textContent =
                    node.last_hash
                        ? node.last_hash.slice(0, 18) + "…"
                        : "—";
            }


            if (status) {
                status.textContent = node.status;
            }


            if (reward) {
                reward.textContent = node.reward;
            }


            if (card) {

                card.classList.remove(
                    "mining",
                    "winner"
                );


                if (node.status === "Minando") {
                    card.classList.add("mining");
                }


                if (node.status === "Ganador") {
                    card.classList.add("winner");
                }

            }

        });


        // -----------------------------------------
        // BOTÓN
        // -----------------------------------------

        const button =
            document.getElementById("mine-button");


        if (button) {

            button.disabled = data.mining;

            button.textContent =
                data.mining
                    ? "Minando…"
                    : "Iniciar minería";

        }


        // -----------------------------------------
        // FIN DE LA CARRERA
        // -----------------------------------------

        if (data.mining) {
            wasMining = true;
        }


        if (
            wasMining &&
            !data.mining &&
            data.winner &&
            !reloadScheduled
        ) {

            reloadScheduled = true;

            setTimeout(() => {
                window.location.reload();
            }, 900);

        }

    }
    catch (error) {

        console.error(
            "No se pudo consultar /estado:",
            error
        );

    }

}


setInterval(updateState, 300);

updateState();