
from functools import lru_cache
from pathlib import Path
import re
import unicodedata

from faster_whisper import WhisperModel


class VozNoDetectadaError(ValueError):
    """Whisper no ha encontrado palabras para subtitular."""


# ============================================================
# CONFIGURACIÓN DE WHISPER
# ============================================================

MODELO_WHISPER = "small"
IDIOMA = "es"

PALABRAS_POR_SUBTITULO = 3
PAUSA_MAXIMA_ENTRE_PALABRAS = 0.45
DURACION_MINIMA_SUBTITULO = 0.10


# ============================================================
# CARGAR MODELO
# ============================================================

@lru_cache(maxsize=1)
def obtener_modelo():
    return WhisperModel(
        MODELO_WHISPER,
        device="cpu",
        compute_type="int8",
    )


# ============================================================
# AGRUPAR PALABRAS EN SUBTÍTULOS
# ============================================================

def agrupar_palabras_subtitulos(palabras):
    subtitulos = []
    grupo_actual = []

    def guardar_grupo():
        if not grupo_actual:
            return

        inicio = grupo_actual[0]["inicio"]
        fin = grupo_actual[-1]["fin"]

        texto = " ".join(
            palabra["texto"]
            for palabra in grupo_actual
        )

        subtitulos.append({
            "inicio": round(inicio, 3),
            "fin": round(
                max(
                    fin,
                    inicio + DURACION_MINIMA_SUBTITULO,
                ),
                3,
            ),
            "texto": texto.upper(),
            "palabras": [
                palabra.copy()
                for palabra in grupo_actual
            ],
        })

        grupo_actual.clear()

    for palabra in palabras:
        texto = str(
            palabra.get("texto", "")
        ).strip()

        if not texto:
            continue

        inicio = max(
            0.0,
            float(palabra["inicio"]),
        )

        fin = max(
            inicio,
            float(palabra["fin"]),
        )

        if grupo_actual:
            fin_anterior = grupo_actual[-1]["fin"]
            pausa = inicio - fin_anterior

            if pausa >= PAUSA_MAXIMA_ENTRE_PALABRAS:
                guardar_grupo()

        grupo_actual.append({
            "inicio": inicio,
            "fin": fin,
            "texto": texto,
        })

        if len(grupo_actual) >= PALABRAS_POR_SUBTITULO:
            guardar_grupo()

    guardar_grupo()

    return subtitulos


# ============================================================
# TRANSCRIBIR VÍDEO
# ============================================================

def transcribir_video(ruta_video):
    modelo = obtener_modelo()

    segmentos, informacion = modelo.transcribe(
        str(ruta_video),
        language=IDIOMA,
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
    )

    transcripcion = []
    palabras_detectadas = []

    for segmento in segmentos:
        texto = segmento.text.strip()

        if not texto:
            continue

        transcripcion.append(texto)

        if segmento.words:
            for palabra in segmento.words:
                texto_palabra = palabra.word.strip()

                if not texto_palabra:
                    continue

                inicio = max(
                    0.0,
                    float(palabra.start or 0),
                )

                fin = max(
                    inicio,
                    float(palabra.end or inicio),
                )

                palabras_detectadas.append({
                    "inicio": round(inicio, 3),
                    "fin": round(fin, 3),
                    "texto": texto_palabra,
                })

        else:
            palabras_segmento = texto.split()

            if not palabras_segmento:
                continue

            inicio_segmento = max(
                0.0,
                float(segmento.start),
            )

            fin_segmento = max(
                inicio_segmento,
                float(segmento.end),
            )

            duracion = fin_segmento - inicio_segmento
            duracion_palabra = (
                duracion / len(palabras_segmento)
            )

            for indice, texto_palabra in enumerate(
                palabras_segmento
            ):
                inicio = (
                    inicio_segmento
                    + indice * duracion_palabra
                )

                fin = inicio + duracion_palabra

                palabras_detectadas.append({
                    "inicio": round(inicio, 3),
                    "fin": round(fin, 3),
                    "texto": texto_palabra,
                })

    palabras_detectadas.sort(
        key=lambda palabra: palabra["inicio"]
    )

    segmentos_subtitulos = agrupar_palabras_subtitulos(
        palabras_detectadas
    )

    if (
        not segmentos_subtitulos
        or not " ".join(transcripcion).strip()
    ):
        raise VozNoDetectadaError(
            "Error: este vídeo no se ha procesado porque no contiene "
            "voz reconocible para generar subtítulos."
        )

    return {
        "texto": " ".join(transcripcion),
        "segmentos": segmentos_subtitulos,
        "palabras": palabras_detectadas,
        "idioma": informacion.language,
    }


