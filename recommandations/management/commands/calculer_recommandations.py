import math
from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.utils import timezone

from produits.models import Produit
from commandes.models import DetailCommande
from recommandations.models import Recommandation, VueProduit

TYPES_TOUS = ["best_sellers", "similaire_categorie", "co_achat"]


class Command(BaseCommand):
    help = "Calculer et stocker les recommandations de produits pour tous les types de recommandations"

    def add_arguments(self, parser):
        parser.add_argument("--type", choices=TYPES_TOUS + ["all"], default="all")
        parser.add_argument("--top", type=int, default=10)

    def handle(self, *args, **options):
        t = options["type"]
        top_k = options["top"]
        debut = timezone.now()
        self.stdout.write(f"[{debut}] Calcul ({t}, top={top_k})...")

        if t in ("all", "best_sellers"):
            self._best_sellers(top_k)
        if t in ("all", "similaire_categorie"):
            self._similaires(top_k)
        if t in ("all", "co_achat"):
            self._co_achat(top_k)

        duree = (timezone.now() - debut).total_seconds()
        self.stdout.write(self.style.SUCCESS(f"Terminé en {duree:.2f}s"))

    # ----- best sellers -----

    def _best_sellers(self, top_k):
        # Calcul des meilleures commandes
        self.stdout.write("  → best-sellers...")
        commandes = (
            DetailCommande.objects.values("produit_id")
            .annotate(total=Sum("quantite"))
            .order_by("-total")[:top_k]
        )
        Recommandation.objects.filter(type_recommandation="best_sellers").delete()
        cache = {p.pk: p for p in Produit.objects.all()}
        nouvelles = [
            Recommandation(
                produit_source=None,
                produit_recommande=cache[c["produit_id"]],
                type_recommandation="best_sellers",
                score=c["total"],
            )
            for c in commandes
        ]
        Recommandation.objects.bulk_create(nouvelles)
        self.stdout.write(f"{len(nouvelles)} enregistrés.")

    # ----- similaires par catégorie -----
    def _similaires(self, top_k):
        self.stdout.write("  → similaires par catégorie...")
        commandes_dict = {
            v["produit_id"]: v["total"]
            for v in DetailCommande.objects.values("produit_id").annotate(
                total=Sum("quantite")
            )
        }
        vue_dict = {
            v["produit_id"]: v["nb"]
            for v in VueProduit.objects.values("produit_id").annotate(nb=Count("id"))
        }

        Recommandation.objects.filter(type_recommandation="similar_categorie").delete()
        par_categorie = defaultdict(list)
        for p in Produit.objects.select_related("categorie_produit").all():
            score = commandes_dict.get(p.pk, 0) + vue_dict.get(p.pk, 0)
            par_categorie[p.categorie_produit_id].append((p, score))
        nouvelles = []
        for items in par_categorie.values():
            items.sort(key=lambda x: x[1], reverse=True)
            for i, (p, s) in enumerate(items[:top_k]):
                for j in range(i + 1, min(i + 1 + top_k, len(items))):
                    p2, s2 = items[j]
                    nouvelles.append(
                        Recommandation(
                            produit_source=p,
                            produit_recommande=p2,
                            type_recommandation="similar_categorie",
                            score=math.sqrt(s * s2),
                        )
                    )
        Recommandation.objects.bulk_create(nouvelles, ignore_conflicts=True)
        self.stdout.write(f"{len(nouvelles)} enregistrés.")

    # ─── Co-achat ────────────────
    def _co_achat(self, top_k):
        self.stdout.write("  → co-achat...")
        commandes_dict = defaultdict(list)
        for d in DetailCommande.objects.values("commande_id", "produit_id"):
            commandes_dict[d["commande_id"]].append(d["produit_id"])

        freq_ind = defaultdict(int)
        freq_pair = defaultdict(int)
        for ids in commandes_dict.values():
            uniques = list(set(ids))
            for pid in uniques:
                freq_ind[pid] += 1
            for i, a in enumerate(uniques):
                for b in uniques[i + 1 :]:
                    freq_pair[(a, b)] += 1
                    freq_pair[(b, a)] += 1

        scores_par_produit = defaultdict(list)
        for (a, b), cooc in freq_pair.items():
            score = cooc / math.sqrt(max(freq_ind[a], 1) * max(freq_ind[b], 1))
            scores_par_produit[a].append((b, score))

        Recommandation.objects.filter(type_recommandation="co_achat").delete()
        cache = {p.pk: p for p in Produit.objects.all()}
        nouvelles = []
        for pid, paires in scores_par_produit.items():
            src = cache.get(pid)
            if not src:
                continue
            for rid, score in sorted(paires, key=lambda x: x[1], reverse=True)[:top_k]:
                reco = cache.get(rid)
                if reco:
                    nouvelles.append(
                        Recommandation(
                            produit_source=src,
                            produit_recommande=reco,
                            type_recommandation="co_achat",
                            score=score,
                        )
                    )
        Recommandation.objects.bulk_create(nouvelles, ignore_conflicts=True)
        self.stdout.write(f"{len(nouvelles)} enregistrés.")
