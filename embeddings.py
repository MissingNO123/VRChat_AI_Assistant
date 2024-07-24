import torch.nn.functional as F
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import semantic_search

matryoshka_dim = 512
top_k = 6
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)


if __name__ == "__main__":
    sentences = ['search_query: What is TSNE?', 'search_query: Who is Laurens van der Maaten?']
    embeddings = model.encode(sentences, convert_to_tensor=True)
    embeddings = F.layer_norm(embeddings, normalized_shape=(embeddings.shape[1],))
    embeddings = embeddings[:, :matryoshka_dim]
    embeddings = F.normalize(embeddings, p=2, dim=1)
    print(embeddings)