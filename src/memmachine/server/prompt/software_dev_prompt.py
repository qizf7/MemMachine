UPDATE_PROMPT = """
    Your job is to handle memory extraction for a developer profile memory system, which tracks USER-SPECIFIC coding preferences, habits, and expertise.
    You will receive a developer profile and the user's coding activity or query, your job is to update that profile by extracting or inferring information about the DEVELOPER'S personal preferences, not project-specific details.
    
    IMPORTANT: This is a PROFILE MEMORY for the USER/DEVELOPER, not for projects. 
    - Profile Memory (this prompt): Stores USER's personal coding preferences, habits, expertise, and working style
    - Episodic Memory (separate): Stores PROJECT-SPECIFIC information with workspace name as session ID
    
    A profile is a two-level key-value store. We call the outer key the *tag*, and the inner key the *feature*. Together, a *tag* and a *feature* are associated with one or several *value*s.

    How to construct profile entries:
    - Entries should be atomic. They should communicate a single discrete fact.
    - Entries should be as short as possible without corrupting meaning. Be careful when leaving out prepositions, qualifiers, negations, etc. Some modifiers will be longer range, find the best way to compactify such phrases.
    - You may see entries which violate the above rules, those are "consolidated memories". Don't rewrite those.
    - Think of yourself as performing the role of a wide, early layer in a neural network, doing "edge detection" in many places in parallel to present as many distinct intermediate features as you possibly can given raw, unprocessed input.

    The tags you are looking for include (USER-SPECIFIC ONLY):
    - Preferred Languages: Programming languages the user prefers or is proficient in.
    - Preferred Frameworks: Frameworks and libraries the user likes to use.
    - Coding Style Preferences: Personal coding style, formatting, and convention preferences.
    - Development Tools: IDEs, editors, extensions, and tools the user prefers.
    - Testing Preferences: User's preferred testing approaches and frameworks.
    - Architecture Preferences: Architectural patterns the user prefers (MVC, microservices, etc.).
    - Design Pattern Preferences: Design patterns the user frequently uses or prefers.
    - Code Review Habits: How the user likes to review code or receive feedback.
    - Learning Style: How the user prefers to learn new technologies.
    - Documentation Habits: User's approach to writing and reading documentation.
    - Debugging Approach: User's preferred debugging strategies and tools.
    - Refactoring Philosophy: User's attitude toward refactoring and code improvement.
    - Performance Optimization Mindset: User's approach to performance considerations.
    - Security Consciousness: User's awareness and practices around security.
    - Error Handling Philosophy: User's preferred approaches to error handling.
    - Version Control Habits: User's Git workflow preferences and commit style.
    - API Design Philosophy: User's preferences for API design (REST, GraphQL, etc.).
    - Database Preferences: User's preferred database technologies and approaches.
    - Frontend Preferences: User's frontend technology and pattern preferences.
    - Backend Preferences: User's backend technology and pattern preferences.
    - DevOps Familiarity: User's experience with CI/CD, containers, cloud platforms.
    - Collaboration Style: How the user prefers to work with teams.
    - Problem-Solving Approach: User's approach to tackling coding problems.
    - Technology Adoption: User's attitude toward new vs. stable technologies.
    - Code Quality Standards: User's expectations for code quality.
    - Productivity Patterns: User's peak coding hours, focus preferences, workflow.
    - Technical Expertise Areas: Domains where user has deep knowledge.
    - Technical Learning Goals: Technologies or skills the user wants to learn.
    - Typical Project Types: Types of projects the user usually works on.
    - Work Environment Preferences: Remote, office, pair programming preferences.
    - Communication Preferences: How user prefers technical communication.
    - Tool Automation Habits: User's approach to automation and tooling.
    - Code Organization Philosophy: How user prefers to structure code.
    - Naming Convention Preferences: User's preferred naming styles.
    - Comment and Documentation Style: User's commenting and doc practices.
    - Type Safety Preferences: User's preference for static vs dynamic typing.
    - Functional vs OOP Preference: User's paradigm preferences.
    - Code Complexity Tolerance: User's preference for simple vs complex solutions.
    - Dependency Management Philosophy: User's approach to managing dependencies.
    - Build Tool Preferences: User's preferred build and bundling tools.
    - Async Programming Comfort: User's experience with async/concurrent code.
    - Mobile Development Experience: User's mobile development background.
    - Accessibility Awareness: User's knowledge and practice of accessibility.
    - Internationalization Experience: User's experience with i18n/l10n.
    - Data Structure Preferences: User's go-to data structures.
    - Algorithm Knowledge: User's familiarity with algorithms.
    - UI/UX Sensitivity: User's awareness of user experience principles.
    - Code Sharing Habits: User's approach to code reuse and modularity.

    Example Profile:
    {
        "Preferred Languages": {
            "primary": "Python for backend, TypeScript for frontend",
            "secondary": "Go for performance-critical services",
            "learning": "Rust - interested but not proficient yet"
        },
        "Preferred Frameworks": {
            "backend": "FastAPI over Flask - prefers async capabilities",
            "frontend": "React with TypeScript - values type safety",
            "testing": "pytest for Python, Jest for JavaScript"
        },
        "Coding Style Preferences": {
            "formatting": "Strict adherence to linters - uses Black for Python, Prettier for JS",
            "line_length": "Prefers 88 characters (Black default) for Python, 100 for TypeScript",
            "imports": "Organized by standard lib, third-party, local",
            "type_hints": "Always uses type hints in Python, strict TypeScript mode"
        },
        "Development Tools": {
            "primary_editor": "VS Code with Vim keybindings",
            "terminal": "iTerm2 with zsh and oh-my-zsh",
            "extensions": "Pylance, ESLint, Prettier, GitLens",
            "package_manager": "pnpm for Node.js, uv for Python"
        },
        "Testing Preferences": {
            "philosophy": "Test-driven development advocate",
            "coverage_expectation": "Aims for 80%+ coverage on critical paths",
            "testing_types": "Prioritizes unit tests, adds integration tests for APIs",
            "mocking_approach": "Prefers dependency injection over mocking when possible"
        },
        "Architecture Preferences": {
            "patterns": "Microservices for large systems, modular monolith for smaller ones",
            "api_design": "RESTful APIs with OpenAPI documentation",
            "data_flow": "Prefers unidirectional data flow patterns"
        },
        "Design Pattern Preferences": {
            "common_patterns": "Repository pattern, Factory pattern, Strategy pattern",
            "avoids": "Singleton pattern - prefers dependency injection"
        },
        "Code Review Habits": {
            "giving_feedback": "Focuses on architecture first, then implementation details",
            "receiving_feedback": "Appreciates constructive criticism and learning opportunities",
            "review_frequency": "Prefers small, frequent PRs over large batches"
        },
        "Learning Style": {
            "approach": "Hands-on learning through building projects",
            "resources": "Prefers official documentation and technical blogs over videos",
            "practice": "Contributes to open source to learn new technologies"
        },
        "Documentation Habits": {
            "code_comments": "Documents why, not what - code should be self-explanatory",
            "readme_preference": "Comprehensive READMEs with setup, usage, and architecture",
            "api_docs": "Prefers auto-generated docs from code (Swagger, JSDoc)"
        },
        "Debugging Approach": {
            "strategy": "Reproduces bug first, then uses debugger over print statements",
            "tools": "Python debugger (pdb), Chrome DevTools",
            "logging": "Structured logging with different levels (debug, info, error)"
        },
        "Version Control Habits": {
            "commit_style": "Conventional commits with clear, descriptive messages",
            "branching": "Feature branches from main, prefers rebase over merge",
            "pr_size": "Keeps PRs under 500 lines when possible"
        },
        "Performance Optimization Mindset": {
            "approach": "Measure before optimizing - profile to find bottlenecks",
            "tradeoffs": "Willing to trade some performance for code clarity",
            "caching": "Uses caching strategically, not by default"
        },
        "Security Consciousness": {
            "practices": "Never commits secrets, uses environment variables",
            "authentication": "Prefers OAuth2/JWT for APIs",
            "input_validation": "Validates and sanitizes all user inputs"
        },
        "Technology Adoption": {
            "attitude": "Pragmatic - adopts when technology is stable and well-documented",
            "experimentation": "Tests new tech in side projects before production use"
        },
        "Collaboration Style": {
            "preference": "Enjoys pair programming for complex problems",
            "communication": "Prefers async communication (Slack) for most things, meetings for big decisions",
            "knowledge_sharing": "Writes technical docs and gives internal tech talks"
        },
        "Productivity Patterns": {
            "peak_hours": "Most productive in morning (9 AM - 1 PM)",
            "focus_time": "Needs 2-3 hour blocks of uninterrupted time for deep work",
            "breaks": "Takes short breaks every 90 minutes"
        },
        "Technical Expertise Areas": {
            "domains": "Backend APIs, data pipelines, LLM integration",
            "specialization": "Memory systems and vector databases"
        },
        "Work Environment Preferences": {
            "location": "Prefers remote work with occasional in-person collaboration",
            "setup": "Dual monitor setup, mechanical keyboard, standing desk option"
        },
        "Type Safety Preferences": {
            "philosophy": "Strong advocate for static typing and type hints",
            "tooling": "Uses mypy for Python, strict TypeScript configuration"
        },
        "Functional vs OOP Preference": {
            "style": "Prefers functional style where appropriate, OOP for domain modeling",
            "immutability": "Favors immutable data structures"
        },
        "Code Complexity Tolerance": {
            "philosophy": "Prefers simple, explicit code over clever, implicit code",
            "readability": "Optimizes for readability and maintainability"
        }
    }


    To update the developer's profile, you will output a JSON document containing a list of commands to be executed in sequence.
    The following output will add a feature:
    {
        "0": {
            "command": "add",
            "tag": "Preferred Languages",
            "feature": "emerging_interest",
            "value": "Exploring Rust for systems programming"
        }
    }
    The following will delete all values associated with the feature:
    {
        "0": {
            "command": "delete",
            "tag": "Development Tools",
            "feature": "old_editor"
        }
    }
    And the following will update a feature:
    {
        "0": {
            "command": "delete",
            "tag": "Preferred Frameworks",
            "feature": "frontend",
            "value": "Angular"
        },
        "1": {
            "command": "add",
            "tag": "Preferred Frameworks",
            "feature": "frontend",
            "value": "React with TypeScript - switched from Angular"
        }
    }

    Example Scenarios:
    Query: "I prefer using TypeScript over JavaScript because of type safety."
    {
        "0": {
            "command": "add",
            "tag": "Preferred Languages",
            "feature": "frontend_language",
            "value": "TypeScript preferred over JavaScript"
        },
        "1": {
            "command": "add",
            "tag": "Type Safety Preferences",
            "feature": "typescript_preference",
            "value": "Values type safety as primary reason for TypeScript adoption"
        }
    }

    Query: "I always write unit tests before implementing features. TDD helps me think through the design."
    {
        "0": {
            "command": "add",
            "tag": "Testing Preferences",
            "feature": "methodology",
            "value": "Practices test-driven development (TDD)"
        },
        "1": {
            "command": "add",
            "tag": "Testing Preferences",
            "feature": "tdd_benefit",
            "value": "Uses TDD to improve design thinking and architecture"
        }
    }

    Query: "Can you help me set up ESLint? I like the Airbnb style guide."
    {
        "0": {
            "command": "add",
            "tag": "Development Tools",
            "feature": "javascript_linting",
            "value": "Uses ESLint for JavaScript/TypeScript"
        },
        "1": {
            "command": "add",
            "tag": "Coding Style Preferences",
            "feature": "javascript_style",
            "value": "Follows Airbnb style guide for JavaScript"
        }
    }

    Query: "I find pair programming really helpful for tackling complex algorithms."
    {
        "0": {
            "command": "add",
            "tag": "Collaboration Style",
            "feature": "pair_programming",
            "value": "Finds pair programming valuable for complex problems"
        },
        "1": {
            "command": "add",
            "tag": "Problem-Solving Approach",
            "feature": "collaborative_problem_solving",
            "value": "Prefers collaborative approach for algorithmic challenges"
        }
    }

    Query: "I'm learning Rust but still not comfortable with the borrow checker."
    {
        "0": {
            "command": "add",
            "tag": "Technical Learning Goals",
            "feature": "rust_learning",
            "value": "Currently learning Rust, struggling with borrow checker"
        },
        "1": {
            "command": "add",
            "tag": "Preferred Languages",
            "feature": "rust_proficiency",
            "value": "Learning Rust but not yet proficient"
        }
    }

    Further Guidelines:
    - CRITICAL: Only extract USER preferences and habits, NOT project-specific information
    - Project details (like "this project uses FastAPI") should NOT be stored in profile memory
    - Focus on what the user PREFERS, LIKES, KNOWS, or HABITUALLY DOES
    - Distinguish between "user prefers X" vs "project uses X" - only store the former
    - Not everything you ought to record will be explicitly stated. Make inferences.
    - If you are less confident about a particular entry, you should still include it, but make sure that the language you use (briefly) expresses this uncertainty in the value field
    - Look at the text from as many distinct angles as you can find, remember you are the "wide layer".
    - Keep only the key details (highest-entropy) in the feature name. The nuances go in the value field.
    - Do not couple together distinct details. Just because the user associates certain details doesn't mean you should combine them.
    - Do not create new tags which you don't see in the tag list above. However, you can and should create new features.
    - Do not delete anything unless a user asks you to or when correcting an error.
    - If you want to keep the profile the same, as you should if the query is completely irrelevant or the information will soon be outdated, return the empty object: {}.
    - Listen to any additional instructions specific to the execution context provided underneath 'EXTRA EXTERNAL INSTRUCTIONS'
    - First, think about what should go in the profile inside <think> </think> tags. Then output only a valid JSON.
EXTRA EXTERNAL INSTRUCTIONS:
NONE
"""

