
import re
import uuid
from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Reel, Plantilla, ConfiguracionMarca


# ============================================================
# FORMULARIO DE REGISTRO DE USUARIOS
# ============================================================

class RegistroUsuarioForm(UserCreationForm):

    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "rc-input",
                "placeholder": "Introduce tu nombre",
                "autocomplete": "given-name",
            }
        ),
    )

    email = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "rc-input",
                "placeholder": "Introduce tu correo electrónico",
                "autocomplete": "email",
            }
        ),
    )

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "rc-input",
                "placeholder": "Crea una contraseña",
                "autocomplete": "new-password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "rc-input",
                "placeholder": "Repite la contraseña",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = get_user_model()

        fields = [
            "first_name",
            "email",
            "password1",
            "password2",
        ]

    def clean_email(self):

        email = self.cleaned_data.get(
            "email", ""
        ).strip().lower()

        if not email:
            raise ValidationError(
                "Introduce un correo electrónico."
            )

        Usuario = get_user_model()

        if Usuario._default_manager.filter(
            email__iexact=email
        ).exists():

            raise ValidationError(
                "Ya existe una cuenta con este correo electrónico."
            )

        return email

    def save(self, commit=True):

        usuario = super().save(commit=False)

        usuario.first_name = self.cleaned_data["first_name"]
        usuario.email = self.cleaned_data["email"]

        usuario.username = uuid.uuid4().hex

        if commit:
            usuario.save()

        return usuario


# ============================================================
# FORMULARIO DE SUBIDA DE VÍDEOS
# ============================================================

class ReelUploadForm(forms.ModelForm):

    palabras_destacadas = forms.CharField(
        required=False,
        max_length=1000,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "Ej.: Retorika, creatividad, resultados",
            }
        ),
    )

    def clean_palabras_destacadas(self):

        texto = self.cleaned_data.get(
            "palabras_destacadas", ""
        )

        palabras = [
            p.strip()
            for p in texto.split(",")
            if p.strip()
        ]

        if len(palabras) > 40:
            raise forms.ValidationError(
                "Puedes introducir hasta 40 palabras o expresiones."
            )

        return ", ".join(dict.fromkeys(palabras))

    EXTENSIONES_PERMITIDAS = {
        ".mp4",
        ".mov",
        ".m4v",
        ".webm",
        ".mxf",
    }

    TAMANO_MAXIMO = 1024 * 1024 * 1024

    class Meta:

        model = Reel

        fields = [
            "archivo_original",
            "plantilla",
            "palabras_destacadas",
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

    def __init__(self, *args, usuario=None, **kwargs):

        super().__init__(*args, **kwargs)

        filtro = Q(
            tipo="oficial",
            activa=True,
        )

        if (
            usuario is not None
            and usuario.is_authenticated
        ):

            filtro |= Q(
                tipo="personalizada",
                activa=True,
                usuario=usuario,
            )

        self.fields["plantilla"].queryset = (
            Plantilla.objects
            .filter(filtro)
            .distinct()
            .order_by("tipo", "nombre")
        )

        self.fields["plantilla"].required = False

        self.fields["plantilla"].empty_label = (
            "Retorika (predeterminada)"
        )

        plantilla_oficial = (
            Plantilla.objects
            .filter(
                tipo="oficial",
                activa=True,
            )
            .first()
        )

        if plantilla_oficial and not self.is_bound:

            self.fields["plantilla"].initial = (
                plantilla_oficial
            )

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

    def clean_plantilla(self):

        plantilla = self.cleaned_data.get(
            "plantilla"
        )

        if plantilla is None:

            plantilla = (
                Plantilla.objects
                .filter(
                    tipo="oficial",
                    activa=True,
                )
                .first()
            )

        if plantilla is None:

            raise ValidationError(
                "No hay ninguna plantilla disponible. "
                "Crea primero la plantilla oficial de Retorika."
            )

        return plantilla

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

    class Meta:

        model = Plantilla

        fields = [
            "nombre",
            "descripcion",
            "color_azul",
            "color_fucsia",
            "color_verde",
            "color_blanco",
            "tipografia",
            "archivo_tipografia",
            "subtitulos_activos",
            "formato_subtitulos",
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

            "color_azul": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "rc-input-color",
                }
            ),

            "color_fucsia": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "rc-input-color",
                }
            ),

            "color_verde": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "rc-input-color",
                }
            ),

            "color_blanco": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "rc-input-color",
                }
            ),

            "tipografia": forms.Select(
                attrs={
                    "class": "rc-select",
                }
            ),

            "archivo_tipografia": forms.ClearableFileInput(
                attrs={
                    "class": "rc-input-archivo",
                    "accept": ".ttf,.otf",
                }
            ),

            "subtitulos_activos": forms.CheckboxInput(
                attrs={
                    "class": "rc-checkbox",
                }
            ),

            "formato_subtitulos": forms.Select(
                attrs={"class": "rc-select"}
            ),

            "tamano_subtitulos": forms.NumberInput(
                attrs={
                    "class": "rc-input",
                    "min": 8,
                    "max": 72,
                }
            ),

            "posicion_subtitulos": forms.Select(
                attrs={
                    "class": "rc-select",
                }
            ),

            "margen_vertical": forms.NumberInput(
                attrs={
                    "class": "rc-input",
                    "min": 0,
                }
            ),

            "margen_horizontal": forms.NumberInput(
                attrs={
                    "class": "rc-input",
                    "min": 0,
                }
            ),

            "interlineado": forms.NumberInput(
                attrs={
                    "class": "rc-input",
                    "min": 0,
                }
            ),

            "animacion_subtitulos": forms.Select(
                attrs={
                    "class": "rc-select",
                }
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
                attrs={
                    "class": "rc-checkbox",
                }
            ),

            "color_destacado": forms.TextInput(
                attrs={
                    "type": "color",
                    "class": "rc-input-color",
                }
            ),

            "efectos_activos": forms.CheckboxInput(
                attrs={
                    "class": "rc-checkbox",
                }
            ),

            "intensidad_efectos": forms.Select(
                attrs={
                    "class": "rc-select",
                }
            ),
        }

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

    def clean(self):

        datos = super().clean()

        campos_color = [
            "color_azul",
            "color_fucsia",
            "color_verde",
            "color_blanco",
            "color_destacado",
        ]

        for campo in campos_color:

            valor = datos.get(campo)

            if valor:

                if not re.fullmatch(
                    r"#[0-9a-fA-F]{6}",
                    valor,
                ):

                    self.add_error(
                        campo,
                        "Introduce un color hexadecimal válido.",
                    )

                else:

                    datos[campo] = valor.lower()

        return datos

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
