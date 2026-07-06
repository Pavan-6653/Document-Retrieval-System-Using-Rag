from transformers import AutoTokenizer, RagRetriever, RagSequenceForGeneration

_tokenizer = None
_retriever = None
_model = None

def get_models():
    global _tokenizer, _retriever, _model

    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(
            "facebook/rag-sequence-nq",
            use_auth_token=False
        )

    if _retriever is None:
        _retriever = RagRetriever.from_pretrained(
            "facebook/rag-sequence-nq",
            index_name="exact",
            use_dummy_dataset=True
        )

    if _model is None:
        _model = RagSequenceForGeneration.from_pretrained(
            "facebook/rag-token-nq",
            retriever=_retriever
        )

    return _tokenizer, _retriever, _model