from fastapi import FastAPI

app = FastAPI(title="EMR Prototype")


@app.get("/health")
def health():
    return {"status": "ok"}
