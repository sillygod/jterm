# AI Provider Setup Guide

This guide explains how to configure different AI providers for the Web Terminal AI Assistant.

## Supported Providers

The Web Terminal supports the following AI providers:

1. **OpenAI** - GPT-4, GPT-3.5-turbo, etc.
2. **Anthropic** - Claude 3 models
3. **OpenAI-Compatible Providers** (via Local provider):
   - Mistral AI
   - together.ai
   - Groq
   - OpenRouter
   - Ollama (local)
   - Any OpenAI-compatible API

## Configuration

All configuration is done via environment variables in your `.env` file.

### Option 1: OpenAI

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4
```

Available models: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`, etc.

### Option 2: Anthropic Claude

```bash
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

Available models: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`, `claude-3-haiku-20240307`

### Option 3: Mistral AI

```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=https://api.mistral.ai
LOCAL_AI_API_KEY=your-mistral-api-key
LOCAL_AI_MODEL=mistral-large-latest
```

Available models: `mistral-large-latest`, `mistral-medium-latest`, `mistral-small-latest`, `open-mixtral-8x7b`

### Option 4: together.ai

```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=https://api.together.xyz
LOCAL_AI_API_KEY=your-together-api-key
LOCAL_AI_MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1
```

Popular models:
- `mistralai/Mixtral-8x7B-Instruct-v0.1`
- `meta-llama/Llama-3-70b-chat-hf`
- `togethercomputer/CodeLlama-34b-Instruct`

### Option 5: Groq

```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=https://api.groq.com/openai
LOCAL_AI_API_KEY=your-groq-api-key
LOCAL_AI_MODEL=mixtral-8x7b-32768
```

Available models: `mixtral-8x7b-32768`, `llama2-70b-4096`, `gemma-7b-it`

### Option 6: OpenRouter

```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=https://openrouter.ai/api
LOCAL_AI_API_KEY=your-openrouter-api-key
LOCAL_AI_MODEL=mistralai/mixtral-8x7b-instruct
```

OpenRouter provides access to many models. Check their docs for available models.

### Option 7: Ollama (Local)

```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=http://localhost:11434
# No API key needed for local Ollama
LOCAL_AI_MODEL=mistral
```

First, install and run Ollama:
```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama
ollama serve

# Pull a model
ollama pull mistral
```

Popular Ollama models: `mistral`, `llama2`, `codellama`, `mixtral`, `gemma`

## Getting API Keys

### Mistral AI
1. Visit https://console.mistral.ai/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key

### together.ai
1. Visit https://api.together.xyz/
2. Sign up or log in
3. Go to Settings → API Keys
4. Create a new API key

### Groq
1. Visit https://console.groq.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key

### OpenRouter
1. Visit https://openrouter.ai/
2. Sign up or log in
3. Go to Keys
4. Create a new API key

## Testing Your Configuration

After configuring your `.env` file:

1. Start the server:
   ```bash
   source venv/bin/activate
   uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. Open your browser to `http://localhost:8000`

3. Look for the AI Assistant sidebar on the right

4. Check the status indicator:
   - 🟢 **Green (Online)** - AI provider is configured and working
   - 🔴 **Red (Offline)** - AI provider not configured or connection failed

5. Try sending a test message in the chat

## Troubleshooting

### Status shows "Offline"
- Check that your API key is correct in `.env`
- Verify the endpoint URL is correct
- Check your internet connection
- Look at server logs for error messages

### "Rate limit exceeded" errors
- You've hit your provider's rate limit
- Wait a few moments and try again
- Consider upgrading your plan

### "Invalid API key" errors
- Double-check your API key in `.env`
- Make sure there are no extra spaces
- Verify the key hasn't expired

### Local Ollama not connecting
- Ensure Ollama is running: `ollama serve`
- Check the endpoint is `http://localhost:11434`
- Verify the model is pulled: `ollama list`

## Advanced Configuration

You can fine-tune AI behavior by creating a custom configuration in your code:

```python
from src.config import settings

# Modify settings before starting the app
settings.OPENAI_MODEL = "gpt-4-turbo"
```

Or add these to your `.env`:
```bash
# Increase max tokens for longer responses
AI_MAX_TOKENS=2000

# Adjust temperature (0.0 = deterministic, 1.0 = creative)
AI_TEMPERATURE=0.7

# Timeout for AI requests (seconds)
AI_TIMEOUT=30
```

## Cost Optimization

Different providers have different pricing:

- **Groq**: Free tier with fast inference
- **together.ai**: Competitive pricing, good for experimentation
- **Mistral AI**: Affordable pricing, good quality
- **Ollama**: Free (runs locally)
- **OpenAI**: Premium pricing, high quality
- **Anthropic**: Premium pricing, excellent for complex tasks

For development, consider:
1. Start with Groq (free) or Ollama (local)
2. Use together.ai for cost-effective production
3. Use OpenAI/Anthropic for production workloads requiring highest quality

## Next Steps

Once you have AI configured:
- Try voice input by clicking the 🎤 microphone button
- Ask for command suggestions
- Request explanations for terminal output
- Use the AI to help debug errors

For more information, see the [Quickstart Guide](../specs/001-web-based-terminal/quickstart.md).
