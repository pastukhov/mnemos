from __future__ import annotations

from fastmcp import FastMCP

from core.config import Settings, get_settings
from core.logging import get_logger, setup_logging
from mcp_server.client import MnemosRestClient
from mcp_server.tools import register_tools

logger = get_logger(__name__)


def build_mcp_server(
  settings: Settings | None = None,
  client: MnemosRestClient | None = None,
) -> FastMCP:
  settings = settings or get_settings()
  mcp = FastMCP(
    "mnemos",
    instructions="Query and write Mnemos memory through the Mnemos REST gateway.",
  )
  rest_client = client or MnemosRestClient(
    base_url=settings.mnemos_url,
    timeout_seconds=settings.mnemos_timeout_seconds,
  )
  register_tools(mcp, rest_client)
  return mcp


def run_server(
  *,
  settings: Settings | None = None,
  transport: str | None = None,
  host: str | None = None,
  port: int | None = None,
) -> None:
  settings = settings or get_settings()
  setup_logging(settings.mnemos_log_level)
  selected_transport = transport or settings.mcp_server_transport
  server = build_mcp_server(settings=settings)

  logger.info(
    "starting mcp server",
    extra={
      "event": "mcp_server_start",
      "transport": selected_transport,
      "mnemos_url": settings.mnemos_url,
      "host": host or settings.mcp_server_host,
      "port": port or settings.mcp_server_port,
    },
  )

  if selected_transport == "stdio":
    server.run(
      transport="stdio",
      show_banner=False,
      log_level=settings.mnemos_log_level.lower(),
      stateless=True,
    )
    return

  server.run(
    transport=selected_transport,
    host=host or settings.mcp_server_host,
    port=port or settings.mcp_server_port,
    show_banner=False,
    log_level=settings.mnemos_log_level.lower(),
    stateless=True,
  )


if __name__ == "__main__":
  run_server()
