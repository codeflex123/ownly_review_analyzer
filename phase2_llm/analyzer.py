import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple
from groq import Groq
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class ReviewAnalyzer:
    def __init__(self, api_key: str = None, model_name: str = "llama-3.3-70b-versatile"):
        """
        Initialize the analyzer. If api_key is not passed, it will try to read from environment.
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            logger.warning("No GROQ_API_KEY found in the environment. LLM calls will fail.")
        
        self.model_name = model_name
        logger.info(f"Initialized ReviewAnalyzer using model: {model_name}")

    def scrub_pii(self, text: str) -> str:
        """
        Remove personal identifiable information (PII) like emails and phone numbers.
        """
        if not text:
            return ""

        # Mask emails
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        text = re.sub(email_pattern, "[EMAIL]", text)

        # Mask Indian and international phone numbers (e.g. +91 9876543210, 98765-43210, 9876543210)
        phone_pattern = r'(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b|\b\d{10}\b|\b\d{3}[-\s]\d{3}[-\s]\d{4}\b'
        text = re.sub(phone_pattern, "[PHONE]", text)
        
        return text

    def clean_reviews(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean and scrub PII from all reviews.
        """
        cleaned = []
        for r in reviews:
            scrubbed_text = self.scrub_pii(r.get("text", ""))
            scrubbed_title = self.scrub_pii(r.get("title", "")) if r.get("title") else None
            
            cleaned.append({
                "source": r.get("source", "unknown"),
                "rating": r.get("rating"),
                "title": scrubbed_title,
                "text": scrubbed_text,
                "date": r.get("date", ""),
                # Ensure no other metadata slips PII
            })
        return cleaned

    def analyze_reviews(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send cleaned reviews to Gemini to generate themes, group them, and generate insights.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set in the environment or passed to the constructor to run the LLM analysis.")

        cleaned_reviews = self.clean_reviews(reviews)
        
        # Format reviews as a neat string for the prompt
        formatted_reviews = ""
        for idx, r in enumerate(cleaned_reviews):
            title_str = f" | Title: {r['title']}" if r.get("title") else ""
            rating_str = f" | Rating: {r['rating']}/5" if r.get("rating") else ""
            formatted_reviews += f"Review #{idx+1} [Source: {r['source']}{rating_str}{title_str} | Date: {r['date']}]:\n\"{r['text']}\"\n\n"

        prompt = f"""
You are a senior Lead Product Analyst for "Ownly", a new zero-commission food delivery app owned by Rapido.
Your task is to analyze user feedback (App Store reviews, Play Store reviews, Reddit threads, LinkedIn posts, and Twitter mentions) from the last 7 weeks.

Here are the reviews to analyze:
---
{formatted_reviews}
---

Your analysis MUST strictly adhere to the following requirements:
1. **Dynamic Theme Generation**: Discover between 3 and 5 distinct themes (max 5) that encapsulate the primary customer and partner experiences. Provide a Name and Description for each theme.
2. **Review Clustering**: Map every review (by its Index number, e.g., Review #1, Review #2) to exactly one of your discovered themes.
3. **Structured Question Answering**: Provide detailed, data-backed answers to these product questions:
   - What are the users' struggle points on the app?
   - What are the most common frustrations while ordering using Ownly?
   - What are the problems delivery partners and users are facing on the Ownly app?
   - What causes them to switch to other apps, preventing Ownly from converting them into loyal users?
   - Which user segments experience different discovery challenges?
   - What unmet needs emerge consistently across reviews?
4. **Weekly One-Page Note**:
   - **Top 3 Themes**: The three most dominant/impactful themes ranked by volume or severity, with a brief explanation.
   - **3 User Quotes**: Three highly representative quotes from the feedback. They MUST be completely anonymized (scrub any names like Ramesh, John, Anil, or addresses/streets, and use [EMAIL] or [PHONE] if they contain contact details).
   - **3 Strategic Action Ideas**: High-impact, concrete, actionable product or operational ideas to address the findings.
5. **No PII**: Ensure absolutely NO personal identifiable information (emails, phone numbers, names of users/drivers) appears in the theme descriptions, quotes, or answers.

You must respond with a JSON object. Ensure the JSON is valid and can be parsed directly in Python. Use the following schema:
{{
  "themes": [
    {{
      "id": "theme_id_1",
      "name": "Theme Name",
      "description": "Short explanation of the theme"
    }}
  ],
  "clustering": [
    {{
      "review_index": 1,
      "theme_id": "theme_id_1"
    }}
  ],
  "question_answers": {{
    "struggle_points": "Detailed answer...",
    "ordering_frustrations": "Detailed answer...",
    "delivery_partner_and_user_issues": "Detailed answer...",
    "switch_causes_and_loyalty_barriers": "Detailed answer...",
    "discovery_challenges": "Detailed answer...",
    "unmet_needs": "Detailed answer..."
  }},
  "weekly_note": {{
    "top_themes": [
      {{
        "rank": 1,
        "name": "Theme Name",
        "rationale": "Why this theme is top"
      }}
    ],
    "user_quotes": [
      "Quote 1...",
      "Quote 2...",
      "Quote 3..."
    ],
    "action_ideas": [
      "Action 1...",
      "Action 2...",
      "Action 3..."
    ]
  }}
}}
"""
        logger.info("Sending review payload to Groq...")
        try:
            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model_name,
                response_format={"type": "json_object"}
            )
            response_text = response.choices[0].message.content
            result = json.loads(response_text)
            logger.info("Successfully parsed Groq response.")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON. Raw output:\n{response_text}")
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(0))
                    logger.info("Successfully extracted and parsed JSON fallback block.")
                    return result
                except Exception:
                    pass
            raise e
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise e

    def generate_html_email(self, analysis_result: Dict[str, Any], date_str: str) -> str:
        """
        Compile the weekly note and analysis results into a gorgeous, responsive HTML email.
        """
        # Parse data
        weekly_note = analysis_result.get("weekly_note", {})
        top_themes = weekly_note.get("top_themes", [])
        user_quotes = weekly_note.get("user_quotes", [])
        action_ideas = weekly_note.get("action_ideas", [])
        q_answers = analysis_result.get("question_answers", {})
        themes_list = analysis_result.get("themes", [])

        # Build theme list HTML
        themes_html = ""
        for t in themes_list:
            themes_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px; font-weight: bold; color: #1a202c; width: 30%;">{t['name']}</td>
                <td style="padding: 12px; color: #4a5568; line-height: 1.5;">{t['description']}</td>
            </tr>
            """

        # Build top themes HTML
        top_themes_html = ""
        colors = ["#ebf8ff", "#faf5ff", "#fffaf0"]
        border_colors = ["#3182ce", "#805ad5", "#dd6b20"]
        for idx, t in enumerate(top_themes[:3]):
            bg = colors[idx % len(colors)]
            border = border_colors[idx % len(border_colors)]
            top_themes_html += f"""
            <div style="background-color: {bg}; border-left: 4px solid {border}; padding: 15px; margin-bottom: 12px; border-radius: 4px;">
                <h4 style="margin: 0 0 6px 0; color: #2d3748; font-size: 16px;">#{idx+1}. {t['name']}</h4>
                <p style="margin: 0; color: #4a5568; font-size: 14px; line-height: 1.5;">{t['rationale']}</p>
            </div>
            """

        # Build quotes HTML
        quotes_html = ""
        for q in user_quotes:
            quotes_html += f"""
            <div style="background-color: #f7fafc; border: 1px solid #edf2f7; padding: 15px; margin-bottom: 10px; border-radius: 6px; font-style: italic; color: #4a5568; line-height: 1.5; position: relative;">
                “{q}”
            </div>
            """

        # Build action ideas HTML
        actions_html = ""
        for idx, act in enumerate(action_ideas):
            actions_html += f"""
            <div style="display: flex; margin-bottom: 12px; align-items: flex-start;">
                <div style="background-color: #319795; color: white; border-radius: 50%; width: 24px; height: 24px; text-align: center; line-height: 24px; font-weight: bold; font-size: 12px; margin-right: 12px; flex-shrink: 0;">{idx+1}</div>
                <div style="color: #2d3748; font-size: 14px; line-height: 1.5; padding-top: 2px;">{act}</div>
            </div>
            """

        # Build Q&A HTML
        qa_html = ""
        qa_labels = {
            "struggle_points": "1. What are the users' struggle points on the app?",
            "ordering_frustrations": "2. What are the most common frustrations while ordering?",
            "delivery_partner_and_user_issues": "3. What problems are delivery partners and users facing?",
            "switch_causes_and_loyalty_barriers": "4. What causes them to switch to competitors & blocks loyalty?",
            "discovery_challenges": "5. Which user segments experience different discovery challenges?",
            "unmet_needs": "6. What unmet needs emerge consistently across reviews?"
        }
        for key, question in qa_labels.items():
            answer = q_answers.get(key, "No analysis available.")
            qa_html += f"""
            <div style="margin-bottom: 18px; border-bottom: 1px solid #edf2f7; padding-bottom: 12px;">
                <h4 style="margin: 0 0 6px 0; color: #2c5282; font-size: 15px;">{question}</h4>
                <p style="margin: 0; color: #4a5568; font-size: 13.5px; line-height: 1.5;">{answer}</p>
            </div>
            """

        # Premium CSS template
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Ownly Weekly Pulse Note</title>
</head>
<body style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; -webkit-font-smoothing: antialiased;">
    <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 680px; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); overflow: hidden; border-collapse: collapse; margin: 0 auto;">
        <!-- Header -->
        <tr style="background: linear-gradient(135deg, #1A365D 0%, #2A4365 100%);">
            <td style="padding: 30px 40px; text-align: center;">
                <div style="font-size: 12px; font-weight: bold; color: #319795; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px;">Rapido / Ownly Intelligence</div>
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Weekly Review Pulse Note</h1>
                <div style="color: #cbd5e0; font-size: 13px; margin-top: 8px;">Audit Period: Last 7 Weeks | Date: {date_str}</div>
            </td>
        </tr>
        
        <!-- Main Content -->
        <tr>
            <td style="padding: 40px;">
                <p style="margin-top: 0; color: #4a5568; font-size: 14.5px; line-height: 1.6; border-left: 3px solid #319795; padding-left: 12px; margin-bottom: 30px;">
                    Here is the synthesized review feedback analysis for the <strong>Ownly</strong> zero-commission food delivery application. Reviews have been collected across Google Play Store, Apple App Store, Reddit, LinkedIn, and social media platforms. All PII has been scrubbed.
                </p>

                <!-- SECTION 1: TOP THEMES (THE WEEKLY NOTE) -->
                <h2 style="color: #1a202c; font-size: 18px; font-weight: 700; border-bottom: 2px solid #319795; padding-bottom: 8px; margin-bottom: 16px; margin-top: 0;">Top Themes This Week</h2>
                {top_themes_html}

                <!-- SECTION 2: USER QUOTES -->
                <h2 style="color: #1a202c; font-size: 18px; font-weight: 700; border-bottom: 2px solid #319795; padding-bottom: 8px; margin-bottom: 16px; margin-top: 35px;">Voice of the Customer (Anonymized Quotes)</h2>
                {quotes_html}

                <!-- SECTION 3: ACTION IDEAS -->
                <h2 style="color: #1a202c; font-size: 18px; font-weight: 700; border-bottom: 2px solid #319795; padding-bottom: 8px; margin-bottom: 16px; margin-top: 35px;">Strategic Action Items</h2>
                <div style="background-color: #e6fffa; border: 1px solid #b2f5ea; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                    {actions_html}
                </div>

                <!-- SECTION 4: ALL DISCOVERED THEMES -->
                <h2 style="color: #1a202c; font-size: 18px; font-weight: 700; border-bottom: 2px solid #2d3748; padding-bottom: 8px; margin-bottom: 16px; margin-top: 40px;">All Discovered Themes ({len(themes_list)})</h2>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                    <thead>
                        <tr style="background-color: #f7fafc; border-bottom: 2px solid #edf2f7; text-align: left;">
                            <th style="padding: 12px; font-size: 13px; color: #718096; text-transform: uppercase;">Theme</th>
                            <th style="padding: 12px; font-size: 13px; color: #718096; text-transform: uppercase;">Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        {themes_html}
                    </tbody>
                </table>

                <!-- SECTION 5: PRODUCT STRATEGY QUESTIONS -->
                <h2 style="color: #1a202c; font-size: 18px; font-weight: 700; border-bottom: 2px solid #2b6cb0; padding-bottom: 8px; margin-bottom: 20px; margin-top: 40px;">Deep-Dive Question Analysis</h2>
                <div style="background-color: #ebf8ff; border: 1px solid #bee3f8; padding: 20px; border-radius: 8px;">
                    {qa_html}
                </div>
            </td>
        </tr>

        <!-- Footer -->
        <tr style="background-color: #f7fafc; border-top: 1px solid #edf2f7;">
            <td style="padding: 30px 40px; text-align: center; color: #a0aec0; font-size: 12px; line-height: 1.5;">
                This analysis is generated automatically by the Ownly Review Analyzer engine using Gemini AI.<br>
                For questions or suggestions, please contact the Rapido Food-Tech Growth and Analytics team.<br>
                &copy; 2026 Rapido / CTRLX Technologies. All rights reserved.
            </td>
        </tr>
    </table>
</body>
</html>
"""
        return html_template
