from fastapi import FastAPI
from app.route.erp import router

app = FastAPI(title="Mock ERP Service")

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "healthy"}