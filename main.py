from dataclasses import dataclass
from env import load_env_file
from pdf_service import generate_resume_pdf
from services.metadata_service import get_all_resumes
from typing import Optional

load_env_file()

@dataclass
class Resume:
    name: str
    description: str

def list_resumes_interactive() -> Optional[str]:
    try:
        resumes = get_all_resumes()
    except Exception as ex:
        print(f"Error fetching resumes: {ex}")
        return None

    if not resumes:
        print("No resumes found.")
        return None

    print("\nAvailable Resumes:")
    for idx, r in enumerate(resumes, start=1):
        code = r.get("code") or "N/A"
        name = r.get("name") or "Unnamed"
        print(f"[{idx}] {code} - {name}")

    choice = input("\nEnter a number to view details (or press Enter to go back): ").strip()
    if not choice:
        return None

    if not choice.isdigit():
        print("Invalid input. Please enter a number.")
        return None

    i = int(choice)
    if i < 1 or i > len(resumes):
        print("Selection out of range.")
        return None

    selected = resumes[i - 1]
    print("\nResume Details:")
    print(f"- Code:        {selected.get('code')}")
    print(f"- Name:        {selected.get('name')}")
    print(f"- Description: {selected.get('description')}")
    print(f"- Page Size:   {selected.get('page_size')}")
    print(f"- Created At:  {selected.get('created_at')}")
    print(f"- Blob URL:    {selected.get('blob_url')}\n")

    return selected.get("code")

def create_resume_interactive() -> None:
    print("\nCreate a Resume")
    name = input("Name: ").strip()
    description = input("Description: ").strip()
    page_size = input("Page size (e.g., A4, Letter): ").strip() or "A4"

    if not name:
        print("Name is required.")
        return

    print("\n[Preview] Resume to be created:")
    print(f"- Name:        {name}")
    print(f"- Description: {description}")
    print(f"- Page Size:   {page_size}")

    choice = input("\nProceed with creating this resume? (y/N): ").strip().lower()
    if choice not in ("y", "yes"):
        print("Canceled. Returning to menu...")
        return

    from datetime import datetime
    safe_name = "".join(c for c in name if c.isalnum() or c in "-_ ").strip().replace(" ", "_") or "resume"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = f"./resumes/{safe_name}-{timestamp}.pdf"

    try:
        result_path_or_url = generate_resume_pdf(
            name=name,
            description=description,
            output_path=output_path,
            page_size=page_size,
        )
        print("\nSuccess! Resume generated.")
        print(f"Location: {result_path_or_url}")
    except Exception as ex:
        print(f"\nFailed to generate resume: {ex}")

    input("\nPress Enter to return to the menu...")


def run_cli() -> None:
    while True:
        print("\nWhat do you want to do?")
        print("1 - Get All Resumes")
        print("2 - Create a resume")
        print("q - Quit")

        choice = input("Choose an option: ").strip().lower()

        if choice == "1":
            selected_code = list_resumes_interactive()
            if selected_code:
                print(f"(You selected code: {selected_code})")
        elif choice == "2":
            create_resume_interactive()
        elif choice in {"q", "quit", "exit"}:
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    run_cli()

