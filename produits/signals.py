from django.db.models.signals import post_delete,post_migrate,post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Produit

@receiver([post_delete,post_migrate,post_save],sender=Produit)
def invalider_cache_produit (sender,instance,**kwargs):
    try:
        cache.delete_pattern('produit_list_*')
        print("cache produit invalidé")

    except:
        keys_to_delete = []
        current_version = cache.get('produits_cache_version', 1)
        cache.set('produits_cache_version', current_version + 1, None)