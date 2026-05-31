# Assignment: Build Your Own LangGraph + MCP Agent

## Overview

Using the provided reference implementation (`agent.py`, `mcp_servers/`), build a **local MCP server** with custom tools and wire it up to a **LangGraph ReAct agent**. Each student has a unique use-case domain. You may reuse the reference code structure directly — the goal is to adapt it to your domain, not rewrite from scratch.

---

## How to Reuse the Reference Code

```
your_project/
├── agent.py                   ← copy & adapt from reference
├── mcp_servers/
│   └── your_server.py         ← your custom MCP server (replace notes/calculator)
├── data/                      ← your local data files (JSON, markdown, txt)
└── requirements.txt
```

**Steps:**
1. Copy `agent.py` from the reference project
2. Replace `MCP_CONFIG` to point to your server file
3. Update `SYSTEM_PROMPT` to describe your tools
4. Build `mcp_servers/your_server.py` with at least **4 tools** using `FastMCP`
5. Update `NOTES_SERVER`/`CALC_SERVER` references to your single server path
6. Run and test with `python -X utf8 agent.py`

**Minimal MCP server template:**
```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("your-server-name")

@mcp.tool()
def your_tool(param: str) -> str:
    """Tool description for the LLM."""
    # your logic here
    return result

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

---

## Evaluation Scorecard (Total: 100 Points)

| # | Criteria | Points |
|---|----------|--------|
| 1 | MCP server runs without errors and connects to agent | 15 |
| 2 | Minimum 4 working tools implemented with correct docstrings | 20 |
| 3 | LangGraph ReAct agent correctly routes to tools | 15 |
| 4 | Agent gives meaningful final answers using tool output | 15 |
| 5 | At least one tool reads/writes to a local data file | 10 |
| 6 | Demo: run 3 different queries end-to-end and show output | 10 |
| 7 | Human-in-the-Loop (HITL) enabled with approve/deny working | 10 |
| 8 | Code is clean: functions named clearly, no dead code | 5 |

**Bonus (+10):** Chain two or more tools in a single agent response (e.g. read data → calculate → summarize).

---

---

## Student Assignments

---

### 1. Chan Wei Khjan — Personal Finance Tracker

**Use Case:** An AI-powered assistant that helps you manage your personal budget. You store expense entries in a local JSON file and the agent helps you query, analyze, and summarize your spending.

**MCP Tools to Build (minimum 4):**
- `add_expense(category, amount, description, date)` → logs an expense entry
- `list_expenses(category=None)` → returns all expenses, optionally filtered by category
- `monthly_summary(month, year)` → total spending per category for a given month
- `top_spending_category()` → returns the category with highest total spend

**Sample Queries to Demo:**
1. `"Add an expense: Food, RM 45, lunch with friends, today"`
2. `"What did I spend the most on this month?"`
3. `"Give me a summary of my May expenses"`

**Data file:** `data/expenses.json` (list of `{date, category, amount, description}` objects)

---

### 2. Gurleen Kaur — Recipe Manager

**Use Case:** A cooking assistant that stores your personal recipe collection in markdown files and helps you find recipes based on what ingredients you have, calculate serving sizes, and suggest what to cook.

**MCP Tools to Build (minimum 4):**
- `list_recipes()` → lists all available recipe names
- `get_recipe(name)` → returns full recipe details (ingredients + steps)
- `search_by_ingredient(ingredient)` → finds all recipes containing that ingredient
- `scale_recipe(name, servings)` → adjusts ingredient quantities for N servings

**Sample Queries to Demo:**
1. `"What recipes can I make with chicken and garlic?"`
2. `"Show me the pasta recipe scaled for 6 people"`
3. `"List all my dessert recipes"`

**Data file:** `data/recipes/` — one `.md` file per recipe

---

### 3. Komal Patil — Study Planner

**Use Case:** A personal study assistant that helps you plan study sessions, track which topics you've covered, and calculate how much time you've studied. All data stored in a local JSON file.

**MCP Tools to Build (minimum 4):**
- `add_study_session(subject, topic, duration_minutes, date)` → logs a completed session
- `list_sessions(subject=None)` → shows all logged study sessions
- `total_hours_studied(subject)` → sums hours spent on a subject
- `suggest_next_topic(subject)` → returns the next unstudied topic from a predefined syllabus

**Sample Queries to Demo:**
1. `"I just studied Python for 90 minutes — log it"`
2. `"How many total hours have I studied for my ML exam?"`
3. `"What should I study next for Data Structures?"`

**Data file:** `data/study_log.json`, `data/syllabus.json`

---

### 4. Anived Mishra — Code Snippet Library

**Use Case:** A developer assistant that maintains a searchable library of reusable code snippets. Each snippet is stored as a file and the agent can retrieve, search, add, and explain snippets.

**MCP Tools to Build (minimum 4):**
- `save_snippet(title, language, code, tags)` → saves a new snippet to a file
- `list_snippets(language=None)` → lists all snippets, optionally filtered by language
- `search_snippets(keyword)` → finds snippets whose title, tags, or code match a keyword
- `get_snippet(title)` → retrieves the full code of a named snippet

**Sample Queries to Demo:**
1. `"Save this Python quicksort implementation with tags: sorting, algorithms"`
2. `"Find all my JavaScript snippets"`
3. `"Show me the snippet for binary search"`

**Data file:** `data/snippets/` — one `.txt` or `.md` file per snippet, with metadata header

---

### 5. Lalit Jain — Inventory Manager

**Use Case:** A small business inventory assistant. You track stock items in a JSON file. The agent helps you log stock updates, check low-inventory alerts, and generate reports.

**MCP Tools to Build (minimum 4):**
- `add_item(name, quantity, unit, reorder_threshold)` → adds a new inventory item
- `update_stock(name, quantity_change)` → increases or decreases stock (use negative for usage)
- `list_low_stock()` → returns all items below their reorder threshold
- `inventory_report()` → full inventory summary with total item count and total units

**Sample Queries to Demo:**
1. `"We used 50 units of raw cotton today — update the stock"`
2. `"Which items are running low and need to be reordered?"`
3. `"Give me a full inventory report"`

**Data file:** `data/inventory.json`

---

### 6. Gurkamal Singh — Fitness Tracker

**Use Case:** A personal fitness coach agent. You log your workouts, and the agent helps you track progress, calculate calories burned, and suggest improvements based on your history.

**MCP Tools to Build (minimum 4):**
- `log_workout(exercise, sets, reps_or_duration, date)` → records a workout session
- `list_workouts(exercise=None)` → shows workout history
- `calculate_calories(exercise, duration_minutes, weight_kg)` → estimates calories burned using MET values
- `weekly_summary()` → total workouts and estimated calories burned in the current week

**Sample Queries to Demo:**
1. `"I just did 4 sets of 12 reps of bench press — log it"`
2. `"How many calories did I burn running for 30 minutes at 70kg?"`
3. `"Give me my workout summary for this week"`

**Data file:** `data/workouts.json`, `data/met_values.json`

---

### 7. Joseph — Personal Book Library

**Use Case:** A reading assistant that manages your personal book collection. You can catalog books, mark them as read/unread/in-progress, rate them, and get reading statistics.

**MCP Tools to Build (minimum 4):**
- `add_book(title, author, genre, total_pages)` → adds a book to your library
- `update_status(title, status, current_page=None)` → sets status to `reading`, `completed`, or `want-to-read`
- `list_books(status=None, genre=None)` → lists books filtered by status or genre
- `reading_stats()` → total books read, pages read, favourite genre, average rating

**Sample Queries to Demo:**
1. `"Add 'Atomic Habits' by James Clear, self-help, 320 pages"`
2. `"I finished reading Sapiens — mark it complete"`
3. `"Show me all books I want to read"`

**Data file:** `data/library.json`

---

### 8. Siddhesh Sawant — Bug Tracker

**Use Case:** A developer tool that acts as a simple local bug tracker. You file bugs, update their status, assign priority, and query them — all through a conversational agent.

**MCP Tools to Build (minimum 4):**
- `file_bug(title, description, severity, component)` → creates a new bug entry with auto-ID
- `update_bug(bug_id, status=None, assignee=None, notes=None)` → updates bug fields
- `list_bugs(status=None, severity=None)` → returns bugs filtered by status or severity
- `bug_summary()` → counts of open, in-progress, and resolved bugs by component

**Sample Queries to Demo:**
1. `"File a new bug: login button unresponsive on mobile, severity high, component auth"`
2. `"Mark bug #3 as resolved"`
3. `"How many critical bugs are still open?"`

**Data file:** `data/bugs.json`

---

### 9. Karthik Balaje R — Student Grade Tracker

**Use Case:** A grade management assistant for a teacher or student. Store exam/assignment scores and compute GPA, class averages, and generate report-style summaries.

**MCP Tools to Build (minimum 4):**
- `add_grade(student_name, subject, score, max_score, assessment_type)` → logs a grade entry
- `get_student_report(student_name)` → shows all scores and overall percentage for a student
- `class_average(subject)` → calculates average score for a subject across all students
- `top_performers(n=3)` → lists the top N students by overall average

**Sample Queries to Demo:**
1. `"Add grade: Riya scored 88/100 in Math, mid-term exam"`
2. `"Generate a report card for Arjun"`
3. `"Who are the top 3 students this semester?"`

**Data file:** `data/grades.json`

---

### 10. Sai Sankar — Event Planner

**Use Case:** A personal event planning assistant. You create events, manage guest lists, and the agent helps you track RSVPs, check for scheduling conflicts, and summarize upcoming events.

**MCP Tools to Build (minimum 4):**
- `create_event(name, date, location, description)` → creates a new event entry
- `add_guest(event_name, guest_name, rsvp_status)` → adds/updates a guest's RSVP
- `list_upcoming_events()` → shows all future events sorted by date
- `event_summary(event_name)` → shows event details with confirmed vs pending guest count

**Sample Queries to Demo:**
1. `"Create event: Team Lunch, 2026-06-15, Conference Room A"`
2. `"Mark Priya as confirmed for Team Lunch"`
3. `"What events do I have coming up and how many confirmed attendees?"`

**Data file:** `data/events.json`

---

### 11. Bala Krishna Yenumula — Task Manager

**Use Case:** A productivity assistant that manages your to-do list. Tasks have priorities, deadlines, and tags. The agent helps you add, update, complete, and prioritize your work.

**MCP Tools to Build (minimum 4):**
- `add_task(title, priority, deadline, tags)` → creates a task
- `complete_task(task_id)` → marks a task as done
- `list_tasks(priority=None, tag=None, show_completed=False)` → filtered task list
- `overdue_tasks()` → returns all tasks past their deadline that are still open

**Sample Queries to Demo:**
1. `"Add task: Submit assignment, priority high, deadline 2026-06-05, tag: college"`
2. `"What high-priority tasks do I have left?"`
3. `"Which tasks am I already overdue on?"`

**Data file:** `data/tasks.json`

---

### 12. Beadon Roy — Personal Weather Journal

**Use Case:** A weather observation logger and analyzer. You record daily weather observations (temperature, condition, notes) and the agent helps you spot patterns, compare days, and generate monthly weather summaries.

**MCP Tools to Build (minimum 4):**
- `log_weather(date, temperature_c, condition, humidity_percent, notes)` → records an observation
- `get_day(date)` → retrieves observation for a specific date
- `monthly_summary(month, year)` → average temp, most common condition, extremes
- `search_by_condition(condition)` → finds all days matching a weather condition (e.g., "rainy")

**Sample Queries to Demo:**
1. `"Log today's weather: 32°C, sunny, 60% humidity, clear skies"`
2. `"How was the weather on 2026-05-20?"`
3. `"Give me a summary of May 2026 — what was the average temperature?"`

**Data file:** `data/weather_journal.json`

---

### 13. Sagar Sable — Restaurant Menu Manager

**Use Case:** A restaurant assistant that manages a digital menu. The agent helps add/update dishes, handle dietary filters, calculate order totals, and suggest popular items.

**MCP Tools to Build (minimum 4):**
- `add_dish(name, category, price, dietary_tags, description)` → adds a dish to the menu
- `list_menu(category=None, dietary_filter=None)` → shows filtered menu
- `calculate_order(dish_names_and_quantities)` → takes a list of `{dish, qty}` and returns total bill
- `most_popular_category()` → returns the category with the most dishes (simulates popularity)

**Sample Queries to Demo:**
1. `"Add dish: Paneer Tikka, Starters, ₹250, vegetarian"`
2. `"Show me all vegetarian main course options"`
3. `"Calculate the total for: 2 Paneer Tikka, 1 Dal Makhani, 3 Rotis"`

**Data file:** `data/menu.json`

---

### 14. Ankith Dasu — Travel Planner

**Use Case:** A travel assistant that helps you plan trips. You store destinations, itineraries, and the agent helps you with trip planning, distance estimates, currency conversion, and packing checklists.

**MCP Tools to Build (minimum 4):**
- `add_destination(name, country, best_season, notes)` → adds a travel destination to your wishlist
- `create_itinerary(trip_name, destinations, start_date, duration_days)` → plans a trip
- `convert_currency(amount, from_currency, to_currency)` → uses hardcoded exchange rates for conversion
- `packing_checklist(climate_type, duration_days)` → generates a packing list based on climate and length

**Sample Queries to Demo:**
1. `"Add Bali, Indonesia to my wishlist — best season is April"`
2. `"Convert 5000 INR to USD"`
3. `"Generate a packing list for a 7-day tropical trip"`

**Data file:** `data/destinations.json`, `data/itineraries.json`, `data/exchange_rates.json`

---

### 15. Tilottama Pawar — Quote & Inspiration Library

**Use Case:** An inspiration assistant that maintains your personal quote collection. Add quotes, browse by author or category, get a random motivational quote, and generate themed quote collections.

**MCP Tools to Build (minimum 4):**
- `add_quote(text, author, category, source=None)` → saves a new quote
- `random_quote(category=None)` → returns a random quote, optionally from a category
- `quotes_by_author(author)` → lists all quotes from a specific author
- `search_quotes(keyword)` → finds quotes containing a keyword in text or author

**Sample Queries to Demo:**
1. `"Save this quote: 'The only way to do great work is to love what you do' — Steve Jobs, category: motivation"`
2. `"Give me a random quote about resilience"`
3. `"Show all quotes by Marcus Aurelius"`

**Data file:** `data/quotes.json`

---

### 16. Mini Yadav — Vocabulary Builder

**Use Case:** A language learning assistant that helps you grow your vocabulary. You add new words with definitions, track which ones you've mastered, quiz yourself, and see learning stats.

**MCP Tools to Build (minimum 4):**
- `add_word(word, definition, example_sentence, difficulty)` → adds a word to your vocabulary list
- `get_word(word)` → retrieves a word's details
- `quiz_me(difficulty=None)` → returns a random unmastered word for practice
- `mark_mastered(word)` → marks a word as learned
- `learning_stats()` → total words, mastered count, words by difficulty

**Sample Queries to Demo:**
1. `"Add the word 'ephemeral' — meaning: lasting for a very short time, difficulty: hard"`
2. `"Quiz me on a medium difficulty word"`
3. `"Show my vocabulary learning stats"`

**Data file:** `data/vocabulary.json`

---

### 17. Jocelyn Jose — Personal Health Log

**Use Case:** A personal health tracking assistant. You log daily vitals (weight, blood pressure, heart rate), medications taken, and symptoms. The agent helps you spot trends and generate health summaries.

**MCP Tools to Build (minimum 4):**
- `log_vitals(date, weight_kg, blood_pressure, heart_rate, notes)` → records daily health data
- `log_medication(date, medication_name, dosage, time_taken)` → logs medication intake
- `health_summary(days=7)` → average vitals over the past N days
- `search_symptoms(symptom_keyword)` → finds all entries where a symptom was noted

**Sample Queries to Demo:**
1. `"Log today's vitals: 68kg, BP 120/80, heart rate 72"`
2. `"Log that I took Vitamin D 1000IU this morning"`
3. `"Give me a health summary for the past 7 days"`

**Data file:** `data/health_log.json`, `data/medications.json`

---

## Submission Checklist

Before submitting, verify all of the following:

- [ ] `mcp_servers/your_server.py` runs standalone without errors: `python mcp_servers/your_server.py`
- [ ] Agent connects to your server and lists your tools on startup
- [ ] All 4+ tools return sensible output when called
- [ ] At least one tool reads from or writes to a local file in `data/`
- [ ] You can demonstrate 3 different queries end-to-end
- [ ] HITL mode: approve a tool call and deny a tool call — agent responds correctly to both
- [ ] No hardcoded API keys in committed code (use `.env` or environment variables)
- [ ] `README.md` with setup instructions and your 3 demo queries

---

## Submission

Push your code to a **public GitHub repository** and share the link.  
Repository name format: `mcp-agent-<your-first-name-lowercase>` (e.g., `mcp-agent-gurleen`)

**Due Date:** Confirm with instructor.
