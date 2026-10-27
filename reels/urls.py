
from django.urls import path

from . import views
from . import configuracion_views
from . import media_views


urlpatterns = [

    # ============================================================
    # NUEVO REEL
    # ============================================================

    path(
        "",
        views.nuevo_reel,
        name="nuevo_reel",
    ),

    # ============================================================
    # CUENTAS DE USUARIO
    # ============================================================

    path(
        "registro/",
        views.registro,
        name="registro",
    ),

    path(
        "iniciar-sesion/",
        views.iniciar_sesion,
        name="iniciar_sesion",
    ),

    path(
        "cerrar-sesion/",
        views.cerrar_sesion,
        name="cerrar_sesion",
    ),

    # ============================================================
    # MI PERFIL
    # ============================================================

    path(
        "mi-perfil/",
        views.mi_perfil,
        name="mi_perfil",
    ),

    # ============================================================
    # MIS VÍDEOS
    # ============================================================

    path(
        "mis-videos/",
        views.mis_videos,
        name="mis_videos",
    ),

    # ============================================================
    # ELIMINAR VÍDEO
    # ============================================================

    path(
        "mis-videos/<int:reel_id>/eliminar/",
        views.eliminar_reel,
        name="eliminar_reel",
    ),

    # ============================================================
    # PANTALLA DE PROCESAMIENTO
    # ============================================================

    path(
        "reel/<int:reel_id>/procesando/",
        views.procesando_reel,
        name="procesando_reel",
    ),

    # ============================================================
    # CONSULTAR PROGRESO DEL REEL
    # ============================================================

    path(
        "reel/<int:reel_id>/estado/",
        views.estado_reel,
        name="estado_reel",
    ),

    # ============================================================
    # ARCHIVOS MULTIMEDIA PROTEGIDOS
    # ============================================================

    path(
        "reel/<int:reel_id>/video/",
        media_views.video_reel_protegido,
        name="video_reel_protegido",
    ),

    path(
        "reel/<int:reel_id>/miniatura/",
        media_views.miniatura_reel_protegida,
        name="miniatura_reel_protegida",
    ),

    path(
        "reel/<int:reel_id>/subtitulos/",
        media_views.subtitulos_reel_protegidos,
        name="subtitulos_reel_protegidos",
    ),

    # ============================================================
    # PLANTILLAS
    # ============================================================

    path(
        "plantillas/",
        views.mis_plantillas,
        name="mis_plantillas",
    ),

    path(
        "plantillas/crear/",
        views.crear_plantilla,
        name="crear_plantilla",
    ),

    path(
        "plantillas/<int:plantilla_id>/editar/",
        views.editar_plantilla,
        name="editar_plantilla",
    ),

    path(
        "plantillas/<int:plantilla_id>/eliminar/",
        views.eliminar_plantilla,
        name="eliminar_plantilla",
    ),

    # ============================================================
    # CONFIGURACIÓN GENERAL
    # ============================================================

    path(
        "configuracion/",
        configuracion_views.configuracion,
        name="configuracion",
    ),

    # ============================================================
    # CONFIGURACIÓN DE MARCA
    # ============================================================

    path(
        "configuracion-marca/",
        views.configuracion_marca,
        name="configuracion_marca",
    ),

]