CONSOLIDATION_PROMPT = """
Your job is to perform memory consolidation for a developer profile memory system.
Despite the name, consolidation is not solely about reducing the amount of memories, but rather, minimizing interference between memories.
By consolidating memories, we remove unnecessary couplings of memory from context, spurious correlations inherited from the circumstances of their acquisition.

IMPORTANT: This consolidation is for USER-SPECIFIC preferences and habits, NOT project-specific information.

You will receive a new memory, as well as a select number of older memories which are semantically similar to it.
Produce a new list of memories to keep.

A memory is a json object with 4 fields:
- tag: broad category of memory (e.g., "Preferred Languages", "Coding Style Preferences")
- feature: executive summary of memory content (e.g., "primary_language", "formatting_preference")
- value: detailed contents of memory (e.g., "Python preferred for backend work due to expressiveness")
- metadata: object with 1 field
-- id: integer
You will output consolidated memories, which are json objects with 4 fields:
- tag: string
- feature: string
- value: string
- metadata: object with 1 field
-- citations: list of ids of old memories which influenced this one
You will also output a list of old memories to keep (memories are deleted by default)

Guidelines:
Memories should not contain unrelated ideas. Memories which do are artifacts of couplings that exist in original context. Separate them. This minimizes interference.
Memories containing only redundant information should be deleted entirely, especially if they seem unprocessed or the information in them has been processed.
If memories are sufficiently similar, but differ in key details, synchronize their tags and/or features. This creates beneficial interference.
    - To aid in this, you may want to shuffle around the components of each memory, moving parts that are alike to the feature, and parts that differ to the value.
    - Note that features should remain (brief) summaries, even after synchronization, you can do this with parallelism in the feature names (e.g. prefers_react and prefers_vue).
    - Keep only the key details (highest-entropy) in the feature name. The nuances go in the value field.
    - this step allows you to speculatively build towards more permanent structures
If enough memories share similar features (due to prior synchronization, i.e. not done by you), delete all of them and create a single new memory containing a list.
    - In these memories, the feature contains all parts of the memory which are the same, and the value contains only the parts which vary.
    - You can also directly transfer information to existing lists as long as the new item has the same type as the list's items.
    - Don't make lists too early. Have at least three examples in a non-gerrymandered category first. You need to find the natural groupings. Don't force it.

Overall memory life-cycle:
raw memory ore -> pure memory pellets -> memory pellets sorted into bins -> alloyed memories

Special considerations for developer profile memories:
- Preferences evolve over time - newer preferences may override older ones (e.g., "switched from X to Y")
- Keep context about WHY a user prefers something when available (e.g., "prefers TypeScript for type safety")
- Skills and expertise levels change - track learning progression
- Tools and technology preferences should note the context (e.g., "Python for backend, TypeScript for frontend")
- Distinguish between strong preferences vs casual mentions
- Consolidate learning goals as they become expertise areas
- Separate work style preferences from technical preferences

The more memories you receive, the more interference there is in the overall memory system.
This causes cognitive load. cognitive load is bad.
To minimize this, under such circumstances, you need to be more aggressive about deletion:
    - Be looser about what you consider to be similar. Some distinctions are not worth the energy to maintain.
    - Message out the parts to keep and ruthlessly throw away the rest
    - There is no free lunch here! at least some information must be deleted!

Do not create new tag names.


The proper noop syntax is:
{
    "consolidate_memories": []
    "keep_memories": []
}

The final output schema is:
<think> insert your chain of thought here. </think>
{
    "consolidate_memories": list of new memories to add
    "keep_memories": list of ids of old memories to keep
}
"""

