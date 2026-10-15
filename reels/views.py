
import logging
import threading
from pathlib import Path

from django.contrib import messages
from django.core.files import File
from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ReelUploadForm, ConfiguracionMarcaForm, PlantillaForm
from .models import Reel, ConfiguracionMarca, Plantilla
from .transcription_utils import (
    transcribir_video,
    guardar_subtitulos_srt,
)
from .video_utils import (
    analizar_video,
    extraer_primer_fotograma,
    incrustar_subtitulos_video,
)


logger = logging.getLogger(__name__)


# ============================================================
# ACTUALIZAR ESTADO DEL PROCESAMIENTO
# ============================================================

def actualizar_progreso(reel, estado, progreso, mensaje):

    reel.estado = estado
    reel.progreso = progreso
    reel.mensaje_procesamiento = mensaje

    reel.save(
        update_fields=[
            "estado",
            "progreso",
            "mensaje_procesamiento",
        ]
    )


# ============================================================
# PROCESAR REEL EN SEGUNDO PLANO
# ============================================================

def procesar_reel_segundo_plano(reel_id):

    # Cada hilo utiliza su propia conexión a la base de datos.

    close_old_connections()

    try:

        reel = Reel.objects.get(id=reel_id)

        ruta_video = Path(
            reel.archivo_original.path
        )

        # ====================================================
        # FASE 1: ANÁLISIS TÉCNICO
        # ====================================================

        actualizar_progreso(
            reel,
            Reel.ESTADO_ANALIZANDO,
            10,
            "Analizando las características del vídeo...",
        )

        datos = analizar_video(ruta_video)

        reel.duracion = datos["duracion"]
        reel.ancho = datos["ancho"]
        reel.alto = datos["alto"]

        reel.formato = (
            Path(reel.archivo_original.name)
            .suffix
            .lstrip(".")
            .upper()
        )

        reel.peso = reel.archivo_original.size

        reel.progreso = 25
        reel.mensaje_procesamiento = (
            "Análisis técnico completado."
        )

        reel.save(
            update_fields=[
                "duracion",
                "ancho",
                "alto",
                "formato",
                "peso",
                "progreso",
                "mensaje_procesamiento",
            ]
        )

        # ====================================================
        # FASE 2: GENERAR MINIATURA
        # ====================================================

        actualizar_progreso(
            reel,
            Reel.ESTADO_ANALIZANDO,
            30,
            "Generando vista previa del vídeo...",
        )

        nombre_miniatura = (
            f"reel_{reel.id}_miniatura.jpg"
        )

        ruta_temporal = (
            ruta_video.parent
            / f"reel_{reel.id}_fotograma.jpg"
        )

        try:

            extraer_primer_fotograma(
                ruta_video,
                ruta_temporal,
            )

            with open(ruta_temporal, "rb") as imagen:

                reel.miniatura.save(
                    nombre_miniatura,
                    File(imagen),
                    save=False,
                )

            reel.save(
                update_fields=["miniatura"]
            )

        finally:

            if ruta_temporal.exists():
                ruta_temporal.unlink()

        # ====================================================
        # FASE 3: TRANSCRIPCIÓN CON WHISPER
        # ====================================================

        actualizar_progreso(
            reel,
            Reel.ESTADO_TRANSCRIBIENDO,
            35,
            "Transcribiendo el audio con Whisper...",
        )

        resultado = transcribir_video(
            str(ruta_video)
        )

        reel.transcripcion = resultado["texto"]

        reel.progreso = 60
        reel.mensaje_procesamiento = (
            "Transcripción completada. "
            "Generando subtítulos sincronizados..."
        )

        reel.save(
            update_fields=[
                "transcripcion",
                "progreso",
                "mensaje_procesamiento",
            ]
        )

        # ====================================================
        # FASE 4: GENERAR SUBTÍTULOS SRT
        # ====================================================

        actualizar_progreso(
            reel,
            Reel.ESTADO_TRANSCRIBIENDO,
            65,
            "Generando archivo de subtítulos SRT...",
        )

        if reel.subtitulos_activos:

            segmentos = resultado["segmentos"]

            if not segmentos:
                raise ValueError(
                    "Whisper no ha detectado fragmentos "
                    "de voz para generar subtítulos."
                )

            nombre_srt = (
                f"reel_{reel.id}_subtitulos.srt"
            )

            ruta_srt_temporal = (
                ruta_video.parent
                / nombre_srt
            )

            try:

                guardar_subtitulos_srt(
                    segmentos,
                    ruta_srt_temporal,
                )

                with open(ruta_srt_temporal, "rb") as archivo:

                    reel.archivo_subtitulos.save(
                        nombre_srt,
                        File(archivo),
                        save=False,
                    )

                reel.save(
                    update_fields=["archivo_subtitulos"]
                )

            finally:

                if ruta_srt_temporal.exists():
                    ruta_srt_temporal.unlink()

        # ====================================================
        # FASE 5: PREPARAR EXPORTACIÓN
        # ====================================================

        actualizar_progreso(
            reel,
            Reel.ESTADO_EDITANDO,
            70,
            (
                "Subtítulos preparados. "
                "Iniciando exportación del vídeo..."
                if reel.subtitulos_activos
                else
                "Transcripción completada. "
                "Iniciando exportación del vídeo..."
            ),
        )

        # ====================================================
        # FASE 6: EXPORTAR VÍDEO
        # ====================================================

        actualizar_progreso(
            reel,
            Reel.ESTADO_EDITANDO,
            80,
            "Exportando vídeo MP4 con FFmpeg...",
        )

        nombre_exportado = (
            f"reel_{reel.id}_exportado.mp4"
        )

        ruta_exportacion_temporal = (
            ruta_video.parent
            / nombre_exportado
        )

        try:

            if reel.subtitulos_activos:

                # Utilizamos la ruta real del SRT guardado
                # por Django en MEDIA_ROOT.

                ruta_srt = Path(
                    reel.archivo_subtitulos.path
                )

                incrustar_subtitulos_video(
                    ruta_video,
                    ruta_srt,
                    ruta_exportacion_temporal,
                )

            else:

                # Si los subtítulos están desactivados,
                # generamos un MP4 sin incrustarlos.

                import subprocess

                comando = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel", "error",
                    "-y",
                    "-i", str(ruta_video),
                    "-map", "0:v:0",
                    "-map", "0:a?",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "20",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    str(ruta_exportacion_temporal),
                ]

                subprocess.run(
                    comando,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=1800,
                )

            if (
                not ruta_exportacion_temporal.is_file()
                or ruta_exportacion_temporal.stat().st_size == 0
            ):
                raise RuntimeError(
                    "No se ha generado el vídeo exportado."
                )

            # ====================================================
            # GUARDAR MP4 EN EL MODELO
            # ====================================================

            actualizar_progreso(
                reel,
                Reel.ESTADO_EDITANDO,
                95,
                "Guardando el vídeo exportado...",
            )

            with open(
                ruta_exportacion_temporal,
                "rb",
            ) as archivo:

                reel.archivo_editado.save(
                    nombre_exportado,
                    File(archivo),
                    save=False,
                )

            reel.save(
                update_fields=["archivo_editado"]
            )

        finally:

            if ruta_exportacion_temporal.exists():
                ruta_exportacion_temporal.unlink()

        # ====================================================
        # FASE 7: FINALIZACIÓN
        # ====================================================

        actualizar_progreso(
            reel,
            Reel.ESTADO_LISTO,
            100,
            (
                "Vídeo exportado correctamente "
                "con subtítulos incrustados."
                if reel.subtitulos_activos
                else
                "Vídeo exportado correctamente."
            ),
        )

        logger.info(
            "Reel %s: procesamiento y exportación completados.",
            reel.id,
        )

    except Exception:

        logger.exception(
            "Error procesando el reel %s",
            reel_id,
        )

        try:

            Reel.objects.filter(
                id=reel_id
            ).update(
                estado=Reel.ESTADO_ERROR,
                progreso=0,
                mensaje_procesamiento=(
                    "No se ha podido procesar el vídeo. "
                    "Consulta la terminal para ver el error."
                ),
            )

        except Exception:

            logger.exception(
                "No se pudo guardar el error del reel %s",
                reel_id,
            )

    finally:

        close_old_connections()


