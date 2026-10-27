
import json
import re
import subprocess
from pathlib import Path


# ============================================================
# ANALIZAR VÍDEO MEDIANTE FFPROBE
# ============================================================

def analizar_video(ruta_video):
    """
    Analiza un vídeo mediante FFprobe y devuelve
    sus características técnicas.
    """

    comando = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "format=duration,format_name:stream=codec_type,width,height,r_frame_rate",
        "-of", "json",
        str(ruta_video),
    ]

    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )

    datos = json.loads(resultado.stdout)

    formato = datos.get("format", {})
    streams = datos.get("streams", [])

    video = next(
        (
            stream
            for stream in streams
            if stream.get("codec_type") == "video"
        ),
        None,
    )

    if video is None:
        raise ValueError(
            "El archivo no contiene una pista de vídeo válida."
        )

    fps_texto = video.get("r_frame_rate", "0/1")

    try:
        numerador, denominador = map(
            int,
            fps_texto.split("/")
        )

        fps = (
            round(numerador / denominador, 2)
            if denominador
            else 0
        )

    except (ValueError, ZeroDivisionError):
        fps = 0

    return {
        "duracion": round(
            float(formato.get("duration") or 0),
            2
        ),
        "ancho": video.get("width"),
        "alto": video.get("height"),
        "fps": fps,
        "formato": formato.get("format_name", ""),
    }


# ============================================================
# EXTRAER PRIMER FOTOGRAMA DEL VÍDEO
# ============================================================

def extraer_primer_fotograma(
    ruta_video,
    ruta_imagen,
):
    """
    Extrae el primer fotograma decodificable del vídeo
    mediante FFmpeg y lo guarda como imagen JPG.

    Devuelve la ruta de la imagen generada.
    """

    ruta_video = Path(ruta_video)
    ruta_imagen = Path(ruta_imagen)

    if not ruta_video.is_file():
        raise FileNotFoundError(
            f"No existe el vídeo: {ruta_video}"
        )

    ruta_imagen.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    comando = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(ruta_video),
        "-map", "0:v:0",
        "-frames:v", "1",
        "-q:v", "2",
        str(ruta_imagen),
    ]

    try:
        subprocess.run(
            comando,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
    ):
        if ruta_imagen.exists():
            ruta_imagen.unlink()

        raise

    if (
        not ruta_imagen.is_file()
        or ruta_imagen.stat().st_size == 0
    ):
        raise RuntimeError(
            "FFmpeg no ha generado una miniatura válida."
        )

    return str(ruta_imagen)


# ============================================================
# PREPARAR RUTA DE SUBTÍTULOS PARA FFMPEG
# ============================================================

def preparar_ruta_subtitulos(ruta_subtitulos):
    """
    Prepara una ruta absoluta para el filtro subtitles
    de FFmpeg en Windows y Linux.
    """

    ruta = Path(ruta_subtitulos).resolve().as_posix()

    ruta = ruta.replace("\\", "\\\\")
    ruta = ruta.replace(":", "\\:")
    ruta = ruta.replace("'", "\\'")
    ruta = ruta.replace("[", "\\[")
    ruta = ruta.replace("]", "\\]")
    ruta = ruta.replace(",", "\\,")

    return ruta


# ============================================================
# CONVERTIR COLORES HEXADECIMALES A FORMATO ASS
# ============================================================

def convertir_color_ass(color, predeterminado="#ffffff"):
    """
    Convierte #RRGGBB al formato ASS:
    &H00BBGGRR
    """

    if not isinstance(color, str):
        color = predeterminado

    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        color = predeterminado

    rojo = color[1:3]
    verde = color[3:5]
    azul = color[5:7]

    return f"&H00{azul}{verde}{rojo}".upper()


# ============================================================
# GENERAR ESTILO A PARTIR DE UNA PLANTILLA
# ============================================================

def obtener_estilo_subtitulos(plantilla=None):
    """
    Construye el estilo de los subtítulos SRT.

    Los archivos ASS ya contienen su propio estilo,
    por lo que no necesitan esta configuración.
    """

    if plantilla is None:
        return (
            "FontName=Arial,"
            "FontSize=18,"
            "PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,"
            "BorderStyle=1,"
            "Outline=2,"
            "Shadow=1,"
            "Alignment=2,"
            "MarginV=65"
        )

    tipografia = getattr(
        plantilla,
        "tipografia",
        "Arial"
    )

    fuentes_admitidas = {
        "Arial",
        "Montserrat",
        "Retorika",
    }

    if tipografia not in fuentes_admitidas:
        tipografia = "Arial"

    tamano = int(
        getattr(
            plantilla,
            "tamano_subtitulos",
            18
        )
    )

    tamano = max(8, min(tamano, 72))

    posicion = getattr(
        plantilla,
        "posicion_subtitulos",
        "inferior"
    )

    alineaciones = {
        "inferior": 2,
        "centro": 5,
        "superior": 8,
    }

    alineacion = alineaciones.get(posicion, 2)

    margen_vertical = max(
        0,
        int(
            getattr(
                plantilla,
                "margen_vertical",
                65
            )
        )
    )

    margen_horizontal = max(
        0,
        int(
            getattr(
                plantilla,
                "margen_horizontal",
                30
            )
        )
    )

    color_texto = convertir_color_ass(
        getattr(
            plantilla,
            "color_blanco",
            "#ffffff"
        )
    )

    color_contorno = convertir_color_ass(
        "#000000"
    )

    return (
        f"FontName={tipografia},"
        f"FontSize={tamano},"
        f"PrimaryColour={color_texto},"
        f"OutlineColour={color_contorno},"
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=1,"
        f"Alignment={alineacion},"
        f"MarginV={margen_vertical},"
        f"MarginL={margen_horizontal},"
        f"MarginR={margen_horizontal}"
    )


