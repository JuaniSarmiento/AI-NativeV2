from app.core.llm.adapters import AnthropicAdapter, LLMAdapter, MistralAdapter, OpenAIAdapter


def get_adapter(provider: str, api_key: str, model_name: str) -> LLMAdapter:
    if provider == "openai":
        return OpenAIAdapter(api_key=api_key, model=model_name)
    if provider == "anthropic":
        return AnthropicAdapter(api_key=api_key, model=model_name)
    if provider == "mistral":
        return MistralAdapter(api_key=api_key, model=model_name)
    raise ValueError(f"Unsupported LLM provider: {provider}")


__all__ = ["LLMAdapter", "OpenAIAdapter", "AnthropicAdapter", "MistralAdapter", "get_adapter"]
