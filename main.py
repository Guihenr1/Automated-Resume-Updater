from dataclasses import dataclass
from env import load_env_file
from pdf_service import generate_resume_pdf
from services.metadata_service import get_all_resumes, delete_resume_blob
from typing import Optional

load_env_file()

@dataclass
class Resume:
    name: str
    description: str

def update_resume_interactive() -> None:
    print("\nUpdate a Resume")
    try:
        resumes = get_all_resumes()
    except Exception as ex:
        print(f"Error fetching resumes: {ex}")
        return

    if not resumes:
        print("No resumes found.")
        return

    print("\nAvailable Resumes:")
    for idx, r in enumerate(resumes, start=1):
        code = r.get("code") or "N/A"
        name = r.get("name") or "Unnamed"
        print(f"[{idx}] {code} - {name}")

    choice = input("\nEnter a number to update (or press Enter to cancel): ").strip()
    if not choice:
        print("Canceled. Returning to menu...")
        return
    if not choice.isdigit():
        print("Invalid input. Please enter a number.")
        return

    i = int(choice)
    if i < 1 or i > len(resumes):
        print("Selection out of range.")
        return

    selected = resumes[i - 1]
    current_name = selected.get("name") or ""
    current_desc = selected.get("description") or ""
    current_page_size = selected.get("page_size") or "A4"
    old_blob_url = selected.get("blob_url")
    code = selected.get("code")

    print("\nPress Enter to keep the current value.")
    new_name = input(f"Name [{current_name}]: ").strip() or current_name
    new_desc = input(
        f"Description [{current_desc[:40] + ('...' if len(current_desc) > 40 else '')}]: ").strip() or current_desc
    new_page_size = input(f"Page size [{current_page_size}]: ").strip() or current_page_size

    print("\n[Preview] Updated Resume:")
    print(f"- Code (unchanged): {code}")
    print(f"- Name:             {new_name}")
    print(f"- Description:      {new_desc}")
    print(f"- Page Size:        {new_page_size}")

    confirm = input("\nProceed with updating this resume? (y/N): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Canceled. Returning to menu...")
        return

    from datetime import datetime
    safe_name = "".join(c for c in new_name if c.isalnum() or c in "-_ ").strip().replace(" ", "_") or "resume"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = f"./output/{safe_name}-updated-{timestamp}.pdf"

    try:
        new_location = generate_resume_pdf(
            name=new_name,
            description=new_desc,
            output_path=output_path,
            page_size=new_page_size,
        )
        print("\nNew version generated.")
        print(f"New location: {new_location}")

        if old_blob_url:
            try:
                delete_resume_blob(old_blob_url)
                print("Old resume deleted successfully.")
            except Exception as del_ex:
                print(f"Warning: failed to delete old resume: {del_ex}")
        else:
            print("No previous resume file URL found; skipping deletion.")

    except Exception as ex:
        print(f"\nFailed to update resume: {ex}")

    input("\nPress Enter to return to the menu...")

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
    objective = input("Objective: ").strip()
    technical_skills = input("Technical Skills: ").strip()
    experience = input("Experience: ").strip()
    education = input("Education: ").strip()
    certification = input("Certification: ").strip()
    courses = input("Courses: ").strip()
    languages = input("Languages: ").strip()
    links = input("Links: ").strip()

    if not name:
        print("Name is required.")
        return

    print("\n[Preview] Resume to be created:")
    print(f"- Name:        {name}")
    print(f"- Description: {description}")
    print(f"- Page Size:   {page_size}")
    print(f"- Objective: {objective}")
    print(f"- Technical Skills: {technical_skills}")
    print(f"- Experience: {experience}")
    print(f"- Education: {education}")
    print(f"- Certification: {certification}")
    print(f"- Courses: {courses}")
    print(f"- Languages: {languages}")
    print(f"- Links: {links}")

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
            objective=objective,
            technical_skills=technical_skills,
            experience=experience,
            education=education,
            certification=certification,
            courses=courses,
            languages=languages,
            links=links,
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
        print("3 - Update a resume")
        print("q - Quit")

        choice = input("Choose an option: ").strip().lower()

        if choice == "1":
            selected_code = list_resumes_interactive()
            if selected_code:
                print(f"(You selected code: {selected_code})")
        elif choice == "2":
            create_resume_interactive()
        elif choice == "3":
            update_resume_interactive()
        elif choice in {"q", "quit", "exit"}:
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    run_cli()

