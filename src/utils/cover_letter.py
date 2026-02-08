"""
Cover letter generation using the same LLM that drives the browser agent.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from config import profile
from src.models.schemas import JobListing

_SYSTEM_PROMPT = """\
You are an expert career coach writing a cover letter.

Rules:
- Keep it under 350 words.
- Be specific: reference the company name, role, and 2-3 requirements from the
  job description that align with the candidate's background.
- Use a professional but warm tone.  No clichés like "I am writing to express
  my interest" or "passionate about".
- Structure: opening hook → relevant experience (2 paragraphs) → closing with
  enthusiasm and availability.
- Do NOT fabricate experience.  Only reference skills and history from the
  resume and profile provided.
- Output ONLY the cover letter body text.  No subject line, no "Dear Hiring
  Manager" header, no sign-off — the application portal adds those.
"""


def generate_cover_letter(
    llm: BaseChatModel,
    job: JobListing,
    resume_text: str,
) -> str:
    """Generate a tailored cover letter for *job* using the candidate's resume."""

    user_prompt = f"""\
## Candidate Profile
Name: {profile.FIRST_NAME} {profile.LAST_NAME}
Current role: {profile.CURRENT_TITLE} at {profile.CURRENT_COMPANY}
Years of experience: {profile.YEARS_OF_EXPERIENCE}
Key skills: {', '.join(profile.SKILLS)}

## Resume
{resume_text}

## Target Position
Title: {job.title}
Company: {job.company}
Location: {job.location}

## Job Description
{job.description[:3000]}

Write the cover letter now.
"""

    response = llm.invoke([
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ])
    return response.content.strip()
