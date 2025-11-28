from nicegui import ui
from fastapi import Request, Depends
from pydantic import BaseModel, EmailStr, ValidationError, Field, field_validator
from user_service.models.user import UserRepository, get_user_repository

class _Create(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=1)
    tier: int = Field(ge=1, default=1)

    @field_validator('name', 'password', mode='before')
    @classmethod
    def _strip_and_require(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('must not be empty or whitespace')
        return v
    
@ui.page('/create')
async def create_user_page(request: Request, user_repo: UserRepository = Depends(get_user_repository)):
    with ui.column().classes('w-full h-screen items-center justify-center') as create_user_container:
            create_user_container.visible = True
            with ui.column().classes('items-start mb-6'):
                with ui.card().classes('p-4'):
                    ui.label('Create New User').classes('text-lg font-bold')
                    name_input = ui.input('Name').props('outlined dense').classes('w-64')
                    email_input = ui.input('Email').props('outlined dense').classes('w-64')
                    password_input = ui.input('Password', password=True).props('outlined dense').classes('w-64')
                    tier_input = ui.number('Tier', value=1, min=1).classes('w-32')

                    async def create_user():
                        try:
                            payload = _Create(
                                name=name_input.value,
                                email=email_input.value,
                                password=password_input.value,
                                tier=int(tier_input.value or 1),
                            )
                        except ValidationError as ve:
                            ui.notify(f"Invalid input: {ve.errors()[0]['msg']}", color='negative')
                            return

                        try:
                            await user_repo.create(
                                name=payload.name,
                                email=payload.email,
                                password=payload.password,
                                tier=payload.tier,
                            )
                            ui.notify("User created!", color='positive')
                        except Exception as e:
                            ui.notify(f"Create failed: {e}", color='negative')
                        finally:
                            name_input.value = ''
                            email_input.value = ''
                            password_input.value = ''
                            tier_input.value = 1

                    with ui.row().classes('gap-4 mt-4'):  # row for buttons, small gap
                        ui.button('Create User', on_click=create_user).props('color=primary')
                        ui.button('Return to Homepage', on_click=lambda: ui.run_javascript("window.location.href='http://localhost:5173';")).props('color=secondary')
        