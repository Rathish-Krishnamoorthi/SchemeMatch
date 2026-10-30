Build a complete, production-oriented web application called:

# Personalized Government Scheme & Benefit Discovery

## 1. Project Objective

Build an AI-powered Government Scheme Recommendation System that helps citizens discover government schemes, scholarships, subsidies, financial assistance programs, and welfare benefits that may be relevant to them.

The system must collect user information through a structured form, filter schemes using deterministic rule-based eligibility checking, rank the remaining eligible schemes using content-based machine learning, and use an LLM to provide a clear, personalized explanation of the recommendations.

The system must NOT allow the LLM to make the final eligibility decision.

The core pipeline must be:

User Form
→ User Profile
→ Rule-Based Eligibility Filtering
→ Remove Clearly Ineligible Schemes
→ Content-Based ML Recommendation
→ Rank Eligible Schemes
→ LLM Explanation
→ Personalized Results

---

# 2. Technology Stack

Use the following technologies:

### Frontend
- React.js
- Modern responsive UI
- Form validation
- Recommendation dashboard
- Scheme detail page

### Backend
- Python
- FastAPI
- REST APIs
- Pydantic models

### Database
- MongoDB / MongoDB Atlas
- Use MongoDB to store government scheme information, eligibility rules, benefits, documents, source information, and user interaction data.

### Machine Learning
- Python
- Sentence Transformers or another suitable embedding model
- Cosine similarity for content-based recommendation
- Start with a simple and explainable approach rather than training a complex neural recommendation model.

### LLM
Use an LLM through a configurable API layer.

The LLM should be responsible for:
- Understanding natural-language user needs if required
- Generating personalized explanations
- Summarizing scheme information
- Creating simple action plans
- Explaining why a scheme was recommended

The LLM must NOT independently determine eligibility.

### Optional RAG
Implement a grounded retrieval mechanism so that the LLM receives verified scheme information from the database before generating explanations.

---

# 3. Overall Architecture

Implement this architecture:

User
↓
React Form
↓
FastAPI
↓
User Profile Validation
↓
Rule-Based Eligibility Engine
↓
Eligible / Needs Verification / Not Eligible
↓
Content-Based Recommendation Engine
↓
Embedding + Cosine Similarity
↓
Ranking
↓
Top-K Schemes
↓
RAG / Verified Scheme Context
↓
LLM
↓
Explanation + Documents + Benefits + Next Steps
↓
React Recommendation Dashboard

---

# 4. User Input Form

Create a comprehensive but user-friendly form.

Collect fields such as:

- Age
- Gender, only where relevant to scheme eligibility
- State
- District, if required
- Annual/family income
- Occupation
- Education level
- Student status
- Employment status
- Farmer/business status where relevant
- Social/category information only when genuinely required by a scheme
- Disability status only where relevant
- Marital status where relevant
- Business type where relevant
- Need / purpose

Also provide a natural-language field:

"Tell us what kind of help you are looking for"

Example:

"I am an engineering student and I need financial assistance for my education."

The structured form should be the primary source for eligibility checking.

---

# 5. MongoDB Database Design

Create a `schemes` collection.

Each scheme should contain fields similar to:

{
  "scheme_id": "SCH001",
  "name": "Example Education Scholarship",
  "category": "Education",
  "description": "...",

  "eligibility": {
    "min_age": 18,
    "max_age": 25,
    "max_income": 250000,
    "states": ["Tamil Nadu"],
    "occupations": ["Student"],
    "education_levels": ["Undergraduate"]
  },

  "benefits": {
    "type": "Financial Assistance",
    "description": "...",
    "amount": "..."
  },

  "documents": [
    "Aadhaar",
    "Income Certificate",
    "College ID"
  ],

  "application_process": [
    "Register on official portal",
    "Upload required documents",
    "Submit application"
  ],

  "official_url": "...",
  "source": "...",
  "status": "ACTIVE",
  "last_verified": "..."
}

Design the schema flexibly because different schemes can have different eligibility requirements.

Do not assume every scheme has every field.

---

# 6. Rule-Based Eligibility Engine

Implement a separate Python eligibility engine.

This is the most important component for eligibility.

The engine should compare:

User Profile
against
Scheme Eligibility Rules

Example:

User:

Age = 20
Income = 180000
State = Tamil Nadu
Occupation = Student

Scheme:

Age = 18–25
Income <= 250000
State = Tamil Nadu
Occupation = Student

Result:

LIKELY_ELIGIBLE

The engine should support:

