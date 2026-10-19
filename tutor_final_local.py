"""Consola opcional que comparte la lógica del tutor web."""
from nikali.config import make_client
from nikali.index import open_retriever
from nikali.tutor import PROBLEM, STEPS, guided_turn, new_session


def main():
    client = make_client()
    retriever = open_retriever()
    session = new_session()
    print(PROBLEM)
    print(STEPS[0].instruction)
    while session["step"] < len(STEPS):
        answer = input("\nTú (o salir): ")
        if answer.strip().lower() in {"salir", "exit", "quit"}:
            break
        try:
            session = guided_turn(client, retriever, session, answer)
        except Exception as exc:
            print(f"No se completó el turno; se conserva tu progreso. {exc}")
            continue
        print("NIK:", session["messages"][-1]["content"])


if __name__ == "__main__":
    main()
