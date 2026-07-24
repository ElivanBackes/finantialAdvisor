from persistence.repositories.base_repository import BaseRepository


class RecommendationRepository(BaseRepository):
    """Coleção `recommendations` — stub para a Etapa 4.

    Contrato futuro esperado: mesmo envelope append-only, mais referência à
    conclusão que originou a recomendação (`conclusion_id`) e o veredito
    final (ex: campo `verdict`: comprar / manter / evitar).
    """

    collection_name = "recommendations"
