from fastapi import FastAPI

from database import Base, engine
from routers import movies, auth, users

app = FastAPI(title="Entertainment API", version="0.1.0")

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(users.router)
