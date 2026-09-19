"""Real BPE when available. Model mapping and estimation are never implicit."""
from functools import lru_cache

@lru_cache(maxsize=16)
def tokenizer(model=None):
    try:
        import tiktoken
        try:
            encoding = tiktoken.encoding_for_model(model or '')
            label = 'tiktoken:' + encoding.name + ' (model mapping)'
        except KeyError:
            encoding = tiktoken.get_encoding('o200k_base')
            label = 'tiktoken:o200k_base (local reference; model not mapped)'
        return lambda text: len(encoding.encode(text, disallowed_special=())), label
    except Exception:
        return lambda text: (len(text.encode('utf-8')) + 2)//3, 'ESTIMATE:utf8-bytes/3 (BPE unavailable)'
