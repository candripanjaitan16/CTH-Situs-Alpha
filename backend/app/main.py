from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.colab import router as colab_router
from app.database import init_db
from app.datasets import router as datasets_router
from app.drive_auth import check_drive_connection
from app.projects import router as projects_router
from app.model_testing import router as model_testing_router


app = FastAPI(
    title="ChanThecno Training Hub",
    version="1.0.0",
)

init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(colab_router)
app.include_router(datasets_router)
app.include_router(model_testing_router)


@app.get("/", tags=["General"])
def home():
    return {
        "status": "success",
        "message": "ChanThecno Training Hub API berjalan",
    }


@app.get("/api/hello", tags=["General"])
def hello():
    return {
        "message": "ChanThecno Training Hub Run!",
    }


@app.get("/api/connections/google-drive", tags=["Connections"])
def google_drive_status():
    return check_drive_connection()
