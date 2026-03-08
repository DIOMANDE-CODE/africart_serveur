from django.contrib import admin
from .models import chatMessage

# Register your models here.
@admin.register(chatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display=('id','identifiant_chatbot','utilisateur','role','message','timestamp',)
    search_fields=('utilisateur__email_utilisateur','utilisateur__nom_utilisateur')
    ordering = ['-timestamp']