import logging
import subprocess
import threading
from pathlib import Path

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.files import File
from django.db import close_old_connections
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    ReelUploadForm,
    ConfiguracionMarcaForm,
    PlantillaForm,
    RegistroUsuarioForm,
)

from .models import (
    Reel,
    ConfiguracionMarca,
    Plantilla,
    PreferenciasUsuario,
)

from .transcription_utils import (
    transcribir_video,
    guardar_subtitulos_srt,
    guardar_subtitulos_ass,
    VozNoDetectadaError,
    aplicar_formato_subtitulos,
)

from .video_utils import (
    analizar_video,
    video_tiene_audio,
    extraer_primer_fotograma,
    incrustar_subtitulos_video,
    obtener_filtros_exportacion,
    obtener_argumentos_codificacion,
)


logger = logging.getLogger(__name__)


# ============================================================
# AUTENTICACIÓN MEDIANTE CORREO ELECTRÓNICO
# ============================================================

class AutenticacionCorreoForm(AuthenticationForm):

    """
    Permite iniciar sesión utilizando el correo electrónico.
    """

    def clean(self):

        correo = self.cleaned_data.get(
            "username", ""
        ).strip()

        if correo:

            modelo_usuario = get_user_model()

            coincidencias = modelo_usuario._default_manager.filter(
                email__iexact=correo
            )

            if coincidencias.count() == 1:

                usuario = coincidencias.first()

                self.cleaned_data["username"] = (
                    usuario.get_username()
                )

        return super().clean()


# ============================================================
# REDIRECCIÓN SEGURA DESPUÉS DE INICIAR SESIÓN
# ============================================================

def redireccion_segura(request, destino="nuevo_reel"):

    siguiente = (
        request.POST.get("next")
        or request.GET.get("next")
    )

    if siguiente and url_has_allowed_host_and_scheme(
        url=siguiente,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):

        return redirect(siguiente)

    return redirect(destino)


# ============================================================
# REGISTRO DE USUARIOS
# ============================================================

@require_http_methods(["GET", "POST"])
def registro(request):

    if request.user.is_authenticated:
        return redirect("nuevo_reel")

    if request.method == "POST":

        formulario = RegistroUsuarioForm(
            request.POST
        )

        if formulario.is_valid():

            usuario = formulario.save()

            login(
                request,
                usuario,
                backend="django.contrib.auth.backends.ModelBackend",
            )

            messages.success(
                request,
                "Tu cuenta se ha creado correctamente.",
            )

            return redirect("nuevo_reel")

    else:

        formulario = RegistroUsuarioForm()

    return render(
        request,
        "reels/registro.html",
        {
            "formulario": formulario,
        },
    )


# ============================================================
# INICIAR SESIÓN
# ============================================================

@require_http_methods(["GET", "POST"])
def iniciar_sesion(request):

    if request.user.is_authenticated:
        return redirect("nuevo_reel")

    if request.method == "POST":

        formulario = AutenticacionCorreoForm(
            request,
            data=request.POST,
        )

        if formulario.is_valid():

            usuario = formulario.get_user()

            login(request, usuario)

            messages.success(
                request,
                "Has iniciado sesión correctamente.",
            )

            return redireccion_segura(request)

    else:

        formulario = AutenticacionCorreoForm(
            request
        )

    return render(
        request,
        "reels/iniciar_sesion.html",
        {
            "formulario": formulario,
            "next": request.POST.get(
                "next",
                request.GET.get("next", ""),
            ),
        },
    )


# ============================================================
# CERRAR SESIÓN
# ============================================================

@login_required(login_url="iniciar_sesion")
@require_POST
def cerrar_sesion(request):

    logout(request)

    messages.success(
        request,
        "Has cerrado sesión correctamente.",
    )

    return redirect("iniciar_sesion")


# ============================================================
# FORMULARIO DE MI PERFIL
# ============================================================

