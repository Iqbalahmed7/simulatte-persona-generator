# Simulatte Persona Generator API

POST /generate
POST /simulate
POST /survey
GET  /report/{cohort_id}
GET  /health

Run: uvicorn src.api.main:app --host 0.0.0.0 --port 8000
