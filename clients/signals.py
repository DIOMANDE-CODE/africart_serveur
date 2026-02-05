from django.db.models.signals import post_delete,post_migrate,post_save
from .models import Client
from django.core.cache import cache
from django.dispatch import receiver

@receiver([post_delete,post_migrate,post_save],sender=Client)
def invalider_cache_client(sender,instance,**kwargs):
    try:
        cache.delete_pattern('cache_client_list_v_*')
    except:
        current_version = cache.get("clients_cache_version",1)
        cache.set("clients_cache_version",current_version + 1,None)