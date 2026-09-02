# My Book Library

A local Streamlit dashboard for exploring the composition, subjects, languages, and publication history of a personal book collection. It reads `Books_Sept2.xlsx` directly and never writes to the workbook.

For Collection analysis, the administrative/storage labels `archive`, `Box1`, `Box2`, and `Box3` are ignored. They remain unchanged in the source workbook and do not remove their books or any other Collection memberships from the dashboard.

## Run locally

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit will print the local URL in the terminal, normally `http://localhost:8501`.
