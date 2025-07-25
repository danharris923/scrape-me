## FEATURE:
# 📦 CONTEXT ENGINEERING PROMPT: Modular Affiliate Scraper (Built via GCP Browser SSH)

You are Claude Code running locally with an active Playwright MCP (Modular Command Proxy) agent attached. This allows you to interact with web pages by clicking, typing, and reading content, as if you were a human using a browser.

---

# 🧠 BUILD METHOD (IMPORTANT)

You will not be using SSH directly.

Instead, you will:

✅ Open https://console.cloud.google.com/compute/instances  
✅ Locate the target Google Cloud VM (Ubuntu 22.04)  
✅ Click the “SSH” button to launch the **web-based browser terminal**  
✅ Type and paste commands directly into that **browser-based SSH shell**

This is your only method of remote execution.  
Treat this like sitting at a browser with your hands on the keyboard, one command at a time.

You may:
- Type code using `nano`, `vim`, or `cat > file.py` as needed  
- Run `python3` or `bash` commands to test  
- Install system packages  
- Paste full scripts slowly, line by line if needed  
- Sanity check by reading terminal output

This process is **manual and slow**, and will be monitored the entire time.  
You are allowed to be methodical and verbose.

---

# 🎯 OBJECTIVE

You are building a modular cloud-based scraper system that will:

- Run on a Google Cloud VM (Ubuntu 22.04)
- Use **Playwright** (headful) to scrape affiliate product data
- Validate scraped items with **Pydantic** models
- Rename + upload product images to **Google Cloud Storage**
- Save output as a validated list of product cards in `output.json`
- Feed that file to a **Vercel-hosted static frontend** (React)

This scraper system will scale across multiple niches by changing only the source URL and output location.

---

# 🧱 TECH STACK + DOCS

| Tool | Purpose | Link |
|------|---------|------|
| Python 3.10+ | Core scripting language | https://docs.python.org/3/ |
| Playwright (Python) | Real browser-based scraping | https://playwright.dev/python/docs/intro |
| Pydantic v2 | Defines/validates product schema | https://docs.pydantic.dev/latest/ |
| Google Cloud Storage | Image hosting (SEO-named, public URLs) | https://cloud.google.com/storage/docs |
| Google Cloud Console | Web interface used for SSH | https://console.cloud.google.com/compute/instances |
| Vercel (Frontend) | Reads JSON, renders affiliate cards | https://vercel.com/docs |

You may only rely on these sources for technical truth.  
Do not hallucinate behaviors, syntax, or assumptions not backed by these docs.

---

# 🧪 DATA STRUCTURE (models.py)

```python
from pydantic import BaseModel, HttpUrl

class ProductCard(BaseModel):
    title: str
    price: str
    affiliate_url: HttpUrl
    image_url: HttpUrl
    slug: str

- Pydantic AI agent that has another Pydantic AI agent as a tool.
-
- CLI to interact with the agent.
- 

## EXAMPLES:

In the `examples/` folder, there is a README for you to read to understand what the example is all about and also how to structure your own README when you create documentation for the above feature.

- `examples/cli.py` - use this as a template to create the CLI
- `examples/agent/` - read through all of the files here to understand best practices for creating Pydantic AI agents that support different providers and LLMs, handling agent dependencies, and adding tools to the agent.

Don't copy any of these examples directly, it is for a different project entirely. But use this as inspiration and for best practices.

## DOCUMENTATION:

Pydantic AI documentation: https://ai.pydantic.dev/

## OTHER CONSIDERATIONS:


- Include the project structure in the README.
-
- Use python_dotenv and load_env() for environment variables


📂 TARGET FILE STRUCTURE (On the VM)
arduino
Copy
Edit
/home/ubuntu/scraper/
├── main.py
├── models.py
├── playwright_scraper.py
├── gcs_uploader.py
├── output.json
├── requirements.txt
└── setup.sh



🤖 AGENT STRUCTURE
You will act in stages:

1. Planner
Breaks the build into files

Confirms Pydantic model + field types

Outlines flow: scrape → upload → validate → save

2. Builder
Writes modular Python files, one per role

Adds logging + safety checks

3. Installer
Writes setup.sh to install: Python, pip, Playwright, Chrome libs, GCS SDK

4. Executor
Uses Playwright MCP to open GCP console and type into the web terminal

Types and pastes each file (slowly) into the VM

Runs setup and test runs interactively

🔐 CONSTRAINTS
You must only interact with the VM via the browser SSH terminal

You may type full files into nano, or paste content into cat > filename.py

You may pause, verify, and adjust based on terminal output

You are being supervised by a human — proceed slowly and cleanly

Never skip validation — all scraped items must pass the ProductCard model

This system must run with zero external input beyond the build prompt