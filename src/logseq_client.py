import httpx


class LogseqClient:
    def __init__(
        self,
        token: str,
        base_url: str,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        self._client = httpx.AsyncClient(timeout=10.0)

    async def call_logseq_api(self, method: str, args: list) -> object:
        response = await self._client.post(
            self._base_url,
            headers=self._headers,
            json={"method": method, "args": args},
        )
        response.raise_for_status()
        return response.json()
