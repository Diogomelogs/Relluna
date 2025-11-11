import os, uuid, requests
from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from fastapi.responses import JSONResponse
from azure.storage.blob import BlobClient
import openai

# Configurações do ambiente
APP_NAME = "relume-api"
CONTAINER_URL = os.environ["AZURE_STORAGE_URL"].rstrip("/")
ACCOUNT_KEY = os.environ["AZURE_STORAGE_KEY"]
VISION_ENDPOINT = os.environ["VISION_ENDPOINT"].rstrip("/")
VISION_KEY = os.environ["VISION_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_ENDPOINT = os.environ["OPENAI_ENDPOINT"]

# Inicializa API FastAPI
app = FastAPI(title="Relume API", version="0.1.1")

# Inicializa cliente OpenAI via Azure
openai.api_type = "azure"
openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_ENDPOINT
openai.api_version = "2023-05-15"

@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    blob_name = f"{uuid.uuid4()}_{file.filename}"
    blob = BlobClient.from_blob_url(f"{CONTAINER_URL}/{blob_name}", credential=ACCOUNT_KEY)
    data = await file.read()
    blob.upload_blob(data, overwrite=True)
    blob_url = f"{CONTAINER_URL}/{blob_name}"

    analyze_url = f"{VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Description,Tags,Faces"
    headers = {"Ocp-Apim-Subscription-Key": VISION_KEY, "Content-Type": "application/json"}
    payload = {"url": blob_url}
    
    vision = {"note": "container privado; gere SAS para análise"}
    try:
        r = requests.post(analyze_url, headers=headers, json=payload, timeout=20)
        if r.status_code < 300:
            vision = r.json()
    except Exception:
        pass

    return JSONResponse({"blob": blob_url, "vision": vision})

@app.post("/narrate")
async def narrate(data: dict = Body(...)):
    try:
        tags = ", ".join(data.get("tags", []))
        prompt = f"Crie uma narrativa curta e emocional sobre uma lembrança que envolve: {tags}."
        
        response = openai.ChatCompletion.create(
            engine="gpt-35-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120
        )
        
        text = response.choices[0].message["content"].strip()
        return {"narrative": text}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