- Minimum age
- Maximum age
- Minimum income
- Maximum income
- State
- District
- Occupation
- Education
- Student status
- Employment status
- Category
- Disability status
- Other configurable conditions

Do NOT hard-code all conditions into one giant if/else block.

Create a modular rule evaluation system.

---

# 7. Eligibility States

Every scheme should receive one of these statuses:

1. LIKELY_ELIGIBLE
2. NEEDS_VERIFICATION
3. NOT_ELIGIBLE

Important:

Missing information should not automatically mean NOT_ELIGIBLE.

For example:

If a scheme requires a particular certificate and the user has not provided information about it:

NEEDS_VERIFICATION

If the user's income clearly exceeds the scheme's maximum income:

NOT_ELIGIBLE

If all known conditions are satisfied:

LIKELY_ELIGIBLE

---

# 8. Filtering Pipeline

Suppose the database contains 1,000 schemes.

The rule engine should process them:

1000 schemes
↓
700 NOT_ELIGIBLE
↓
200 LIKELY_ELIGIBLE
↓
100 NEEDS_VERIFICATION

For the main recommendation ranking, prioritize the 200 likely eligible schemes.

Optionally show the "Needs Verification" schemes separately.

Do not delete ineligible schemes from MongoDB.

They are only filtered from the recommendation candidate set.

---

# 9. Content-Based Recommendation Engine

After rule-based filtering, rank the eligible schemes based on the user's needs.

Example user need:

"I need financial assistance for my engineering education."

Scheme:

"Financial assistance for undergraduate students pursuing technical education."

These should have a high semantic similarity even if they don't share exactly the same keywords.

Use:

Sentence Transformer
↓
Generate user-need embedding

Sentence Transformer
↓
Generate scheme-description embedding

Then calculate:

Cosine Similarity

Rank schemes from highest similarity to lowest.

Example:

Engineering Scholarship       0.94
Higher Education Grant       0.89
Student Assistance            0.84
Skill Development            0.63

---

# 10. Embedding Storage

Design the system so embeddings can be generated for scheme descriptions.

Prefer an architecture that can support MongoDB Atlas Vector Search if available.

If vector search is not configured initially, implement a simple fallback using precomputed embeddings and cosine similarity.

Do not make the project dependent on an expensive infrastructure setup.

---

# 11. Recommendation Ranking

The initial ranking should primarily use:

- Eligibility status
- Semantic similarity
- Profile match
- Location match
- Category/need match

Do not allow semantic similarity to override a failed eligibility condition.

For example:

A scheme with:

Semantic similarity = 0.98
Eligibility = NOT_ELIGIBLE

must NOT be recommended as an eligible scheme.

A simple initial scoring approach can be:

Final Score =
Eligibility Weight
+
Semantic Similarity Weight
+
Profile Match Weight
+
Location Match Weight

Keep the weights configurable.

Do not claim that the score represents actual probability of eligibility.

Display it as:

"Match Score"

not:

"98% chance of getting the scheme."

---

# 12. LLM Integration

Use the LLM only after the recommendation engine has produced the top schemes.

Provide the LLM with:

- User profile
- User's stated need
- Scheme name
- Scheme description
- Eligibility conditions
- Eligibility result
- Benefits
- Documents
- Application process
- Official source
- Official URL
- Last verified date

The LLM should generate:

### Why this scheme was recommended

Explain the matching factors in simple language.

### Benefits

Explain the benefit using only retrieved scheme data.

### Documents

List the documents stored in the verified scheme record.

### Next Steps

Give a simple application action plan.

### Verification Warning

If any condition is uncertain, explicitly state that final eligibility must be verified through the official government source.

---

# 13. LLM Grounding / RAG

Implement grounded generation.

The LLM must not invent:

- Eligibility criteria
- Benefit amounts
- Deadlines
- Documents
- Government rules
- Application URLs

Use retrieved MongoDB scheme data as the context.

System instruction for the LLM:

"You are an assistant for explaining government schemes. Use only the verified scheme information provided in the context. Do not invent eligibility criteria, benefits, documents, deadlines, or application procedures. If information is missing, clearly say that it needs verification from the official source."

---

# 14. Recommendation Result

Create a clean dashboard.

Example:

### Recommended Schemes

#### 1. ABC Education Scholarship
Match Score: 94%

Status:
LIKELY ELIGIBLE

Why recommended:
- Age requirement satisfied
- Income requirement satisfied
- Student requirement satisfied
- Location requirement satisfied
- Strong match with education assistance need

Benefits:
Financial assistance for higher education.

