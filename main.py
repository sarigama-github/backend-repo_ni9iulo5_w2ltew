import os
import base64
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Habit, RoadmapItem, Resource, Progress, Message

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Habit Genius API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_name"] = getattr(db, "name", None)
            collections = db.list_collection_names()
            response["collections"] = collections
            response["database"] = "✅ Connected & Working"
            response["connection_status"] = "Connected"
        else:
            response["database"] = "❌ Not Initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:120]}"
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# --------- Helpers: simple generation logic (rule-based, no external deps) ---------
class GenerateRequest(BaseModel):
    habit: str
    description: Optional[str] = None

class GenerateResponse(BaseModel):
    roadmap: List[RoadmapItem]
    resources: List[Resource]


def generate_roadmap_and_resources(habit_id: str, habit: str, description: Optional[str]):
    habit_lower = habit.lower()

    # Milestones template
    milestones = [
        ("Define success & baseline", "Write your why, measure current level", 0),
        ("Learn the fundamentals", "Pick a starter guide and finish it", 1),
        ("Build a repeatable routine", "Set time, trigger, environment", 2),
        ("Deepen practice", "Do 14-day focused streak", 3),
        ("Showcase milestone", "Publish a small project or reflection", 4),
    ]

    roadmap_items: List[RoadmapItem] = []
    for title, desc, order in milestones:
        roadmap_items.append(RoadmapItem(
            habit_id=habit_id,
            title=title,
            description=desc,
            order=order,
            completed=False,
        ))

    # Resources template based on keywords
    resources: List[Resource] = []
    def add_res(title, url, type="article", provider=None, notes=None):
        resources.append(Resource(habit_id=habit_id, title=title, url=url, type=type, provider=provider, notes=notes))

    if "design" in habit_lower:
        add_res("UI Design Crash Course", "https://youtu.be/_Hp_dI0DzY4", type="video", provider="Jesse Showalter")
        add_res("Refactoring UI", "https://www.refactoringui.com/", type="course", provider="Adam Wathan")
        add_res("Laws of UX", "https://lawsofux.com/", type="article")
        add_res("Awesome Design Tools", "https://github.com/goabstract/Awesome-Design-Tools", type="article")
    if "work out" in habit_lower or "workout" in habit_lower or "fitness" in habit_lower:
        add_res("Beginner Bodyweight Workout", "https://www.nerdfitness.com/blog/beginner-bodyweight-workout/")
        add_res("Athlean-X", "https://www.youtube.com/@athleanx", type="video")
        add_res("r/Fitness Wiki", "https://thefitness.wiki/", type="article")
    if "read" in habit_lower:
        add_res("How to Read More Books", "https://jamesclear.com/reading", type="article")
        add_res("Readwise", "https://readwise.io/", type="tool")
        add_res("Blinkist", "https://www.blinkist.com/", type="tool")

    # Always add some general-purpose resources
    add_res("Atomic Habits Summary", "https://jamesclear.com/atomic-habits", type="article", provider="James Clear")
    add_res("Building a Habit Streak", "https://www.youtube.com/watch?v=U_nzqnXWvSo", type="video", provider="Ali Abdaal")

    return roadmap_items, resources

# ------------------------- API: Habits -------------------------
class HabitCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_days_per_week: int = 5

@app.post("/api/habits")
async def create_habit(payload: HabitCreate):
    habit_doc = Habit(
        name=payload.name,
        description=payload.description,
        target_days_per_week=payload.target_days_per_week,
    )
    habit_id = create_document("habit", habit_doc)

    roadmap_items, resources = generate_roadmap_and_resources(habit_id, payload.name, payload.description)

    # Persist roadmap + resources
    for item in roadmap_items:
        create_document("roadmapitem", item)
    for res in resources:
        create_document("resource", res)

    return {"habit_id": habit_id, "message": "Habit created with roadmap and resources"}

@app.get("/api/habits")
async def list_habits():
    docs = get_documents("habit")
    # convert ObjectId to string if present
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return docs

@app.get("/api/habits/{habit_id}/roadmap")
async def get_habit_roadmap(habit_id: str):
    items = get_documents("roadmapitem", {"habit_id": habit_id})
    for d in items:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    items.sort(key=lambda x: x.get("order", 0))
    return items

@app.get("/api/habits/{habit_id}/resources")
async def get_habit_resources(habit_id: str):
    items = get_documents("resource", {"habit_id": habit_id})
    for d in items:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return items

# ------------------------- API: Progress -------------------------
class ProgressCreate(BaseModel):
    habit_id: str
    note: Optional[str] = None
    image_base64: Optional[str] = None

@app.post("/api/progress")
async def add_progress(p: ProgressCreate):
    progress_doc = Progress(habit_id=p.habit_id, note=p.note, image_base64=p.image_base64)
    progress_id = create_document("progress", progress_doc)
    return {"progress_id": progress_id}

@app.get("/api/progress/{habit_id}")
async def list_progress(habit_id: str):
    items = get_documents("progress", {"habit_id": habit_id})
    for d in items:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    # streak: count last consecutive days with at least one progress
    dates = sorted({item.get("taken_at", item.get("created_at")).date() for item in items}) if items else []
    from datetime import date, timedelta
    streak = 0
    today = date.today()
    check = today
    while check in dates or (check in [d for d in dates]):
        if check in dates:
            streak += 1
            check = check - timedelta(days=1)
        else:
            break
    return {"items": items, "streak": streak}

# ------------------------- API: Ask AI (simple local rules) -------------------------
class AskPayload(BaseModel):
    habit_id: Optional[str] = None
    question: Optional[str] = None
    image_base64: Optional[str] = None

@app.post("/api/ask")
async def ask_ai(payload: AskPayload):
    # This is a lightweight heuristic assistant without external AI calls.
    # It looks at keywords and, if an image is provided, acknowledges it.
    reply = ""
    tips = []
    q = (payload.question or "").lower()
    if "design" in q:
        tips.append("Focus on spacing, alignment, and contrast. Try a 4/8pt grid.")
        tips.append("Collect 3 references and recreate one UI daily for 7 days.")
    if "work out" in q or "workout" in q or "gym" in q:
        tips.append("Start with 3 full-body sessions/week. Track sets x reps.")
        tips.append("Progressive overload: add small increments weekly.")
    if "read" in q or "book" in q:
        tips.append("Set a 20–30 min window daily. Use a timer and go distraction-free.")
        tips.append("Write a 3-sentence summary after each session.")
    if not tips:
        tips.append("Clarify your goal and current level. What's one tiny step today?")

    if payload.image_base64:
        reply += "I looked at your image. Consider composition, clarity, and consistency with your stated goal. "
    reply += "Here are tailored suggestions: " + " ".join(tips)

    # log conversation
    create_document("message", Message(habit_id=payload.habit_id, role="user", content=payload.question or "", image_base64=payload.image_base64))
    create_document("message", Message(habit_id=payload.habit_id, role="assistant", content=reply))

    return {"answer": reply}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
