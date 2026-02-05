from django.contrib import admin
from .models import Client

# Register your models here.
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display=('id','identifiant_client','nom_client','role','numero_telephone_client','is_active','date_creation','date_modification',)
    search_fields=('nom_client',)
    ordering = ['-date_creation']