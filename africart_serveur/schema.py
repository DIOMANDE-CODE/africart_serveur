import graphene
import produits.schema
import ventes.schema


class Query(produits.schema.Query, ventes.schema.Query, graphene.ObjectType):
    pass


class Mutation(produits.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
