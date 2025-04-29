import random
import string
from typing import Optional

from nicegui import ui, app
from authlib.integrations.starlette_client import OAuthError
from fastapi import Request
from starlette.responses import RedirectResponse

from aam import initialization
from aam.config import CONFIG
from aam.ui.main import UIMainForm
from aam.utilities import load_icon
from aam.initialization import oauth


def main():
    app.on_exception(lambda e: ui.notify(f"Exception: {e}"))
    app.on_startup(initialization.initialize)
    favicon = load_icon()
    secret = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(50))
    ui.run(favicon=favicon, storage_secret=secret)


@app.get('/auth')
async def oidc_authentication(request: Request) -> RedirectResponse:
    try:
        user_data = await oauth.aam_oidc.authorize_access_token(request)
    except OAuthError as e:
        print(f'OAuth error: {e}')
        return RedirectResponse('/')  # or return an error page/message
    app.storage.user['user_data'] = user_data
    return RedirectResponse('/')


@ui.page('/')
async def homepage(request: Request) -> Optional[RedirectResponse]:
    user_data = app.storage.user.get('user_data', None)
    if user_data or CONFIG["oauth"]["auth"] is False:
        UIMainForm()
    else:
        url = request.url_for('oidc_authentication')
        return await oauth.aam_oidc.authorize_redirect(request, url)


main()
