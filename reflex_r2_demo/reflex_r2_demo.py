"""reflex-r2-upload demo application entry."""

from __future__ import annotations

import reflex as rx
import reflex_r2_upload as r2
from dotenv import load_dotenv
from reflex_r2_demo.demo_auth import demo_presign_guard
from reflex_r2_demo.pages.auth.page import page as auth_page
from reflex_r2_demo.pages.basic.page import page as basic_page
from reflex_r2_demo.pages.home.page import page as home_page
from reflex_r2_demo.pages.multi.page import page as multi_page
from reflex_r2_demo.pages.private_read.page import page as private_read_page
from reflex_r2_demo.pages.shared_callback.page import page as shared_callback_page

load_dotenv()

app = rx.App()

app.add_page(home_page, route="/")
app.add_page(basic_page, route="/examples/basic")
app.add_page(multi_page, route="/examples/multi")
app.add_page(shared_callback_page, route="/examples/shared-callback")
app.add_page(private_read_page, route="/examples/private-read")
app.add_page(auth_page, route="/examples/auth")

r2.wrap_app(app, presign_guard=demo_presign_guard)
