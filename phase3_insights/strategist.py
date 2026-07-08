import os
import csv
import json
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

class Strategist:
    def __init__(self):
        logger.info("Initialized Strategist for Phase 3 Insights & Strategy.")

    def generate_markdown_report(self, result: Dict[str, Any], date_str: str) -> str:
        """
        Generate a professional Markdown weekly pulse note and strategy Q&A report.
        """
        weekly_note = result.get("weekly_note", {})
        top_themes = weekly_note.get("top_themes", [])
        user_quotes = weekly_note.get("user_quotes", [])
        action_ideas = weekly_note.get("action_ideas", [])
        q_answers = result.get("question_answers", {})
        
        md = f"""# Ownly Review Analyzer - Weekly Pulse Note
**Date**: {date_str}
**Audit Period**: Last 7 Weeks
**Status**: Confidential - Internal Use Only

---

## 📋 Top Themes This Week
"""
        for idx, t in enumerate(top_themes[:3]):
            md += f"### {idx+1}. {t['name']}\n> {t['rationale']}\n\n"
            
        md += "---\n\n## 🗣️ User Quotes (Voice of the Customer)\n"
        for q in user_quotes:
            md += f"- *\"{q}\"*\n"
            
        md += "\n---\n\n## 💡 Strategic Action Ideas\n"
        for idx, act in enumerate(action_ideas):
            md += f"{idx+1}. **{act}**\n"
            
        md += "\n---\n\n## 🔍 Deep-Dive Product Strategy Answers\n"
        md += f"### 1. What are the users' struggle points on the app?\n{q_answers.get('struggle_points', 'N/A')}\n\n"
        md += f"### 2. What are the most common frustrations while ordering?\n{q_answers.get('ordering_frustrations', 'N/A')}\n\n"
        md += f"### 3. What problems are delivery partners and users facing?\n{q_answers.get('delivery_partner_and_user_issues', 'N/A')}\n\n"
        md += f"### 4. What causes them to switch to competitors & blocks loyalty?\n{q_answers.get('switch_causes_and_loyalty_barriers', 'N/A')}\n\n"
        md += f"### 5. Which user segments experience different discovery challenges?\n{q_answers.get('discovery_challenges', 'N/A')}\n\n"
        md += f"### 6. What unmet needs emerge consistently?\n{q_answers.get('unmet_needs', 'N/A')}\n"
        
        return md

    def save_report(self, report_content: str, filepath: str) -> bool:
        """
        Save the compiled report to disk.
        """
        try:
            with open(filepath, "w") as f:
                f.write(report_content)
            logger.info(f"[Insights] Markdown report saved to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"[Insights] Failed to save markdown report: {e}")
            return False

    def export_themes_csv(self, result: Dict[str, Any], filepath: str) -> bool:
        """
        Export the discovered themes into a structured CSV.
        """
        themes = result.get("themes", [])
        if not themes:
            logger.warning("[Insights] No themes found in analysis result to export.")
            return False
            
        try:
            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Theme ID", "Theme Name", "Description"])
                for t in themes:
                    writer.writerow([t.get("id", ""), t.get("name", ""), t.get("description", "")])
            logger.info(f"[Insights] Discovered themes exported to CSV: {filepath}")
            return True
        except Exception as e:
            logger.error(f"[Insights] Failed to export themes to CSV: {e}")
            return False

    def export_qa_json(self, result: Dict[str, Any], filepath: str) -> bool:
        """
        Export strategic question answers to a clean JSON file.
        """
        q_answers = result.get("question_answers", {})
        if not q_answers:
            logger.warning("[Insights] No question answers found in analysis result to export.")
            return False
            
        try:
            with open(filepath, "w") as f:
                json.dump(q_answers, f, indent=2)
            logger.info(f"[Insights] Strategic Q&A exported to JSON: {filepath}")
            return True
        except Exception as e:
            logger.error(f"[Insights] Failed to export Q&A to JSON: {e}")
            return False
