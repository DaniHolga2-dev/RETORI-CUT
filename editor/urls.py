
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from reels import media_views


# ============================================================
# RUTAS PRINCIPALES
# ============================================================

urlpatterns = [

    # ========================================================
    # ADMINISTRACIÓN
    # ========================================================

    path(
        "admin/",
        admin.site.urls,
    ),

    # ========================================================
    # ARCHIVOS DE REELS PROTEGIDOS
    # ========================================================
    #
    # Esta ruta funciona con DEBUG=True y DEBUG=False.
    #
    # Comprueba que el archivo pertenece al usuario
    # que ha iniciado sesión.
    # ========================================================

    path(
        "media/reels/<path:relative_path>",
        media_views.servir_archivo_reel,
        name="servir_archivo_reel",
    ),

    # ========================================================
    # APLICACIÓN RETORI-CUT
    # ========================================================

    path(
        "",
        include("reels.urls"),
    ),

]


# ============================================================
# ARCHIVOS MULTIMEDIA EN DESARROLLO
# ============================================================
#
# Los archivos de /media/reels/ se sirven mediante
# la ruta protegida anterior.
#
# Las demás rutas multimedia pueden seguir funcionando
# en desarrollo, por ejemplo archivos de marca.
#
# Con DEBUG=False no se publica MEDIA_ROOT completo.
# ============================================================

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
