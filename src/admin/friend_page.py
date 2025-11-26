import os
from typing import List, Dict, Any
from nicegui import ui, app
import httpx

API_BASE = os.getenv('FRIENDS_API_BASE', 'http://localhost:8000')

FRIENDS_URL = f"{API_BASE}/v2/users"

async def get_user_id(path: str, token: str):
    if not token:
        return None
    params = {'token': token} 
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        response = await client.get(path, params=params) 
        if response.status_code >= 400:
            return None

        if not response.content: 
            return None
        else:
            user_data = response.json()
            return user_data.get('id')
    
    
async def api_request(method: str, path: str, token: str, json_data: dict = None, params: dict = None):
    if params is None:
        params = {}
    if token:
        params['token'] = token

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as client:
        response = await client.request(method, path, json=json_data, params=params)

        if response.status_code >= 400:
            try:
                msg = response.json().get('detail') or response.text
            except Exception:
                msg = response.text
            raise RuntimeError(msg)

        return response.json() if response.content else {}
    
async def api_get(path, token, params = None):
    return await api_request('GET', path, token, params=params)

async def api_post(path, token, json = None, params = None):
    return await api_request('POST', path, token, json_data=json, params=params)

async def api_put(path, token, json = None, params = None):
    return await api_request('PUT', path, token, json_data=json, params=params)

@ui.page('/friends')
def friends_page():
    ui.label('Friends').classes('text-2xl font-bold mb-4')
    token = app.storage.user.get('token')
    current_user = get_user_id("/v2/authentications/me", token)

    if not token or not current_user:
        ui.label('Log in to be friends with other.').classes('text-red-500 text-xl')
        return
    
    ui.label(f'Friend System (User ID: {current_user})').classes('text-2xl font-bold mb-4')
    
    # --- send request ---
    with ui.row().classes('items-end gap-2 mb-6'):
        other_user_input = ui.input('Send request to... (User ID)').props('outlined dense').classes('w-64')

        async def send():
            target_id_str = (other_user_input.value or '').strip()
            if not target_id_str:
                ui.notify('Enter an ID', color='warning')
                return
            try:
                target_id = int(target_id_str)
            except ValueError:
                ui.notify('ID must be a number', color='negative')
                return
            if target_id == current_user:
                ui.notify('Cannot add yourself', color='warning')
                return
            
            try:
                await api_post(
                    path=f"/v2/users/{current_user}/friend-requests/", 
                    token=token, 
                    json={'other': target_id}
                )
                ui.notify('Request sent', color='positive')
                other_user_input.value = ''
                await load_pending()
            except Exception as e:
                ui.notify(str(e), color='negative')

        ui.button('Send request', on_click=send).props('color=primary')

    # --- pending table ---
    pending_rows: List[Dict[str, Any]] = []
    pending_table = ui.table(
        columns=[
            {'name': 'id', 'label': 'ID', 'field': 'id'},
            {'name': 'from', 'label': 'From', 'field': 'from'},
            {'name': 'to', 'label': 'To', 'field': 'to'},
            {'name': 'status', 'label': 'Status', 'field': 'status'},
            {'name': 'created_at', 'label': 'Created', 'field': 'created_at'},
        ],
        rows=pending_rows,
        row_key='id',
        selection='single',
    ).classes('w-full mb-2')

    async def load_pending():
        try:
            data = await api_get(
                path=f"/v2/users/{current_user}/friend-requests/", 
                token=token,
                params={'q': 'incoming'}
            )
            # normalize dict -> list if API returns a single object
            rows = [data] if isinstance(data, dict) else (data or [])
            pending_table.rows = rows
            pending_table.update()
        except Exception as e:
            ui.notify(f'Failed to load pending: {e}', color='negative')

    # --- friends list ---
    friends_list = ui.list().classes('w-full')

    async def load_friends():
        try:
            data = await api_get(f"/v2/users/{current_user}/friends", token=token)
            # ["bob"] or {"value": ["bob"], "Count": 1}
            if isinstance(data, dict):
                items = data.get('value') or data.get('friends') or []
            elif isinstance(data, list):
                items = data
            else:
                items = []

            friends_list.clear()
            with friends_list:
                if not items:
                    ui.item('No friends yet.')
                else:
                    for f in items:
                        ui.item(str(f))
            friends_list.update()
        except Exception as e:
            ui.notify(f'Failed to load friends: {e}', color='negative')

    async def accept_selected():
        if not pending_table.selected:
            ui.notify('Select a pending request first', color='warning')
            return

        row = pending_table.selected[0]
        requester_id = row['from']

        try:
            await api_put(
                path=f"/v2/users/{current_user}/friend-requests/{requester_id}/",
                token=token
            )
            ui.notify('Accepted', color='positive')
            await load_pending()
            await load_friends()
        except Exception as e:
            ui.notify(f'Accept failed: {e}', color='negative')

    with ui.row().classes('gap-2 mb-8'):
        ui.button('Refresh pending', on_click=load_pending)
        ui.button('Accept selected', on_click=accept_selected).props('color=positive')

    with ui.row().classes('gap-2'):
        ui.button('Refresh friends', on_click=load_friends)

    ui.timer(0.1, load_pending, once=True)
    ui.timer(0.1, load_friends, once=True)
