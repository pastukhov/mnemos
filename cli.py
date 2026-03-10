import argparse

from core.config import get_settings
from core.logging import setup_logging
from db.session import create_engine, create_session_factory
from embeddings.factory import build_embedder
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
  return parser


def main() -> int:
  parser = build_parser()
  args = parser.parse_args()
  settings = get_settings()
  setup_logging(settings.mnemos_log_level)

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

  if args.command != "ingest":
    parser.error(f"unsupported command: {args.command}")

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

  summary = runner.run_all()
  print(summary.render())
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
