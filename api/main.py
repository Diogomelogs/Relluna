import os, uuid, requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from azure.storage.blob import BlobClient

APP_NAME = "relume-api"
CONTAINER_URL = os.environ["AZURE_STORAGE_URL"].rstrip("/")
ACCOUNT_KEY = os.environ["AZURE_STORAGE_KEY"]
VISION_ENDPOINT = os.environ["VISION_ENDPOINT"].rstrip("/")
VISION_KEY = os.environ["VISION_API_KEY"]

app = FastAPI(title="Relume API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    # 1) grava no Blob
    blob_name = f"{uuid.uuid4()}_{file.filename}"
    blob = BlobClient.from_blob_url(f"{CONTAINER_URL}/{blob_name}", credential=ACCOUNT_KEY)
    data = await file.read()
    blob.upload_blob(data, overwrite=True)
    blob_url = f"{CONTAINER_URL}/{blob_name}"

    # 2) chama Vision (descrição + tags + faces)
    analyze_url = f"{VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Description,Tags,Faces"
    headers = {"Ocp-Apim-Subscription-Key": VISION_KEY, "Content-Type": "application/json"}
    payload = {"url": blob_url.replace("/uploads/", "/uploads/")}  # URL do Blob (privado) funciona para Vision somente se público; se privado, pule Vision aqui.
    # Observação: se o contêiner for privado, use Vision com "Read SAS URL". Ver seção 4.

    vision = {"note": "container privado; gere SAS para análise"}  # placeholder seguro
    try:
        r = requests.post(analyze_url, headers=headers, json=payload, timeout=20)
        if r.status_code < 300:
            vision = r.json()
    except Exception:
        pass

    return JSONResponse({"blob": blob_url, "vision": vision})
