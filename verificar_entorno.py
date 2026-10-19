"""Diagnóstico local: --modelos carga BGE-M3 y consulta Qdrant; --sin-descarga usa solo caché."""
import argparse
import importlib
from importlib.metadata import version
import platform
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modelos', action='store_true', help='Probar embeddings reales y Qdrant; puede descargar BGE-M3')
    parser.add_argument('--sin-descarga', action='store_true', help='Con --modelos, exigir pesos ya descargados')
    args = parser.parse_args(argv)
    if args.sin_descarga and not args.modelos:
        parser.error('--sin-descarga requiere --modelos')
    print(f'Python {platform.python_version()} | {platform.system()} {platform.machine()}')
    print(f'Intérprete: {sys.executable}')
    if sys.version_info < (3, 11):
        print('[ERROR] Usa Python 3.11 o superior; recomendamos 3.11 o 3.12.')
        return 1
    missing = False
    for package, module in [('streamlit', 'streamlit'), ('ollama', 'ollama'),
                            ('sentence-transformers', 'sentence_transformers'),
                            ('qdrant-client', 'qdrant_client'), ('python-dotenv', 'dotenv')]:
        try:
            installed = version(package)
            importlib.import_module(module)
            print(f'[OK] {package} {installed}')
        except Exception as exc:
            print(f'[ERROR] {package}: {type(exc).__name__}: {exc}')
            missing = True
    if missing:
        print('Activa tu entorno y ejecuta: python -m pip install -r requirements.txt')
        return 1

    from nikali.config import CHAT_MODEL, EMBED_MODEL, make_client, make_embedder, settings
    from nikali.preflight import check_ollama
    from nikali.rag import Retriever, load_chunks
    errors = 0
    chunks = None
    print(f'LLM: {CHAT_MODEL} | Embeddings: {EMBED_MODEL} | Dispositivo: {settings.EMBED_DEVICE}')
    try:
        chunks = load_chunks()
        if not chunks:
            raise ValueError('El material está vacío.')
        print(f'[OK] Material del libro: {len(chunks)} chunks; {sum(c.partial for c in chunks)} parcial(es).')
    except Exception as exc:
        errors += 1
        print(f'[ERROR] Material: {exc}')
    try:
        check_ollama(make_client(timeout=5))
        print(f'[OK] Ollama responde y tiene {CHAT_MODEL}. Aún no se ha generado una respuesta.')
    except Exception as exc:
        errors += 1
        print(f'[ERROR] {exc}')
    if args.modelos and chunks:
        retriever = None
        try:
            print('Cargando BGE-M3 y probando Qdrant. La primera carga puede tardar...', flush=True)
            encoder = make_embedder(local_files_only=args.sin_descarga)
            retriever = Retriever(chunks, encoder=encoder)
            hits = retriever.search('¿Cuál es la regla de la cadena?')
            if not hits:
                raise ValueError('Qdrant no devolvió resultados.')
            print(f'[OK] Embeddings reales y Qdrant funcionan. Primer resultado: {hits[0].chunk.id}')
        except Exception as exc:
            errors += 1
            print(f'[ERROR] BGE-M3/Qdrant: {type(exc).__name__}: {exc}')
            print('Comprueba la conexión o la caché de Hugging Face, la RAM y las dependencias.')
        finally:
            if retriever is not None:
                retriever.qdrant.close()
    elif not args.modelos:
        print('[PENDIENTE] Pesos BGE-M3: python verificar_entorno.py --modelos')
    print('Diagnóstico terminado. La calidad de Qwen se revisa con evaluar_tutor.py.')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
