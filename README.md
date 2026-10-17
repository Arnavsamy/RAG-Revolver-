# RAG Revolver

An intelligent Retrieval-Augmented Generation system built to improve answer quality, reuse successful workflows, detect security threats, compare conflicting information, recall historical knowledge, and monitor web-page changes.


## Demo:


<img width="400" height="250" alt="rag" src="https://github.com/user-attachments/assets/2a260e4f-8687-479e-8def-7a428928c8f3" />






## Features:

- Answer improvement using approved training pairs
- Retrieval evaluation using Hit@4 and MRR
- Reusable workflow and skill creation
- Prompt-attack and adversarial testing
- Poisoned-source detection
- Hidden-instruction exposure testing
- Document conflict detection and comparison
- Page-level citation preservation
- Time-based knowledge recall
- Dated notes and historical information storage
- Web-page monitoring and change detection
- Automatic update summaries
- Optional notifications for detected changes

## How It Works:

The user provides documents, notes, approved training pairs, or web pages through the application. The system processes and indexes the available information so that relevant content can be retrieved for each request.

When a question is asked, RAG Revolver retrieves the most relevant sources and generates a grounded response. The system can evaluate the answer, detect conflicting claims, preserve page citations, and identify potentially harmful or manipulated content.

Depending on the task, the system can improve retrieval using Mender, save successful workflows with Skill Forge, test for attacks using Adversary, compare sources using Conflict Hunter, recall historical information with Recall, or monitor web pages through Sentinel.

## RAG Revolver Workflow:

1. Add documents, notes, training pairs, or web pages.
2. Process and index the available information.
3. Ask a question or start a workflow.
4. Retrieve the most relevant sources.
5. Evaluate the answer and source quality.
6. Detect conflicts, attacks, or poisoned content.
7. Generate a grounded response.
8. Preserve citations and supporting evidence.
9. Save successful workflows as reusable skills.
10. Monitor selected sources for future changes.

## RAG Revolver Modules:

### Mender

Finds incorrect or low-quality answers and improves retrieval using approved training pairs, Hit@4, and Mean Reciprocal Rank evaluation.

### Skill Forge

Saves successful workflows as reusable skills that can be applied to similar future tasks.

### Adversary

Tests the system with prompt attacks, poisoned sources, malicious instructions, and attempts to reveal hidden instructions.

### Conflict Hunter

Compares documents, detects conflicting claims, and preserves page-level citations for source verification.

### Recall

Stores dated notes and answers questions based on what was known at a specific point in time.

### Sentinel

Monitors web pages, detects changes, summarizes updates, and optionally sends notifications.

## Supported Applications:

- Knowledge-base question answering
- Document comparison
- Research and fact verification
- Retrieval-quality evaluation
- Prompt-injection testing
- Historical information tracking
- Workflow automation
- Web-page monitoring
- Change detection and summarization
- Citation-aware research

## Example Use Case:

A user asks a question based on multiple documents. RAG Revolver retrieves the relevant content, compares the documents, detects conflicting claims, and preserves the page citations.

If the answer is incorrect, Mender improves the retrieval process using an approved training pair. If the workflow is successful, Skill Forge saves it for future use. Adversary can test the sources for malicious instructions, Recall can provide historical information, and Sentinel can monitor related web pages for future updates.

## Project Structure:
```text
rag_revolver/
│
├── app/
│   ├── retrieval/
│   ├── evaluation/
│   ├── security/
│   ├── conflict_detection/
│   ├── recall/
│   ├── monitoring/
│   └── skills/
│
├── data/
├── assets/
│   └── rag-revolver-demo.gif
│
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables:
```ini
LLM_API_KEY=your_llm_api_key
EMBEDDING_API_KEY=your_embedding_api_key
```


## Future Improvements:

- Advanced citation validation
- More retrieval evaluation metrics
- Improved conflict-resolution workflows
- Additional prompt-attack test cases
- Automated skill quality scoring
- Scheduled web-page monitoring
- More notification channels
- Document and note version history
- Multi-user knowledge bases
- Multilingual information retrieval
- Retrieval and answer-quality analytics

## Conclusion:

RAG Revolver helps build more reliable, secure, and intelligent retrieval systems. Its six modules improve answer quality, reuse successful workflows, detect threats, compare sources, preserve historical knowledge, and monitor changing information.

CC: Arnav Ahilasamy
