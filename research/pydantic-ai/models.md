# Pydantic AI Models and Providers

## Supported Providers
- OpenAI (gpt-4o, gpt-4, gpt-3.5-turbo)
- Anthropic (claude-3-5-sonnet-latest, claude-3-opus)
- Gemini (google-gla:gemini-1.5-flash)
- Groq
- Mistral
- Cohere
- Bedrock
- Hugging Face

## Model Configuration

### Simple Model Creation
```python
from pydantic_ai import Agent

# Automatic model selection
agent = Agent('openai:gpt-4o')
agent = Agent('anthropic:claude-3-5-sonnet-latest')
agent = Agent('google-gla:gemini-1.5-flash')
```

### Fallback Model
```python
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.fallback import FallbackModel

openai_model = OpenAIModel('gpt-4o')
anthropic_model = AnthropicModel('claude-3-5-sonnet-latest')
fallback_model = FallbackModel(openai_model, anthropic_model)

agent = Agent(fallback_model)
```

## OpenAI-Compatible Providers
Can use `OpenAIModel` with:
- DeepSeek
- Grok (xAI)
- Ollama
- OpenRouter
- Perplexity
- Together AI
- Azure AI Foundry