# ============================================================
# FORMATO DE MAYÚSCULAS Y MINÚSCULAS
# ============================================================

def aplicar_formato_subtitulos(
    segmentos,
    formato="mayusculas",
):
    """
    Mayúsculas:
        Todo el texto en mayúsculas.

    Minúsculas:
        Primera letra de frase en mayúscula.
        El resto en minúsculas.

    Se conserva el estado entre segmentos.
    """

    inicio_frase = True

    def transformar(texto):
        nonlocal inicio_frase

        resultado = []

        for caracter in str(texto).lower():
            if caracter.isalpha() and inicio_frase:
                resultado.append(caracter.upper())
                inicio_frase = False
            else:
                resultado.append(caracter)

            if caracter in ".!?":
                inicio_frase = True

        return "".join(resultado)

    resultado = []

    for segmento in segmentos:
        nuevo = dict(segmento)
        palabras = segmento.get("palabras") or []

        if formato == "minusculas":
            if palabras:
                nuevas_palabras = []

                for palabra in palabras:
                    copia = dict(palabra)
                    copia["texto"] = transformar(
                        palabra.get("texto", "")
                    )
                    nuevas_palabras.append(copia)

                nuevo["palabras"] = nuevas_palabras
                nuevo["texto"] = " ".join(
                    palabra["texto"]
                    for palabra in nuevas_palabras
                )

            else:
                nuevo["texto"] = transformar(
                    segmento.get("texto", "")
                )

        else:
            nuevo["texto"] = str(
                segmento.get("texto", "")
            ).upper()

            if palabras:
                nuevo["palabras"] = [
                    {
                        **palabra,
                        "texto": str(
                            palabra.get("texto", "")
                        ).upper(),
                    }
                    for palabra in palabras
                ]

        resultado.append(nuevo)

    return resultado


# ============================================================
# TIEMPOS SRT
# ============================================================

def formatear_tiempo_srt(segundos):
    milisegundos_totales = max(
        0,
        round(float(segundos) * 1000),
    )

    horas, resto = divmod(
        milisegundos_totales,
        3600000,
    )

    minutos, resto = divmod(
        resto,
        60000,
    )

    segundos, milisegundos = divmod(
        resto,
        1000,
    )

    return (
        f"{horas:02d}:"
        f"{minutos:02d}:"
        f"{segundos:02d},"
        f"{milisegundos:03d}"
    )


# ============================================================
# GENERAR SRT
# ============================================================

def generar_contenido_srt(segmentos):
    bloques = []
    numero_subtitulo = 1

    for segmento in segmentos:
        texto = str(
            segmento.get("texto", "")
        ).strip()

        if not texto:
            continue

        inicio = max(
            0.0,
            float(segmento["inicio"]),
        )

        fin = max(
            inicio + 0.001,
            float(segmento["fin"]),
        )

        bloque = (
            f"{numero_subtitulo}\n"
            f"{formatear_tiempo_srt(inicio)} --> "
            f"{formatear_tiempo_srt(fin)}\n"
            f"{texto}"
        )

        bloques.append(bloque)
        numero_subtitulo += 1

    if not bloques:
        return ""

    return "\n\n".join(bloques) + "\n"


