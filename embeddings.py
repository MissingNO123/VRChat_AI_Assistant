# embeddings.py (c) 2024 MissingNO123
# Description: This module handles vector embeddings for the bot's memory system. It uses the SentenceTransformers library to encode text data into vectors, which are then used to find similar data in the memory. The memory is a list of dictionaries, each containing a text data field and its corresponding vector embedding. The data returned from semantic search is used by the chat module to dynamically inject the results from memory search into the system prompt at generation time.
import torch.nn.functional as F
from torch import cuda
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import semantic_search

import time
import os
import json
from typing import List, Dict

import options as opts
import functions as funcs

print("hi mom")
matryoshka_dim = 512
top_k = 6
# model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
model = SentenceTransformer(opts.sentence_transformer_model)
if cuda.is_available():
    model.to("cuda")

memory =  []
history = []

def search_memory(query, similarity_threshold=opts.similarity_threshold) -> List[str]:
    query_embedding = _get_embedding(query)
    results = _get_similarity(query_embedding, memory)
    filtered_results = []
    for i, result in enumerate(results[0]):
        if isinstance(result, dict) and 'corpus_id' in result:
            # print(f"> {i+1}. [{result['score']:0.4f}] {memory[result['corpus_id']]['data']}")
            if result['score'] > similarity_threshold:
                filtered_results.append(memory[result['corpus_id']]['data'])
        else:
            print(f"Unexpected result format at index {i}: {result}")
    return filtered_results


def add_to_memory(data: str) -> None:
    start_time = time.time()
    data_embedding = _get_embedding(data)
    if data_embedding is not None: 
        memory.append({"data": data, "embedding": data_embedding})
    end_time = time.time()
    funcs.v_print(f"Added to memory in {end_time - start_time:0.3f} seconds.")


def add_list_to_memory(data: List[str]) -> None:
    start_time = time.time()
    data_emeddings = _get_embedding(data)
    for i, data_embedding in enumerate(data_emeddings):
        memory.append({"data": data[i], "embedding": data_embedding})
    end_time = time.time()
    funcs.v_print(f"Added list to memory in {end_time - start_time:0.3f} seconds.")


def load_memory_from_file() -> None:
    start_time = time.time()
    memory_file = os.path.join(os.path.dirname(__file__), "memory.json")
    memory_file_example = os.path.join(os.path.dirname(__file__), "memory.example.json")
    if not os.path.exists(memory_file):
        if os.path.exists(memory_file_example):
            os.copy(memory_file_example, memory_file)
        else: 
            print(f"Memory file not found: {memory_file}")
            return
    with open(memory_file, 'r', encoding='utf8') as memory_file_data:
        global memory
        old_memory = memory.copy()
        try: 
            memory_json = json.load(memory_file_data)
            items = memory_json.get("items", [])
            memory.clear()
            add_list_to_memory(items)
            # for item in items:
            #     add_to_memory(item)
        except Exception as e:
            print(f"Error loading memory from file: {e}")
            memory = old_memory
        finally:
            del old_memory
    end_time = time.time()
    funcs.v_print(f"Memory loaded from file in {end_time - start_time:0.3f} seconds.")


def _get_similarity(query_embedding, db, top_k=top_k) -> List[List[Dict[str, int | float]]]:
    db_embedding = [x["embedding"] for x in db]
    return semantic_search(query_embedding, db_embedding, top_k=top_k)


def _get_embedding(query):
    device = "cuda" if cuda.is_available() else "cpu"
    return model.encode(query, convert_to_tensor=True, precision="float32", device=device)


if __name__ == "__main__":
    start_time = time.time()
    add_to_memory("The Great Pug is a virtual bar in VRChat.",)
    add_to_memory("The square root of 2 is 1.41421356237.",)
    add_to_memory("This is a useless factoid",)
    add_to_memory("Cheese goes great on toast",)
    add_to_memory("A double rainbow is when two rainbows appear at the same time.",)
    add_to_memory("The Black Cat is a virtual restaurant in VRChat. It supports PC and Quest platforms.")
    add_to_memory("The Great Pug has three floors. The second floor is called the Night View Hall. The third floor is called The Roost.")
    add_to_memory("The Great Pug is a popular hangout spot in VRChat. It is known for its cozy atmosphere and friendly community.")
    add_to_memory("Shrimps is bugs.")
    end_time = time.time()
    print(f"All memory loaded in {end_time - start_time:0.3f} seconds.")
    while True:
        query = input("Query:")
        start_time = time.time()
        results = search_memory(query)
        print("Top results:\n", "|".join(results))
        end_time = time.time()
        print(f"Search completed in {end_time - start_time:0.3f} seconds.")