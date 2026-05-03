from search import search_prompt

def main():
    chain = search_prompt()

    if not chain:
        print("Não foi possível iniciar o chat. Verifique os erros de inicialização.")
        return

    print("\n💬 Chat — digite 'sair' para encerrar\n")
    print("-" * 50)

    while True:
        try:
            question = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break

        if not question:
            continue

        if question.lower() in {"sair", "exit", "quit", "q"}:
            print("Até logo!")
            break

        answer = chain(question)

        print("\nAssistente:")
        print(answer)
        print("-" * 50)


if __name__ == "__main__":
    main()