Documents:
- Aadhaar
- Income Certificate
- College ID

Next Steps:
1. Verify the remaining requirements.
2. Prepare the required documents.
3. Open the official government portal.
4. Submit the application.

[View Scheme]
[Official Application]

---

# 15. Explainable Rejection

Provide an optional section:

### Schemes You May Not Be Eligible For

Example:

Scheme XYZ

Reason:
Your stated annual income exceeds the maximum income specified by the scheme.

This should come directly from the rule engine.

Do not ask the LLM to determine this reason.

---

# 16. API Design

Create APIs such as:

POST /api/users/profile

POST /api/recommendations

POST /api/eligibility/check

GET /api/schemes

GET /api/schemes/{scheme_id}

POST /api/chat/explain

GET /api/categories

Optional:

POST /api/admin/schemes

PUT /api/admin/schemes/{scheme_id}

DELETE /api/admin/schemes/{scheme_id}

---

# 17. Backend Folder Structure

Use a clean structure such as:

backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── users.py
│   │   │   ├── schemes.py
│   │   │   ├── recommendations.py
│   │   │   └── eligibility.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   └── scheme.py
│   │
│   ├── services/
│   │   ├── eligibility_service.py
│   │   ├── recommendation_service.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   └── rag_service.py
│   │
│   ├── database/
│   │   └── mongodb.py
│   │
│   └── core/
│       ├── config.py
│       └── security.py
│
├── requirements.txt
└── .env.example

frontend/
│
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── hooks/
│   └── App.jsx
│
└── package.json

---

# 18. Security

Do not expose:

- MongoDB connection strings
- LLM API keys
- Secret keys

Use `.env`.

Example:

MONGODB_URI=
LLM_API_KEY=
DATABASE_NAME=
JWT_SECRET=

Add `.env` to `.gitignore`.

---

# 19. Validation

Validate user inputs on both frontend and backend.

Examples:

Age:
0–120

Income:
>= 0

State:
selected from valid list

Do not trust frontend validation alone.

---

# 20. Important safety and reliability requirements

This application provides informational recommendations, not legal or official eligibility decisions.

Every result should clearly state:

"Eligibility is indicative and should be verified with the official government scheme authority before applying."

Always provide the official source/application URL where available.

Do not fabricate government schemes.

Do not fabricate eligibility requirements.

Do not fabricate benefits or deadlines.

---

# 21. ML Evaluation

Include evaluation metrics for the recommendation component.

For the content-based recommendation system, evaluate using:

- Precision@K
- Recall@K
- Mean Reciprocal Rank where suitable
- NDCG@K where suitable

For the rule engine, create unit tests covering:

- Clearly eligible users
- Clearly ineligible users
- Missing information
- Boundary age
- Boundary income
- State mismatch
- Multiple conditions
- Different scheme structures

---

# 22. LLM Evaluation

Test that the LLM:

- Does not invent scheme information
- Uses only retrieved information
- Clearly identifies missing information
- Gives understandable explanations
- Provides correct reasons based on rule-engine output

The rule engine remains the source of truth for eligibility.

---

# 23. Initial MVP

Do NOT over-engineer the first version.

Build this first:

1. MongoDB scheme database
2. React user form
3. FastAPI backend
4. Rule-based eligibility engine
5. Sentence Transformer embeddings
6. Cosine similarity ranking
7. Top-5 recommendation API
8. LLM explanation
9. Recommendation dashboard
10. Official source links

After this works, add:

- RAG
- MongoDB Vector Search
- User accounts
- Saved schemes
- Interaction tracking
- ML learning-to-rank
- Admin dashboard
- Scheme update verification

---

# 24. Final Expected Flow

The final application must behave like this:

USER
↓
Fills form
↓
FastAPI receives profile
↓
MongoDB retrieves government schemes
↓
Rule engine checks eligibility
↓
Clearly ineligible schemes are filtered out
↓
Remaining schemes are passed to the content-based recommendation engine
↓
Embeddings + cosine similarity determine relevance
↓
Top schemes are ranked
↓
Verified scheme information is retrieved
↓
LLM generates a grounded explanation
↓
React displays:
- Scheme name
- Match score
- Eligibility status
- Why recommended
- Benefits
- Required documents
- Next steps
- Official source
↓
USER can view the official scheme/application page

Build the project modularly, with clean separation between eligibility logic, recommendation logic, database access, ML/embedding logic, and LLM logic.

Prioritize correctness, explainability, maintainability, and ease of deployment over unnecessary complexity.