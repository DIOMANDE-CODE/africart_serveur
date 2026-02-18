from django.core.management.base import BaseCommand
from produits.models import Produit

class Command(BaseCommand):
    help = "Génère automatiquement les thumbnails_2 et thumbnails_3 pour les produits si elles sont vides"

    def handle(self, *args, **kwargs):
        produits = Produit.objects.all()
        for produit in produits:
            updated = False

            # Thumbnail principal
            if produit.image_produit and not produit.thumbnail:
                produit.thumbnail = produit.compress_and_upload(
                    produit.image_produit.url,
                    f"thumb_{produit.identifiant_produit}"
                )
                updated = True

            # Thumbnail 2
            if produit.image_produit_2 and not produit.thumbnail_2:
                produit.thumbnail_2 = produit.compress_and_upload(
                    produit.image_produit_2.url,
                    f"thumb2_{produit.identifiant_produit}"
                )
                updated = True

            # Thumbnail 3
            if produit.image_produit_3 and not produit.thumbnail_3:
                produit.thumbnail_3 = produit.compress_and_upload(
                    produit.image_produit_3.url,
                    f"thumb3_{produit.identifiant_produit}"
                )
                updated = True

            if updated:
                produit.save(update_fields=["thumbnail", "thumbnail_2", "thumbnail_3"])
                self.stdout.write(self.style.SUCCESS(
                    f"Thumbnails générés pour {produit.nom_produit}"
                ))
