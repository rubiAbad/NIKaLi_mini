"""Solo para quien prepara material. Los usuarios cargan el paquete incluido en Git."""
import argparse
from nikali.config import PREPARED_PATH
from nikali.index import prepare_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recrear', action='store_true', help='Regenerar el paquete tras cambios de material/modelo')
    args = parser.parse_args()
    print('Preparando o comprobando el paquete compartido...', flush=True)
    prepared = prepare_index(recreate=args.recrear)
    print(f'Listo: {PREPARED_PATH}\n{len(prepared.chunks)} chunks y embeddings guardados. SHA256: {prepared.digest}')
    print('Comparte este archivo junto con el código y el Markdown. Tus compañeras no deben repetir este comando.')


if __name__ == '__main__':
    main()
