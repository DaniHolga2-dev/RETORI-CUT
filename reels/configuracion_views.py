
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import PreferenciasUsuario, Reel


# ============================================================
# FORMULARIO DE PREFERENCIAS
# ============================================================

class PreferenciasForm(forms.ModelForm):

    class Meta:
        model = PreferenciasUsuario

        fields = [
            "resolucion",
            "fps",
            "calidad",
            "tema",
            "ir_a_mis_videos",
            "limpieza_automatica",
            "dias_limpieza",
        ]


# ============================================================
# PÁGINA DE CONFIGURACIÓN
# ============================================================

@login_required(login_url="iniciar_sesion")
@require_http_methods(["GET", "POST"])
def configuracion(request):

    preferencias, _ = PreferenciasUsuario.objects.get_or_create(
        usuario=request.user
    )

    if request.method == "POST":

        formulario = PreferenciasForm(
            request.POST,
            instance=preferencias,
        )

        if formulario.is_valid():

            formulario.save()

            messages.success(
                request,
                "Preferencias guardadas correctamente.",
            )

            return redirect("configuracion")

    else:

        formulario = PreferenciasForm(
            instance=preferencias
        )

    # ========================================================
    # ESTADÍSTICAS DE ALMACENAMIENTO
    # ========================================================

    reels = Reel.objects.filter(
        usuario=request.user
    )

    cantidad = reels.count()

    bytes_originales = (
        reels.aggregate(
            total=Sum("peso")
        )["total"] or 0
    )

    espacio_originales_mb = round(
        bytes_originales / (1024 * 1024),
        1,
    )

    # ========================================================
    # MOSTRAR PÁGINA
    # ========================================================

    return render(
        request,
        "reels/configuracion.html",
        {
            "formulario": formulario,
            "cantidad_videos": cantidad,
            "espacio_originales_mb": espacio_originales_mb,
        },
    )
