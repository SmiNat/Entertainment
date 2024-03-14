from fastapi import FastAPI

from database import Base, engine

app = FastAPI(title="Entertainment API", version="0.1.0")

Base.metadata.create_all(bind=engine)
