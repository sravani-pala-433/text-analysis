import logging
from typing import List

import numpy as np
from fastembed import TextEmbedding
from sklearn.decomposition import PCA

from textAnalysisService.auth.schema import TextContentRow, TextEmbeddingRow, TextItemsContent, TextEmbeddingRowV1

logger = logging.getLogger(__name__)

_embedding_model = None


def get_embedding_model() -> TextEmbedding:
	"""Lazy singleton — the ONNX model downloads on first use and caches."""
	global _embedding_model
	if _embedding_model is None:
		logger.info("Loading fastembed model 'all-MiniLM-L6-v2'...")
		_embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
	return _embedding_model


def _embed_texts(texts: List[str]) -> np.ndarray:
	if not texts:
		return np.zeros((0, 384), dtype=np.float32)
	rows = list(get_embedding_model().embed(texts, batch_size=max(1, len(texts))))
	return np.asarray(rows, dtype=np.float32)


def handle_embeddings_list(text_content_list: List[TextContentRow]) -> List[TextEmbeddingRow]:
	embedding_rows = []
	segments = [sentence.text_content for sentence in text_content_list]
	logger.info(f"list of textContent rows: {len(text_content_list)}")
	if not segments:
		return embedding_rows

	embeddings = _embed_texts(segments)
	n_components = min(3, len(segments))
	pca = PCA(n_components=n_components)
	pca_vectors = pca.fit_transform(embeddings)

	for index in range(len(segments)):
		list_item = text_content_list[index]
		embedding_row = TextEmbeddingRow(
			**list_item.model_dump(),  # Use the dictionary representation of the TextContentRow
			embeddings=embeddings[index],
			pca_vector=pca_vectors[index],
		)
		logger.debug(f"handle_embeddings_list embedding_row  {embedding_row}")
		embedding_rows.append(embedding_row)
	return embedding_rows


def get_embeddings_by_text(query_str: str) -> np.ndarray:
	embeddings = _embed_texts([query_str])
	logger.debug(f"get_embeddings_by_text str {query_str} embeddings  {embeddings[0]}")
	return embeddings[0]


def handle_embeddings_list_V1(text_content_list: List[TextItemsContent]) -> List[TextEmbeddingRowV1]:
	embedding_rows = []
	segments = [sentence.text_content for sentence in text_content_list]
	logger.info(f"list of textContent rows: {len(text_content_list)}")
	if not segments:
		return embedding_rows

	embeddings = _embed_texts(segments)
	n_components = min(3, len(segments))
	pca = PCA(n_components=n_components)
	pca_vectors = pca.fit_transform(embeddings)

	for index in range(len(segments)):
		list_item = text_content_list[index]
		embedding_row = TextEmbeddingRowV1(
			**list_item.model_dump(),  # Use the dictionary representation of the TextContentRow
			embeddings=embeddings[index],
			pca_vector=pca_vectors[index],
		)
		logger.debug(f"handle_embeddings_list embedding_row  {embedding_row}")
		embedding_rows.append(embedding_row)
	return embedding_rows