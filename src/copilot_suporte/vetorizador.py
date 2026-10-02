"""Modelo de embeddings, carregado uma vez só e apenas quando for usado."""


class Vetorizador:
    """Transforma textos em vetores com um modelo do Hugging Face.

    O Gemma usa um prefixo para o que fica guardado (documento) e outro para o que se
    pergunta (consulta). Misturar os dois piora a busca: ticket contra ticket usa
    documento; texto digitado usa consulta.
    """

    def __init__(self, nome_modelo: str):
        self.nome = nome_modelo
        self._modelo = None

    @property
    def carregado(self) -> bool:
        return self._modelo is not None

    def carregar(self) -> None:
        if self._modelo is None:
            # Import preguiçoso: o PyTorch (vários segundos para importar) só é carregado
            # quando um vetor é realmente necessário. Os testes nunca pagam esse custo.
            from sentence_transformers import SentenceTransformer

            self._modelo = SentenceTransformer(self.nome)

    def documentos(self, textos: list[str], lote: int = 16):
        self.carregar()
        return self._modelo.encode_document(
            textos, batch_size=lote, show_progress_bar=True, normalize_embeddings=True
        )

    def consulta(self, texto: str):
        self.carregar()
        return self._modelo.encode_query(texto, normalize_embeddings=True)
