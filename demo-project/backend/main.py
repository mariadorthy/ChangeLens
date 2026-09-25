from backend.api.tasks import list_tasks

def main() -> None:
    print({"tasks": list_tasks()})

if __name__ == "__main__":
    main()
