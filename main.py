from dataclasses import dataclass
from env import load_env_file
from pdf_service import generate_resume_pdf

load_env_file()

@dataclass
class Resume:
    name: str
    description: str

def prompt_resume() -> Resume:
    name = input("Write your name: ").strip()
    description = input("Write your description: ").strip()
    return Resume(name, description)

def generate_resume(resume: Resume) -> None:
    output_file = generate_resume_pdf(resume.name, resume.description, output_path=f"resumes/{resume.name}.pdf")
    print(f"PDF saved to: {output_file}")

if __name__ == "__main__":
    print("Welcome to Automated Resume Updater")
    generate_resume(prompt_resume())