QUERY_CONSTRUCTION_PROMPT = """
Your job is to construct effective search queries for a developer profile memory system.
Given a user's current question or action, generate queries that will retrieve relevant USER PREFERENCES and HABITS.

IMPORTANT: This queries USER-SPECIFIC profile memory (preferences, habits, expertise), NOT project details.
Project-specific information is stored separately in episodic memory with workspace as session ID.

The memory system contains user-specific information organized by tags such as:
- Preferred Languages
- Preferred Frameworks  
- Coding Style Preferences
- Development Tools
- Testing Preferences
- Architecture Preferences
- Design Pattern Preferences
- Code Review Habits
- Learning Style
- Documentation Habits
- Debugging Approach
- Performance Optimization Mindset
- Security Consciousness
- And many more (see UPDATE_PROMPT for full list)

Guidelines for query construction:
- Generate 2-5 queries that approach the question from different angles
- Focus on USER preferences, habits, and expertise - not project specifics
- Include both specific technical preferences and general working style
- Consider related preference areas that might inform the current task
- Think about what user preferences would be relevant to answer the query

Example scenarios:

User query: "Should I use TypeScript or JavaScript for this new component?"
{
    "queries": [
        "preferred frontend language TypeScript JavaScript",
        "type safety preferences",
        "frontend development preferences",
        "JavaScript framework preferences",
        "technology adoption philosophy"
    ]
}

User query: "How should I write tests for this feature?"
{
    "queries": [
        "testing methodology preferences",
        "test-driven development habits",
        "testing framework preferences",
        "code coverage expectations",
        "unit testing approach"
    ]
}

User query: "What code style should I follow?"
{
    "queries": [
        "coding style preferences",
        "linting and formatting tools",
        "code formatting standards",
        "naming convention preferences",
        "code organization philosophy"
    ]
}

User query: "I need to optimize this slow function"
{
    "queries": [
        "performance optimization approach",
        "debugging strategies",
        "profiling and benchmarking habits",
        "performance vs readability tradeoffs",
        "optimization mindset"
    ]
}

User query: "How do I structure this API?"
{
    "queries": [
        "API design philosophy",
        "RESTful API preferences",
        "architecture patterns preferences",
        "backend framework preferences",
        "code organization philosophy"
    ]
}

Output format:
{
    "queries": ["query1", "query2", "query3", ...]
}
"""
