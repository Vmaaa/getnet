import argparse
import json

from app.config import get_settings
from app.graph.builder import build_orchestrator
from app.logging import configure_logging


def main() -> None:
    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--user-id", default=None)
    args = parser.parse_args()
    response = build_orchestrator().handle(args.message, args.user_id)
    print(json.dumps(response.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
