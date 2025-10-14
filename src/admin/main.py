import os
from fastapi import Depends
from nicegui import ui, app
#making a comment.
from user_service.models.user import UserRepository, UserSchema, get_user_repository

@ui.page('/')
async def admin_page(user_repo: UserRepository = Depends(get_user_repository)):
    # This dictionary stores if the user is logged in for the current session
    if 'authenticated' not in app.storage.user:
        app.storage.user['authenticated'] = False

    # 1. DEFINE THE PASSWORD DIALOG
    with ui.dialog() as password_dialog, ui.card():
        ui.label('Admin Access Required').classes('text-h6')
        password_input = ui.input('password', password=True)
        ui.button('Submit', on_click=lambda: check_password(password_input.value))
        password_dialog.props('persistent')

    def check_password(password: str):
        if password == os.environ.get('ADMIN_PASSWORD'):
            app.storage.user['authenticated'] = True
            password_dialog.close()
            # Reveal the main content. Delay for dialog close.
            ui.timer(0.1, lambda: main_content.set_visibility(True), once=True)
            ui.notify('Admin Access Granted', color='positive')
        else:
            ui.notify('Incorrect password', color='negative')

    # 2. CREATE THE MAIN CONTENT CONTAINER (initially hidden)
    main_content = ui.column()
    main_content.visible = False
    with main_content:
        ui.label('User Management').classes('text-h4')
        with ui.row().classes('w-full items-center px-4'):
            name_input = ui.input(label='Name')

            async def create() -> None:
                """Creates a new user and refreshes the list."""
                if name_input.value:
                    await user_repo.create(name=name_input.value)
                    ui.notify(f"Created user '{name_input.value}'", color='positive')
                    name_input.value = ""
                    user_list.refresh()
                else:
                    ui.notify('Please enter a name', color='warning')

            ui.button(on_click=create, icon='add')
        @ui.refreshable
        async def user_list(user_repo: UserRepository) -> None:
            user_models = await user_repo.get_all()
            users = [UserSchema.from_db_model(model).model_dump() for model in user_models]

    columns = [{'name': 'name', 'label': 'Name', 'field': 'name', 'required': True, 'align': 'left'}, 
               {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True, 'align': 'left'}, 
               {'name': 'email', 'label': 'Email', 'field': 'email', 'align': 'left'}]
    table = ui.table(columns=columns, rows=users,
                     row_key='name',
                     on_select=toggle_delete_button)
    table.set_selection('multiple')

            def toggle_delete_button(e):
                nonlocal selected
                selected = e.selection
                delete_button.props(remove='disabled' if selected else 'disabled')

@ui.page("/")
async def index(user_repo: UserRepository = Depends(get_user_repository)):
    async def create() -> None:
        try:
            await user_repo.create(name=name.value, email=email.value, password=password.value)
        except:
            pass
        finally:
            name.value = ""
            email.value = ""
            password.value = ""
            user_list.refresh()

    with ui.column().classes('mx-auto'):
        # tailwind
        with ui.row().classes('w-full items-center px-4'):
            name = ui.input(label='Name')
            email = ui.input(label='Email')
            password = ui.input(label='Password')
            ui.button(icon='add').on('click', create)
        await user_list(user_repo)

    # 3. SHOW DIALOG OR CONTENT
    if app.storage.user['authenticated']:
        main_content.set_visibility(True)
    else:
        password_dialog.open()