class MiPerfilForm(forms.Form):

    nombre = forms.CharField(
        label="Nombre",
        max_length=150,
        required=False,
    )

    apellidos = forms.CharField(
        label="Apellidos",
        max_length=150,
        required=False,
    )

    email = forms.EmailField(
        label="Correo electrónico",
        max_length=254,
    )

    def __init__(
        self,
        *args,
        usuario=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.usuario = usuario

        if usuario is not None and not self.is_bound:

            self.initial.update({
                "nombre": usuario.first_name,
                "apellidos": usuario.last_name,
                "email": usuario.email,
            })

    def clean_email(self):

        email = self.cleaned_data[
            "email"
        ].strip()

        if self.usuario is not None:

            modelo = get_user_model()

            if modelo._default_manager.filter(
                email__iexact=email
            ).exclude(
                pk=self.usuario.pk
            ).exists():

                raise forms.ValidationError(
                    "Este correo ya está registrado."
                )

        return email

    def guardar(self):

        usuario = self.usuario

        usuario.first_name = (
            self.cleaned_data["nombre"].strip()
        )

        usuario.last_name = (
            self.cleaned_data["apellidos"].strip()
        )

        usuario.email = (
            self.cleaned_data["email"]
        )

        usuario.save(
            update_fields=[
                "first_name",
                "last_name",
                "email",
            ]
        )

        return usuario


# ============================================================
# MI PERFIL
# ============================================================

@login_required(login_url="iniciar_sesion")
@require_http_methods(["GET", "POST"])
def mi_perfil(request):

    if request.method == "POST":

        formulario = MiPerfilForm(
            request.POST,
            usuario=request.user,
        )

        if formulario.is_valid():

            formulario.guardar()

            messages.success(
                request,
                "Tu perfil se ha actualizado correctamente.",
            )

            return redirect("mi_perfil")

    else:

        formulario = MiPerfilForm(
            usuario=request.user
        )

    return render(
        request,
        "reels/mi_perfil.html",
        {
            "formulario": formulario,
            "usuario": request.user,
        },
    )


# ============================================================
# MIS VÍDEOS
# ============================================================

@login_required(login_url="iniciar_sesion")
@require_http_methods(["GET"])
def mis_videos(request):

    reels = list(
        Reel.objects
        .filter(usuario=request.user)
        .select_related("plantilla")
        .order_by("-fecha_creacion")
    )

    for reel in reels:
        # El aviso solo aparece si Whisper registró ausencia de voz.
        # No se presupone que todos los errores antiguos sean por este motivo.
        reel.sin_voz = (
            reel.estado == Reel.ESTADO_ERROR
            and "voz reconocible" in (reel.mensaje_procesamiento or "").lower()
        )

    return render(
        request,
        "reels/mis_videos.html",
        {
            "reels": reels,
        },
    )


# ============================================================
# ELIMINAR REEL PROPIO Y SUS ARCHIVOS
# ============================================================

@login_required(login_url="iniciar_sesion")
@require_POST
def eliminar_reel(request, reel_id):

    reel = get_object_or_404(
        Reel,
        pk=reel_id,
        usuario=request.user,
    )

    # No eliminar mientras se está procesando.

    if reel.estado not in (
        Reel.ESTADO_LISTO,
        Reel.ESTADO_ERROR,
    ):

        messages.error(
            request,
            "Espera a que termine el procesamiento "
            "antes de eliminar el vídeo.",
        )

        return redirect("mis_videos")

    archivos = []

    for campo in (
        "archivo_original",
        "archivo_editado",
        "miniatura",
        "archivo_subtitulos",
    ):

        archivo = getattr(
            reel,
            campo,
            None,
        )

        if archivo and archivo.name:

            archivos.append((
                archivo.storage,
                archivo.name,
            ))

    nombre = reel.nombre

    reel.delete()

    for almacenamiento, ruta in archivos:

        try:

            almacenamiento.delete(ruta)

        except Exception:

            logger.exception(
                "No se pudo eliminar el archivo %s "
                "del reel %s",
                ruta,
                reel_id,
            )

    messages.success(
        request,
        f"El vídeo «{nombre}» se ha eliminado.",
    )

    return redirect("mis_videos")


# ============================================================
# ACTUALIZAR ESTADO DEL PROCESAMIENTO
# ============================================================

def actualizar_progreso(
    reel,
    estado,
    progreso,
    mensaje,
):

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
# OBTENER PLANTILLA OFICIAL RETORIKA
# ============================================================

def obtener_plantilla_oficial():

    plantilla, _ = Plantilla.objects.get_or_create(
        tipo="oficial",
        defaults={
            "nombre": "Retorika",
            "descripcion": (
                "Plantilla corporativa de Retorika."
            ),
            "activa": True,
        },
    )

    return plantilla


# ============================================================
# COMPROBAR ARCHIVO ASS GENERADO
# ============================================================

def comprobar_archivo_ass(ruta_ass):

    ruta_ass = Path(ruta_ass)

    if not ruta_ass.is_file():

        raise FileNotFoundError(
            f"No se ha generado el archivo ASS: {ruta_ass}"
        )

    if ruta_ass.stat().st_size == 0:

        raise ValueError(
            "El archivo ASS generado está vacío."
        )

    contenido = ruta_ass.read_text(
        encoding="utf-8-sig"
    )

    if "[Events]" not in contenido:

        raise ValueError(
            "El archivo ASS no contiene la sección [Events]."
        )

    lineas_dialogo = [
        linea
        for linea in contenido.splitlines()
        if linea.strip().startswith("Dialogue:")
    ]

    if not lineas_dialogo:

        raise ValueError(
            "El archivo ASS no contiene líneas de subtítulos."
        )

    logger.info(
        "ASS generado: %s | %s líneas de diálogo | %s bytes",
        ruta_ass,
        len(lineas_dialogo),
        ruta_ass.stat().st_size,
    )

    print(
        f"\n[RETORI-CUT] Archivo ASS: {ruta_ass}\n"
        f"[RETORI-CUT] Diálogos encontrados: "
        f"{len(lineas_dialogo)}\n"
    )

    return len(lineas_dialogo)
# ============================================================
# PROCESAR REEL EN SEGUNDO PLANO
# ============================================================

def procesar_reel_segundo_plano(reel_id):

    close_old_connections()

    try:

        reel = Reel.objects.select_related(
            "plantilla",
            "usuario",
        ).get(
            id=reel_id
        )

        # ====================================================
        # RECUPERAR PLANTILLA SELECCIONADA
        # ====================================================

        plantilla = reel.plantilla

        if plantilla is None:

            plantilla = obtener_plantilla_oficial()

            reel.plantilla = plantilla

            reel.save(
                update_fields=["plantilla"]
            )

        # ====================================================
        # RECUPERAR PREFERENCIAS DEL USUARIO
        # ====================================================

        preferencias = None

        if reel.usuario_id is not None:

            preferencias, _ = (
                PreferenciasUsuario.objects.get_or_create(
                    usuario=reel.usuario
                )
            )

            logger.info(
                "Reel %s | Exportación: %sp, %s FPS, "
                "calidad %s",
                reel.id,
                preferencias.resolucion,
                preferencias.fps,
                preferencias.calidad,
            )

        # ====================================================
        # APLICAR CONFIGURACIÓN DE LA PLANTILLA
        # ====================================================

        reel.subtitulos_activos = (
            plantilla.subtitulos_activos
        )

        reel.efectos_activos = (
            plantilla.efectos_activos
        )

        reel.intensidad_efectos = (
            plantilla.intensidad_efectos
        )

        reel.save(
            update_fields=[
                "subtitulos_activos",
                "efectos_activos",
                "intensidad_efectos",
            ]
        )

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
        # DETECTAR VÍDEOS SIN PISTA DE AUDIO
        # ====================================================

        if not video_tiene_audio(ruta_video):

            actualizar_progreso(
                reel,
                Reel.ESTADO_ERROR,
                100,
                "Error: este vídeo no se ha procesado porque no contiene "
                "voz reconocible para generar subtítulos.",
            )

            logger.info(
                "Reel %s subido correctamente, "
                "sin pista de audio.",
                reel.id,
            )

            return

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

        segmentos = aplicar_formato_subtitulos(
            resultado["segmentos"],
            getattr(plantilla, "formato_subtitulos", "mayusculas"),
        )

        if reel.subtitulos_activos:

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

                with open(
                    ruta_srt_temporal,
                    "rb",
                ) as archivo:

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
                "Aplicando plantilla y preparando exportación..."
                if reel.subtitulos_activos
                else
                "Transcripción completada. "
                "Preparando exportación sin subtítulos..."
            ),
        )

        # ====================================================
        # FASE 6: EXPORTAR VÍDEO
        # ====================================================

        nombre_exportado = (
            f"reel_{reel.id}_exportado.mp4"
        )

        ruta_exportacion_temporal = (
            ruta_video.parent
            / nombre_exportado
        )

        ruta_ass_temporal = (
            ruta_video.parent
            / f"reel_{reel.id}_animado.ass"
        )

        try:

            if reel.subtitulos_activos:

                # ============================================
                # GENERAR SUBTÍTULOS ASS ANIMADOS
                # ============================================

                actualizar_progreso(
                    reel,
                    Reel.ESTADO_EDITANDO,
                    75,
                    "Generando subtítulos animados ASS...",
                )

                guardar_subtitulos_ass(
                    segmentos=segmentos,
                    ruta_destino=ruta_ass_temporal,
                    plantilla=plantilla,
                    ancho=reel.ancho or 1080,
                    alto=reel.alto or 1920,
                    palabras_destacadas=reel.palabras_destacadas,
                )

                # ============================================
                # COMPROBAR ARCHIVO ASS
                # ============================================

                comprobar_archivo_ass(
                    ruta_ass_temporal
                )

                # ============================================
                # INCRUSTAR SUBTÍTULOS Y EXPORTAR
                # ============================================

                actualizar_progreso(
                    reel,
                    Reel.ESTADO_EDITANDO,
                    80,
                    "Exportando vídeo con subtítulos ASS...",
                )

                incrustar_subtitulos_video(
                    ruta_video,
                    ruta_ass_temporal,
                    ruta_exportacion_temporal,
                    plantilla=plantilla,
                    preferencias=preferencias,
                )

            else:

                # ============================================
                # EXPORTAR SIN SUBTÍTULOS
                # ============================================

                actualizar_progreso(
                    reel,
                    Reel.ESTADO_EDITANDO,
                    80,
                    "Exportando vídeo sin subtítulos...",
                )

                filtro_video = (
                    obtener_filtros_exportacion(
                        preferencias=preferencias
                    )
                )

                argumentos_codificacion = (
                    obtener_argumentos_codificacion(
                        preferencias=preferencias
                    )
                )

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
                    str(ruta_exportacion_temporal),
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

                    detalle = (
                        error.stderr
                        or "FFmpeg no ha indicado el motivo."
                    )

                    raise RuntimeError(
                        "Error al exportar el vídeo "
                        "sin subtítulos:\n"
                        + detalle
                    ) from error

            # ================================================
            # COMPROBAR VÍDEO EXPORTADO
            # ================================================

            if (
                not ruta_exportacion_temporal.is_file()
                or ruta_exportacion_temporal.stat().st_size == 0
            ):

                raise RuntimeError(
                    "No se ha generado el vídeo exportado."
                )

            # ================================================
            # GUARDAR MP4 EN EL MODELO
            # ================================================

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

            # Mantener el archivo ASS temporal
            # para facilitar el diagnóstico.

            if ruta_ass_temporal.exists():

                logger.info(
                    "Archivo ASS conservado para diagnóstico: %s",
                    ruta_ass_temporal,
                )

            # Eliminar únicamente el MP4 temporal,
            # no el archivo exportado guardado.

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
                "con subtítulos y plantilla aplicada."
                if reel.subtitulos_activos
                else
                "Vídeo exportado correctamente."
            ),
        )

        logger.info(
            "Reel %s: procesamiento y exportación completados.",
            reel.id,
        )

    # ========================================================
    # CONTROL GENERAL DE ERRORES
    # ========================================================

    except VozNoDetectadaError as error:
        logger.info("Reel %s sin voz reconocible: %s", reel_id, error)
        Reel.objects.filter(id=reel_id).update(
            estado=Reel.ESTADO_ERROR,
            progreso=100,
            mensaje_procesamiento=str(error),
        )

    except Reel.DoesNotExist:

        logger.warning(
            "El reel %s ya no existe.",
            reel_id,
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

@login_required(login_url="iniciar_sesion")
def nuevo_reel(request):

    plantilla_oficial = obtener_plantilla_oficial()

    if request.method == "POST":

        formulario = ReelUploadForm(
            request.POST,
            request.FILES,
            usuario=request.user,
        )

        if formulario.is_valid():

            reel = formulario.save(
                commit=False
            )

            reel.usuario = request.user

            if reel.plantilla_id is None:

                reel.plantilla = plantilla_oficial

            reel.estado = Reel.ESTADO_ANALIZANDO
            reel.progreso = 5

            reel.mensaje_procesamiento = (
                "Vídeo recibido. Iniciando análisis..."
            )

            reel.save()

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

        formulario = ReelUploadForm(
            usuario=request.user,
        )

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

@login_required(login_url="iniciar_sesion")
def procesando_reel(request, reel_id):

    reel = get_object_or_404(
        Reel,
        id=reel_id,
        usuario=request.user,
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

@login_required(login_url="iniciar_sesion")
def estado_reel(request, reel_id):

    reel = get_object_or_404(
        Reel,
        id=reel_id,
        usuario=request.user,
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

@login_required(login_url="iniciar_sesion")
@require_http_methods(["GET", "POST"])
def configuracion_marca(request):

    configuracion = (
        ConfiguracionMarca.obtener_configuracion()
    )

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

    else:

        formulario = ConfiguracionMarcaForm(
            instance=configuracion
        )

    return render(
        request,
        "reels/configuracion_marca.html",
        {
            "formulario": formulario,
            "configuracion": configuracion,
        },
    )


# ============================================================
# LISTADO DE PLANTILLAS
# ============================================================

@login_required(login_url="iniciar_sesion")
@require_http_methods(["GET"])
def mis_plantillas(request):

    obtener_plantilla_oficial()

    plantillas = (
        Plantilla.objects.filter(
            tipo="oficial",
        )
        |
        Plantilla.objects.filter(
            tipo="personalizada",
            usuario=request.user,
        )
    )

    plantillas = plantillas.order_by(
        "tipo",
        "nombre",
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

@login_required(login_url="iniciar_sesion")
@require_http_methods(["GET", "POST"])
def crear_plantilla(request):

    formulario = PlantillaForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and formulario.is_valid():

        plantilla = formulario.save(
            commit=False
        )

        plantilla.usuario = request.user
        plantilla.tipo = "personalizada"

        plantilla.save()

        messages.success(
            request,
            "Plantilla creada correctamente.",
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

@login_required(login_url="iniciar_sesion")
@require_http_methods(["GET", "POST"])
def editar_plantilla(request, plantilla_id):

    plantilla = get_object_or_404(
        Plantilla,
        pk=plantilla_id,
        tipo="personalizada",
        usuario=request.user,
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
            "Plantilla actualizada correctamente.",
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

@login_required(login_url="iniciar_sesion")
@require_POST
def eliminar_plantilla(request, plantilla_id):

    plantilla = get_object_or_404(
        Plantilla,
        pk=plantilla_id,
        tipo="personalizada",
        usuario=request.user,
    )

    plantilla.delete()

    messages.success(
        request,
        "Plantilla eliminada correctamente.",
    )

    return redirect("mis_plantillas")


# ============================================================
# CONFIGURACIÓN GENERAL DEL USUARIO
# ============================================================

from .configuracion_views import configuracion