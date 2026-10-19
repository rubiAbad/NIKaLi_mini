from nikali.rag import load_chunks

if __name__ == "__main__":
    chunks = load_chunks()
    print(f"Total: {len(chunks)} chunks (mismos que usa la web)")
    for chunk in chunks:
        print(f"\nID: {chunk.id}\nFuente: {chunk.source}\nParcial: {chunk.partial}\n{chunk.text}")
