# Preventing Jailbreaking AI with Guardrails

## Quick Start

### 1. Setup Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

```bash
# Copy example config and add your API keys
cp config.example.yaml config.yaml
```

### 4. Install Guardrails

```bash
# Install all 5 guardrail validators from the hub
# Be sure that you are in your virtual enviornment (source venv/bin/activate)
guardrails hub install hub://arize-ai/dataset_embeddings_guardrails
guardrails hub install hub://guardrails/valid_length
guardrails hub install hub://guardrails/ban_list
guardrails hub install hub://tryolabs/restricttotopic
guardrails hub install hub://guardrails/web_sanitization
```

## Usage

This will:
- Apply guardrails to incoming queries
- Trace everything to Arize for observability
- Process test queries and show results

## Guardrails

### 1. **Arize Dataset Embeddings**
- Uses semantic similarity to detect jailbreak attempts
- 86% detection rate on known jailbreak patterns
- Threshold configurable (default: 0.3)
- Hub: `hub://arize-ai/dataset_embeddings_guardrails`

### 2. **Length Validation**
- Prevents overly long queries that could cause issues
- Configurable maximum length (default: 500 characters)
- Hub: `hub://guardrails/valid_length`

### 3. **Ban List**
- Blocks queries containing forbidden keywords
- Includes common jailbreak terms like "DAN", "ignore previous", "bypass"
- Hub: `hub://guardrails/ban_list`

### 4. **Topic Restriction**
- Ensures queries stay within allowed topics
- Blocks inappropriate content categories
- Configurable valid/invalid topic lists
- Hub: `hub://tryolabs/restricttotopic`

### 5. **Web Sanitization**
- Sanitizes web-related content and potential XSS
- Removes malicious HTML/JavaScript patterns
- No configuration required
- Hub: `hub://guardrails/web_sanitization`

## Resources

Want to dive deeper? Explore jailbreaking techniques in our blog [The Complete Guide to Jailbreaking AI Models (for Good)], and learn about guardrail strategies in [Everything You Need to Know About Guardrails for LLMs].

Check out the [Guardrails Hub](https://hub.guardrailsai.com/) for a more comprehensive list of guardrails you can install today.
