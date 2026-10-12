import argparse
import json
from .db import migrate
from .catalog import import_catalog, load_demos, IntegrationError

def main():
    parser = argparse.ArgumentParser(description='RetroVault operations')
    parser.add_argument('command', choices=['migrate', 'import', 'demos', 'tick', 'worker'])
    parser.add_argument('--initial', action='store_true')
    parser.add_argument('--enable-embeds', action='store_true', help='Use somente após verificar compatibilidade das demonstrações.')
    args = parser.parse_args()
    if args.command=='import':
        if not args.initial:
            parser.error('Expansão disponível somente no painel administrativo.')
        migrate()
        from .db import connect
        with connect() as db:
            if db.execute('SELECT 1 FROM offers LIMIT 1').fetchone():
                parser.error('Carga inicial exige catálogo vazio; use o painel para adicionar jogos.')
    migrate()
    if args.command == 'migrate':
        print('Migrações aplicadas.')
    elif args.command == 'import':
        try: print(json.dumps(import_catalog(initial=args.initial)))
        except IntegrationError as e: print(str(e)); raise SystemExit(1)
    elif args.command == 'demos':
        print(json.dumps(load_demos(args.enable_embeds)))
    else:
        from .worker import tick, run
        if args.command == 'tick': print(json.dumps(tick(), default=str))
        else: run()

if __name__ == '__main__':
    main()
