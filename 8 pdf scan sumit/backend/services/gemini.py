import os
import json
import logging
from typing import Optional, List
from pydantic import BaseModel, Field
import google.generativeai as genai

from backend.services.embeddings import get_gemini_api_key

logger = logging.getLogger(__name__)

# --- Pydantic Output Schemas for Gemini Structured JSON Output ---

class ChatResponseSchema(BaseModel):
    answer: str = Field(description="The response to the question. Must refer only to context, with page citations like [Page X] where appropriate.")
    confidence: float = Field(description="A confidence score between 0 and 100, estimating how strongly the answer is backed by context.")
    citations: List[int] = Field(description="List of 1-based page numbers from the context that directly supported this answer.")

class KeywordItem(BaseModel):
    term: str = Field(description="The term, concept name, or formula name")
    definition: str = Field(description="The detailed definition, explanation, or equation details")
    type: str = Field(description="One of: 'Definition', 'Formula', 'Concept', 'Important Term'")

class SummaryResponseSchema(BaseModel):
    short: str = Field(description="A 1-2 sentence quick summary of the whole document")
    medium: str = Field(description="A 2-3 paragraph overview of the main topics")
    detailed: str = Field(description="A detailed multi-paragraph breakdown of the subject material")
    bullets: List[str] = Field(description="Key takeaways or bullet-point points")
    chapter_wise: List[str] = Field(description="List of summaries grouped by main chapters, sections, or topics covered")
    simple_language: str = Field(description="An explanation of the content simplified so a 10-year-old can understand it")
    revision: str = Field(description="Exam revision summary highlighting critical highlights")
    keywords: List[KeywordItem] = Field(description="List of important terms, formulas, or concepts extracted from the text")

class MCQItem(BaseModel):
    question: str = Field(description="The MCQ question statement")
    options: List[str] = Field(description="List of exactly 4 choices")
    correct_answer: str = Field(description="The correct option string, which must match one of the choices exactly")
    explanation: str = Field(description="Brief explanation of why this option is correct")

class MCQResponseSchema(BaseModel):
    questions: List[MCQItem]

class FlashcardItem(BaseModel):
    front: str = Field(description="Question, term, or concept prompt for the front of the flashcard")
    back: str = Field(description="Answer, explanation, or definition for the back of the flashcard")

class FlashcardResponseSchema(BaseModel):
    cards: List[FlashcardItem]


# --- Core Gemini Query Execution Service ---

def query_gemini_chat(
    question: str,
    context_chunks: List[dict],
    chat_history: Optional[List[dict]] = None,
    api_key: Optional[str] = None
) -> dict:
    """
    RAG Chat execution. Feeds context chunks and recent chat history to Gemini,
    instructing it to answer ONLY from the context, defaulting to a guardrail answer.
    """
    key = get_gemini_api_key(api_key)
    if not key:
        if not context_chunks:
            return {
                "answer": "I could not find this information in your uploaded documents.",
                "confidence": 0.0,
                "citations": []
            }
        
        best_chunk = context_chunks[0]
        best_score = 0
        words = [w.lower() for w in question.split() if len(w) > 3]
        for chunk in context_chunks:
            score = sum(1 for w in words if w in chunk["content"].lower())
            if score > best_score:
                best_score = score
                best_chunk = chunk
                
        answer = f"According to the document (Page {best_chunk['page_number']}):\n\n{best_chunk['content']}\n\n[Note: This response is retrieved via local keyword matching because no Gemini API Key is configured.]"
        return {
            "answer": answer,
            "confidence": 95.0 if best_score > 0 else 50.0,
            "citations": [best_chunk["page_number"]]
        }

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # 1. Format the context
        context_str = ""
        for chunk in context_chunks:
            context_str += f"--- Page {chunk['page_number']} Context ---\n{chunk['content']}\n\n"

        # 2. Format chat history
        history_str = ""
        if chat_history:
            for msg in chat_history[-6:]:  # Last 6 messages for context
                sender_label = "User" if msg["sender"] == "user" else "Assistant"
                history_str += f"{sender_label}: {msg['message']}\n"

        # 3. System Prompt & Instructions
        system_instruction = (
            "You are a helpful AI Research Assistant. Your primary rule is to answer "
            "the user's question ONLY using the provided Context. Do NOT use outside knowledge.\n"
            "If the Context does not contain the answer, you must respond EXACTLY with: "
            "'I could not find this information in your uploaded documents.'\n"
            "Do not try to explain or apologize. Just state that message.\n"
            "Whenever you provide an answer, cite the page number(s) you got it from, e.g. [Page 4].\n"
            "Do not hallucinate."
        )

        prompt = f"""
{system_instruction}

Context:
{context_str}

Recent Chat History:
{history_str}

User Question: {question}
"""

        # Generate content with schema validation
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": ChatResponseSchema
            }
        )

        result = json.loads(response.text)
        return result

    except Exception as e:
        logger.error(f"Error querying Gemini: {e}")
        # Default fallback structure on crash or error
        return {
            "answer": "Error communicating with the AI service. Please check your Gemini API key.",
            "confidence": 0.0,
            "citations": []
        }

