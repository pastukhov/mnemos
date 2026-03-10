import argparse

from core.config import get_settings
from core.logging import setup_logging
from db.session import create_engine, create_session_factory
from embeddings.factory import build_embedder
from mcp_server.server import run_server as run_mcp_server
from pipelines.extract.fact_llm_client import build_fact_llm_client
from pipelines.extract.fact_runner import FactExtractionRunner
from pipelines.governance.candidate_runner import CandidateRunner
from pipelines.ingest.ingest_runner import IngestRunner
from pipelines.reflect.reflection_llm_client import build_reflection_llm_client
from pipelines.reflect.reflection_runner import ReflectionRunner
from services.memory_governance_service import MemoryGovernanceService
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

  extract_parser = subparsers.add_parser("extract")
  extract_subparsers = extract_parser.add_subparsers(dest="extract_target", required=True)
  extract_facts_parser = extract_subparsers.add_parser("facts")
  extract_facts_parser.add_argument("--domain", default="self")

  reflect_parser = subparsers.add_parser("reflect")
  reflect_subparsers = reflect_parser.add_subparsers(dest="reflect_target", required=True)
  reflect_build_parser = reflect_subparsers.add_parser("build")
  reflect_build_parser.add_argument("--domain", default="self")
  reflect_build_parser.add_argument("--theme", default=None)

  candidates_parser = subparsers.add_parser("candidates")
  candidates_subparsers = candidates_parser.add_subparsers(dest="candidates_target", required=True)
  candidates_list_parser = candidates_subparsers.add_parser("list")
  candidates_list_parser.add_argument("--status", default=None)
  candidates_list_parser.add_argument("--domain", default=None)
  candidates_list_parser.add_argument("--kind", default=None)
  candidates_accept_parser = candidates_subparsers.add_parser("accept")
  candidates_accept_parser.add_argument("candidate_id")
  candidates_reject_parser = candidates_subparsers.add_parser("reject")
  candidates_reject_parser.add_argument("candidate_id")
  candidates_reject_parser.add_argument("--reason", required=True)

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


def run_extract_command(args, parser, settings) -> int:
  engine = create_engine(settings.postgres_dsn)
  session_factory = create_session_factory(engine)
  qdrant = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  embedder = build_embedder(settings)
  memory_service = MemoryService(session_factory, qdrant, embedder, settings)
  llm_client = build_fact_llm_client(settings)
  runner = FactExtractionRunner(memory_service, llm_client, settings)

  if args.extract_target != "facts":
    parser.error(f"unsupported extract target: {args.extract_target}")

  report = runner.run(domain=args.domain)
  print(report.render())
  return 0


def run_reflect_command(args, parser, settings) -> int:
  engine = create_engine(settings.postgres_dsn)
  session_factory = create_session_factory(engine)
  qdrant = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  embedder = build_embedder(settings)
  memory_service = MemoryService(session_factory, qdrant, embedder, settings)
  llm_client = build_reflection_llm_client(settings)
  runner = ReflectionRunner(memory_service, llm_client, settings)

  if args.reflect_target != "build":
    parser.error(f"unsupported reflect target: {args.reflect_target}")

  report = runner.run(domain=args.domain, theme=args.theme)
  print(report.render())
  return 0


def run_candidates_command(args, parser, settings) -> int:
  engine = create_engine(settings.postgres_dsn)
  session_factory = create_session_factory(engine)
  qdrant = MnemosQdrantClient(
    url=settings.qdrant_url,
    vector_size=settings.qdrant_vector_size,
    timeout_seconds=settings.qdrant_timeout_seconds,
  )
  embedder = build_embedder(settings)
  memory_service = MemoryService(session_factory, qdrant, embedder, settings)
  governance_service = MemoryGovernanceService(session_factory)

  if args.candidates_target == "list":
    items = governance_service.list_candidates(status=args.status, domain=args.domain, kind=args.kind)
    for item in items:
      print(f"{item.id}\t{item.status}\t{item.domain}\t{item.kind}\t{item.statement}")
    return 0

  if args.candidates_target == "accept":
    decision = CandidateRunner(governance_service, memory_service).accept(args.candidate_id)
    print(f"Candidate: {decision.candidate.id}")
    print(f"Status: {decision.candidate.status}")
    if decision.merged_item is not None:
      print(f"Merged item: {decision.merged_item.id}")
    if decision.validation_errors:
      print("Validation errors:")
      for error in decision.validation_errors:
        print(f"- {error}")
    return 0

  if args.candidates_target == "reject":
    candidate = governance_service.reject_candidate(args.candidate_id, reason=args.reason)
    print(f"Candidate: {candidate.id}")
    print(f"Status: {candidate.status}")
    return 0

  parser.error(f"unsupported candidates target: {args.candidates_target}")
  return 1


def main() -> int:
  parser = build_parser()
  args = parser.parse_args()
  settings = get_settings()
  setup_logging(settings.mnemos_log_level)

  if args.command == "ingest":
    return run_ingest_command(args, parser, settings)

  if args.command == "extract":
    return run_extract_command(args, parser, settings)

  if args.command == "reflect":
    return run_reflect_command(args, parser, settings)

  if args.command == "candidates":
    return run_candidates_command(args, parser, settings)

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
