import os
import fitz  # PyMuPDF

def generate_test_pdf(output_path: str):
    """
    Generates a structured, multi-page test PDF file with facts about astronomy and planets.
    This serves as a mock text document for checking RAG, summarizations, flashcards, and MCQs.
    """
    doc = fitz.open()

    # --- PAGE 1: TITLE & CORE INTRO ---
    page1 = doc.new_page()
    page1.insert_text((50, 80), "Astronomy Study Guide: The Solar System", fontsize=22, fontname="helvetica-bold", color=(0.14, 0.38, 0.92))
    
    intro_lines = [
        "Welcome to the Astronomy Study Guide. This document contains key concepts, definitions,",
        "and facts regarding the bodies in our Solar System, including planets, the Sun, and gravity.",
        "Use this study material to test the AI Research Assistant's Q&A, summary, and quiz tools."
    ]
    y_pos = 140
    for line in intro_lines:
        page1.insert_text((50, y_pos), line, fontsize=12, fontname="helv")
        y_pos += 25

    # Section 1
    page1.insert_text((50, 240), "Section 1: The Sun and Gravity", fontsize=15, fontname="helvetica-bold")
    sun_lines = [
        "The Sun is the star at the center of the Solar System. It is a nearly perfect sphere of hot plasma,",
        "heated to incandescence by nuclear fusion reactions in its core. The Sun radiates this energy",
        "mainly as light, ultraviolet, and infrared radiation, providing the primary energy source for Earth.",
        "",
        "Gravity is the force by which a planet or other body draws objects toward its center.",
        "The force of gravity keeps all of the planets in orbit around the Sun. Without the Sun's gravitational pull,",
        "the planets would float off into deep space."
    ]
    y_pos = 280
    for line in sun_lines:
        if line == "":
            y_pos += 15
            continue
        page1.insert_text((50, y_pos), line, fontsize=11, fontname="helv")
        y_pos += 20

    # --- PAGE 2: INNER PLANETS ---
    page2 = doc.new_page()
    page2.insert_text((50, 80), "Section 2: The Inner Terrestrial Planets", fontsize=16, fontname="helvetica-bold", color=(0.14, 0.38, 0.92))
    
    terrestrial_lines = [
        "The inner Solar System contains four terrestrial planets: Mercury, Venus, Earth, and Mars.",
        "Terrestrial planets are composed primarily of rock and metal, having solid, cratered surfaces.",
        "",
        "Mercury: The smallest and closest planet to the Sun. It has virtually no atmosphere and experiences",
        "extreme temperature fluctuations, ranging from -173 degrees Celsius at night to 427 degrees Celsius during the day.",
        "",
        "Venus: The second planet from the Sun. It is the hottest planet in the Solar System due to a runaway",
        "greenhouse effect caused by its dense carbon dioxide atmosphere. Its surface temperature is a constant 462 degrees Celsius.",
        "",
        "Earth: The third planet from the Sun, and the only known astronomical object to harbor life. Over 70 percent of",
        "its surface is covered by liquid water oceans. Earth orbits the Sun in approximately 365.25 days.",
        "",
        "Mars: Known as the Red Planet due to iron oxide (rust) on its surface. It has a thin carbon dioxide atmosphere,",
        "polar ice caps, and Olympus Mons, the largest volcano in the Solar System."
    ]
    y_pos = 120
    for line in terrestrial_lines:
        if line == "":
            y_pos += 12
            continue
        page2.insert_text((50, y_pos), line, fontsize=11, fontname="helv")
        y_pos += 18

    # --- PAGE 3: OUTER GAS GIANTS & FORMULAS ---
    page3 = doc.new_page()
    page3.insert_text((50, 80), "Section 3: The Outer Gas Giants and Core Equations", fontsize=16, fontname="helvetica-bold", color=(0.14, 0.38, 0.92))
    
    gas_lines = [
        "The outer Solar System contains four giant planets: Jupiter, Saturn, Uranus, and Neptune.",
        "These planets are much larger than the terrestrial planets and are composed mostly of gases like hydrogen and helium.",
        "",
        "Jupiter: The largest planet in our Solar System, with a mass more than two and a half times that of all the",
        "other planets combined. It has a prominent Great Red Spot, which is a giant atmospheric storm.",
        "",
        "Saturn: Famous for its extensive, bright ring system composed of ice particles, rocky debris, and dust.",
        "",
        "Uranus and Neptune: Often classified as ice giants. Uranus is unique because it rotates on its side.",
        "Neptune is the farthest planet from the Sun and experiences the strongest winds in the Solar System, up to 2,100 km/h."
    ]
    y_pos = 120
    for line in gas_lines:
        if line == "":
            y_pos += 12
            continue
        page3.insert_text((50, y_pos), line, fontsize=11, fontname="helv")
        y_pos += 18

    # Core Formula Section
    page3.insert_text((50, 350), "Key Astrodynamics Formulas", fontsize=14, fontname="helvetica-bold")
    
    formulas = [
        "Formula 1 (Newton's Law of Universal Gravitation): F = G * (m1 * m2) / r^2",
        "Where F is the gravitational force, G is the gravitational constant, m1 and m2 are the masses, and r is the distance.",
        "",
        "Formula 2 (Kepler's Third Law): T^2 = k * a^3",
        "Where T is the orbital period, a is the semi-major axis, and k is a constant constant."
    ]
    y_pos = 380
    for line in formulas:
        if line == "":
            y_pos += 10
            continue
        page3.insert_text((50, y_pos), line, fontsize=11, fontname="helv")
        y_pos += 18

    # Save to disk
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)
    doc.close()
    print(f"Sample PDF created successfully at: {output_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generate_test_pdf(os.path.join(script_dir, "test_solar_system.pdf"))