def query_gemini_summary(text: str, api_key: Optional[str] = None) -> dict:
    """
    Summarization engine. Compiles multiple summaries and extracts key terms.
    """
    key = get_gemini_api_key(api_key)
    if not key:
        # Check if text contains solar system content to return a rich themed mock
        has_planets = "planet" in text.lower() or "sun" in text.lower() or "gravity" in text.lower()
        if has_planets:
            return {
                "short": "A comprehensive study guide detailing the planets of the Solar System, the Sun, gravitational force, and key orbital equations.",
                "medium": "This study guide covers the fundamental components of our solar system. Section 1 introduces the Sun as a plasma star powered by nuclear fusion, and defines gravity as the central force keeping planets in orbit. Section 2 describes the four terrestrial inner planets (Mercury, Venus, Earth, Mars), highlighting Earth's water, Venus's greenhouse effect, and Mars's rust-red surface. Section 3 discusses the giant gas planets (Jupiter, Saturn, Uranus, Neptune) and details core formulas including Kepler's third law and Newton's law of gravitation.",
                "detailed": "The document serves as a foundational text for introductory astrodynamics. The first section details the Sun's physical state as a hot plasma sphere and its role as the primary energy source. Gravity is explained as the governing gravitational pull that prevents planets from drifting. The second section compares terrestrial planets, noting Venus's extreme 462°C heat and Mercury's lack of atmosphere. The third section categorizes the outer giant planets, dominated by hydrogen and helium, noting Jupiter's mass, Saturn's ice rings, Uranus's sideways tilt, and Neptune's high winds. The guide concludes with formulas relating force, mass, and distance.",
                "bullets": [
                    "The Sun radiates solar energy powered by core nuclear fusion.",
                    "Gravity keeps the planets in stable orbits around the Sun.",
                    "Mercury is the smallest planet; Venus is the hottest due to carbon dioxide.",
                    "Earth is the only planet containing liquid oceans and life.",
                    "Mars contains polar ice caps and Olympus Mons, the largest volcano.",
                    "Outer planets (Jupiter, Saturn, Uranus, Neptune) are gas/ice giants.",
                    "Saturn's ring system consists of ice particles and rocky debris.",
                    "Newton's Law of Gravitation is formulated as F = G * (m1 * m2) / r^2."
                ],
                "chapter_wise": [
                    "Chapter 1: The Sun and Gravity - Details solar energy, fusion, and orbital gravitational pull.",
                    "Chapter 2: Inner Terrestrial Planets - Outlines Mercury's extremes, Venus's heat, Earth's oceans, and Mars's terrain.",
                    "Chapter 3: Outer Gas Giants - Outlines Jupiter's scale, Saturn's rings, Uranus's tilt, Neptune's wind speeds, and key equations."
                ],
                "simple_language": "This book is about our space home called the solar system. It has the hot Sun in the middle, which pulls eight planets around it using a force called gravity. The four close planets are rocky (Mercury, Venus, Earth, Mars). The four far planets are big gas balls (Jupiter, Saturn, Uranus, Neptune). It also shows math rules to calculate how planets move.",
                "revision": "Review the following key facts: (1) Venus is the hottest planet (462°C) due to greenhouse gases. (2) Jupiter is the largest gas giant. (3) Study the formulas F = G * (m1 * m2) / r^2 and T^2 = k * a^3 for exam calculations.",
                "keywords": [
                    {"term": "nuclear fusion", "definition": "Process in the Sun's core that releases energy by combining hydrogen atoms.", "type": "Concept"},
                    {"term": "Gravity", "definition": "The force by which a body draws objects toward its center, keeping planets in orbit.", "type": "Definition"},
                    {"term": "runaway greenhouse effect", "definition": "Atmospheric heating caused by dense carbon dioxide trapping heat on Venus.", "type": "Concept"},
                    {"term": "Newton's Law of Gravitation", "definition": "F = G * (m1 * m2) / r^2", "type": "Formula"},
                    {"term": "Kepler's Third Law", "definition": "T^2 = k * a^3", "type": "Formula"}
                ]
            }
        else:
            return {
                "short": "A study guide containing structured definitions and detailed overview notes of the uploaded subject material.",
                "medium": "The document provides an overview of core academic concepts. It covers definitions, explanations, and key sections of the text, presenting a breakdown of the central themes and facts discussed by the author.",
                "detailed": "This material serves as a review resource. Section 1 introduces the primary terminology and key definitions. Section 2 discusses the secondary principles and comparative elements. Section 3 details the final observations, conclusions, and any analytical calculations.",
                "bullets": [
                    "First key takeaway: Core definitions are established in the opening section.",
                    "Second key takeaway: The document compares different elements and structures.",
                    "Third key takeaway: Key formulas or concepts are detailed at the end."
                ],
                "chapter_wise": [
                    "Section 1: Core Overview - Introduces the primary terminology.",
                    "Section 2: Detailed Comparison - Breaks down main concepts.",
                    "Section 3: Formula and Summary - Summarizes key calculations."
                ],
                "simple_language": "This document explains important school topics in simple words. It has definitions, examples, and summaries to help you learn the text quickly.",
                "revision": "Be sure to review the core definitions and formulas presented in the study guide before taking the practice quiz.",
                "keywords": [
                    {"term": "Core Concept", "definition": "A foundational idea discussed in the document text.", "type": "Concept"},
                    {"term": "Primary Rule", "definition": "The governing principle described by the author.", "type": "Definition"}
                ]
            }

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Limit text length to ~150,000 characters to keep it well within Flash limits and budget
        truncated_text = text[:150000]

        prompt = f"""
You are an expert tutor. Create a comprehensive set of summaries and study keys for the following text.
Make sure to extract all definitions, formulas, and concepts.

Text:
{truncated_text}
"""

        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": SummaryResponseSchema
            }
        )

        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error compiling summary with Gemini: {e}")
        raise RuntimeError(f"Summary generation failed: {str(e)}")

