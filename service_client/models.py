from django.db import models
from utilisateurs.models import Utilisateur
import uuid

# Create your models here.

class chatMessage(models.Model):
    identifiant_chatbot = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="chat_message")
    role = models.CharField(max_length=10)  # 'user' ou 'model'
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp'] # Important pour l'ordre chronologique
        indexes = [
            models.Index(fields=['utilisateur', 'timestamp']),
            models.Index(fields=['role', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        

    def __str__(self):
        return f"{self.utilisateur.email_utilisateur} - {self.message[:20]}..."
