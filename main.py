from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator
from datetime import date, timedelta
import database

app = FastAPI(title="Medicine Stock Tracker", version="2.0")

# Allow the HTML frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

database.setup()

# Serve the frontend UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


# --- Input Model with Validation ---
class MedicineIn(BaseModel):
    name: str
    stock_qty: int
    doses_per_day: int

    @validator("name")
    def name_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Medicine name cannot be empty")
        if len(v) < 2:
            raise ValueError("Medicine name must be at least 2 characters")
        return v.title()

    @validator("stock_qty")
    def stock_positive(cls, v):
        if v <= 0:
            raise ValueError("Stock quantity must be greater than 0")
        if v > 10000:
            raise ValueError("Stock quantity seems unrealistically high (max 10000)")
        return v

    @validator("doses_per_day")
    def doses_valid(cls, v):
        if v <= 0:
            raise ValueError("Doses per day must be at least 1")
        if v > 20:
            raise ValueError("Doses per day cannot exceed 20")
        return v


# --- Routes ---

@app.post("/medicines")
def add_medicine(med: MedicineIn):
    conn = database.get_connection()
    try:
        today = date.today()
        days_supply = med.stock_qty // med.doses_per_day
        finish_date = today + timedelta(days=days_supply)
        restock_date = finish_date - timedelta(days=3)

        # Prevent restock date from being in the past
        if restock_date < today:
            restock_date = today

        next_id = conn.execute("SELECT NEXTVAL('medicine_id_seq')").fetchone()[0]

        conn.execute("""
            INSERT INTO medicines VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [next_id, med.name, med.stock_qty, med.doses_per_day,
              today, finish_date, restock_date])

        return {
            "id": next_id,
            "name": med.name,
            "stock_qty": med.stock_qty,
            "doses_per_day": med.doses_per_day,
            "added_date": str(today),
            "finish_date": str(finish_date),
            "restock_date": str(restock_date),
            "days_supply": days_supply
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/medicines")
def get_all_medicines():
    conn = database.get_connection()
    try:
        rows = conn.execute("""
            SELECT id, name, stock_qty, doses_per_day,
                   added_date, finish_date, restock_date
            FROM medicines
            ORDER BY restock_date ASC
        """).fetchall()
        return {"medicines": [
            {
                "id": r[0], "name": r[1], "stock_qty": r[2],
                "doses_per_day": r[3], "added_date": str(r[4]),
                "finish_date": str(r[5]), "restock_date": str(r[6])
            } for r in rows
        ]}
    finally:
        conn.close()


@app.delete("/medicines/{med_id}")
def delete_medicine(med_id: int):
    conn = database.get_connection()
    try:
        conn.execute("DELETE FROM medicines WHERE id = ?", [med_id])
        return {"message": f"Medicine {med_id} removed."}
    finally:
        conn.close()