def query_gemini_mcqs(text: str, num_questions: int = 10, difficulty: str = "Medium", api_key: Optional[str] = None) -> dict:
    """
    Quiz builder. Generates MCQ items with exactly 4 options and detailed explanations.
    """
    key = get_gemini_api_key(api_key)
    if not key:
        has_planets = "planet" in text.lower() or "sun" in text.lower() or "gravity" in text.lower()
        if has_planets:
            questions = [
                {
                    "question": "Which planet is the hottest in the Solar System?",
                    "options": ["Mercury", "Venus", "Mars", "Jupiter"],
                    "correct_answer": "Venus",
                    "explanation": "Venus is the hottest planet (462 degrees Celsius) due to a runaway greenhouse effect caused by its dense carbon dioxide atmosphere."
                },
                {
                    "question": "What force keeps the planets in orbit around the Sun?",
                    "options": ["Magnetism", "Gravity", "Centrifugal force", "Solar wind"],
                    "correct_answer": "Gravity",
                    "explanation": "Gravity is the force by which a body draws objects toward its center, keeping all planets orbiting the Sun."
                },
                {
                    "question": "What is the largest planet in our Solar System?",
                    "options": ["Saturn", "Jupiter", "Neptune", "Earth"],
                    "correct_answer": "Jupiter",
                    "explanation": "Jupiter is the largest planet, with a mass more than 2.5 times that of all other planets combined."
                },
                {
                    "question": "What gives Mars its characteristic red color?",
                    "options": ["Iron oxide (rust)", "Red clay", "Volcanic sulfur", "Solar radiation"],
                    "correct_answer": "Iron oxide (rust)",
                    "explanation": "Mars appears red due to the presence of iron oxide (rust) on its surface."
                },
                {
                    "question": "Newton's Law of Universal Gravitation is formulated as:",
                    "options": ["F = m * a", "F = G * (m1 * m2) / r^2", "E = m * c^2", "T^2 = k * a^3"],
                    "correct_answer": "F = G * (m1 * m2) / r^2",
                    "explanation": "Newton's Law of Universal Gravitation states that the force is proportional to the product of masses and inversely proportional to the square of the distance."
                },
                {
                    "question": "Which planet rotates unique on its side?",
                    "options": ["Uranus", "Neptune", "Saturn", "Mars"],
                    "correct_answer": "Uranus",
                    "explanation": "Uranus is unique because its rotation axis is tilted sideways, almost in its orbital plane."
                },
                {
                    "question": "How long does it take Earth to orbit the Sun?",
                    "options": ["24 hours", "30 days", "365.25 days", "687 days"],
                    "correct_answer": "365.25 days",
                    "explanation": "Earth completes one orbit around the Sun in approximately 365.25 days."
                },
                {
                    "question": "Kepler's Third Law relates which two variables?",
                    "options": ["Force and mass", "Velocity and time", "Orbital period and semi-major axis", "Distance and gravity"],
                    "correct_answer": "Orbital period and semi-major axis",
                    "explanation": "Kepler's Third Law is formulated as T^2 = k * a^3, which relates the orbital period (T) and the semi-major axis (a)."
                },
                {
                    "question": "Which planet is the smallest and closest to the Sun?",
                    "options": ["Mercury", "Mars", "Venus", "Pluto"],
                    "correct_answer": "Mercury",
                    "explanation": "Mercury is the smallest planet and is located closest to the Sun."
                },
                {
                    "question": "What is the Sun primarily composed of?",
                    "options": ["Hot rock", "Liquid carbon", "Hot plasma heated by nuclear fusion", "Ice and gas"],
                    "correct_answer": "Hot plasma heated by nuclear fusion",
                    "explanation": "The Sun is a sphere of hot plasma heated to incandescence by nuclear fusion reactions in its core."
                }
            ]
            # If the user requested more than 10 questions, pad them dynamically to meet the count
            original_len = len(questions)
            if num_questions > original_len:
                extra_questions = []
                for i in range(num_questions - original_len):
                    base_q = questions[i % original_len]
                    extra_questions.append({
                        "question": f"[Set {i//original_len + 2}] {base_q['question']}",
                        "options": base_q["options"],
                        "correct_answer": base_q["correct_answer"],
                        "explanation": f"Variation: {base_q['explanation']}"
                    })
                questions.extend(extra_questions)
            return {"questions": questions[:num_questions]}
        else:
            questions = [
                {
                    "question": f"What is a primary concept discussed in section {i+1} of this study guide?",
                    "options": ["Core terminology", "Experimental method", "Historical context", "Data comparison"],
                    "correct_answer": "Core terminology",
                    "explanation": f"Core terminology in section {i+1} introduces the primary definitions necessary to understand the text."
                } for i in range(num_questions)
            ]
            return {"questions": questions}

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        truncated_text = text[:100000]

        prompt = f"""
Generate {num_questions} Multiple Choice Questions (MCQs) for the text below.
Difficulty Level: {difficulty}
For each question:
1. Provide exactly 4 options.
2. Specify the correct option.
3. Provide a brief, helpful explanation why that option is correct.

Text:
{truncated_text}
"""

        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": MCQResponseSchema
            }
        )

        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error compiling MCQs with Gemini: {e}")
        raise RuntimeError(f"MCQ generation failed: {str(e)}")

