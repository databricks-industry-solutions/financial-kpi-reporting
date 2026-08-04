"""Databricks Genie Conversation API client (via the Databricks SDK)."""
import asyncio
from datetime import timedelta

from databricks.sdk import WorkspaceClient

from .logger import logger

# Cap how long we wait for a Genie message to complete (the SDK waiter defaults
# to 20 min, far too long for an interactive endpoint).
_WAIT_TIMEOUT = timedelta(seconds=150)


class GenieClient:
    """Proxies the Genie Conversation API via the typed Databricks SDK (`w.genie`),
    keeping auth server-side. The SDK calls are synchronous, so they run in a worker
    thread to avoid blocking the async event loop."""

    def __init__(self, space_id: str):
        self.space_id = space_id
        self._ws = WorkspaceClient()

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
        genie = self._ws.genie

        # Start or continue the conversation. The *_and_wait helpers poll internally
        # until the message reaches COMPLETED (raising on FAILED/timeout); run them off
        # the event loop. We catch failures and surface them as a FAILED result rather
        # than a 500 — matching the previous client's graceful behavior.
        conv_id_early: str | None = conversation_id
        msg_id_early: str | None = None
        try:
            if conversation_id:
                waiter = await asyncio.to_thread(
                    genie.create_message, self.space_id, conversation_id, content,
                )
            else:
                waiter = await asyncio.to_thread(
                    genie.start_conversation, self.space_id, content,
                )
            # Capture IDs from the initial response before blocking on the wait,
            # so we can fetch the message's .error field on failure.
            init = waiter.response
            conv_id_early = init.conversation_id or conversation_id
            msg_id_early = init.message_id

            message = await asyncio.to_thread(waiter.result, timeout=_WAIT_TIMEOUT)
        except Exception as e:
            # Fetch the raw message to surface Genie's own error text rather than
            # the opaque SDK wrapper message ("failed to reach COMPLETED").
            error_detail = str(e)
            try:
                if conv_id_early and msg_id_early:
                    raw = await asyncio.to_thread(
                        genie.get_message, self.space_id, conv_id_early, msg_id_early,
                    )
                    if raw.error:
                        # raw.error is a MessageError dataclass; .error holds the string
                        error_detail = raw.error.error or str(raw.error)
            except Exception:
                pass
            logger.warning(f"Genie message did not complete: {type(e).__name__}: {error_detail}")
            return {
                "conversation_id": conv_id_early,
                "message_id": msg_id_early,
                "status": "FAILED",
                "error": error_detail,
                "attachments": [],
            }

        conv_id = message.conversation_id or conversation_id
        msg_id = message.message_id or message.id
        status = message.status.value if message.status else "COMPLETED"
        logger.info(f"Genie message {msg_id} (conversation {conv_id}) status: {status}")

        attachments = []
        for att in message.attachments or []:
            text_content = att.text.content if att.text else None
            sql_content = att.query.query if att.query else None

            columns: list[str] = []
            data_array: list = []
            row_count = 0
            truncated = False

            if att.attachment_id and att.query and conv_id and msg_id:
                try:
                    qr = await asyncio.to_thread(
                        genie.get_message_attachment_query_result,
                        self.space_id, conv_id, msg_id, att.attachment_id,
                    )
                    sr = qr.statement_response
                    if sr is not None:
                        manifest = sr.manifest
                        if manifest and manifest.schema and manifest.schema.columns:
                            columns = [c.name or "" for c in manifest.schema.columns]
                        if sr.result and sr.result.data_array:
                            data_array = sr.result.data_array
                        row_count = len(data_array)
                        truncated = bool(manifest.truncated) if manifest else False
                except Exception as e:
                    logger.warning(f"Failed to fetch query result for attachment {att.attachment_id}: {e}")

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
