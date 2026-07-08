# Architecture Design: Ownly Review Analyzer

This document defines the technical architecture, directory layouts, schemas, and data flow for the **Ownly Review Analyzer**—an automated pipeline designed to ingest, clean, analyze, and distribute customer and delivery partner feedback for Rapido's zero-commission food delivery app, **Ownly**.

---

## 1. Core Architecture Blueprint

The Ownly Review Analyzer is structured as a modular, decoupled pipeline across 5 distinct operational phases:

```mermaid
graph TD
    subgraph Phase 1: Ingestion & Normalization
        A1[Google Play Store Scraper]
        A2[Apple App Store Scraper]
        A3[Social Ingestion scaling]
    end

    subgraph Phase 2: Core Review Analyzer
        B1[PII Masker / Text Cleaning]
        B2[Groq Payload Sub-sampler]
        B3[LLM Theme Generation & Clustering]
    end

    subgraph Phase 3: Insights & Q&A
        C1[Weekly Note Generator]
        C2[Strategy Q&A Engine]
    end

    subgraph Phase 4: Delivery & Mailer
        D1[HTML Template Compiler]
        D2[SMTP Dispatcher]
    end

    subgraph Phase 5: UI & Visualization
        E1[Streamlit app.py Hub]
    end

    A1 & A2 & A3 -->|JSON Reviews| B1
    B1 --> B2 --> B3
    B3 -->|Theme Map| C1 & C2
    C1 --> D1 --> D2
    C2 & D1 & D2 --> E1
```

### 1.1 Phase Status at a Glance

| Phase | Core Objective | Key Directories & Files | Implementation Status |
| --- | --- | --- | --- |
| **Phase 1: Ingestion** | Ingest Play Store, App Store, and social reviews, and scale synthesis to 550 items | `phase1_ingestion/ingestor.py` | **Fully Implemented** |
| **Phase 2: Core Analyzer** | Clean data, scrub email/phone PII, run Groq theme clustering | `phase2_llm/analyzer.py` | **Fully Implemented** (Groq-driven) |
| **Phase 3: Insights** | Generate strategist answers and weekly pulse reports | `phase3_insights/strategist.py` | **Fully Implemented** |
| **Phase 4: Delivery** | Compile HTML newsletter and dispatch via SMTP | `phase4_delivery/delivery.py` | **Fully Implemented** (SMTP active) |
| **Phase 5: UI & Dashboard** | Streamlit visualization, checklist, custom email dispatcher | `app.py` | **Fully Implemented** |

### 1.2 High-Level Data Flow Sequence

The following sequence diagram outlines the chronological flow of data, transformation states, and output generation within the review analysis system:

```mermaid
sequenceDiagram
    autonumber
    participant Src as Feedback Sources (App Stores, Socials)
    participant Agg as Aggregator (run_analyzer.py)
    participant Scrub as PII Scrubber (analyzer.py)
    participant Groq as Groq API (llama-3.3-70b-versatile)
    participant Out as Local Outputs (Markdown, HTML, CSV)
    participant Mail as Mailer (SMTP)
    participant UI as Streamlit UI (app.py)

    Src->>Agg: 1. Ingest Play/App Store & social mock reviews (last 7 weeks)
    Note over Src,Agg: Play Store API crawl + App Store RSS + Ingestion Scaling (550 reviews)
    Agg->>Scrub: 2. Submit raw reviews for cleaning
    Note over Scrub: Regex patterns mask phone numbers & emails
    Scrub-->>Agg: 3. Return sanitized, anonymized payload
    Agg->>Groq: 4. Post sub-sampled review pool (up to 35 reviews)
    Note over Groq: Group themes, map clusters, answer growth Qs, write note
    Groq-->>Agg: 5. Return structured JSON payload
    Agg->>Out: 6. Compile & write weekly_note.md, email_draft.html, & themes_roadmap.csv
    Agg->>Mail: 7. Dispatch HTML email newsletter (if SMTP and RECIPIENT_EMAIL enabled)
    UI->>Agg: 8. Trigger manual runs & send dynamic email reports from frontend
```

---

## 2. Directory Layout & Module Structure

```
ownly_review_analyzer/
├── ARCHITECTURE.md            # System architecture details (this file)
├── README.md                  # Quickstart and run instructions
├── requirements.txt           # Dependency declaration
├── .gitignore                 # Git ignore configuration
├── .env.example               # Configuration template
├── .env                       # Local secrets (GROQ_API_KEY, SMTP details)
├── run_analyzer.py            # Primary CLI execution runner
├── app.py                     # Main Streamlit dashboard app
│
├── data/
│   └── mock_reviews.json      # Pre-populated reviews from App Store, Reddit, etc.
│
├── phase1_ingestion/          # INGESTION LAYER
│   ├── __init__.py
│   └── ingestor.py            # Handles scrapers (Play Store, App Store RSS) and mock scaling
│
├── phase2_llm/                # LLM & ANALYSIS LAYER
│   ├── __init__.py
│   └── analyzer.py            # PII masking, Groq LLM prompts, HTML compiler
│
├── phase3_insights/           # STRATEGIC INSIGHTS LAYER
│   ├── __init__.py
│   └── strategist.py          # Weekly MD note formatter, CSV/JSON report exports
│
└── phase4_delivery/           # EMAIL DELIVERY LAYER
    ├── __init__.py
    └── delivery.py            # SMTP mail dispatch logic
```

