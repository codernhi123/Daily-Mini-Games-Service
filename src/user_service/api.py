import os
from typing import List
from fastapi import FastAPI, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import TypeAdapter
import logging
from nicegui import ui
from admin import main
from dotenv import load_dotenv
from .models.user import UserRepository, UserSchemaCreate, UserSchemaReturn, UserSchemaUpdate, get_user_repository, password_hash, password_verification
# from .models.user import UserRepository, UserSchema, get_user_repository, password_hash, password_verification

logger = logging.getLogger('uvicorn.error')
app = FastAPI()
load_dotenv()

@app.post("/users/", status_code=201)
async def create_user(user: UserSchemaCreate, response: Response, user_repo: UserRepository = Depends(get_user_repository)):
    try:
        new_user = await user_repo.create_with_id(user.name, user.id, user.email, user.password) #can use without id but then we got to change some tests, so leaving as is works for both functions and the local admin
        return {"user": UserSchemaReturn.from_db_model(new_user)}
    except IntegrityError as e:
        response.status_code = 409
        return {"detail": "Item already exists"}
    except AssertionError as e:
        response.status_code = 422
        return {"detail": "Empty fields not allowed"}

@app.post("/users/{id}")
async def delete_user(id: int, delete: UserSchemaUpdate, user_repo: UserRepository = Depends(get_user_repository)):
    
    if not delete.password: 
        raise HTTPException(status_code=401, detail="Password required for deletion")
    
    user = await user_repo.get_by_id(id)
    if not user: 
        raise HTTPException(status_code=404, detail="User not found")
    
    if not password_verification(delete.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password for deletion")

    await user_repo.delete_by_id(user.id)
    return {"message": f"User '{user.id}' deleted successfully."}

@app.get("/all_users/")
async def list_users(user_repo: UserRepository = Depends(get_user_repository)):

    user_models = await user_repo.get_all()
    users = []
    for model in user_models:
        users.append(UserSchemaReturn.from_db_model(model))
    return {'users': users}

@app.get("/users/{name}")
async def get_user(name: str, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_name(name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchemaReturn.from_db_model(user)}

@app.get("/users_by_id/{id}")
async def get_user_by_id(id: int, user_repo: UserRepository = Depends(get_user_repository)):
    user = await user_repo.get_by_id(id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": UserSchemaReturn.from_db_model(user)}

@app.put("/users/{id}")
async def update_user(id: int, updates: UserSchemaUpdate, user_repo: UserRepository = Depends(get_user_repository)):
    
    if not updates.password: 
        raise HTTPException(status_code=401, detail="Password required for update")
    
    user = await user_repo.get_by_id(id)
    if not user: 
        raise HTTPException(status_code=404, detail="User not found")
    
    if not password_verification(updates.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid password for update")
    
    try:
        if updates.new_password:
            update_user = await user_repo.update_password(id, updates.new_password)
            return {"user": UserSchemaReturn.from_db_model(update_user)}
        
        update_user = await user_repo.update_user(id, name=updates.name, email=updates.email)
        return {"user": UserSchemaReturn.from_db_model(update_user)} 
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

ui.run_with(app,
            mount_path="/admin",
            favicon="👤",
            title="User Admin",
            storage_secret=os.getenv('STORAGE_SECRET'))