# ============================================================
# CONFIGURACIÓN REAL DE EXPORTACIÓN
# ============================================================

def obtener_parametros_exportacion(preferencias=None):
    """
    Obtiene los parámetros de exportación a partir
    de las preferencias del usuario.

    Si no se proporcionan preferencias, utiliza
    los valores predeterminados de RETORI-CUT.

    Devuelve:
        ancho
        alto
        fps
        crf
        preset
    """

    resolucion = str(
        getattr(
            preferencias,
            "resolucion",
            "1080"
        )
    )

    fps = getattr(
        preferencias,
        "fps",
        30
    )

    calidad = getattr(
        preferencias,
        "calidad",
        "equilibrada"
    )

    # ========================================================
    # VALIDAR RESOLUCIÓN
    # ========================================================

    resoluciones = {
        "720": (720, 1280),
        "1080": (1080, 1920),
    }

    ancho, alto = resoluciones.get(
        resolucion,
        (1080, 1920)
    )

    # ========================================================
    # VALIDAR FPS
    # ========================================================

    try:
        fps = int(fps)
    except (TypeError, ValueError):
        fps = 30

    if fps not in (24, 30, 60):
        fps = 30

    # ========================================================
    # CALIDAD DE COMPRESIÓN
    # ========================================================

    calidades = {
        "alta": 18,
        "equilibrada": 20,
        "ligera": 25,
    }

    crf = calidades.get(
        calidad,
        20
    )

    return {
        "ancho": ancho,
        "alto": alto,
        "fps": fps,
        "crf": crf,
        "preset": "medium",
    }


# ============================================================
# GENERAR FILTROS DE EXPORTACIÓN
# ============================================================

def obtener_filtros_exportacion(
    preferencias=None,
    filtro_previo=None,
):
    """
    Genera los filtros FFmpeg para exportar
    a la resolución y FPS configurados.

    Respeta la relación de aspecto del original.

    Si el vídeo no es vertical 9:16, añade bandas
    para completar el formato sin deformarlo.

    El filtro previo permite incrustar subtítulos
    antes de redimensionar el vídeo, conservando
    la escala relativa de sus estilos.
    """

    parametros = obtener_parametros_exportacion(
        preferencias
    )

    ancho = parametros["ancho"]
    alto = parametros["alto"]
    fps = parametros["fps"]

    filtros = []

    if filtro_previo:
        filtros.append(
            filtro_previo
        )

    # ========================================================
    # REDIMENSIONAR SIN DEFORMAR
    # ========================================================

    filtros.append(
        f"scale={ancho}:{alto}:"
        "force_original_aspect_ratio=decrease:"
        "flags=lanczos"
    )

    # ========================================================
    # COMPLETAR FORMATO VERTICAL
    # ========================================================

    filtros.append(
        f"pad={ancho}:{alto}:"
        "(ow-iw)/2:(oh-ih)/2:"
        "color=black"
    )

    # ========================================================
    # ESTABLECER FPS
    # ========================================================

    filtros.append(
        f"fps={fps}"
    )

    # ========================================================
    # FORMATO DE PÍXELES
    # ========================================================

    filtros.append(
        "format=yuv420p"
    )

    return ",".join(filtros)


# ============================================================
# GENERAR PARÁMETROS DE CODIFICACIÓN
# ============================================================

def obtener_argumentos_codificacion(preferencias=None):
    """
    Devuelve los parámetros reales de codificación
    de vídeo y audio para FFmpeg.

    El formato final es MP4 con H.264 y AAC.
    """

    parametros = obtener_parametros_exportacion(
        preferencias
    )

    return [
        "-c:v", "libx264",
        "-preset", parametros["preset"],
        "-crf", str(parametros["crf"]),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
    ]


# ============================================================
# INCRUSTAR SUBTÍTULOS SRT O ASS EN EL VÍDEO
# ============================================================

