document.addEventListener("DOMContentLoaded", function () {

    /* =========================================================
       ELEMENTOS
    ========================================================= */

    const zonaSubida = document.getElementById("zona-subida");

    const inputVideo = document.querySelector(
        'input[name="archivo_original"]'
    );

    const botonSeleccionar = document.getElementById(
        "boton-seleccionar-video"
    );

    const botonCambiar = document.getElementById(
        "boton-cambiar-video"
    );

    const subidaVacia = document.getElementById(
        "subida-vacia"
    );

    const archivoSeleccionado = document.getElementById(
        "archivo-seleccionado"
    );

    const archivoNombre = document.getElementById(
        "archivo-nombre"
    );

    const archivoFormato = document.getElementById(
        "archivo-formato"
    );

    const archivoPeso = document.getElementById(
        "archivo-peso"
    );

    const botonCrear = document.getElementById(
        "boton-crear-reel"
    );

    const formulario = document.getElementById(
        "formulario-reel"
    );


    /* =========================================================
       COMPROBACIÓN
    ========================================================= */

    if (
        !zonaSubida ||
        !inputVideo ||
        !botonSeleccionar ||
        !subidaVacia ||
        !archivoSeleccionado ||
        !botonCrear
    ) {
        return;
    }


    /* =========================================================
       CONFIGURACIÓN
    ========================================================= */

    const extensionesPermitidas = [
        "mp4",
        "mov",
        "m4v",
        "webm",
        "mxf"
    ];

    const tamanoMaximo = 1024 * 1024 * 1024;


    /* =========================================================
       ABRIR SELECTOR
    ========================================================= */

    botonSeleccionar.addEventListener(
        "click",
        function () {
            inputVideo.click();
        }
    );


    if (botonCambiar) {

        botonCambiar.addEventListener(
            "click",
            function () {
                inputVideo.click();
            }
        );

    }


    /* =========================================================
       ARCHIVO ELEGIDO DESDE WINDOWS
    ========================================================= */

    inputVideo.addEventListener(
        "change",
        function () {

            if (
                inputVideo.files &&
                inputVideo.files.length > 0
            ) {
                procesarArchivo(
                    inputVideo.files[0]
                );
            }

        }
    );


    /* =========================================================
       DRAG & DROP
    ========================================================= */

    zonaSubida.addEventListener(
        "dragenter",
        function (evento) {

            evento.preventDefault();

            zonaSubida.classList.add(
                "arrastrando"
            );

        }
    );


    zonaSubida.addEventListener(
        "dragover",
        function (evento) {

            evento.preventDefault();

            zonaSubida.classList.add(
                "arrastrando"
            );

        }
    );


    zonaSubida.addEventListener(
        "dragleave",
        function (evento) {

            evento.preventDefault();

            if (
                !zonaSubida.contains(
                    evento.relatedTarget
                )
            ) {
                zonaSubida.classList.remove(
                    "arrastrando"
                );
            }

        }
    );


    zonaSubida.addEventListener(
        "drop",
        function (evento) {

            evento.preventDefault();

            zonaSubida.classList.remove(
                "arrastrando"
            );

            const archivos =
                evento.dataTransfer.files;

            if (
                !archivos ||
                archivos.length === 0
            ) {
                return;
            }

            const archivo = archivos[0];

            const transferencia =
                new DataTransfer();

            transferencia.items.add(
                archivo
            );

            inputVideo.files =
                transferencia.files;

            procesarArchivo(
                archivo
            );

        }
    );


    /* =========================================================
       PROCESAR ARCHIVO
    ========================================================= */

    function procesarArchivo(archivo) {

        limpiarError();

        const extension =
            obtenerExtension(
                archivo.name
            );


        /* -----------------------------------------------------
           FORMATO
        ----------------------------------------------------- */

        if (
            !extensionesPermitidas.includes(
                extension
            )
        ) {

            mostrarError(
                "Formato no compatible. Utiliza MP4, MOV, M4V, WEBM o MXF."
            );

            limpiarArchivo();

            return;

        }


        /* -----------------------------------------------------
           TAMAÑO
        ----------------------------------------------------- */

        if (
            archivo.size > tamanoMaximo
        ) {

            mostrarError(
                "El vídeo no puede superar 1 GB."
            );

            limpiarArchivo();

            return;

        }


        /* -----------------------------------------------------
           MOSTRAR INFORMACIÓN
        ----------------------------------------------------- */

        archivoNombre.textContent =
            archivo.name;

        archivoFormato.textContent =
            extension.toUpperCase();

        archivoPeso.textContent =
            formatearTamano(
                archivo.size
            );


        subidaVacia.hidden = true;

        archivoSeleccionado.hidden =
            false;

        botonCrear.disabled =
            false;

    }


    /* =========================================================
       OBTENER EXTENSIÓN
    ========================================================= */

    function obtenerExtension(nombre) {

        const partes =
            nombre.split(".");

        if (
            partes.length < 2
        ) {
            return "";
        }

        return partes
            .pop()
            .toLowerCase();

    }


    /* =========================================================
       FORMATEAR TAMAÑO
    ========================================================= */

    function formatearTamano(bytes) {

        if (bytes === 0) {
            return "0 MB";
        }

        const megabytes =
            bytes / (1024 * 1024);

        if (megabytes < 1) {

            const kilobytes =
                bytes / 1024;

            return (
                kilobytes.toFixed(1) +
                " KB"
            );

        }

        if (megabytes < 1024) {

            return (
                megabytes.toFixed(1) +
                " MB"
            );

        }

        const gigabytes =
            megabytes / 1024;

        return (
            gigabytes.toFixed(2) +
            " GB"
        );

    }


    /* =========================================================
       LIMPIAR ARCHIVO
    ========================================================= */

    function limpiarArchivo() {

        inputVideo.value = "";

        subidaVacia.hidden =
            false;

        archivoSeleccionado.hidden =
            true;

        botonCrear.disabled =
            true;

    }


    /* =========================================================
       MOSTRAR ERROR
    ========================================================= */

    function mostrarError(mensaje) {

        limpiarError();

        const error =
            document.createElement(
                "div"
            );

        error.className =
            "errores-formulario error-javascript";

        error.id =
            "error-javascript";

        const parrafo =
            document.createElement(
                "p"
            );

        parrafo.textContent =
            mensaje;

        error.appendChild(
            parrafo
        );

        zonaSubida.insertAdjacentElement(
            "afterend",
            error
        );

    }


    /* =========================================================
       LIMPIAR ERROR
    ========================================================= */

    function limpiarError() {

        const errorAnterior =
            document.getElementById(
                "error-javascript"
            );

        if (errorAnterior) {
            errorAnterior.remove();
        }

    }


    /* =========================================================
       ENVÍO DEL FORMULARIO
    ========================================================= */

    formulario.addEventListener(
        "submit",
        function () {

            if (
                !inputVideo.files ||
                inputVideo.files.length === 0
            ) {
                return;
            }

            botonCrear.disabled =
                true;

            botonCrear.innerHTML = `
                <span>
                    Subiendo vídeo...
                </span>
            `;

        }
    );

});