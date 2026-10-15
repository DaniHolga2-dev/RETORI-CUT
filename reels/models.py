
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ============================================================
# PLANTILLAS DE EDICIÓN
# ============================================================

class Plantilla(models.Model):

    TIPOS = [
        ("oficial", "Oficial"),
        ("personalizada", "Personalizada"),
    ]

    TIPOGRAFIAS = [
        ("Montserrat", "Montserrat"),
        ("Arial", "Arial"),
        ("Retorika", "Retorika"),
    ]

    POSICIONES = [
        ("centro", "Centro"),
        ("inferior", "Inferior"),
        ("superior", "Superior"),
    ]

    ANIMACIONES = [
        ("palabra", "Por palabra"),
        ("bloque", "Por bloque"),
        ("ninguna", "Sin animación"),
    ]

    INTENSIDADES = [
        ("limpio", "Limpio"),
        ("dinamico", "Dinámico"),
        ("impacto", "Impacto"),
    ]

    # ========================================================
    # INFORMACIÓN GENERAL
    # ========================================================

    nombre = models.CharField(
        max_length=100
    )

    descripcion = models.TextField(
        blank=True
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        default="personalizada"
    )

    activa = models.BooleanField(
        default=True
    )

    # ========================================================
    # IDENTIDAD VISUAL
    # ========================================================

    logo = models.ImageField(
        upload_to="plantillas/logos/",
        null=True,
        blank=True
    )

    color_azul = models.CharField(
        max_length=7,
        default="#156fe7"
    )

    color_fucsia = models.CharField(
        max_length=7,
        default="#ff3a72"
    )

    color_verde = models.CharField(
        max_length=7,
        default="#03d26e"
    )

    color_blanco = models.CharField(
        max_length=7,
        default="#ffffff"
    )

    # ========================================================
    # TIPOGRAFÍA
    # ========================================================

    tipografia = models.CharField(
        max_length=50,
        choices=TIPOGRAFIAS,
        default="Montserrat"
    )

    archivo_tipografia = models.FileField(
        upload_to="plantillas/fuentes/",
        null=True,
        blank=True
    )

    # ========================================================
    # SUBTÍTULOS
    # ========================================================

    subtitulos_activos = models.BooleanField(
        default=True
    )

    tamano_subtitulos = models.PositiveIntegerField(
        default=12,
        validators=[
            MinValueValidator(8),
            MaxValueValidator(72),
        ]
    )

    posicion_subtitulos = models.CharField(
        max_length=20,
        choices=POSICIONES,
        default="centro"
    )

    margen_vertical = models.PositiveIntegerField(
        default=65
    )

    margen_horizontal = models.PositiveIntegerField(
        default=30
    )

    interlineado = models.PositiveIntegerField(
        default=5
    )

    # ========================================================
    # ANIMACIONES
    # ========================================================

    animacion_subtitulos = models.CharField(
        max_length=20,
        choices=ANIMACIONES,
        default="palabra"
    )

    duracion_animacion = models.FloatField(
        default=0.2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(3),
        ]
    )

    # ========================================================
    # PALABRAS DESTACADAS
    # ========================================================

    destacar_palabras = models.BooleanField(
        default=True
    )

    color_destacado = models.CharField(
        max_length=7,
        default="#156fe7"
    )

    # ========================================================
    # EFECTOS
    # ========================================================

    efectos_activos = models.BooleanField(
        default=True
    )

    intensidad_efectos = models.CharField(
        max_length=20,
        choices=INTENSIDADES,
        default="dinamico"
    )

    # ========================================================
    # FECHAS
    # ========================================================

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_modificacion = models.DateTimeField(
        auto_now=True
    )

    # ========================================================
    # REPRESENTACIÓN
    # ========================================================

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Plantilla"
        verbose_name_plural = "Plantillas"
        ordering = ["nombre"]


# ============================================================
# MODELO REEL
# ============================================================

