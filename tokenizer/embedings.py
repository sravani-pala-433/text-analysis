import logging
from typing import List
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
import numpy as np
from transformers import AutoTokenizer

import os

from textAnalysisService.auth.config import config
from textAnalysisService.auth.schema import TextContentRow, TextEmbeddingRow, TextItemsContent, TextEmbeddingRowV1

logger = logging.getLogger(__name__)

os.environ["TOKENIZERS_PARALLELISM"] = "false"
model = SentenceTransformer('all-MiniLM-L6-v2')
# tokenizer = model.tokenizer
# tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

pca = PCA(n_components=3)


def handle_embeddings_list(text_content_list: List[TextContentRow]) -> List[TextEmbeddingRow]:
	embedding_rows = []
	pca = PCA(n_components=3)
	if len(text_content_list) < 3:
		pca = PCA(n_components=len(text_content_list))

	logger.info(f" list of textContent rows: {len(text_content_list)}")
	segments = [sentence.text_content for sentence in text_content_list]
	# all_Segments = tokenizer(segments, padding=True, truncation=True, return_tensors="pt", max_length=512)
	logger.debug(f"handle_embeddings_list segments  {len(segments)}")
	# logger.debug(f"handle_embeddings_list all_Segments  {segments}")
	
	try:
		embeddings = model.encode(sentences=segments, batch_size=len(segments), show_progress_bar=True)
		logger.debug(f"handle_embeddings_list embeddings  {embeddings}")
		pca_vectors = pca.fit_transform(embeddings)
	except Exception as e:
		logger.warning(f"exception identified in handle_embeddings_list {str(e)}")
	
	logger.debug(f"handle_embeddings_list pca_vectors  {pca_vectors}")
	for index, row in enumerate(segments):
		list_item = text_content_list[index]
		embedding_row = TextEmbeddingRow(
			**list_item.model_dump(),  # Use the dictionary representation of the TextContentRow
			embeddings=embeddings[index],
			pca_vector=pca_vectors[index],
		)
		logger.debug(f"handle_embeddings_list embedding_row  {embedding_row}")
		embedding_rows.append(embedding_row)
	return embedding_rows

def get_embeddings_by_text(query_str: str) :
	embeddings = model.encode(sentences=query_str, batch_size=1, show_progress_bar=False)
	logger.debug(f"get_embeddings_by_text str {query_str} embeddings  {embeddings}")
	return embeddings


def handle_embeddings_list_V1(text_content_list: List[TextItemsContent]) -> List[TextEmbeddingRowV1]:
	embedding_rows = []
	pca = PCA(n_components=3)
	if len(text_content_list) < 3:
		pca = PCA(n_components=len(text_content_list))
	logger.info(f" list of textContent rows: {len(text_content_list)}")
	segments = [sentence.text_content for sentence in text_content_list]
	logger.debug(f"handle_embeddings_list segments  {len(segments)}")
	try:
		embeddings = model.encode(sentences=segments, batch_size=len(segments), show_progress_bar=True)
		logger.debug(f"handle_embeddings_list embeddings{embeddings}")
		pca_vectors = pca.fit_transform(embeddings)
	except Exception as e:
		logger.warning(f"exception identified in handle_embeddings_list {str(e)}")

	logger.debug(f"handle_embeddings_list pca_vectors{pca_vectors}")
	for index, row in enumerate(segments):
		list_item = text_content_list[index]
		embedding_row = TextEmbeddingRowV1(
			**list_item.model_dump(),  # Use the dictionary representation of the TextContentRow
			embeddings=embeddings[index],
			pca_vector=pca_vectors[index],
		)
		logger.debug(f"handle_embeddings_list embedding_row  {embedding_row}")
		embedding_rows.append(embedding_row)
	return embedding_rows