def guardar_subtitulos_srt(
    segmentos,
    ruta_destino,
):
    ruta_destino = Path(ruta_destino)

    ruta_destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    contenido = generar_contenido_srt(
        segmentos
    )

    ruta_destino.write_text(
        contenido,
        encoding="utf-8-sig",
    )

    return str(ruta_destino)


# ============================================================
# TIEMPOS ASS
# ============================================================

def formatear_tiempo_ass(segundos):
    centesimas_totales = max(
        0,
        round(float(segundos) * 100),
    )

    horas, resto = divmod(
        centesimas_totales,
        360000,
    )

    minutos, resto = divmod(
        resto,
        6000,
    )

    segundos, centesimas = divmod(
        resto,
        100,
    )

    return (
        f"{horas}:{minutos:02d}:"
        f"{segundos:02d}.{centesimas:02d}"
    )


# ============================================================
# COLORES ASS
# ============================================================

def convertir_color_ass(color):
    color = str(color).strip().lstrip("#")

    if (
        len(color) != 6
        or any(
            caracter not in "0123456789abcdefABCDEF"
            for caracter in color
        )
    ):
        color = "FFFFFF"

    rojo = color[0:2]
    verde = color[2:4]
    azul = color[4:6]

    return f"&H00{azul}{verde}{rojo}".upper()


# ============================================================
# LIMPIAR TEXTO ASS
# ============================================================

def limpiar_texto_ass(texto):
    texto = str(texto)

    texto = texto.replace("\\", "＼")
    texto = texto.replace("{", "(")
    texto = texto.replace("}", ")")
    texto = texto.replace("\n", " ")

    return texto.strip()


# ============================================================
# ADAPTAR ESTILO A LA RESOLUCIÓN
# ============================================================

def calcular_estilo_ass(
    tamano,
    margen_vertical,
    margen_horizontal,
    ancho,
    alto,
):
    alto = max(1, int(alto))
    ancho = max(1, int(ancho))

    escala_vertical = alto / 288.0
    escala_horizontal = ancho / 384.0

    tamano_ass = max(
        12,
        round(
            float(tamano) * escala_vertical
        ),
    )

    margen_vertical_ass = max(
        0,
        round(
            float(margen_vertical)
            * escala_vertical
        ),
    )

    margen_horizontal_ass = max(
        0,
        round(
            float(margen_horizontal)
            * escala_horizontal
        ),
    )

    margen_vertical_ass = min(
        margen_vertical_ass,
        round(alto * 0.40),
    )

    margen_horizontal_ass = min(
        margen_horizontal_ass,
        round(ancho * 0.25),
    )

    contorno_ass = max(
        1,
        round(1.2 * escala_vertical),
    )

    sombra_ass = max(
        0,
        round(0.3 * escala_vertical),
    )

    return {
        "tamano": tamano_ass,
        "margen_vertical": margen_vertical_ass,
        "margen_horizontal": margen_horizontal_ass,
        "contorno": contorno_ass,
        "sombra": sombra_ass,
    }


# ============================================================
# NORMALIZAR TEXTO PARA BUSCAR PALABRAS
# ============================================================

def _normalizar_para_busqueda(texto):
    """
    Permite comparar sin distinguir
    mayúsculas ni tildes.
    """
    return "".join(
        caracter
        for caracter in unicodedata.normalize(
            "NFD",
            str(texto).casefold(),
        )
        if unicodedata.category(caracter) != "Mn"
    )


# ============================================================
# RESALTAR COINCIDENCIAS
# ============================================================

