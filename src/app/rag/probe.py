import argparse

from app.config import get_settings
from app.logging import configure_logging
from app.rag.retriever import retrieve


def main() -> None:
    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--k", type=int, default=None)
    args = parser.parse_args()
    passages = retrieve(args.query, k=args.k)
    for p in passages:
        print(f"[{p.score:.3f}] {p.url} | {p.breadcrumbs}")
        print(p.text[:300].replace("\n", " "))
        print("-" * 80)
    if not passages:
        print("no results")


if __name__ == "__main__":
    main()