# ============================================================
# SUBIR NUEVO REEL
# ============================================================

def nuevo_reel(request):

    obtener_plantilla_oficial()

    if request.method == "POST":

        formulario = ReelUploadForm(
            request.POST,
            request.FILES,
        )

        if formulario.is_valid():

            reel = formulario.save(
                commit=False
            )

            reel.estado = Reel.ESTADO_ANALIZANDO
            reel.progreso = 5

            reel.mensaje_procesamiento = (
                "Vídeo recibido. Iniciando análisis..."
            )

            reel.save()

            # Procesamiento en segundo plano para desarrollo local.

            hilo = threading.Thread(
                target=procesar_reel_segundo_plano,
                args=(reel.id,),
                daemon=True,
                name=f"retoricut-reel-{reel.id}",
            )

            try:

                hilo.start()

            except Exception:

                logger.exception(
                    "No se pudo iniciar el procesamiento "
                    "del reel %s",
                    reel.id,
                )

                Reel.objects.filter(
                    id=reel.id
                ).update(
                    estado=Reel.ESTADO_ERROR,
                    progreso=0,
                    mensaje_procesamiento=(
                        "No se pudo iniciar el procesamiento."
                    ),
                )

            return redirect(
                "procesando_reel",
                reel_id=reel.id,
            )

    else:

        formulario = ReelUploadForm()

    return render(
        request,
        "reels/nuevo_reel.html",
        {
            "formulario": formulario,
        },
    )


# ============================================================
# PANTALLA DE PROCESAMIENTO
# ============================================================

def procesando_reel(request, reel_id):

    reel = get_object_or_404(
        Reel,
        id=reel_id,
    )

    return render(
        request,
        "reels/procesando_reel.html",
        {
            "reel": reel,
        },
    )


# ============================================================
# CONSULTAR PROGRESO EN TIEMPO REAL
# ============================================================

