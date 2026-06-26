# SkillEval Setup Guide - .env Configuration

**Quick Start:** 5 minutes to get running with FREE Google GenAI

---

## 🚀 Quick Setup (Google GenAI - FREE)

### Step 1: Copy .env.example

```bash
cd /path/to/skilleval
cp .env.example .env
```

### Step 2: Get Google API Key (FREE)

1. Visit: https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key (starts with `AIza...`)

### Step 3: Edit .env

```bash
# Open .env in your editor
nano .env  # or code .env, vim .env, etc.

# Find this line:
GOOGLE_API_KEY=your-google-api-key-here

# Replace with your actual key:
GOOGLE_API_KEY=AIzaSyD...your-actual-key...xyz

# Save and exit
```

### Step 4: Verify Configuration

```bash
python3 show_config.py
```

**Expected output:**
```
======================================================================
SkillEval Configuration
======================================================================
Provider: google
Model: gemini-2.0-flash-exp
Max Tokens: 8192
Max Turns: 25
Temperature: 1.0
Timeout: 300s
Google API Key: Set (AIzaSyD...)
Anthropic API Key: Not set
Cost Tracking: Enabled
Cost Warning Threshold: $0.1
======================================================================

✅ Configuration is valid and ready to use
```

### Step 5: Run Your First Evaluation

```bash
# Single skill
python3 -m skilleval.cli eval /path/to/skill

# Batch evaluation
./batch_eval.sh /path/to/skills/skills
```

**That's it!** 🎉 You're using FREE Google GenAI for evaluations.

---

## 📋 .env File Reference

### Full .env Template

```ini
# Provider: 'google' or 'anthropic'
LLM_PROVIDER=google

# Google GenAI (FREE tier)
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_MODEL=gemini-2.0-flash-exp

# Anthropic Claude (Paid)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Agent configuration
MAX_TOKENS=8192
MAX_TURNS=25
TIMEOUT_SECONDS=300
TEMPERATURE=1.0

# Cost tracking
ENABLE_COST_TRACKING=true
COST_WARNING_THRESHOLD=0.10
```

### Configuration Options

#### LLM_PROVIDER

**Options:** `google` or `anthropic`  
**Default:** `google`  
**Example:**
```ini
LLM_PROVIDER=google  # Use Google GenAI (free)
# or
LLM_PROVIDER=anthropic  # Use Anthropic Claude (paid)
```

#### GOOGLE_API_KEY

**Get key:** https://aistudio.google.com/apikey  
**Format:** Starts with `AIza`  
**Example:**
```ini
GOOGLE_API_KEY=AIzaSyDexampleKey123456789
```

#### GOOGLE_MODEL

**Options:**
- `gemini-2.0-flash-exp` (default) - Fast, free tier
- `gemini-2.0-flash-thinking-exp` - With reasoning
- `gemini-1.5-pro` - Larger context

**Example:**
```ini
GOOGLE_MODEL=gemini-2.0-flash-exp
```

#### ANTHROPIC_API_KEY

**Get key:** https://console.anthropic.com/  
**Format:** Starts with `sk-ant-`  
**Example:**
```ini
ANTHROPIC_API_KEY=sk-ant-api03-example123...
```

#### ANTHROPIC_MODEL

**Options:**
- `claude-sonnet-4-20250514` (default) - Balanced
- `claude-opus-4-20250514` - Most capable
- `claude-haiku-4-20250320` - Fastest

**Example:**
```ini
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

#### MAX_TOKENS

**Range:** 1024 - 8192  
**Default:** 8192  
**Purpose:** Maximum tokens per turn  
**Example:**
```ini
MAX_TOKENS=4096  # Reduce for faster responses
```

#### MAX_TURNS

**Range:** 1 - 50  
**Default:** 25  
**Purpose:** Maximum conversation turns  
**Example:**
```ini
MAX_TURNS=10  # Reduce to save costs
```

#### TIMEOUT_SECONDS

**Range:** 60 - 600  
**Default:** 300 (5 minutes)  
**Purpose:** Maximum execution time  
**Example:**
```ini
TIMEOUT_SECONDS=180  # 3 minute timeout
```

#### TEMPERATURE

**Range:** 0.0 - 2.0  
**Default:** 1.0  
**Purpose:** Response randomness (0=deterministic, 2=creative)  
**Example:**
```ini
TEMPERATURE=0.5  # More deterministic
```

#### ENABLE_COST_TRACKING

**Options:** `true` or `false`  
**Default:** `true`  
**Purpose:** Track and report costs  
**Example:**
```ini
ENABLE_COST_TRACKING=true
```

#### COST_WARNING_THRESHOLD

**Range:** 0.01 - 10.00  
**Default:** 0.10 ($0.10 per eval)  
**Purpose:** Warn if cost exceeds threshold  
**Example:**
```ini
COST_WARNING_THRESHOLD=0.05  # Warn at 5 cents
```

---

## 🔄 Switching Providers

### From Google to Anthropic

```bash
# Edit .env
nano .env

