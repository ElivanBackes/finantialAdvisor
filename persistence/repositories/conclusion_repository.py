from persistence.repositories.base_repository import BaseRepository


class ConclusionRepository(BaseRepository):
    """Coleção `conclusions` — stub para a Etapa 3.

    Cada documento sintetiza as 3 análises de um ativo em um dado momento.
    Contrato futuro esperado: mesmo envelope append-only das análises, mais
    um campo `based_on` referenciando os _ids das 3 análises usadas:
        {based_on: {fundamentalist_analysis_id, technical_analysis_id,
                     news_sentiment_analysis_id}}
    """

    collection_name = "conclusions"