def incrustar_subtitulos_video(
    ruta_video,
    ruta_subtitulos,
    ruta_salida,
    plantilla=None,
    preferencias=None,
):
    """
    Genera un MP4 con subtítulos incrustados.

    SRT:
        Aplica los estilos básicos de la plantilla.

    ASS:
        Conserva los estilos y animaciones
        definidos dentro del propio archivo.

    Exportación:
        Permite aplicar resolución, FPS y calidad
        según las preferencias del usuario.

    Compatibilidad:
        El argumento preferencias es opcional para
        mantener las llamadas anteriores.
    """

    ruta_video = Path(ruta_video)
    ruta_subtitulos = Path(ruta_subtitulos)
    ruta_salida = Path(ruta_salida)

    # ========================================================
    # COMPROBAR ARCHIVOS
    # ========================================================

    if not ruta_video.is_file():
        raise FileNotFoundError(
            f"No existe el vídeo: {ruta_video}"
        )

    if not ruta_subtitulos.is_file():
        raise FileNotFoundError(
            f"No existe el archivo de subtítulos: "
            f"{ruta_subtitulos}"
        )

    if ruta_video.resolve() == ruta_salida.resolve():
        raise ValueError(
            "El vídeo de salida debe ser diferente "
            "del vídeo original."
        )

    extension = ruta_subtitulos.suffix.lower()

    if extension not in {".srt", ".ass"}:
        raise ValueError(
            "Formato de subtítulos no compatible. "
            "Utiliza SRT o ASS."
        )

    ruta_salida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # PREPARAR FILTRO DE SUBTÍTULOS
    # ========================================================

    ruta_ffmpeg = preparar_ruta_subtitulos(
        ruta_subtitulos
    )

    if extension == ".ass":

        # El archivo ASS contiene tipografía, colores,
        # posición y animaciones.
        # No aplicamos force_style para no sobrescribirlos.

        filtro_subtitulos = (
            f"subtitles=filename='{ruta_ffmpeg}'"
        )

    else:

        # Los SRT no contienen estilos avanzados.
        # Aplicamos los valores de la plantilla.

        estilo_subtitulos = obtener_estilo_subtitulos(
            plantilla
        )

        filtro_subtitulos = (
            f"subtitles=filename='{ruta_ffmpeg}'"
            f":force_style='{estilo_subtitulos}'"
        )

    # ========================================================
    # PREPARAR EXPORTACIÓN REAL
    # ========================================================

    if preferencias is None:

        # Mantener el comportamiento anterior cuando
        # todavía no se envían preferencias desde views.py.

        filtro_video = filtro_subtitulos

        argumentos_codificacion = [
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
        ]

    else:

        # Aplicar los ajustes elegidos por el usuario.

        filtro_video = obtener_filtros_exportacion(
            preferencias=preferencias,
            filtro_previo=filtro_subtitulos,
        )

        argumentos_codificacion = (
            obtener_argumentos_codificacion(
                preferencias
            )
        )

    # ========================================================
    # GENERAR VÍDEO
    # ========================================================

    comando = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(ruta_video),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-vf", filtro_video,
        *argumentos_codificacion,
        str(ruta_salida),
    ]

    try:
        subprocess.run(
            comando,
            capture_output=True,
            text=True,
            check=True,
            timeout=1800,
        )

    except subprocess.CalledProcessError as error:

        if ruta_salida.exists():
            ruta_salida.unlink()

        detalle = (
            error.stderr
            or "FFmpeg no ha indicado el motivo."
        )

        raise RuntimeError(
            "Error al incrustar los subtítulos:\n"
            + detalle
        ) from error

    except (
        subprocess.TimeoutExpired,
        OSError,
    ):

        if ruta_salida.exists():
            ruta_salida.unlink()

        raise

    # ========================================================
    # COMPROBAR RESULTADO
    # ========================================================

    if (
        not ruta_salida.is_file()
        or ruta_salida.stat().st_size == 0
    ):
        raise RuntimeError(
            "FFmpeg no ha generado un vídeo válido."
        )

    return str(ruta_salida)


# ============================================================
# COMPROBAR SI EL VÍDEO CONTIENE UNA PISTA DE AUDIO
# ============================================================

def video_tiene_audio(ruta_video):
    """
    Comprueba mediante FFprobe si un vídeo contiene
    al menos una pista de audio.

    Devuelve:
        True: existe una pista de audio.
        False: no existe ninguna pista de audio.

    Si FFprobe falla, se propaga la excepción
    para no confundir un archivo dañado con
    un vídeo válido sin audio.
    """

    ruta_video = Path(ruta_video)

    if not ruta_video.is_file():
        raise FileNotFoundError(
            f"No existe el vídeo: {ruta_video}"
        )

    comando = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "json",
        str(ruta_video),
    ]

    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )

    datos = json.loads(resultado.stdout)

    return bool(
        datos.get("streams", [])
    )
