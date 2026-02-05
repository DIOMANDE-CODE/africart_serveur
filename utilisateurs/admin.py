from django.contrib import admin
from .models import Utilisateur

# Register your models here.
@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display=('id','identifiant_utilisateur','email_utilisateur','nom_utilisateur','numero_telephone_utilisateur','photo_profil_utilisateur','thumbnail','role','date_creation','date_modification','is_active',)
    search_fields=('email_utilisateur','nom_utilisateur',)
    ordering = ['nom_utilisateur']