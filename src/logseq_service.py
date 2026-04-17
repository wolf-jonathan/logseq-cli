from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict

from .logseq_client import LogseqClient


class LogseqPage(TypedDict):
    originalName: str
    uuid: NotRequired[str]
    properties: NotRequired[dict]
    journal: NotRequired[bool]  # "journal?" key


def normalize_page(page: dict) -> dict:
    return {
        "name": page.get("originalName") or page.get("name"),
        "uuid": page.get("uuid"),
        "properties": page.get("properties"),
        "isJournal": page.get("journal?"),
    }


class LogseqService:
    def __init__(self, client: LogseqClient) -> None:
        self._client = client

    async def get_all_pages(self, page_number: int = 1, page_size: int = 50) -> dict:
        pages: list = await self._client.call_logseq_api("logseq.Editor.getAllPages", [])
        filtered = [normalize_page(p) for p in pages]
        start = (page_number - 1) * page_size
        return {"pages": filtered[start : start + page_size], "total": len(pages)}

    async def get_page_by_name(self, page_name: str) -> object:
        return await self._client.call_logseq_api("logseq.Editor.getPage", [page_name])

    async def get_page_by_uuid(self, uuid: str) -> object:
        return await self.get_page_by_name(uuid)

    async def create_page(self, page_name: str) -> object:
        return await self._client.call_logseq_api("logseq.Editor.createPage", [page_name])

    async def get_block_by_uuid(self, uuid: str, include_children: bool = False) -> object:
        return await self._client.call_logseq_api(
            "logseq.Editor.getBlock", [uuid, {"includeChildren": include_children}]
        )

    async def get_current_graph(self) -> object:
        return await self._client.call_logseq_api("logseq.App.getCurrentGraph", [])

    async def run_query(
        self, query: str, page_number: int = 1, page_size: int = 50
    ) -> dict:
        result: list = await self._client.call_logseq_api(
            "logseq.DB.datascriptQuery", [query]
        )
        start = (page_number - 1) * page_size
        return {"results": result[start : start + page_size], "total": len(result)}

    async def run_query_raw(self, query: str) -> list:
        return await self._client.call_logseq_api("logseq.DB.datascriptQuery", [query])

    async def run_query_with_inputs(self, query: str, inputs: list) -> list:
        return await self._client.call_logseq_api(
            "logseq.DB.datascriptQuery", [query, *inputs]
        )

    async def get_all_pages_raw(self) -> list:
        return await self._client.call_logseq_api("logseq.Editor.getAllPages", [])

    async def get_all_page_names(self) -> list[str]:
        pages: list = await self._client.call_logseq_api("logseq.Editor.getAllPages", [])
        return sorted(name for p in pages if (name := p.get("originalName") or p.get("name")))

    async def get_page_blocks_tree(self, page_name: str) -> list:
        return await self._client.call_logseq_api(
            "logseq.Editor.getPageBlocksTree", [page_name]
        )

    async def get_page_properties(self, page_name: str) -> dict:
        blocks = await self.get_page_blocks_tree(page_name)
        if not blocks:
            return {}
        first_block = blocks[0]
        if not isinstance(first_block, dict):
            return {}
        properties = first_block.get("properties")
        return properties if isinstance(properties, dict) else {}

    async def create_journal_page(self, date: str) -> object:
        parsed = datetime.strptime(date, "%Y-%m-%d")
        journal_name = parsed.strftime("%Y_%m_%d")
        journal_day = int(parsed.strftime("%Y%m%d"))
        await self.create_page(journal_name)
        pages = await self.get_all_pages_raw()
        for page in pages:
            if page.get("journalDay") == journal_day:
                return page
        raise ValueError(f"Journal page for {date} was not found after creation")

    async def insert_block(
        self,
        src_block_uuid: str,
        content: str,
        opts: dict | None = None,
    ) -> object:
        return await self._client.call_logseq_api(
            "logseq.Editor.insertBlock",
            [src_block_uuid, content, opts or {}],
        )

    async def append_block_in_page(self, page_name: str, content: str) -> object:
        blocks = await self.get_page_blocks_tree(page_name)
        if not blocks:
            return await self.prepend_block_in_page(page_name, content)
        last_block = blocks[-1]
        if not isinstance(last_block, dict) or "uuid" not in last_block:
            return await self.prepend_block_in_page(page_name, content)
        return await self.insert_block(last_block["uuid"], content, opts={"sibling": True})

    async def insert_batch_block(
        self,
        src_block_uuid: str,
        batch: list,
        opts: dict | None = None,
    ) -> object:
        return await self._client.call_logseq_api(
            "logseq.Editor.insertBatchBlock",
            [src_block_uuid, batch, opts or {}],
        )

    async def remove_block(self, uuid: str) -> None:
        await self._client.call_logseq_api("logseq.Editor.removeBlock", [uuid])

    async def update_block(self, uuid: str, content: str) -> object:
        return await self._client.call_logseq_api(
            "logseq.Editor.updateBlock", [uuid, content]
        )

    async def rename_page(self, src_name: str, dest_name: str) -> object:
        return await self._client.call_logseq_api(
            "logseq.Editor.renamePage", [src_name, dest_name]
        )

    async def delete_page(self, page_name: str) -> None:
        await self._client.call_logseq_api("logseq.Editor.deletePage", [page_name])

    async def move_block(
        self, src_uuid: str, target_uuid: str, opts: dict | None = None
    ) -> object:
        return await self._client.call_logseq_api(
            "logseq.Editor.moveBlock", [src_uuid, target_uuid, opts or {}]
        )

    async def prepend_block_in_page(self, page: str, content: str) -> object:
        return await self._client.call_logseq_api(
            "logseq.Editor.prependBlockInPage", [page, content]
        )

    async def set_block_collapsed(self, uuid: str, flag: bool | str) -> None:
        await self._client.call_logseq_api(
            "logseq.Editor.setBlockCollapsed", [uuid, {"flag": flag}]
        )

    async def upsert_block_property(self, uuid: str, key: str, value: object) -> None:
        await self._client.call_logseq_api(
            "logseq.Editor.upsertBlockProperty", [uuid, key, value]
        )

    async def remove_block_property(self, uuid: str, key: str) -> None:
        await self._client.call_logseq_api(
            "logseq.Editor.removeBlockProperty", [uuid, key]
        )

    async def get_block_properties(self, uuid: str) -> dict:
        return await self._client.call_logseq_api(
            "logseq.Editor.getBlockProperties", [uuid]
        )

    async def get_page_linked_references(self, page_name: str) -> list:
        return await self._client.call_logseq_api(
            "logseq.Editor.getPageLinkedReferences", [page_name]
        )

    async def get_pages_from_namespace(self, namespace: str) -> list:
        return await self._client.call_logseq_api(
            "logseq.Editor.getPagesFromNamespace", [namespace]
        )

    async def get_pages_tree_from_namespace(self, namespace: str) -> list:
        return await self._client.call_logseq_api(
            "logseq.Editor.getPagesTreeFromNamespace", [namespace]
        )