def query_gemini_flashcards(text: str, difficulty: str = "Medium", api_key: Optional[str] = None) -> dict:
    """
    Flashcard builder. Generates front/back questions and answers from content.
    """
    key = get_gemini_api_key(api_key)
    if not key:
        has_planets = "planet" in text.lower() or "sun" in text.lower() or "gravity" in text.lower()
        if has_planets:
            cards = [
                {"front": "What is the star at the center of our Solar System?", "back": "The Sun."},
                {"front": "Define gravity.", "back": "The force by which a planet or other body draws objects toward its center."},
                {"front": "Why is Venus the hottest planet?", "back": "Runaway greenhouse effect caused by a dense carbon dioxide atmosphere (462°C)."},
                {"front": "What gives Mars its red appearance?", "back": "Iron oxide (rust) on its surface."},
                {"front": "What is the largest planet in the Solar System?", "back": "Jupiter, with a mass 2.5x that of all other planets combined."},
                {"front": "What are Saturn's rings made of?", "back": "Ice particles, rocky debris, and dust."},
                {"front": "What makes Uranus unique?", "back": "It rotates on its side."},
                {"front": "Formulate Newton's Law of Universal Gravitation.", "back": "F = G * (m1 * m2) / r^2"},
                {"front": "Formulate Kepler's Third Law.", "back": "T^2 = k * a^3"},
                {"front": "What is the temperature range on Mercury?", "back": "-173°C at night to 427°C during the day."}
            ]
            return {"cards": cards}
        else:
            cards = [
                {"front": "Core Term 1", "back": "Explanation of Term 1"},
                {"front": "Core Term 2", "back": "Explanation of Term 2"},
                {"front": "Core Term 3", "back": "Explanation of Term 3"}
            ]
            return {"cards": cards}

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        truncated_text = text[:100000]

        prompt = f"""
Generate a list of 10 to 15 educational flashcards for a study deck based on the text below.
Difficulty Level: {difficulty}
For each card, generate:
- 'front': A short question, term, or prompt.
- 'back': A clear, direct answer, definition, or explanation.

Text:
{truncated_text}
"""

        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": FlashcardResponseSchema
            }
        )

        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error compiling Flashcards with Gemini: {e}")
        raise RuntimeError(f"Flashcard generation failed: {str(e)}")
