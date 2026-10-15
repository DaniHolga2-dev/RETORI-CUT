
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import Reel, Plantilla, ConfiguracionMarca


# ============================================================
# FORMULARIO DE SUBIDA DE VÍDEOS
# ============================================================

class ReelUploadForm(forms.ModelForm):

    # ========================================================
    # FORMATOS PERMITIDOS
    # ========================================================

    EXTENSIONES_PERMITIDAS = {
        ".mp4",
        ".mov",
        ".m4v",
        ".webm",
        ".mxf",
    }

    TAMANO_MAXIMO = 1024 * 1024 * 1024

    # ========================================================
    # CONFIGURACIÓN
    # ========================================================

    class Meta:

        model = Reel

        fields = [
            "archivo_original",
            "plantilla",
        ]

        widgets = {
            "archivo_original": forms.ClearableFileInput(
                attrs={
                    "accept": (
                        ".mp4,.mov,.m4v,.webm,.mxf,"
                        "video/mp4,"
                        "video/quicktime,"
                        "video/x-m4v,"
                        "video/webm,"
                        "application/mxf"
                    ),
                    "class": "input-video",
                }
            ),

            "plantilla": forms.Select(
                attrs={
                    "class": "rc-select",
                }
            ),
        }

    # ========================================================
    # INICIALIZACIÓN
    # ========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["plantilla"].queryset = (
            Plantilla.objects.filter(
                activa=True
            ).order_by(
                "tipo",
                "nombre"
            )
        )

        self.fields["plantilla"].required = False

        self.fields["plantilla"].empty_label = (
            "Retorika (predeterminada)"
        )

        plantilla_oficial = (
            Plantilla.objects.filter(
                tipo="oficial",
                activa=True
            ).first()
        )

        if plantilla_oficial and not self.is_bound:
            self.fields["plantilla"].initial = (
                plantilla_oficial
            )

    # ========================================================
    # VALIDACIÓN DEL VÍDEO
    # ========================================================

    def clean_archivo_original(self):

        archivo = self.cleaned_data.get(
            "archivo_original"
        )

        if not archivo:
            raise ValidationError(
                "Selecciona un vídeo."
            )

        extension = Path(
            archivo.name
        ).suffix.lower()

        if extension not in self.EXTENSIONES_PERMITIDAS:
            raise ValidationError(
                "Formato no compatible. "
                "Utiliza MP4, MOV, M4V, WEBM o MXF."
            )

        if archivo.size > self.TAMANO_MAXIMO:
            raise ValidationError(
                "El vídeo no puede superar 1 GB."
            )

        return archivo

    # ========================================================
    # SELECCIÓN DE PLANTILLA
    # ========================================================

    def clean_plantilla(self):

        plantilla = self.cleaned_data.get(
            "plantilla"
        )

        if plantilla is None:

            plantilla = (
                Plantilla.objects.filter(
                    tipo="oficial",
                    activa=True
                ).first()
            )

        if plantilla is None:
            raise ValidationError(
                "No hay ninguna plantilla disponible. "
                "Crea primero la plantilla oficial de Retorika."
            )

        return plantilla

    # ========================================================
    # CREACIÓN DEL REEL
    # ========================================================

    def save(self, commit=True):

        reel = super().save(commit=False)

        archivo = self.cleaned_data[
            "archivo_original"
        ]

        reel.nombre = archivo.name
        reel.peso = archivo.size

        reel.formato = (
            Path(archivo.name)
            .suffix
            .replace(".", "")
            .upper()
        )

        if commit:
            reel.save()

        return reel


# ============================================================
# FORMULARIO DE PLANTILLAS PERSONALIZADAS
# ============================================================

