from __future__ import annotations

import json
from contextlib import asynccontextmanager
from functools import partialmethod
from typing import AsyncGenerator
from urllib.parse import urlparse
from curl_cffi.requests import AsyncSession, Session, Response
from .webdriver import WebDriver, WebDriverSession, bypass_cloudflare, get_driver_cookies

class StreamResponse:
    def __init__(self, inner: Response) -> None:
        self.inner: Response = inner

    async def text(self) -> str:
        return await self.inner.atext()

    def raise_for_status(self) -> None:
        self.inner.raise_for_status()

    async def json(self, **kwargs) -> dict:
        return json.loads(await self.inner.acontent(), **kwargs)

    async def iter_lines(self) -> AsyncGenerator[bytes, None]:
        async for line in self.inner.aiter_lines():
            yield line

    async def iter_content(self) -> AsyncGenerator[bytes, None]:
        async for chunk in self.inner.aiter_content():
            yield chunk
            
    async def __aenter__(self):
        inner: Response = await self.inner
        self.inner = inner
        self.request = inner.request
        self.status_code: int = inner.status_code
        self.reason: str = inner.reason
        self.ok: bool = inner.ok
        self.headers = inner.headers
        self.cookies = inner.cookies
        return self
    
    async def __aexit__(self, *args):
        await self.inner.aclose()

class StreamSession(AsyncSession):
    def request(
        self, method: str, url: str, **kwargs
    ) -> StreamResponse:
        return StreamResponse(super().request(method, url, stream=True, **kwargs))

    head = partialmethod(request, "HEAD")
    get = partialmethod(request, "GET")
    post = partialmethod(request, "POST")
    put = partialmethod(request, "PUT")
    patch = partialmethod(request, "PATCH")
    delete = partialmethod(request, "DELETE")
    
def get_session_from_browser(url: str, webdriver: WebDriver = None, proxy: str = None, timeout: int = 120):
    with WebDriverSession(webdriver, "", proxy=proxy, virtual_display=True) as driver:
        bypass_cloudflare(driver, url, timeout)
        cookies = get_driver_cookies(driver)
        user_agent = driver.execute_script("return navigator.userAgent")

    parse = urlparse(url)
    return Session(
        cookies=cookies,
        headers={
            'accept': '*/*',
            'authority': parse.netloc,
            'origin': f'{parse.scheme}://{parse.netloc}',
            'referer': url,
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': user_agent
        },
        proxies={"https": proxy, "http": proxy},
        timeout=timeout,
        impersonate="chrome110"
    )
