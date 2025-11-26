import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

class TriviaGameService:
    """
    Trivia game:
    - 10 questions per run (LEVELS = 10)
    - Base scoring: 100 points for any correct answer
    - Streak bonus: +10 points per streak level above 1
        1st correct in a row: 100
        2nd in a row: 100 + 10  = 110
        3rd in a row: 100 + 20  = 120
        ...
    - Max score for 10/10:
        base: 10 * 100 = 1000
        bonus: 10 + 20 + ... + 90 = 450
        total max = 1450
    - Question set depends on the current day of the week
    - Logged-in users: once per day (state + leaderboard)
    - Guests: can play anytime, but scores are not saved
    """

    LEVELS = 10
    BASE_POINTS = 100
    STREAK_INCREMENT = 10

    # 0 = Monday, 6 = Sunday
    QUESTIONS_BY_DAY: Dict[int, List[Dict[str, Any]]] = {
        0: [  # Monday
            {
                "question": "What does CPU stand for?",
                "choices": [
                    "Central Processing Unit",
                    "Computer Personal Unit",
                    "Central Peripheral Utility",
                    "Compute Processing Utility",
                ],
                "answer_index": 0,
                "difficulty": "easy",
                "explanation": "CPU stands for Central Processing Unit, the 'brain' of the computer.",
            },
            {
                "question": "Which data structure uses FIFO order?",
                "choices": ["Stack", "Queue", "Tree", "Graph"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Queues use FIFO (First-In, First-Out) ordering.",
            },
            {
                "question": "What is the time complexity of binary search on a sorted array?",
                "choices": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Binary search halves the search space each step, giving O(log n) time.",
            },
            {
                "question": "In networking, what does HTTPS add over HTTP?",
                "choices": ["Compression", "Encryption", "Caching", "Routing"],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "HTTPS adds encryption (via TLS) on top of HTTP.",
            },
            {
                "question": "Which language is primarily used for styling web pages?",
                "choices": ["HTML", "CSS", "JavaScript", "Python"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "CSS (Cascading Style Sheets) is used to style web pages.",
            },
            {
                "question": "Which device is responsible for forwarding packets between networks?",
                "choices": ["Switch", "Router", "Hub", "Repeater"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Routers connect different networks and forward packets between them.",
            },
            {
                "question": "What is the smallest addressable unit of memory?",
                "choices": ["Bit", "Byte", "Word", "Block"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "A byte (8 bits) is the smallest addressable unit in most architectures.",
            },
            {
                "question": "Which part of the OS is responsible for managing processes?",
                "choices": ["Shell", "Kernel", "File System", "Device Driver"],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "The kernel manages processes, memory, and hardware resources.",
            },
            {
                "question": "What is a common unit for CPU clock speed?",
                "choices": ["Bytes per second", "Gigahertz", "Megabytes", "Nanoseconds"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "CPU clocks are commonly measured in gigahertz (GHz).",
            },
            {
                "question": "Which component typically stores the operating system during normal operation?",
                "choices": ["CPU cache", "GPU", "Main memory (RAM)", "Secondary storage (SSD/HDD)"],
                "answer_index": 3,
                "difficulty": "medium",
                "explanation": "The OS is stored on secondary storage and loaded into RAM when running.",
            },
        ],
        1: [  # Tuesday
            {
                "question": "What is the main purpose of RAM in a computer?",
                "choices": [
                    "Permanent storage",
                    "Temporary working memory",
                    "Graphics processing",
                    "Network communication",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "RAM is the computer's short-term working memory.",
            },
            {
                "question": "Which of these is a relational database?",
                "choices": ["MongoDB", "Redis", "PostgreSQL", "Cassandra"],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "PostgreSQL is a popular open-source relational database.",
            },
            {
                "question": "Which HTTP status code indicates 'Not Found'?",
                "choices": ["200", "301", "404", "500"],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "404 is the standard code for 'Not Found'.",
            },
            {
                "question": "In Git, which command creates a new branch?",
                "choices": [
                    "git clone",
                    "git checkout -b",
                    "git merge",
                    "git status",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "git checkout -b <name> creates and switches to a new branch.",
            },
            {
                "question": "What does SQL stand for?",
                "choices": [
                    "Simple Question Language",
                    "Structured Query Language",
                    "Sequential Query Logic",
                    "Standard Query Language",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "SQL stands for Structured Query Language.",
            },
            {
                "question": "Which SQL command is used to retrieve data?",
                "choices": ["INSERT", "UPDATE", "SELECT", "DELETE"],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "SELECT is used to query and retrieve data.",
            },
            {
                "question": "What is a primary key in a relational table?",
                "choices": [
                    "A column that can be null",
                    "A unique identifier for each row",
                    "A foreign key reference",
                    "A text-only column",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "A primary key uniquely identifies each row in a table.",
            },
            {
                "question": "Which operation combines rows from two tables based on a related column?",
                "choices": ["JOIN", "GROUP BY", "ORDER BY", "LIMIT"],
                "answer_index": 0,
                "difficulty": "medium",
                "explanation": "JOIN combines rows from different tables based on a related column.",
            },
            {
                "question": "In Git, which command uploads local commits to a remote repository?",
                "choices": ["git pull", "git push", "git fetch", "git init"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "git push sends your commits to a remote repository.",
            },
            {
                "question": "Which HTTP method is typically used to create a new resource?",
                "choices": ["GET", "POST", "PUT", "DELETE"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "POST is commonly used to create new resources on the server.",
            },
        ],
        2: [  # Wednesday
            {
                "question": "Which of these is NOT a NoSQL database?",
                "choices": ["MongoDB", "Redis", "PostgreSQL", "Cassandra"],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "PostgreSQL is a relational (SQL) database, not NoSQL.",
            },
            {
                "question": "Which of the following is a compiled language?",
                "choices": ["Python", "JavaScript", "C++", "PHP"],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "C++ is compiled to machine code before execution.",
            },
            {
                "question": "What does 'OOP' stand for?",
                "choices": [
                    "Object-Oriented Programming",
                    "Operational Output Processing",
                    "Ordered Object Processing",
                    "Optimized Oriented Program",
                ],
                "answer_index": 0,
                "difficulty": "easy",
                "explanation": "OOP stands for Object-Oriented Programming.",
            },
            {
                "question": "Which data structure is best for implementing a LIFO behavior?",
                "choices": ["Queue", "Array", "Stack", "Linked List"],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "Stacks use LIFO (Last-In, First-Out) ordering.",
            },
            {
                "question": "Which protocol is used to send emails?",
                "choices": ["HTTP", "SMTP", "FTP", "SSH"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "SMTP (Simple Mail Transfer Protocol) is used for sending email.",
            },
            {
                "question": "In OOP, what is 'inheritance'?",
                "choices": [
                    "Copying code between files",
                    "Reusing interfaces only",
                    "Creating new classes based on existing ones",
                    "Sharing global variables",
                ],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "Inheritance lets a class derive from another, reusing and extending behavior.",
            },
            {
                "question": "What does 'polymorphism' allow in OOP?",
                "choices": [
                    "Multiple inheritance",
                    "Different types to be treated through a common interface",
                    "Copying objects",
                    "Automatic memory management",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Polymorphism lets different types be used interchangeably via a common interface.",
            },
            {
                "question": "Which keyword in many OOP languages refers to the current instance?",
                "choices": ["self/this", "super", "base", "instance"],
                "answer_index": 0,
                "difficulty": "easy",
                "explanation": "Most OOP languages use 'this' or 'self' for the current object.",
            },
            {
                "question": "Which of these is an OOP principle?",
                "choices": ["Compilation", "Encapsulation", "Refactoring", "Debugging"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Encapsulation is one of the core OOP principles.",
            },
            {
                "question": "What is an 'abstract class'?",
                "choices": [
                    "A class with no methods",
                    "A class with at least one abstract method and not directly instantiable",
                    "A compiled class",
                    "A class without inheritance",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Abstract classes define common behavior but aren't meant to be instantiated directly.",
            },
        ],
        3: [  # Thursday
            {
                "question": "Which sorting algorithm is typically fastest on average for large random arrays?",
                "choices": ["Bubble Sort", "Insertion Sort", "Quick Sort", "Selection Sort"],
                "answer_index": 2,
                "difficulty": "hard",
                "explanation": "Quick Sort is usually fastest on average for large random data.",
            },
            {
                "question": "What is the worst-case time complexity of Quick Sort?",
                "choices": ["O(n)", "O(n log n)", "O(log n)", "O(n^2)"],
                "answer_index": 3,
                "difficulty": "hard",
                "explanation": "Quick Sort degrades to O(n^2) in the worst case.",
            },
            {
                "question": "Which of these is a symmetric encryption algorithm?",
                "choices": ["RSA", "ECC", "AES", "Diffie–Hellman"],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "AES is a widely used symmetric-key algorithm.",
            },
            {
                "question": "Which layer of the OSI model does TCP operate at?",
                "choices": ["Application", "Transport", "Network", "Data Link"],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "TCP is a Transport layer protocol.",
            },
            {
                "question": "What is the main purpose of a firewall?",
                "choices": [
                    "Encrypt files",
                    "Block or allow network traffic",
                    "Scan for malware",
                    "Compress data",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Firewalls control which network traffic is allowed or blocked.",
            },
            {
                "question": "Which sorting algorithm has a guaranteed O(n log n) worst-case time?",
                "choices": ["Quick Sort", "Merge Sort", "Insertion Sort", "Bubble Sort"],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Merge Sort guarantees O(n log n) in the worst case.",
            },
            {
                "question": "Which data structure is typically used to implement a priority queue?",
                "choices": ["Stack", "Queue", "Heap", "ArrayList"],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "Heaps are commonly used to implement priority queues efficiently.",
            },
            {
                "question": "Which type of cryptography uses a pair of public and private keys?",
                "choices": ["Symmetric", "Asymmetric", "Hash-based", "Quantum"],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Asymmetric cryptography uses a public/private key pair.",
            },
            {
                "question": "What does TLS stand for?",
                "choices": [
                    "Transport Layer Security",
                    "Transmission Link Service",
                    "Trusted Login System",
                    "Technical Layer Shield",
                ],
                "answer_index": 0,
                "difficulty": "easy",
                "explanation": "TLS stands for Transport Layer Security and secures network communication.",
            },
            {
                "question": "Which protocol is commonly used for secure remote login?",
                "choices": ["FTP", "SSH", "Telnet", "SNMP"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "SSH (Secure Shell) is used for secure remote access.",
            },
        ],
        4: [  # Friday
            {
                "question": "What does 'MITM' stand for in cybersecurity?",
                "choices": [
                    "Machine In The Middle",
                    "Man In The Middle",
                    "Malware In The Machine",
                    "Message Integrity Transfer Mode",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "MITM stands for Man In The Middle, a type of interception attack.",
            },
            {
                "question": "Which port is the default for HTTPS?",
                "choices": ["21", "22", "80", "443"],
                "answer_index": 3,
                "difficulty": "easy",
                "explanation": "HTTPS traffic normally uses TCP port 443.",
            },
            {
                "question": "What does XSS stand for?",
                "choices": [
                    "Cross-Site Scripting",
                    "Cross-Server Security",
                    "XML Site Security",
                    "Cross-Site Security",
                ],
                "answer_index": 0,
                "difficulty": "medium",
                "explanation": "XSS stands for Cross-Site Scripting.",
            },
            {
                "question": "Which of the following best describes a 'phishing' attack?",
                "choices": [
                    "Brute-force password guessing",
                    "Tricking users into revealing information",
                    "Overloading a server with traffic",
                    "Injecting SQL commands",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Phishing tricks users into sharing credentials or sensitive data.",
            },
            {
                "question": "What is a common hashing algorithm used for checksums?",
                "choices": ["RSA", "SHA-256", "AES", "3DES"],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "SHA-256 is a widely used cryptographic hash function.",
            },
            {
                "question": "Which vulnerability allows attackers to inject database queries via user input?",
                "choices": ["XSS", "CSRF", "SQL Injection", "RCE"],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "SQL Injection lets attackers manipulate database queries.",
            },
            {
                "question": "What does CSRF stand for?",
                "choices": [
                    "Cross-Site Request Forgery",
                    "Cross-Site Resource Fetch",
                    "Client-Side Request Filter",
                    "Critical System Remote Function",
                ],
                "answer_index": 0,
                "difficulty": "medium",
                "explanation": "CSRF tricks a user’s browser into making unwanted requests.",
            },
            {
                "question": "Which of the following is a good password hygiene practice?",
                "choices": [
                    "Reusing passwords",
                    "Using short passwords",
                    "Using a password manager",
                    "Sharing passwords with colleagues",
                ],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "Password managers help create and store strong unique passwords.",
            },
            {
                "question": "What is '2FA' or 'MFA' primarily used for?",
                "choices": [
                    "Reducing storage usage",
                    "Improving network speed",
                    "Adding extra layers of authentication",
                    "Encrypting databases",
                ],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "Multi-factor authentication adds extra verification factors to logins.",
            },
            {
                "question": "Which one is a common way malware spreads?",
                "choices": [
                    "Strong encryption",
                    "Security patches",
                    "Opening malicious email attachments",
                    "Regular backups",
                ],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "Malware often spreads through users opening malicious attachments or links.",
            },
        ],
        5: [  # Saturday
            {
                "question": "Which HTTP method is typically used to update an existing resource?",
                "choices": ["GET", "POST", "PUT", "DELETE"],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "PUT is commonly used to update an existing resource.",
            },
            {
                "question": "What does REST stand for?",
                "choices": [
                    "Representational State Transfer",
                    "Remote Execution Service Transport",
                    "Reliable State Transfer",
                    "Resource Execution Service Type",
                ],
                "answer_index": 0,
                "difficulty": "easy",
                "explanation": "REST stands for Representational State Transfer.",
            },
            {
                "question": "What is JSON primarily used for?",
                "choices": [
                    "Image compression",
                    "Data interchange",
                    "Database indexing",
                    "File encryption",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "JSON is a lightweight data-interchange format.",
            },
            {
                "question": "Which of these is a JavaScript runtime?",
                "choices": ["Django", "Node.js", "Flask", ".NET"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Node.js is a JavaScript runtime built on Chrome's V8 engine.",
            },
            {
                "question": "Which command installs packages in a Node.js project?",
                "choices": ["npm install", "git install", "node install", "yarn run"],
                "answer_index": 0,
                "difficulty": "easy",
                "explanation": "npm install installs dependencies in a Node.js project.",
            },
            {
                "question": "In RESTful APIs, which format is most commonly used for responses?",
                "choices": ["XML only", "Binary", "JSON", "CSV"],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "JSON is the most common format for REST API responses.",
            },
            {
                "question": "What does an HTTP 201 status code represent?",
                "choices": ["OK", "Created", "No Content", "Bad Request"],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "201 Created is returned when a resource is successfully created.",
            },
            {
                "question": "Which header is often used to send JSON in an HTTP request?",
                "choices": [
                    "Content-Type: application/json",
                    "Accept-Encoding: gzip",
                    "Authorization: Basic",
                    "Cache-Control: no-cache",
                ],
                "answer_index": 0,
                "difficulty": "easy",
                "explanation": "Content-Type: application/json indicates a JSON request body.",
            },
            {
                "question": "Which HTTP method is considered idempotent (in theory)?",
                "choices": ["POST", "PATCH", "PUT", "CONNECT"],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "PUT is intended to be idempotent: multiple identical requests have the same effect.",
            },
            {
                "question": "What does CORS stand for?",
                "choices": [
                    "Cross-Origin Resource Sharing",
                    "Client-Origin Request System",
                    "Centralized Origin Routing Service",
                    "Cross-Organizational Resource Server",
                ],
                "answer_index": 0,
                "difficulty": "medium",
                "explanation": "CORS controls how resources can be requested from different origins.",
            },
        ],
        6: [  # Sunday
            {
                "question": "What is the main advantage of using a CDN?",
                "choices": [
                    "More secure passwords",
                    "Reduced latency and faster content delivery",
                    "Automatic code deployment",
                    "Better database indexing",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "CDNs serve content from locations closer to users, reducing latency.",
            },
            {
                "question": "What is 'latency' in networking?",
                "choices": [
                    "Total bandwidth available",
                    "Number of users on the network",
                    "Delay between request and response",
                    "Amount of data stored",
                ],
                "answer_index": 2,
                "difficulty": "easy",
                "explanation": "Latency is the delay between sending a request and receiving a response.",
            },
            {
                "question": "Which cloud service model provides virtual machines?",
                "choices": ["SaaS", "PaaS", "IaaS", "FaaS"],
                "answer_index": 2,
                "difficulty": "medium",
                "explanation": "IaaS (Infrastructure as a Service) typically provides VMs and networking.",
            },
            {
                "question": "Which of these best describes containerization?",
                "choices": [
                    "Encrypting application data",
                    "Running applications in isolated environments",
                    "Compressing binaries",
                    "Virtualizing operating systems only",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Containers run apps in lightweight, isolated environments.",
            },
            {
                "question": "What is Kubernetes primarily used for?",
                "choices": [
                    "Source control",
                    "Container orchestration",
                    "Static code analysis",
                    "Continuous integration",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Kubernetes automates deployment and management of containers.",
            },
            {
                "question": "What does 'scalability' mean in cloud computing?",
                "choices": [
                    "Encrypting data at rest",
                    "The ability to handle increased load by adding resources",
                    "Using only local servers",
                    "Compressing network traffic",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Scalability is about handling more load by increasing resources.",
            },
            {
                "question": "Which provider is NOT a major cloud platform?",
                "choices": ["AWS", "Azure", "GCP", "MySQL"],
                "answer_index": 3,
                "difficulty": "easy",
                "explanation": "MySQL is a database, not a cloud provider.",
            },
            {
                "question": "What is 'serverless' computing?",
                "choices": [
                    "Computing without physical servers",
                    "Cloud functions where infrastructure is managed by the provider",
                    "Only using client-side code",
                    "Using bare-metal servers",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Serverless means you deploy code without managing servers yourself.",
            },
            {
                "question": "What does 'multi-region deployment' help with?",
                "choices": [
                    "Code readability",
                    "Latency and fault tolerance",
                    "Unit testing",
                    "CI/CD speed",
                ],
                "answer_index": 1,
                "difficulty": "medium",
                "explanation": "Deploying in multiple regions improves latency and resilience.",
            },
            {
                "question": "What does 'pay-as-you-go' pricing mean in cloud platforms?",
                "choices": [
                    "Flat monthly fees only",
                    "Paying only for resources you actually consume",
                    "Paying yearly for all resources",
                    "Paying only for storage",
                ],
                "answer_index": 1,
                "difficulty": "easy",
                "explanation": "Pay-as-you-go means you are billed based on actual resource usage.",
            },
        ],
    }

    def __init__(self, game_state, game_history, leaderboard):
        self.game_state = game_state
        self.game_history = game_history
        self.leaderboard = leaderboard
        self.active_sessions = _ACTIVE_SESSIONS

        # Max possible score for a perfect game (10 correct in a row)
        base = self.LEVELS * self.BASE_POINTS
        bonus = self.STREAK_INCREMENT * ((self.LEVELS - 1) * self.LEVELS // 2)
        self.max_score = base + bonus

    async def can_play_today(self, id: int) -> Dict[str, Any]:
        state = await self.game_state.get_state(id, "Trivia")

        if state["can_play"]:
            return {"can_play": True}

        next_play_time = state["next_play_time"]
        if next_play_time is None:
            return {"can_play": True}

        return {
            "can_play": False,
            "next_play_time": next_play_time.isoformat(),
            "message": "You have already played the trivia game today",
        }

    def _get_daily_questions(self) -> List[Dict[str, Any]]:
        """Return today's question set based on day of week (0=Monday)."""
        today = datetime.now(timezone.utc).date()
        weekday = today.weekday()  # 0–6
        questions = self.QUESTIONS_BY_DAY.get(weekday)

        if not questions:
            # Fallback: pick the first available set
            for q_list in self.QUESTIONS_BY_DAY.values():
                if q_list:
                    questions = q_list
                    break

        if not questions or len(questions) < self.LEVELS:
            raise RuntimeError("Not enough questions configured for today.")

        # Copy to avoid mutating the class-level constants
        return [q.copy() for q in questions[: self.LEVELS]]

    async def start_game(self, id: Optional[int] = None, name: Optional[str] = None) -> Dict[str, Any]:
        if id is not None:
            can_play = await self.can_play_today(id)
            if not can_play["can_play"]:
                return can_play

        session_id = str(uuid.uuid4())
        questions = self._get_daily_questions()

        self.active_sessions[session_id] = {
            "id": id,
            "name": name,
            "score": 0,
            "index": 0,
            "questions": questions,
            "started_at": datetime.now(timezone.utc),
            "streak": 0,
            "best_streak": 0,
        }

        return {
            "can_play": True,
            "session_id": session_id,
            "current_question": 1,
            "total_questions": self.LEVELS,
            "is_guest": id is None,
        }

    async def get_current_question(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")

        session = self.active_sessions[session_id]
        idx = session["index"]
        q = session["questions"][idx]

        return {
            "question_number": idx + 1,
            "total_questions": self.LEVELS,
            "question": q["question"],
            "choices": q["choices"],
            "difficulty": q.get("difficulty", "unknown"),
            "score": session["score"],
            "streak": session.get("streak", 0),
            "best_streak": session.get("best_streak", 0),
        }

    async def submit_answer(self, session_id: str, answer_index: int) -> Dict[str, Any]:
        if session_id not in self.active_sessions:
            raise ValueError("Invalid session ID")

        session = self.active_sessions[session_id]
        idx = session["index"]
        q = session["questions"][idx]

        correct_index = q["answer_index"]
        is_correct = answer_index == correct_index
        explanation = q.get("explanation", "")

        # --- SCORING + HOT STREAK LOGIC ---
        if is_correct:
            # update streak first
            session["streak"] = session.get("streak", 0) + 1
            session["best_streak"] = max(
                session.get("best_streak", 0), session["streak"]
            )

            # streak bonus: 2 in a row = +10, 3 in a row = +20, etc.
            bonus = max(0, (session["streak"] - 1) * self.STREAK_INCREMENT)

            # total points for this question
            points_for_this_question = self.BASE_POINTS + bonus
            session["score"] += points_for_this_question
        else:
            # wrong answer breaks the streak
            session["streak"] = 0

        # Move to next question
        session["index"] += 1

        if session["index"] < self.LEVELS:
            return {
                "is_correct": is_correct,
                "correct_index": correct_index,
                "score": session["score"],
                "game_over": False,
                "next_question": session["index"] + 1,
                "message": (
                    f"Correct! 🔥 Streak: {session['streak']}"
                    if is_correct
                    else f"Wrong! Correct answer was: {q['choices'][correct_index]}"
                ),
                "streak": session.get("streak", 0),
                "best_streak": session.get("best_streak", 0),
                "explanation": explanation,
            }

        # Game finished
        return await self._complete_game(
            session_id,
            is_correct,
            q["choices"][correct_index],
            explanation,
        )

    async def _complete_game(
        self,
        session_id: str,
        last_correct: bool,
        last_correct_text: str,
        explanation: str,
    ) -> Dict[str, Any]:
        session = self.active_sessions[session_id]
        id = session["id"]
        player_name = session["name"]
        final_score = session["score"]
        best_streak = session.get("best_streak", 0)
        now = datetime.now(timezone.utc)

        if id is not None:
            next_midnight = (
                (now + timedelta(days=1))
                .replace(hour=0, minute=0, second=0, microsecond=0)
            )

            await self.game_state.update_state(id, "Trivia", now, next_midnight)
            await self.game_history.add_entry(id, "Trivia", final_score, now)
            await self.leaderboard.update_scores(
                id, player_name, final_score, "Trivia", now, now
            )

        del self.active_sessions[session_id]

        return {
            "is_correct": last_correct,
            "game_over": True,
            "final_score": final_score,
            "max_score": self.max_score,
            "score_saved": id is not None,
            "best_streak": best_streak,
            "explanation": explanation,
            "message": (
                f"Game complete! 🔥 Best streak: {best_streak}"
                if last_correct
                else f"Game complete! Last correct answer was: {last_correct_text} (Best streak: {best_streak})"
            ),
        }

    def cleanup_inactive_sessions(self):
        now = datetime.now(timezone.utc)
        expired: List[str] = []

        for session_id, session in self.active_sessions.items():
            age = (now - session["started_at"]).total_seconds()
            if age > 3600:
                expired.append(session_id)

        for session_id in expired:
            del self.active_sessions[session_id]

def get_trivia_game_service(
    game_state=None,
    game_history=None,
    leaderboard=None,
) -> "TriviaGameService":
    return TriviaGameService(game_state, game_history, leaderboard)