def _resaltar_coincidencias(
    texto,
    expresiones,
):
    """
    Resalta palabras o expresiones completas.
    Evita coincidencias dentro de otras palabras.
    """
    if not expresiones:
        return texto

    normalizado = _normalizar_para_busqueda(
        texto
    )

    intervalos = []

    for expresion in sorted(
        expresiones,
        key=len,
        reverse=True,
    ):
        patron = _normalizar_para_busqueda(
            expresion
        )

        if not patron:
            continue

        for coincidencia in re.finditer(
            re.escape(patron),
            normalizado,
        ):
            inicio, fin = coincidencia.span()

            if (
                inicio
                and normalizado[inicio - 1].isalnum()
            ):
                continue

            if (
                fin < len(normalizado)
                and normalizado[fin].isalnum()
            ):
                continue

            if any(
                inicio < fin_anterior
                and fin > inicio_anterior
                for inicio_anterior, fin_anterior
                in intervalos
            ):
                continue

            intervalos.append(
                (inicio, fin)
            )

    for inicio, fin in sorted(
        intervalos,
        reverse=True,
    ):
        texto = (
            texto[:inicio]
            + r"{\rResaltado}"
            + texto[inicio:fin]
            + r"{\rDefault}"
            + texto[fin:]
        )

    return texto


# ============================================================
# GENERAR CONTENIDO ASS
# ============================================================

