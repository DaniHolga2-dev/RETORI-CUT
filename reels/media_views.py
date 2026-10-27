
import mimetypes
import re

from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .models import Reel


# ============================================================
# TIPOS DE ARCHIVO PERMITIDOS
# ============================================================

CAMPOS_MULTIMEDIA = (
    "archivo_original",
    "archivo_editado",
    "miniatura",
    "archivo_subtitulos",
)

TIPOS_PROTEGIDOS = {
    "video": "archivo_editado",
    "miniatura": "miniatura",
    "subtitulos": "archivo_subtitulos",
}


# ============================================================
# COMPROBAR USUARIO
# ============================================================

def comprobar_usuario(request):

    if not request.user.is_authenticated:
        return False

    return True


# ============================================================
# ENCONTRAR ARCHIVO DEL USUARIO
# ============================================================

def buscar_archivo_usuario(request, nombre_archivo):

    if not comprobar_usuario(request):
        raise Http404("Archivo no encontrado.")

    reels = Reel.objects.filter(
        usuario=request.user
    )

    for campo in CAMPOS_MULTIMEDIA:

        filtros = {
            campo: nombre_archivo,
        }

        reel = reels.filter(**filtros).first()

        if reel is not None:

            archivo = getattr(reel, campo)

            if archivo and archivo.name == nombre_archivo:
                return archivo

    raise Http404("Archivo no encontrado.")


# ============================================================
# RESPUESTA SEGURA DEL ARCHIVO
# ============================================================

def entregar_archivo(request, archivo):

    try:
        archivo_abierto = archivo.open("rb")
        tamano = archivo.size

    except (OSError, ValueError):
        raise Http404("Archivo no disponible.")

    tipo_contenido, _ = mimetypes.guess_type(
        archivo.name
    )

    if not tipo_contenido:
        tipo_contenido = "application/octet-stream"

    rango = request.headers.get("Range", "")

    # ========================================================
    # DESCARGA O REPRODUCCIÓN NORMAL
    # ========================================================

    if not rango:

        respuesta = FileResponse(
            archivo_abierto,
            as_attachment=False,
            content_type=tipo_contenido,
        )

        respuesta["Accept-Ranges"] = "bytes"
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"

        return respuesta

    # ========================================================
    # REPRODUCCIÓN CON SOPORTE PARA RANGOS
    # ========================================================
    #
    # Los navegadores móviles pueden solicitar fragmentos
    # del MP4 para reproducirlo o avanzar por el vídeo.
    # ========================================================

    coincidencia = re.fullmatch(
        r"bytes=(\d*)-(\d*)",
        rango.strip(),
    )

    if not coincidencia or tamano <= 0:

        archivo_abierto.close()

        respuesta = HttpResponse(status=416)

        respuesta["Content-Range"] = (
            f"bytes */{tamano}"
        )

        return respuesta

    inicio_texto, fin_texto = coincidencia.groups()

    if not inicio_texto and not fin_texto:

        archivo_abierto.close()

        respuesta = HttpResponse(status=416)

        respuesta["Content-Range"] = (
            f"bytes */{tamano}"
        )

        return respuesta

    if inicio_texto:

        inicio = int(inicio_texto)

        fin = (
            int(fin_texto)
            if fin_texto
            else tamano - 1
        )

        fin = min(fin, tamano - 1)

    else:

        cantidad = int(fin_texto)

        inicio = max(0, tamano - cantidad)
        fin = tamano - 1

    if inicio >= tamano or inicio > fin:

        archivo_abierto.close()

        respuesta = HttpResponse(status=416)

        respuesta["Content-Range"] = (
            f"bytes */{tamano}"
        )

        return respuesta

    longitud = fin - inicio + 1

    # ========================================================
    # ENVIAR ÚNICAMENTE EL FRAGMENTO SOLICITADO
    # ========================================================

    def generar_fragmentos():

        try:

            archivo_abierto.seek(inicio)

            restante = longitud

            while restante > 0:

                fragmento = archivo_abierto.read(
                    min(1024 * 1024, restante)
                )

                if not fragmento:
                    break

                restante -= len(fragmento)

                yield fragmento

        finally:

            archivo_abierto.close()

    respuesta = StreamingHttpResponse(
        generar_fragmentos(),
        status=206,
        content_type=tipo_contenido,
    )

    respuesta["Content-Range"] = (
        f"bytes {inicio}-{fin}/{tamano}"
    )

    respuesta["Content-Length"] = str(longitud)
    respuesta["Accept-Ranges"] = "bytes"
    respuesta["Cache-Control"] = "private, no-store"
    respuesta["X-Content-Type-Options"] = "nosniff"

    return respuesta


# ============================================================
# SERVIR ARCHIVOS MEDIANTE SU RUTA MEDIA
# ============================================================
#
# Conserva direcciones como:
#
# /media/reels/exportados/reel_28_exportado.mp4
#
# Pero comprueba la propiedad del archivo.
# ============================================================

@require_GET
def servir_archivo_reel(request, relative_path):

    nombre_archivo = "reels/" + relative_path

    archivo = buscar_archivo_usuario(
        request,
        nombre_archivo,
    )

    return entregar_archivo(
        request,
        archivo,
    )


# ============================================================
# OBTENER ARCHIVO DE UN REEL POR SU IDENTIFICADOR
# ============================================================

def obtener_archivo_reel(request, reel_id, tipo):

    if not comprobar_usuario(request):
        raise Http404("Reel no encontrado.")

    reel = get_object_or_404(
        Reel,
        id=reel_id,
        usuario=request.user,
    )

    campo = TIPOS_PROTEGIDOS.get(tipo)

    if not campo:
        raise Http404("Tipo de archivo no válido.")

    archivo = getattr(reel, campo)

    if not archivo:
        raise Http404("Archivo no disponible.")

    return entregar_archivo(
        request,
        archivo,
    )


# ============================================================
# VÍDEO EXPORTADO PROTEGIDO
# ============================================================

@require_GET
def video_reel_protegido(request, reel_id):

    return obtener_archivo_reel(
        request,
        reel_id,
        "video",
    )


# ============================================================
# MINIATURA PROTEGIDA
# ============================================================

@require_GET
def miniatura_reel_protegida(request, reel_id):

    return obtener_archivo_reel(
        request,
        reel_id,
        "miniatura",
    )


# ============================================================
# SUBTÍTULOS PROTEGIDOS
# ============================================================

@require_GET
def subtitulos_reel_protegidos(request, reel_id):

    return obtener_archivo_reel(
        request,
        reel_id,
        "subtitulos",
    )
