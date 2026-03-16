# Security Guidelines for AI OCR Service

## 🔐 API Key Management

### Critical Security Notice

**NEVER commit API keys to version control.** The `.env` file containing sensitive credentials should always be:

1. Listed in `.gitignore`
2. Never committed to git
3. Rotated immediately if accidentally exposed

### Environment Variables Required

Create a `.env` file from the `.env.example` template:

```bash
cp .env.example .env
```

Then fill in your actual API keys:

| Variable | Description | Source |
|----------|-------------|--------|
| `GEMINI_API_KEY` | Google Gemini API | <https://ai.google.dev/> |
| `ANTHROPIC_API_KEY` | Claude API | <https://console.anthropic.com/> |
| `OPENAI_API_KEY` | OpenAI API | <https://platform.openai.com/> |
| `GROQ_API_KEY` | Groq API | <https://console.groq.com/> |
| `OPENROUTER_API_KEY` | OpenRouter API | <https://openrouter.ai/> |
| `JINA_API_KEY` | Jina Embeddings | <https://jina.ai/> |
| `LANGSMITH_API_KEY` | LangSmith tracing | <https://smith.langchain.com/> |

### If API Keys Are Exposed

**Immediate Actions Required:**

1. **Revoke the exposed keys immediately** at their respective provider consoles
2. **Generate new keys** for all affected services
3. **Update your `.env` file** with the new keys
4. **Clear git history** if keys were committed (see below)

### Clearing Git History (if keys were committed)

```bash
# Remove sensitive file from git history
git filter-branch --force --index-filter \
"git rm --cached --ignore-unmatch AI_OCR_Service/.env" \
--prune-empty --tag-name-filter cat -- --all

# Force push to remote (DANGEROUS - coordinate with team)
git push origin --force --all
```

### Additional Security Measures

1. **Use environment-specific keys**: Different keys for dev/staging/prod
2. **Rotate keys regularly**: Every 90 days recommended
3. **Monitor API usage**: Set up alerts for unusual activity
4. **Use least-privilege access**: Only enable required API endpoints
5. **Enable audit logging**: Track key usage when available

### Secure Development Practices

- Use `.env.example` as a template
- Never hardcode keys in source files
- Use secret management for production (AWS Secrets Manager, Azure Key Vault, etc.)
- Enable 2FA on all API provider accounts
- Review access logs regularly

### Reporting Security Issues

If you discover a security vulnerability:

1. Do NOT open a public issue
2. Contact the maintainers privately
3. Provide detailed reproduction steps
4. Allow time for remediation before disclosure

---

## Recent Security Fixes Applied

- ✅ Created `.env.example` template with placeholder values
- ✅ Fixed Gemini model name to valid `gemini-1.5-flash-latest`
- ✅ Updated all deprecated `ELASTICSEARCH_HOST` references to `ES_HOST`
- ✅ Fixed documentation referencing non-existent Gemini 3.0 models
- ✅ Cleaned up docker-compose.yml syntax
