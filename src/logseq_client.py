import httpx
import typer


class LogseqClient:
    OK_STATUS_CODES = (200, 400, 401, 403, 405)

    def __init__(
        self,
        token: str,
        base_url: str,
    ) -> None:
        self._base_url = base_url.strip()
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        self._client = httpx.AsyncClient(timeout=10.0)

    @staticmethod
    def check_connectivity(url: str, verbose: bool = False) -> bool:
        try:
            with httpx.Client(timeout=3) as sync_client:
                response = sync_client.get(url)
                if response.status_code in LogseqClient.OK_STATUS_CODES:
                    return True
                if verbose:
                    typer.echo(
                        f"Error: Logseq responded with unexpected status {response.status_code} "
                        f"at {url}. Is Logseq running with the HTTP plugin enabled?",
                        err=True,
                    )
                return False
        except httpx.ConnectError:
            if verbose:
                typer.echo(
                    f"Error: Cannot connect to Logseq at {url}. "
                    f"Is Logseq running and reachable?",
                    err=True,
                )
            return False
        except httpx.ReadTimeout:
            if verbose:
                typer.echo(
                    f"Error: Connection to Logseq at {url} timed out. "
                    f"Is Logseq running and responsive?",
                    err=True,
                )
            return False

    async def call_logseq_api(self, method: str, args: list) -> object:
        response = await self._client.post(
            self._base_url,
            headers=self._headers,
            json={"method": method, "args": args},
        )
        response.raise_for_status()
        return response.json()
