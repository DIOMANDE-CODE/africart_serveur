from django.dispatch import receiver
from .models import Vente
from django.db.models.signals import post_delete,post_migrate,post_save
from django.core.cache import cache

@receiver([post_save,post_delete,post_migrate],sender=Vente)
def invalider_cache_vente(sender,instance,**kwargs):
    try:
        cache.delete_pattern('cache_vente_list_v_*')
    except:
        current_version = cache.get('ventes_cache_version', 1)
        cache.set('ventes_cache_version', current_version + 1, None)