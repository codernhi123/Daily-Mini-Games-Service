from typing import List
from fastapi import FastAPI, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import TypeAdapter
import logging

from admin.main import ui
from .models.user import UserRepository, UserSchema, get_user_repository

logger = logging.getLogger('uvicorn.error')
app = FastAPI()

@app.post("/users/", status_code=201)
async def create_user(user: UserSchema, response: Response, user_repo: UserRepository = Depends(get_user_repository)):
    print("hi")


@app.get("/all_users/")
async def list_users(user_repo: UserRepository = Depends(get_user_repository)):

    user_models = await user_repo.get_all()

@app.get("/users/{name}")
async def get_user(name: str, user_repo: UserRepository = Depends(get_user_repository)):
    print("hi")
# @app.get("/users/{name}")
# async def get_user(name: str, response: Response, user_repo: UserRepository = Depends(get_user_repository)):
#     try: 
#         user = await user_repo.get_by_name(name)
#     except AssertionError as e:
#         response.status_code = 404
#         return {"detail": "User not found"}
#     return {"user": user}

ui.run_with(app,
            mount_path="/admin",
            favicon="👤",
            title="User Admin")