# Change:
LLM_PROVIDER=google
# To:
LLM_PROVIDER=anthropic

# Add Anthropic key:
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Verify:
python3 show_config.py
```

### From Anthropic to Google

```bash
# Edit .env
nano .env

# Change:
LLM_PROVIDER=anthropic
# To:
LLM_PROVIDER=google

# Make sure Google key is set:
GOOGLE_API_KEY=AIza...

# Verify:
python3 show_config.py
```

---

## 🧪 Testing Configuration

### Show Current Config

```bash
python3 show_config.py
```

### Test Multi-Provider System

```bash
python3 test_multi_provider.py
```

**Expected output:**
```
1. Provider Detection
   Detected provider: google
   Selected model: gemini-2.0-flash-exp
   GOOGLE_API_KEY: ✅ Set
   ✅ At least one provider available

2. Executor Availability
   ✅ Executor available
   Provider: google
   Model: gemini-2.0-flash-exp

3. Cost Calculation
   Google (10K tokens): $0.0016
   Anthropic (10K tokens): $0.0780
   ✅ Cost calculation working

4. Agent Execution
   ✅ Execution complete
```

---

## 🐛 Troubleshooting

### "Configuration error: No API key found"

**Solution:**
```bash
# 1. Make sure .env file exists
ls -la .env

# 2. If not, copy from example
cp .env.example .env

# 3. Edit and add API key
nano .env

# 4. Verify
python3 show_config.py
```

### ".env file not being loaded"

**Check:**
1. File is named exactly `.env` (not `env` or `.env.txt`)
2. File is in the project root directory
3. File has correct permissions

```bash
# Check location
pwd  # Should be in /path/to/skilleval

# Check file
ls -la .env

# If wrong location, move it
mv .env /path/to/skilleval/
```

### "python-dotenv not installed"

```bash
python3 -m pip install python-dotenv
```

### "Invalid API key format"

**Google keys:**
- Start with `AIza`
- Length: ~39 characters
- Example: `AIzaSyDexampleKey123456789abcdef`

**Anthropic keys:**
- Start with `sk-ant-`
- Length: ~100+ characters
- Example: `sk-ant-api03-...`

### "Rate limit exceeded"

**Google (free tier):**
- 15 requests/minute
- 1M tokens/day

**Solutions:**
1. Wait 60 seconds
2. Reduce MAX_TURNS
3. Evaluate fewer skills at once

---

## 💡 Best Practices

### Development

```ini
# .env for development
LLM_PROVIDER=google
GOOGLE_API_KEY=AIza...dev-key...
MAX_TURNS=10          # Faster iterations
TEMPERATURE=0.7       # Slightly more deterministic
ENABLE_COST_TRACKING=true
```

### Production

```ini
# .env for production
LLM_PROVIDER=anthropic  # Higher quality
ANTHROPIC_API_KEY=sk-ant...prod-key...
MAX_TURNS=25
TEMPERATURE=1.0
ENABLE_COST_TRACKING=true
COST_WARNING_THRESHOLD=0.05  # Stricter threshold
```

### CI/CD

**Don't commit .env!** Use environment variables:

```yaml
# .github/workflows/eval.yml
env:
  GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
  LLM_PROVIDER: google
  MAX_TURNS: 15
```

---

## 📁 File Locations

```
skilleval/
├── .env                    # Your config (don't commit!)
├── .env.example            # Template (committed)
├── show_config.py          # Show current config
├── test_multi_provider.py  # Test providers
└── src/skilleval/utils/
    ├── env_config.py       # Config loader
    └── multi_provider_agent.py  # Uses config
```

---

## ✅ Checklist

After setup, verify:

- [ ] `.env` file exists and is filled in
- [ ] API key is set for chosen provider
- [ ] `python3 show_config.py` shows ✅ valid
- [ ] `python3 test_multi_provider.py` passes
- [ ] First evaluation runs successfully
- [ ] `.env` is in `.gitignore` (don't commit keys!)

---

## 🎯 Next Steps

1. ✅ Complete setup (you're here)
2. Run test evaluation on one skill
3. Run batch evaluation on all skills
4. Check reports in `batch_results/`
5. Adjust config based on results

**Ready to evaluate!** 🚀

---

**Questions?**
- Check `MULTI_PROVIDER_GUIDE.md` for provider details
- Check `HARNESS_IMPLEMENTATION.md` for technical details
- Run `python3 show_config.py` to debug config
