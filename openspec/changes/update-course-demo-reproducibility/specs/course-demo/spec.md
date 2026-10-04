## ADDED Requirements

### Requirement: Reproducible offline source retrieval
The course demo SHALL support offline lexical retrieval through the same Streamlit UI and backend entry point without calling external APIs or loading embedding models.

#### Scenario: Matching fictional course fixture
- **WHEN** a user asks about 晨星晶片主要風險 in offline mode with the synthetic fixture corpus
- **THEN** the app shows the original excerpt from chip_company.md and its chunk identifier
- **AND** it marks the result as retrieved excerpts rather than a generated answer.

#### Scenario: No lexical match
- **WHEN** the offline retriever finds no overlapping terms
- **THEN** it returns no citations and explicitly states that no relevant excerpt was found.

### Requirement: Honest source fallback and session configuration
The system SHALL keep retrieved source excerpts separate from generated answers and SHALL pass UI credentials per request without writing them to process environment variables.

#### Scenario: Generation unavailable
- **WHEN** no generation credential is configured or generation returns no answer
- **THEN** the app displays the original source excerpts without including the prompt or conversation history as a fabricated summary.

#### Scenario: Clear session credential
- **WHEN** a user enters and then clears the UI Gemini credential
- **THEN** the entered session credential is removed without changing GEMINI_API_KEY or RAG_LLM_MODEL in the process environment.
