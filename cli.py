import argparse

from core.config import get_settings
from core.logging import setup_logging
from db.session import create_engine, create_session_factory
from embeddings.factory import build_embedder
from mcp_server.server import run_server as run_mcp_server
from pipelines.ingest.ingest_runner import IngestRunner
from services.memory_service import MemoryService
from vector.qdrant_client import MnemosQdrantClient


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(prog="mnemos")
  subparsers = parser.add_subparsers(dest="command", required=True)

  ingest_parser = subparsers.add_parser("ingest")
  ingest_subparsers = ingest_parser.add_subparsers(dest="ingest_target", required=True)

  questionnaire_parser = ingest_subparsers.add_parser("questionnaire")
  questionnaire_parser.add_argument("path")

  notes_parser = ingest_subparsers.add_parser("notes")
  notes_parser.add_argument("path")

  ingest_subparsers.add_parser("all")

  mcp_parser = subparsers.add_parser("mcp-server")
  mcp_parser.add_argument(
    "--transport",
    choices=("stdio", "streamable-http", "http", "sse"),
    default=None,
  )
  mcp_parser.add_argument("--host", default=None)
  mcp_parser.add_argument("--port", type=int, default=None)
  return parser


def run_ingest_command(args, parser, settings) -> int:
  engine = create_engine(settings.postgres_dsn)
  session_factory = create_session_factory(engine)
  qdrant = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  embedder = build_embedder(settings)
  memory_service = MemoryService(session_factory, qdrant, embedder, settings)
  runner = IngestRunner(memory_service)

  if args.ingest_target == "questionnaire":
    report = runner.run_questionnaire(args.path)
    print(
      "\n".join(
        [
          f"Questionnaire answers ingested: {report.loaded}",
          f"Duplicates skipped: {report.skipped}",
        ]
      )
    )
    return 0

  if args.ingest_target == "notes":
    report = runner.run_notes(args.path)
    print(
      "\n".join(
        [
          f"Notes ingested: {report.loaded}",
          f"Duplicates skipped: {report.skipped}",
        ]
      )
    )
    return 0

  if args.ingest_target != "all":
    parser.error(f"unsupported ingest target: {args.ingest_target}")

  summary = runner.run_all()
  print(summary.render())
  return 0


def main() -> int:
  parser = build_parser()
  args = parser.parse_args()
  settings = get_settings()
  setup_logging(settings.mnemos_log_level)

  if args.command == "ingest":
    return run_ingest_command(args, parser, settings)

  if args.command == "mcp-server":
    run_mcp_server(
      settings=settings,
      transport=args.transport,
      host=args.host,
      port=args.port,
    )
    return 0

  parser.error(f"unsupported command: {args.command}")
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
