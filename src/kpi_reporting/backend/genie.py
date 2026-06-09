"""Databricks Genie Conversation API client."""
import asyncio
import httpx
from databricks.sdk import WorkspaceClient
from .logger import logger


class GenieClient:
    """Proxies the Genie Conversation API, keeping auth tokens server-side."""

    def __init__(self, space_id: str):
        self.space_id = space_id
        self._ws = WorkspaceClient()
        self._host = self._ws.config.host.rstrip("/")

    def _auth_headers(self) -> dict[str, str]:
        """Get fresh auth headers using the Databricks SDK."""
        token = self._ws.config.authenticate()
        return {**token, "Content-Type": "application/json"}

    async def _start_conversation(self, client: httpx.AsyncClient, content: str) -> dict:
        """Start a new Genie conversation."""
        resp = await client.post(
            f"{self._host}/api/2.0/genie/spaces/{self.space_id}/start-conversation",
            headers=self._auth_headers(),
            json={"content": content},
        )
        resp.raise_for_status()
        return resp.json()

    async def _create_message(self, client: httpx.AsyncClient, conversation_id: str, content: str) -> dict:
        """Send a follow-up message in an existing conversation."""
        resp = await client.post(
            f"{self._host}/api/2.0/genie/spaces/{self.space_id}/conversations/{conversation_id}/messages",
            headers=self._auth_headers(),
            json={"content": content},
        )
        resp.raise_for_status()
        return resp.json()

    async def _poll_message(self, client: httpx.AsyncClient, conversation_id: str, message_id: str, timeout: float = 120) -> dict:
        """Poll until message status is COMPLETED or FAILED."""
        url = f"{self._host}/api/2.0/genie/spaces/{self.space_id}/conversations/{conversation_id}/messages/{message_id}"
        elapsed = 0.0
        interval = 2.0
        while elapsed < timeout:
            resp = await client.get(url, headers=self._auth_headers())
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status in ("COMPLETED", "EXECUTING_QUERY"):
                return data
            if status == "FAILED":
                return data
            await asyncio.sleep(interval)
            elapsed += interval
        return data

    async def _get_query_result(self, client: httpx.AsyncClient, conversation_id: str, message_id: str, attachment_id: str) -> dict:
        """Fetch the query result for an attachment."""
        resp = await client.get(
            f"{self._host}/api/2.0/genie/spaces/{self.space_id}/conversations/{conversation_id}/messages/{message_id}/query-result/{attachment_id}",
            headers=self._auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def ask(self, content: str, conversation_id: str | None = None) -> dict:
        """
        Ask a question to Genie.

        Returns:
            {
                conversation_id: str,
                message_id: str,
                status: str,
                attachments: [
                    { text: str|None, sql: str|None, columns: list, data_array: list, row_count: int, truncated: bool }
                ]
            }
        """
        async with httpx.AsyncClient(timeout=150) as client:
            # Start or continue conversation
            if conversation_id:
                result = await self._create_message(client, conversation_id, content)
            else:
                result = await self._start_conversation(client, content)

            conv_id = result.get("conversation_id") or conversation_id
            msg_id = result.get("message_id") or result.get("id")
            logger.info(f"Genie message created: conversation={conv_id}, message={msg_id}")

            # Poll for completion
            message = await self._poll_message(client, conv_id, msg_id)
            status = message.get("status", "UNKNOWN")
            logger.info(f"Genie message status: {status}")

            # Extract attachments
            attachments = []
            for att in message.get("attachments", []):
                text_content = att.get("text", {}).get("content") if att.get("text") else None
                sql_content = att.get("query", {}).get("query") if att.get("query") else None
                attachment_id = att.get("id")

                columns = []
                data_array = []
                row_count = 0
                truncated = False

                if attachment_id and att.get("query"):
                    try:
                        qr = await self._get_query_result(client, conv_id, msg_id, attachment_id)
                        stmt_resp = qr.get("statement_response", {})
                        manifest = stmt_resp.get("manifest", {})
                        result_data = stmt_resp.get("result", {})

                        columns = [col.get("name", "") for col in manifest.get("schema", {}).get("columns", [])]
                        data_array = result_data.get("data_array", [])
                        row_count = len(data_array)
                        truncated = row_count >= manifest.get("total_row_count", row_count + 1)
                    except Exception as e:
                        logger.warning(f"Failed to fetch query result for attachment {attachment_id}: {e}")

                attachments.append({
                    "text": text_content,
                    "sql": sql_content,
                    "columns": columns,
                    "data_array": data_array,
                    "row_count": row_count,
                    "truncated": truncated,
                })

            return {
                "conversation_id": conv_id,
                "message_id": msg_id,
                "status": status,
                "attachments": attachments,
            }
