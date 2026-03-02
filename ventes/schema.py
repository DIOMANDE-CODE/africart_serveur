import graphene
from graphene_django import DjangoObjectType

from africart_serveur import schema
from .models import Vente, DetailVente
from rest_framework.response import Response
from rest_framework import status


class DetailVenteType(DjangoObjectType):
    class Meta:
        model = DetailVente
        fields = '__all__'

class VenteType(DjangoObjectType):
    class Meta:
        model = Vente
        interfaces = (graphene.relay.Node,)
        fields = '__all__'

class VenteConnection(graphene.relay.Connection):
    class Meta:
        node = VenteType


# Classe pour requette
class Query(graphene.ObjectType):
    ventes = graphene.relay.ConnectionField(VenteConnection)

    def resolve_ventes(root, info, **kwargs):
        return Vente.objects.all().order_by('-date_creation')
    


schema = graphene.Schema(query=Query)