# AI Setup Quickstart

Quick reference for setting up AI providers with the Web Terminal.

## 🚀 Quick Setup

### 1. Edit your `.env` file

```bash
nano .env
```

### 2. Choose your provider and configure

#### Option A: Mistral AI (Recommended - Fast & Affordable)

```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=https://api.mistral.ai
LOCAL_AI_API_KEY=your-mistral-api-key-here
LOCAL_AI_MODEL=mistral-large-latest
```

Get API key: https://console.mistral.ai/

#### Option B: Groq (Fast & Free Tier)

```bash
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=https://api.groq.com/openai
LOCAL_AI_API_KEY=your-groq-api-key-here
LOCAL_AI_MODEL=mixtral-8x7b-32768
```

Get API key: https://console.groq.com/

#### Option C: Ollama (Free & Local)

```bash
# First install Ollama
brew install ollama  # macOS
# or download from https://ollama.ai

# Pull a model
ollama pull mistral

# Configure
AI_PROVIDER=local
LOCAL_AI_ENDPOINT=http://localhost:11434
LOCAL_AI_MODEL=mistral
# No API key needed!
```

#### Option D: OpenAI

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4
```

#### Option E: Anthropic Claude

```bash
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

### 3. Start the server

```bash
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open browser

```
http://localhost:8000
```

Look for the AI Assistant sidebar on the right. The status indicator should be green (online).

## 📊 Provider Comparison

| Provider | Cost | Speed | Quality | Setup |
|----------|------|-------|---------|-------|
| **Groq** | Free tier | ⚡ Fastest | Good | Easy |
| **Ollama** | Free (local) | Fast | Good | Medium |
| **Mistral AI** | $$ | Very Fast | Excellent | Easy |
| **together.ai** | $$ | Fast | Very Good | Easy |
| **OpenAI** | $$$ | Medium | Excellent | Easy |
| **Anthropic** | $$$ | Medium | Excellent | Easy |

## 🔧 Troubleshooting

**Status shows "Offline"?**
- Check your API key is correct
- Verify the endpoint URL
- Check server logs for errors

**For Ollama:**
```bash
# Make sure Ollama is running
ollama serve

# Check available models
ollama list
```

## 📚 Full Documentation

For detailed setup instructions, see: `docs/ai-provider-setup.md`

## 🎯 Next Steps

Once configured:
1. Try chatting with the AI
2. Click 🎤 for voice input
3. Ask for command suggestions
4. Get help with terminal errors