def generar_contenido_ass(
    segmentos,
    plantilla=None,
    ancho=1080,
    alto=1920,
    palabras_destacadas="",
):
    tipografia = "Arial"
    tamano = 30
    posicion = "inferior"
    margen_vertical = 65
    margen_horizontal = 30
    color_texto = "#ffffff"
    animacion = "ninguna"
    duracion_animacion = 0.2
    destacar_palabras = False
    color_destacado = "#156fe7"

    if plantilla is not None:
        tipografia = getattr(
            plantilla,
            "tipografia",
            tipografia,
        )

        tamano = getattr(
            plantilla,
            "tamano_subtitulos",
            tamano,
        )

        posicion = getattr(
            plantilla,
            "posicion_subtitulos",
            posicion,
        )

        margen_vertical = getattr(
            plantilla,
            "margen_vertical",
            margen_vertical,
        )

        margen_horizontal = getattr(
            plantilla,
            "margen_horizontal",
            margen_horizontal,
        )

        color_texto = getattr(
            plantilla,
            "color_blanco",
            color_texto,
        )

        animacion = getattr(
            plantilla,
            "animacion_subtitulos",
            animacion,
        )

        duracion_animacion = getattr(
            plantilla,
            "duracion_animacion",
            duracion_animacion,
        )

        destacar_palabras = bool(
            getattr(
                plantilla,
                "destacar_palabras",
                False,
            )
        )

        color_destacado = getattr(
            plantilla,
            "color_destacado",
            color_destacado,
        )

    tipografia = str(tipografia).replace(
        ",",
        "",
    ).replace(
        "\n",
        "",
    )

    tamano = max(
        8,
        min(72, int(tamano)),
    )

    ancho = max(1, int(ancho))
    alto = max(1, int(alto))

    margen_vertical = max(
        0,
        int(margen_vertical),
    )

    margen_horizontal = max(
        0,
        int(margen_horizontal),
    )

    duracion_animacion = max(
        0.0,
        min(
            3.0,
            float(duracion_animacion),
        ),
    )

    estilo = calcular_estilo_ass(
        tamano=tamano,
        margen_vertical=margen_vertical,
        margen_horizontal=margen_horizontal,
        ancho=ancho,
        alto=alto,
    )

    tamano_ass = estilo["tamano"]
    margen_vertical_ass = estilo[
        "margen_vertical"
    ]
    margen_horizontal_ass = estilo[
        "margen_horizontal"
    ]
    contorno_ass = estilo["contorno"]
    sombra_ass = estilo["sombra"]

    alineaciones = {
        "inferior": 2,
        "centro": 5,
        "superior": 8,
    }

    alineacion = alineaciones.get(
        posicion,
        2,
    )

    color_ass = convertir_color_ass(
        color_texto
    )

    destacado_ass = convertir_color_ass(
        color_destacado
    )

    # ========================================================
    # ESTILOS ASS
    # ========================================================

    cabecera = f"""[Script Info]
Title: RETORI-CUT
ScriptType: v4.00+
PlayResX: {ancho}
PlayResY: {alto}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{tipografia},{tamano_ass},{color_ass},{color_ass},&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,{contorno_ass},{sombra_ass},{alineacion},{margen_horizontal_ass},{margen_horizontal_ass},{margen_vertical_ass},1
Style: Resaltado,{tipografia},{tamano_ass},{color_ass},{color_ass},{destacado_ass},{destacado_ass},-1,0,0,0,100,100,0,0,3,{max(4, round(tamano_ass * .16))},0,{alineacion},{margen_horizontal_ass},{margen_horizontal_ass},{margen_vertical_ass},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    eventos = []

    expresiones = [
        palabra.strip()
        for palabra in palabras_destacadas.split(",")
        if palabra.strip()
    ]

    def aplicar_resaltado(texto_evento):
        if not destacar_palabras or not expresiones:
            return texto_evento

        return _resaltar_coincidencias(
            texto_evento,
            expresiones,
        )

    for segmento in segmentos:
        inicio = max(
            0.0,
            float(segmento["inicio"]),
        )

        fin = max(
            inicio + 0.01,
            float(segmento["fin"]),
        )

        texto = limpiar_texto_ass(
            segmento.get("texto", "")
        )

        if not texto:
            continue

        palabras = segmento.get(
            "palabras",
            [],
        )

        # ====================================================
        # ANIMACIÓN POR PALABRA
        # ====================================================

        if animacion == "palabra" and palabras:
            for indice in range(len(palabras)):
                palabra_actual = palabras[indice]

                inicio_palabra = max(
                    inicio,
                    float(
                        palabra_actual["inicio"]
                    ),
                )

                if indice + 1 < len(palabras):
                    fin_palabra = min(
                        fin,
                        float(
                            palabras[indice + 1]["inicio"]
                        ),
                    )
                else:
                    fin_palabra = fin

                fin_palabra = max(
                    inicio_palabra + 0.01,
                    fin_palabra,
                )

                texto_progresivo = " ".join(
                    limpiar_texto_ass(
                        palabra["texto"]
                    )
                    for palabra in palabras[
                        :indice + 1
                    ]
                )

                if not texto_progresivo:
                    continue

                eventos.append((
                    inicio_palabra,
                    fin_palabra,
                    aplicar_resaltado(
                        texto_progresivo
                    ),
                ))

        # ====================================================
        # ANIMACIÓN POR BLOQUE
        # ====================================================

        elif animacion == "bloque":
            milisegundos = min(
                int(
                    duracion_animacion * 1000
                ),
                int(
                    (fin - inicio) * 1000
                ),
            )

            etiqueta = (
                r"{\fad("
                + str(milisegundos)
                + ",0)}"
            )

            eventos.append((
                inicio,
                fin,
                etiqueta + aplicar_resaltado(
                    texto
                ),
            ))

        # ====================================================
        # SIN ANIMACIÓN
        # ====================================================

        else:
            eventos.append((
                inicio,
                fin,
                aplicar_resaltado(texto),
            ))

    eventos.sort(
        key=lambda evento: evento[0]
    )

    lineas = [cabecera]

    for inicio, fin, texto in eventos:
        linea = (
            "Dialogue: 0,"
            f"{formatear_tiempo_ass(inicio)},"
            f"{formatear_tiempo_ass(fin)},"
            "Default,,0,0,0,,"
            f"{texto}"
        )

        lineas.append(linea)

    return "\n".join(lineas) + "\n"


# ============================================================
# GUARDAR SUBTÍTULOS ASS
# ============================================================

def guardar_subtitulos_ass(
    segmentos,
    ruta_destino,
    plantilla=None,
    ancho=1080,
    alto=1920,
    palabras_destacadas="",
):
    ruta_destino = Path(ruta_destino)

    ruta_destino.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    contenido = generar_contenido_ass(
        segmentos=segmentos,
        plantilla=plantilla,
        ancho=ancho,
        alto=alto,
        palabras_destacadas=palabras_destacadas,
    )

    ruta_destino.write_text(
        contenido,
        encoding="utf-8",
    )

    return str(ruta_destino)
