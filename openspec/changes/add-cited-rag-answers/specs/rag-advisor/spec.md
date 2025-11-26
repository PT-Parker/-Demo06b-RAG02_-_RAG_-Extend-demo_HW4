## ADDED Requirements
### Requirement: Answer includes source citations
The chatbot SHALL append supporting citations (source title or identifier plus a short snippet) derived from the retrieved documents alongside each answer.

#### Scenario: Answer with citations
- **WHEN** a student asks a question covered by the indexed policy documents
- **THEN** the chatbot returns a concise answer in Traditional Chinese
- **AND** it lists at least two citations showing the source title/identifier and a snippet for each
- **AND** every citation corresponds to the FAISS documents retrieved for that question.

### Requirement: Fallback when no relevant sources
The chatbot SHALL avoid speculative answers by providing a polite fallback when retrieval yields no relevant documents.

#### Scenario: Retrieval miss fallback
- **WHEN** the retriever finds no documents matching the query intent
- **THEN** the chatbot replies that the information is unavailable and suggests contacting the school office instead of fabricating an answer.
