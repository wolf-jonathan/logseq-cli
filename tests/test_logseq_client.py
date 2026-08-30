from unittest.mock import MagicMock, patch

from src.logseq_client import LogseqClient


def test_connectivity_check_posts_valid_logseq_request():
    client = MagicMock()
    client.__enter__.return_value = client
    client.post.return_value.status_code = 401

    with patch("src.logseq_client.httpx.Client", return_value=client):
        assert LogseqClient.check_connectivity("http://127.0.0.1:12315/api")

    client.post.assert_called_once_with(
        "http://127.0.0.1:12315/api",
        json={"method": "logseq.App.getCurrentGraph", "args": []},
    )
