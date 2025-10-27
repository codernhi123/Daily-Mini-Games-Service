import os
#import random
import logging
#import copy
#from contextlib import contextmanager

from fastapi import Depends
from nicegui import ui, app
#from pydantic import parse_obj_as

from user_service.models.user import UserRepository, UserSchemaReturn, get_user_repository

logger = logging.getLogger('uvicorn.error')

@ui.refreshable
async def user_list(user_repo: UserRepository) -> None:
    user_models = await user_repo.get_all()
    users = [UserSchemaReturn.from_db_model(model).model_dump() for model in user_models]

    ui.label("All Users")

    selected = []

    async def delete():
        nonlocal selected
        for user in selected:
            result = await user_repo.delete(user['name'])
            if getattr(result, 'rowcount', 0) > 0:
                ui.notify(f"Deleted user '{user['name']}'")
            else:
                ui.notify(f"Unable to delete user '{user['name']}'")

        user_list.refresh()

    button = ui.button(on_click=delete, icon='delete')
    button.disable()

    def toggle_delete_button(e):
        nonlocal selected
        selected = e.selection
        if len(selected) > 0:
            button.enable()
        else:
            button.disable()

    columns = [
        {'name': 'name', 'label': 'Name',  'field': 'name',  'required': True, 'align': 'left'},
        {'name': 'id',   'label': 'ID',    'field': 'id',    'required': True, 'align': 'left'},
        {'name': 'email','label': 'Email', 'field': 'email', 'align': 'left'},
        {'name': 'tier','label': 'Tier', 'field': 'tier', 'align': 'left'},
    ]
    table = ui.table(
        columns=columns,
        rows=users,
        row_key='name',
        on_select=toggle_delete_button,
    )
    table.set_selection('multiple')


#page with password gate
@ui.page("/")
async def index(user_repo: UserRepository = Depends(get_user_repository)):

    # session flag
    if 'authenticated' not in app.storage.user:
        app.storage.user['authenticated'] = False

    # password dialogue
    with ui.dialog() as password_dialog, ui.card():
        ui.label('Admin Access Required').classes('text-h6')
        pwd_input = ui.input('password', password=True)
        ui.button(
            'Submit',
            on_click=lambda: check_password(pwd_input.value)
        )
        password_dialog.props('persistent')

    def check_password(pw: str) -> None:
        if pw == os.environ.get('ADMIN_PASSWORD'):
            app.storage.user['authenticated'] = True
            password_dialog.close()
            # reveal 
            ui.timer(0.1, lambda: main_content.set_visibility(True), once=True)
            ui.notify('Admin Access Granted', color='positive')
        else:
            ui.notify('Incorrect password', color='negative')

    # hidden until authenticated
    main_content = ui.column().classes('mx-auto')
    main_content.visible = False

    with main_content:
        async def create() -> None:
            try:
                await user_repo.create(name=name.value, email=email.value, password=password.value, tier=int(tier.value))
            except Exception:
                pass
            finally:
                name.value = ""
                email.value = ""
                password.value = ""
                tier.value = 1
                user_list.refresh()

        with ui.row().classes('w-full items-center px-4'):
            name = ui.input(label='Name') 
            email = ui.input(label='Email')
            password = ui.input(label='Password')
            tier = ui.number(label='Tier', value=1, min=1)
            ui.button(icon='add').on('click', create)

        await user_list(user_repo)

    if app.storage.user['authenticated']:
        main_content.set_visibility(True)
    else:
        password_dialog.open()
