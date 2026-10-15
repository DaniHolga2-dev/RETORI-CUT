
import json
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
# PREPARAR RUTA SRT PARA EL FILTRO DE FFMPEG
# ============================================================

def preparar_ruta_subtitulos(ruta_subtitulos):
    """
    Convierte una ruta de Windows o Linux al formato
    admitido por el filtro subtitles de FFmpeg.

    Escapa los caracteres especiales de la ruta.
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
# INCRUSTAR SUBTÍTULOS SRT EN EL VÍDEO
# ============================================================

def incrustar_subtitulos_video(
    ruta_video,
    ruta_subtitulos,
    ruta_salida,
):
    """
    Genera un nuevo MP4 con los subtítulos SRT
    incrustados permanentemente en la imagen.

    Conserva el audio del vídeo original.

    Requiere una instalación de FFmpeg con
    soporte para el filtro subtitles (libass).
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
            f"No existe el archivo SRT: {ruta_subtitulos}"
        )

    if ruta_video.resolve() == ruta_salida.resolve():
        raise ValueError(
            "El vídeo de salida debe ser diferente "
            "del vídeo original."
        )

    ruta_salida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ========================================================
    # CONFIGURAR ESTILO DE LOS SUBTÍTULOS
    # ========================================================

    # Estilo provisional. Más adelante añadiremos
    # las plantillas visuales de RETORI-CUT.

    estilo_subtitulos = (
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

    ruta_srt_ffmpeg = preparar_ruta_subtitulos(
        ruta_subtitulos
    )

    filtro_subtitulos = (
        f"subtitles=filename='{ruta_srt_ffmpeg}'"
        f":force_style='{estilo_subtitulos}'"
    )

    # ========================================================
    # GENERAR VÍDEO CON SUBTÍTULOS
    # ========================================================

    comando = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(ruta_video),
        "-map", "0:v:0",
        "-map", "0:a?",
        "-vf", filtro_subtitulos,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
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
