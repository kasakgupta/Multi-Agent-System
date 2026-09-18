# 🔬 ResearchFlow AI

### Multi-Agent Research & Intelligence System

ResearchFlow AI is a multi-agent AI research system that transforms a research question into a structured research report by coordinating multiple specialized AI components.

Instead of relying on a single LLM prompt, the system separates the research process into dedicated stages for searching, reading, writing, and critique.

---

## ✨ Features

- 🔎 **Web Search** — Finds relevant information from the web using Tavily.
- 📖 **Content Extraction** — Scrapes and processes information from discovered sources.
- ✍️ **Report Generation** — Uses an LLM to synthesize collected information into a research report.
- 🧐 **AI Critic** — Reviews the generated report and provides feedback.
- 🔗 **Multi-Agent Pipeline** — Passes information between specialized stages.
- 📚 **Source Visibility** — Displays URLs discovered during the research process.
- 🖥️ **Interactive Streamlit UI** — Provides a clean interface for submitting research queries and viewing results.
- 📥 **Report Download** — Allows generated reports to be downloaded as text files.
- 🔐 **Environment-Based API Keys** — API credentials are stored securely using environment variables.

---

## 🧠 How It Works

The system follows a sequential research pipeline:

```text
                    User Query
                        │
                        ▼
               ┌─────────────────┐
               │   Search Agent  │
               │                 │
               │ Find relevant   │
               │ web sources     │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │   Reader Agent  │
               │                 │
               │ Scrape and      │
               │ extract content │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │   Writer Chain  │
               │                 │
               │ Generate the    │
               │ research report │
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │   Critic Chain  │
               │                 │
               │ Review report   │
               │ and provide     │
               │ feedback        │
               └────────┬────────┘
                        │
                        ▼
                 Final Research
                     Report
