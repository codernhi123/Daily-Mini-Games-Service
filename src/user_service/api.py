from datetime import datetime, timezone
import os
#from typing import List
from fastapi import FastAPI, Depends, Response, HTTPException # noqa: F401
from sqlalchemy.orm import Session # noqa: F401
from sqlalchemy.exc import IntegrityError
# from pydantic import TypeAdapter
import logging
from nicegui import ui
from admin import main # noqa: F401
from dotenv import load_dotenv
from user_service.auth.jwt_helper import create_access_token
from .models.user import AuthRequest, AuthResponse, DeauthRequest, UserRepository, UserSchemaCreate, UserSchemaReturn, UserSchemaUpdate, get_user_repository, password_verification

logger = logging.getLogger('uvicorn.error')
app = FastAPI()
load_dotenv()

@app.post("/users/", status_code=201)
async def create_user(user: UserSchemaCreate, response: Response, user_repo: UserRepository = Depends(get_user_repository)):
    try:
        new_user = await user_repo.create_with_id(user.name, user.id, user.email, user.password) #can use without id but then we got to change some tests, so leaving as is works for both functions and the local admin
        return {"user": UserSchemaReturn.from_db_model(new_user)}
    except IntegrityError:
        response.status_code = 409
        return {"detail": "Item already exists"}
    except AssertionError:
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

@app.post("/v2/authentications")
async def become_authenticated(auth_request: AuthRequest, user_repo: UserRepository = Depends(get_user_repository),):
    user = await user_repo.get_by_name(auth_request.name)

    if not user:
        raise HTTPException(
            status_code=401, detail="Invalid credentials"
        )
    if not password_verification(auth_request.password, user.password):
        raise HTTPException(
            status_code=401, detail="Invalid credentials"
        )
    
    try:
        expiry_dt = datetime.strptime(auth_request.expiry, "%Y-%m-%d %H:%M:%S")
        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400,detail="Expiry must be in 'YYYY-MM-DD HH:MM:SS' format in UTC Time")

    now = datetime.now(timezone.utc)
    if expiry_dt <= now:
        raise HTTPException(status_code=400, detail="Expiry must be in the future, time is calculated based on UTC time.")

    access_token = create_access_token(user.id, expiry_dt)

    return AuthResponse(
        jwt=access_token
    )

# @app.delete("/v2/authentications")
# async def delete_authentication(jwt_request: DeauthRequest):
#     try:
#         payload = validate_jwt(jwt_request.jwt)
#     except InvalidTokenError:
#         raise HTTPException(status_code=401, detail="Invalid JWT")

#     revoke_jwt(jwt_request.jwt)

#     return {"detail": "JWT successfully revoked"}

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