class Reel(models.Model):

    # ========================================================
    # ESTADOS DEL REEL
    # ========================================================

    ESTADO_SUBIDO = "subido"
    ESTADO_ANALIZANDO = "analizando"
    ESTADO_TRANSCRIBIENDO = "transcribiendo"
    ESTADO_EDITANDO = "editando"
    ESTADO_LISTO = "listo"
    ESTADO_ERROR = "error"

    ESTADOS = [
        (ESTADO_SUBIDO, "Vídeo subido"),
        (ESTADO_ANALIZANDO, "Analizando vídeo"),
        (ESTADO_TRANSCRIBIENDO, "Generando subtítulos"),
        (ESTADO_EDITANDO, "Aplicando estilo Retorika"),
        (ESTADO_LISTO, "Vídeo listo"),
        (ESTADO_ERROR, "Error"),
    ]

    # ========================================================
    # INFORMACIÓN DEL PROYECTO
    # ========================================================

    nombre = models.CharField(
        max_length=255
    )

    archivo_original = models.FileField(
        upload_to="reels/originales/"
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_modificacion = models.DateTimeField(
        auto_now=True
    )

    # ========================================================
    # PLANTILLA SELECCIONADA
    # ========================================================

    plantilla = models.ForeignKey(
        Plantilla,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reels"
    )

    # ========================================================
    # INFORMACIÓN DEL VÍDEO
    # ========================================================

    duracion = models.FloatField(
        null=True,
        blank=True
    )

    formato = models.CharField(
        max_length=20,
        blank=True
    )

    peso = models.BigIntegerField(
        null=True,
        blank=True
    )

    ancho = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    alto = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # ========================================================
    # PROCESAMIENTO
    # ========================================================

    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default=ESTADO_SUBIDO
    )

    progreso = models.PositiveIntegerField(
        default=0
    )

    mensaje_procesamiento = models.CharField(
        max_length=255,
        blank=True
    )

    # ========================================================
    # TRANSCRIPCIÓN Y SUBTÍTULOS
    # ========================================================

    transcripcion = models.TextField(
        blank=True
    )

    archivo_subtitulos = models.FileField(
        upload_to="reels/subtitulos/",
        null=True,
        blank=True
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    archivo_editado = models.FileField(
        upload_to="reels/exportados/",
        null=True,
        blank=True
    )

    miniatura = models.ImageField(
        upload_to="reels/miniaturas/",
        null=True,
        blank=True
    )

    # ========================================================
    # CONFIGURACIÓN EXISTENTE
    # ========================================================

    subtitulos_activos = models.BooleanField(
        default=True
    )

    efectos_activos = models.BooleanField(
        default=True
    )

    intensidad_efectos = models.CharField(
        max_length=20,
        default="dinamico"
    )

    # ========================================================
    # REPRESENTACIÓN
    # ========================================================

    def __str__(self):
        return self.nombre


# ============================================================
# CONFIGURACIÓN ANTERIOR
# CONSERVADA TEMPORALMENTE PARA NO PERDER DATOS
# ============================================================

class ConfiguracionMarca(models.Model):

    nombre = models.CharField(
        max_length=100,
        default="Retorika"
    )

    logo = models.ImageField(
        upload_to="marca/logos/",
        null=True,
        blank=True
    )

    color_azul = models.CharField(
        max_length=7,
        default="#156fe7"
    )

    color_fucsia = models.CharField(
        max_length=7,
        default="#ff3a72"
    )

    color_verde = models.CharField(
        max_length=7,
        default="#03d26e"
    )

    color_blanco = models.CharField(
        max_length=7,
        default="#ffffff"
    )

    TIPOGRAFIAS = [
        ("Montserrat", "Montserrat"),
        ("Arial", "Arial"),
        ("Retorika", "Retorika"),
    ]

    tipografia = models.CharField(
        max_length=50,
        choices=TIPOGRAFIAS,
        default="Montserrat"
    )

    archivo_tipografia = models.FileField(
        upload_to="marca/fuentes/",
        null=True,
        blank=True
    )

    tamano_subtitulos = models.PositiveIntegerField(
        default=12,
        validators=[
            MinValueValidator(8),
            MaxValueValidator(72),
        ]
    )

    POSICIONES = [
        ("centro", "Centro"),
        ("inferior", "Inferior"),
        ("superior", "Superior"),
    ]

    posicion_subtitulos = models.CharField(
        max_length=20,
        choices=POSICIONES,
        default="centro"
    )

    margen_vertical = models.PositiveIntegerField(
        default=65
    )

    margen_horizontal = models.PositiveIntegerField(
        default=30
    )

    interlineado = models.PositiveIntegerField(
        default=5
    )

    ANIMACIONES = [
        ("palabra", "Por palabra"),
        ("bloque", "Por bloque"),
        ("ninguna", "Sin animación"),
    ]

    animacion_subtitulos = models.CharField(
        max_length=20,
        choices=ANIMACIONES,
        default="palabra"
    )

    duracion_animacion = models.FloatField(
        default=0.2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(3),
        ]
    )

    destacar_palabras = models.BooleanField(
        default=True
    )

    color_destacado = models.CharField(
        max_length=7,
        default="#156fe7"
    )

    INTENSIDADES = [
        ("limpio", "Limpio"),
        ("dinamico", "Dinámico"),
        ("impacto", "Impacto"),
    ]

    intensidad_efectos = models.CharField(
        max_length=20,
        choices=INTENSIDADES,
        default="dinamico"
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_modificacion = models.DateTimeField(
        auto_now=True
    )

    @classmethod
    def obtener_configuracion(cls):

        configuracion, creada = cls.objects.get_or_create(
            pk=1
        )

        return configuracion

    def __str__(self):
        return f"Configuración de marca - {self.nombre}"

    class Meta:
        verbose_name = "Configuración de marca"
        verbose_name_plural = "Configuraciones de marca"