def estado_reel(request, reel_id):

    reel = get_object_or_404(
        Reel,
        id=reel_id,
    )

    return JsonResponse({

        "id": reel.id,

        "nombre": reel.nombre,

        "estado": reel.estado,

        "progreso": reel.progreso,

        "mensaje": reel.mensaje_procesamiento,

        "duracion": reel.duracion,

        "ancho": reel.ancho,

        "alto": reel.alto,

        "formato": reel.formato,

        "miniatura": (
            reel.miniatura.url
            if reel.miniatura
            else None
        ),

        "archivo_subtitulos": (
            reel.archivo_subtitulos.url
            if reel.archivo_subtitulos
            else None
        ),

        "subtitulos_generados": bool(
            reel.archivo_subtitulos
        ),

        "archivo_editado": (
            reel.archivo_editado.url
            if reel.archivo_editado
            else None
        ),

        "video_exportado": bool(
            reel.archivo_editado
        ),

        "transcripcion_completada": (
            bool(reel.transcripcion)
        ),

        "procesamiento_terminado": (
            reel.estado in [
                Reel.ESTADO_LISTO,
                Reel.ESTADO_ERROR,
            ]
        ),

    })


# ============================================================
# CONFIGURACIÓN DE MARCA RETORIKA
# ============================================================

@require_http_methods(["GET", "POST"])
def configuracion_marca(request):

    # Recuperar la configuración global.
    # Si no existe todavía, crearla con los valores iniciales.

    configuracion = (
        ConfiguracionMarca.obtener_configuracion()
    )

    # ========================================================
    # GUARDAR CAMBIOS
    # ========================================================

    if request.method == "POST":

        formulario = ConfiguracionMarcaForm(
            request.POST,
            request.FILES,
            instance=configuracion,
        )

        if formulario.is_valid():

            formulario.save()

            messages.success(
                request,
                "La configuración de marca se ha guardado "
                "correctamente.",
            )

            return redirect(
                "configuracion_marca"
            )

    # ========================================================
    # MOSTRAR CONFIGURACIÓN ACTUAL
    # ========================================================

    else:

        formulario = ConfiguracionMarcaForm(
            instance=configuracion
        )

    # ========================================================
    # RENDERIZAR PANTALLA
    # ========================================================

    return render(
        request,
        "reels/configuracion_marca.html",
        {
            "formulario": formulario,
            "configuracion": configuracion,
        },
    )


# ============================================================
# PLANTILLA OFICIAL RETORIKA
# ============================================================

def obtener_plantilla_oficial():

    # Crea la plantilla oficial una sola vez.
    # No sobrescribe sus valores si ya existe.

    plantilla, _ = Plantilla.objects.get_or_create(
        tipo="oficial",
        defaults={
            "nombre": "Retorika",
            "descripcion": "Plantilla corporativa de Retorika.",
            "activa": True,
        },
    )

    return plantilla


# ============================================================
# LISTADO DE PLANTILLAS
# ============================================================

@require_http_methods(["GET"])
def mis_plantillas(request):

    obtener_plantilla_oficial()

    plantillas = Plantilla.objects.all().order_by(
        "tipo",
        "nombre"
    )

    return render(
        request,
        "reels/mis_plantillas.html",
        {
            "plantillas": plantillas,
        },
    )


# ============================================================
# CREAR PLANTILLA PERSONALIZADA
# ============================================================

@require_http_methods(["GET", "POST"])
def crear_plantilla(request):

    formulario = PlantillaForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and formulario.is_valid():

        formulario.save()

        messages.success(
            request,
            "Plantilla creada correctamente."
        )

        return redirect("mis_plantillas")

    return render(
        request,
        "reels/formulario_plantilla.html",
        {
            "formulario": formulario,
            "titulo": "Crear plantilla",
        },
    )


# ============================================================
# EDITAR PLANTILLA PERSONALIZADA
# ============================================================

@require_http_methods(["GET", "POST"])
def editar_plantilla(request, plantilla_id):

    plantilla = get_object_or_404(
        Plantilla,
        pk=plantilla_id,
        tipo="personalizada",
    )

    formulario = PlantillaForm(
        request.POST or None,
        request.FILES or None,
        instance=plantilla,
    )

    if request.method == "POST" and formulario.is_valid():

        formulario.save()

        messages.success(
            request,
            "Plantilla actualizada correctamente."
        )

        return redirect("mis_plantillas")

    return render(
        request,
        "reels/formulario_plantilla.html",
        {
            "formulario": formulario,
            "titulo": "Editar plantilla",
            "plantilla": plantilla,
        },
    )


# ============================================================
# ELIMINAR PLANTILLA PERSONALIZADA
# ============================================================

@require_http_methods(["POST"])
def eliminar_plantilla(request, plantilla_id):

    plantilla = get_object_or_404(
        Plantilla,
        pk=plantilla_id,
        tipo="personalizada",
    )

    plantilla.delete()

    messages.success(
        request,
        "Plantilla eliminada correctamente."
    )

    return redirect("mis_plantillas")
