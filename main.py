from fastapi import FastAPI

from database import Base, engine
from routers import movies

app = FastAPI(title="Entertainment API", version="0.1.0")

Base.metadata.create_all(bind=engine)

app.include_router(movies.router)
