
from functools import lru_cache
from pathlib import Path

from faster_whisper import WhisperModel


# ============================================================
# CONFIGURACIÓN DE WHISPER
# ============================================================

MODELO_WHISPER = "small"
IDIOMA = "es"

# Configuración de subtítulos Retorika
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
# AGRUPAR PALABRAS EN SUBTÍTULOS RETORIKA
# ============================================================

def agrupar_palabras_subtitulos(palabras):
    """
    Agrupa palabras en bloques de hasta tres.

    Cada bloque conserva los tiempos de inicio
    y final de las palabras detectadas por Whisper.

    Si existe una pausa importante, se inicia
    un nuevo subtítulo.
    """

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
                    inicio + DURACION_MINIMA_SUBTITULO
                ),
                3
            ),
            "texto": texto.upper(),
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
            float(palabra["inicio"])
        )

        fin = max(
            inicio,
            float(palabra["fin"])
        )

        # Detectar pausas entre palabras

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

        # Limitar cada subtítulo a tres palabras

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

        # Obtener los tiempos individuales de las palabras

        if segmento.words:

            for palabra in segmento.words:

                texto_palabra = palabra.word.strip()

                if not texto_palabra:
                    continue

                palabras_detectadas.append({
                    "inicio": round(
                        max(0.0, palabra.start),
                        3
                    ),
                    "fin": round(
                        max(palabra.start, palabra.end),
                        3
                    ),
                    "texto": texto_palabra,
                })

        else:

            # Compatibilidad si Whisper no devuelve
            # tiempos individuales para algún segmento.

            palabras_segmento = texto.split()

            if not palabras_segmento:
                continue

            inicio_segmento = max(
                0.0,
                float(segmento.start)
            )

            fin_segmento = max(
                inicio_segmento,
                float(segmento.end)
            )

            duracion = (
                fin_segmento - inicio_segmento
            )

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

                fin = (
                    inicio + duracion_palabra
                )

                palabras_detectadas.append({
                    "inicio": round(inicio, 3),
                    "fin": round(fin, 3),
                    "texto": texto_palabra,
                })

    # Ordenar palabras por tiempo de aparición

    palabras_detectadas.sort(
        key=lambda palabra: palabra["inicio"]
    )

    # Generar subtítulos con estilo Retorika

    segmentos_subtitulos = agrupar_palabras_subtitulos(
        palabras_detectadas
    )

    return {
        "texto": " ".join(transcripcion),
        "segmentos": segmentos_subtitulos,
        "palabras": palabras_detectadas,
        "idioma": informacion.language,
    }


# ============================================================
# CONVERTIR SEGUNDOS AL FORMATO SRT
# ============================================================

def formatear_tiempo_srt(segundos):

    milisegundos_totales = max(
        0,
        round(float(segundos) * 1000)
    )

    horas, resto = divmod(
        milisegundos_totales,
        3600000
    )

    minutos, resto = divmod(
        resto,
        60000
    )

    segundos, milisegundos = divmod(
        resto,
        1000
    )

    return (
        f"{horas:02d}:"
        f"{minutos:02d}:"
        f"{segundos:02d},"
        f"{milisegundos:03d}"
    )


# ============================================================
# GENERAR CONTENIDO SRT
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
            float(segmento["inicio"])
        )

        fin = max(
            inicio + 0.001,
            float(segmento["fin"])
        )

        tiempo_inicio = formatear_tiempo_srt(
            inicio
        )

        tiempo_fin = formatear_tiempo_srt(
            fin
        )

        bloque = (
            f"{numero_subtitulo}\n"
            f"{tiempo_inicio} --> {tiempo_fin}\n"
            f"{texto.upper()}"
        )

        bloques.append(bloque)

        numero_subtitulo += 1

    if not bloques:
        return ""

    return "\n\n".join(bloques) + "\n"


# ============================================================
# GUARDAR ARCHIVO DE SUBTÍTULOS SRT
# ============================================================

def guardar_subtitulos_srt(segmentos, ruta_destino):

    ruta_destino = Path(
        ruta_destino
    )

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