class PlantillaForm(forms.ModelForm):

    # ========================================================
    # CONFIGURACIÓN
    # ========================================================

    class Meta:

        model = Plantilla

        fields = [
            "nombre",
            "descripcion",
            "logo",
            "color_azul",
            "color_fucsia",
            "color_verde",
            "color_blanco",
            "tipografia",
            "archivo_tipografia",
            "subtitulos_activos",
            "tamano_subtitulos",
            "posicion_subtitulos",
            "margen_vertical",
            "margen_horizontal",
            "interlineado",
            "animacion_subtitulos",
            "duracion_animacion",
            "destacar_palabras",
            "color_destacado",
            "efectos_activos",
            "intensidad_efectos",
        ]

        widgets = {

            "nombre": forms.TextInput(
                attrs={
                    "class": "rc-input",
                    "placeholder": "Nombre de la plantilla",
                }
            ),

            "descripcion": forms.Textarea(
                attrs={
                    "class": "rc-input",
                    "rows": 3,
                    "placeholder": (
                        "Describe el estilo de esta plantilla"
                    ),
                }
            ),

            "logo": forms.ClearableFileInput(
                attrs={
                    "class": "rc-input-archivo",
                    "accept": ".png,.jpg,.jpeg,.webp",
                }
            ),

            "color_azul": forms.TextInput(
                attrs={"type": "color", "class": "rc-input-color"}
            ),

            "color_fucsia": forms.TextInput(
                attrs={"type": "color", "class": "rc-input-color"}
            ),

            "color_verde": forms.TextInput(
                attrs={"type": "color", "class": "rc-input-color"}
            ),

            "color_blanco": forms.TextInput(
                attrs={"type": "color", "class": "rc-input-color"}
            ),

            "tipografia": forms.Select(
                attrs={"class": "rc-select"}
            ),

            "archivo_tipografia": forms.ClearableFileInput(
                attrs={
                    "class": "rc-input-archivo",
                    "accept": ".ttf,.otf",
                }
            ),

            "subtitulos_activos": forms.CheckboxInput(
                attrs={"class": "rc-checkbox"}
            ),

            "tamano_subtitulos": forms.NumberInput(
                attrs={
                    "class": "rc-input",
                    "min": 8,
                    "max": 72,
                }
            ),

            "posicion_subtitulos": forms.Select(
                attrs={"class": "rc-select"}
            ),

            "margen_vertical": forms.NumberInput(
                attrs={"class": "rc-input", "min": 0}
            ),

            "margen_horizontal": forms.NumberInput(
                attrs={"class": "rc-input", "min": 0}
            ),

            "interlineado": forms.NumberInput(
                attrs={"class": "rc-input", "min": 0}
            ),

            "animacion_subtitulos": forms.Select(
                attrs={"class": "rc-select"}
            ),

            "duracion_animacion": forms.NumberInput(
                attrs={
                    "class": "rc-input",
                    "min": 0,
                    "max": 3,
                    "step": 0.1,
                }
            ),

            "destacar_palabras": forms.CheckboxInput(
                attrs={"class": "rc-checkbox"}
            ),

            "color_destacado": forms.TextInput(
                attrs={"type": "color", "class": "rc-input-color"}
            ),

            "efectos_activos": forms.CheckboxInput(
                attrs={"class": "rc-checkbox"}
            ),

            "intensidad_efectos": forms.Select(
                attrs={"class": "rc-select"}
            ),
        }

    # ========================================================
    # INICIALIZACIÓN
    # ========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if (
            self.instance.pk
            and self.instance.tipo == "oficial"
        ):
            raise ValueError(
                "La plantilla oficial de Retorika "
                "no puede editarse desde este formulario."
            )

    # ========================================================
    # VALIDACIÓN DE COLORES
    # ========================================================

    def clean(self):

        datos = super().clean()

        campos_color = [
            "color_azul",
            "color_fucsia",
            "color_verde",
            "color_blanco",
            "color_destacado",
        ]

        import re

        for campo in campos_color:

            valor = datos.get(campo)

            if valor:

                if not re.fullmatch(
                    r"#[0-9a-fA-F]{6}",
                    valor
                ):
                    self.add_error(
                        campo,
                        "Introduce un color hexadecimal válido."
                    )

                else:
                    datos[campo] = valor.lower()

        return datos

    # ========================================================
    # VALIDACIÓN DEL LOGO
    # ========================================================

    def clean_logo(self):

        archivo = self.cleaned_data.get("logo")

        if not archivo:
            return archivo

        extension = Path(
            archivo.name
        ).suffix.lower()

        if extension not in {
            ".png", ".jpg", ".jpeg", ".webp"
        }:
            raise ValidationError(
                "El logotipo debe ser PNG, JPG o WEBP."
            )

        if archivo.size > 5 * 1024 * 1024:
            raise ValidationError(
                "El logotipo no puede superar 5 MB."
            )

        return archivo

    # ========================================================
    # VALIDACIÓN DE TIPOGRAFÍA
    # ========================================================

    def clean_archivo_tipografia(self):

        archivo = self.cleaned_data.get(
            "archivo_tipografia"
        )

        if not archivo:
            return archivo

        extension = Path(
            archivo.name
        ).suffix.lower()

        if extension not in {".ttf", ".otf"}:
            raise ValidationError(
                "La fuente debe ser TTF u OTF."
            )

        if archivo.size > 10 * 1024 * 1024:
            raise ValidationError(
                "La fuente no puede superar 10 MB."
            )

        return archivo

    # ========================================================
    # GUARDAR PLANTILLA
    # ========================================================

    def save(self, commit=True):

        plantilla = super().save(commit=False)

        plantilla.tipo = "personalizada"

        if commit:
            plantilla.save()

        return plantilla


# ============================================================
# FORMULARIO DE CONFIGURACIÓN ANTERIOR
# CONSERVADO TEMPORALMENTE
# ============================================================

class ConfiguracionMarcaForm(forms.ModelForm):

    class Meta:

        model = ConfiguracionMarca

        fields = [
            "nombre",
            "logo",
            "color_azul",
            "color_fucsia",
            "color_verde",
            "color_blanco",
            "tipografia",
            "archivo_tipografia",
            "tamano_subtitulos",
            "posicion_subtitulos",
            "margen_vertical",
            "margen_horizontal",
            "interlineado",
            "animacion_subtitulos",
            "duracion_animacion",
            "destacar_palabras",
            "color_destacado",
            "intensidad_efectos",
        ]
