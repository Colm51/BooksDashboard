# My Book Library

A local Streamlit dashboard for exploring the composition, subjects, languages, and publication history of a personal book collection. It reads `Books_Sept2.xlsx` directly and never writes to the workbook.

## Run locally

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print the local URL in the terminal, normally `http://localhost:8501`.
