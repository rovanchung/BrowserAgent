"""
Cover letter generation using the same LLM that drives the browser agent.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from config.cover_letter_prompt import COVER_LETTER_PROMPT
from config.profile import PROFILE
from src.models.schemas import JobListing


async def generate_cover_letter(
    llm: BaseChatModel,
    job: JobListing,
    resume_text: str,
) -> str:
    """Generate a tailored cover letter for *job* using the candidate's resume."""

    user_prompt = f"""\
## Candidate Profile
Name: {PROFILE["first_name"]} {PROFILE["last_name"]}
Current role: {PROFILE["current_title"]} at {PROFILE["current_company"]}
Years of experience: {PROFILE["years_of_experience"]}
Key skills: {', '.join(PROFILE["skills"])}

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

    response = await llm.ainvoke(
        [
            SystemMessage(content=COVER_LETTER_PROMPT),
            HumanMessage(content=user_prompt),
        ]
    )
    return response.content.strip()
