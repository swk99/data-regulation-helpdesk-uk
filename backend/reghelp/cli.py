import argparse
import asyncio
import json
from .config import Settings
from .storage import Store
from .models import Ollama, Vectors
from .ingestion import Ingestor
from .agent import Agent


async def run(args):
    s = Settings()
    store, models, vectors = Store(s.data_dir), Ollama(s), Vectors(s)
    ingestor = Ingestor(s, store, models, vectors)
    try:
        if args.command == 'update':
            output = await ingestor.update()
        elif args.command == 'ask':
            output = await Agent(store, models, vectors, ingestor).answer(args.question, args.live)
        else:
            output = store.status()
        print(json.dumps(output, indent=2))
    finally:
        await ingestor.fetcher.close()


def main():
    parser = argparse.ArgumentParser(description='UK regulation evidence helpdesk')
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('update')
    subs.add_parser('status')
    ask = subs.add_parser('ask')
    ask.add_argument('question')
    ask.add_argument('--live', action='store_true')
    asyncio.run(run(parser.parse_args()))


if __name__ == '__main__':
    main()
