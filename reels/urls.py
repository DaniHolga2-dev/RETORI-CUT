
from django.urls import path

from . import views


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
    # PANTALLA DE PROCESAMIENTO
    # ============================================================

    path(
        "reel/<int:reel_id>/procesando/",
        views.procesando_reel,
        name="procesando_reel",
    ),


    # ============================================================
    # CONSULTAR PROGRESO EN TIEMPO REAL
    # ============================================================

    path(
        "reel/<int:reel_id>/estado/",
        views.estado_reel,
        name="estado_reel",
    ),


    # ============================================================
    # PLANTILLAS
    # ============================================================

    path(
        "plantillas/",
        views.mis_plantillas,
        name="mis_plantillas",
    ),


    # ============================================================
    # CREAR PLANTILLA
    # ============================================================

    path(
        "plantillas/crear/",
        views.crear_plantilla,
        name="crear_plantilla",
    ),


    # ============================================================
    # EDITAR PLANTILLA
    # ============================================================

    path(
        "plantillas/<int:plantilla_id>/editar/",
        views.editar_plantilla,
        name="editar_plantilla",
    ),


    # ============================================================
    # ELIMINAR PLANTILLA
    # ============================================================

    path(
        "plantillas/<int:plantilla_id>/eliminar/",
        views.eliminar_plantilla,
        name="eliminar_plantilla",
    ),


    # ============================================================
    # CONFIGURACIÓN DE MARCA (ANTERIOR)
    # ============================================================

    # Se conserva temporalmente para evitar errores mientras
    # terminamos de trasladar la configuración al nuevo
    # sistema de plantillas.

    path(
        "configuracion-marca/",
        views.configuracion_marca,
        name="configuracion_marca",
    ),

]