---

## 3. Detailed Phase Breakdown

### Phase 1: Ingestion & Normalization (`phase1_ingestion/`)
*   **Purpose**: Gathers feedback from multiple channels, normalizes fields, and filters to the last 7 weeks. Scales the workload to exactly 550 entries.
*   **Target Identifiers**:
    *   *Google Play Store*: Package `com.ctrlx.ownly`
    *   *Apple App Store*: ID `6739922216`
    *   *Reddit, LinkedIn, Twitter*: Contextual keyword crawls (`#Ownly`, `Ownly app`, `Ownly Rapido`).
*   **Data Schema (Normalized Review Object)**:
    ```json
    {
      "source": "playstore | appstore | reddit | linkedin | twitter",
      "rating": 1, // 1-5 integer, or null for social media
      "title": "Short Header", // String or null
      "text": "Full review body text...",
      "date": "YYYY-MM-DDTHH:MM:SSZ" // ISO UTC timestamp
    }
    ```

### Phase 2: Core Review Analyzer (`phase2_llm/`)
*   **Purpose**: Preprocesses feedback, scrubs PII, sub-samples the payload to fit token restrictions, and executes theme clustering.
*   **PII Masking Rules**:
    *   *Emails*: Regex `[\w\.-]+@[\w\.-]+\.\w+` replaced with `[EMAIL]`.
    *   *Phone Numbers*: Regex `(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}\b|\b\d{10}\b` replaced with `[PHONE]`.
    *   *Names*: Prompt-guided filtering to redact personal names (e.g. Ramesh, John) and exact addresses.
*   **Theme Generation & Clustering**:
    *   Calls the Groq LLM (`llama-3.3-70b-versatile`) to define high-level themes that encapsulate the reviews.
    *   Assigns every review to a generated theme ID.

### Phase 3: Insights & Strategy (`phase3_insights/`)
*   **Purpose**: Creates the strategic report answering specific business questions:
    1.  *Struggle Points*: App UI bugs, lag, search engine indexing.
    2.  *Ordering Frustrations*: Payment failures, order cancellations, delayed deliveries.
    3.  *Delivery Partner & User Issues*: Route tracking inaccuracies, distance payouts, app crashes.
    4.  *Competitor Switching & Loyalty*: Causes for switching back to Zomato/Swiggy (e.g., poor customer support, missing call button).
    5.  *Discovery Challenges*: App Store search optimizations, search keywords.
    6.  *Unmet Needs*: Pre-booking, corporate invoices (GST), multi-restaurant order carts.
*   **Output Product**: A **Weekly One-Page Note** comprising:
    -   Top 3 themes.
    -   3 raw user quotes (scrubbed).
    -   3 action ideas.

### Phase 4: Delivery (`phase4_delivery/`)
*   **Purpose**: Compiles a professional HTML email with the insights and drafts/sends it.
*   **Delivery Infrastructure**:
    *   *SMTP Path*: `smtp.gmail.com` via Port 465 (using app passwords) to dispatch emails securely.

### Phase 5: UI & Dashboard (`app.py`)
*   **Purpose**: Visual interface for product and growth managers.
*   **Dashboard Features**:
    -   Theme breakdown metrics and Plotly charts.
    -   Interactive reviews feed filtered by source, rating, theme, and query text.
    -   Growth/action idea checkbox checklist using Streamlit session state.
    -   Downloadable reports (PDF / CSV / MD).
    -   Dynamic email delivery triggers.

---

## 4. LLM API Payload Contract

The LLM is prompted to return a valid JSON payload matching this exact schema:

```json
{
  "themes": [
    {
      "id": "theme_commission_fees",
      "name": "Zero-Commission Sustainability",
      "description": "Feedback related to how the zero-commission model works and restaurant margins."
    }
  ],
  "clustering": [
    {
      "review_index": 1,
      "theme_id": "theme_commission_fees"
    }
  ],
  "question_answers": {
    "struggle_points": "Answer...",
    "ordering_frustrations": "Answer...",
    "delivery_partner_and_user_issues": "Answer...",
    "switch_causes_and_loyalty_barriers": "Answer...",
    "discovery_challenges": "Answer...",
    "unmet_needs": "Answer..."
  },
  "weekly_note": {
    "top_themes": [
      {
        "rank": 1,
        "name": "Zero-Commission Sustainability",
        "rationale": "High volume of posts and questions concerning restaurant model sustainability."
      }
    ],
    "user_quotes": [
      "The zero commission structure is great, but the onboarding process is incredibly slow.",
      "Review quote 2...",
      "Review quote 3..."
    ],
    "action_ideas": [
      "Simplify the restaurant merchant onboarding dashboard.",
      "Action 2...",
      "Action 3..."
    ]
  }
}
```

---

## 5. Security & PII Protection Standards

1.  **Double-Shield Approach**:
    -   *Shield 1 (Regex)*: Input content is passed through regex checks in Python to immediately replace emails and phone numbers.
    -   *Shield 2 (LLM Instruction)*: Prompt rules strictly forbid printing user/driver names, exact locations, or metadata in quotes, theme explanations, or answers.
2.  **No Storage of Identifiers**: The system stores ONLY anonymized strings.
