from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator
from datetime import date, timedelta
import database

app = FastAPI(title="Medicine Stock Tracker", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

database.setup()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


# --- Models ---
class MedicineIn(BaseModel):
    name: str
    stock_qty: int
    doses_per_day: int

    @validator("name")
    def name_not_empty(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Medicine name must be at least 2 characters")
        return v.title()

    @validator("stock_qty")
    def stock_positive(cls, v):
        if v <= 0 or v > 10000:
            raise ValueError("Stock quantity must be between 1 and 10,000")
        return v

    @validator("doses_per_day")
    def doses_valid(cls, v):
        if v <= 0 or v > 20:
            raise ValueError("Doses per day must be between 1 and 20")
        return v


class RestockIn(BaseModel):
    added_qty: int

    @validator("added_qty")
    def qty_positive(cls, v):
        if v <= 0 or v > 10000:
            raise ValueError("Added quantity must be between 1 and 10,000")
        return v


def calc_dates(current_stock: int, doses_per_day: int, from_date: date):
    days_supply = current_stock // doses_per_day
    finish_date = from_date + timedelta(days=days_supply)
    # Restock when last 5 pills remain
    days_to_last5 = max(0, (current_stock - 5)) // doses_per_day
    restock_date = from_date + timedelta(days=days_to_last5)
    if restock_date < from_date:
        restock_date = from_date
    return finish_date, restock_date


def row_to_dict(r):
    return {
        "id": r[0], "name": r[1],
        "original_stock": r[2], "current_stock": r[3],
        "doses_per_day": r[4], "added_date": str(r[5]),
        "finish_date": str(r[6]), "restock_date": str(r[7]),
        "is_active": r[8]
    }


# --- Routes ---

@app.post("/medicines")
def add_medicine(med: MedicineIn):
    conn = database.get_connection()
    try:
        today = date.today()
        finish_date, restock_date = calc_dates(med.stock_qty, med.doses_per_day, today)
        next_id = database.get_next_id(conn)
        conn.execute("""
            INSERT INTO medicines
            (id, name, original_stock, current_stock, doses_per_day, added_date, finish_date, restock_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, TRUE)
        """, [next_id, med.name, med.stock_qty, med.stock_qty,
              med.doses_per_day, today, finish_date, restock_date])
        return row_to_dict(conn.execute(
            "SELECT * FROM medicines WHERE id = ?", [next_id]).fetchone())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/medicines")
def get_all_medicines():
    conn = database.get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM medicines
            ORDER BY is_active DESC, restock_date ASC
        """).fetchall()
        return {"medicines": [row_to_dict(r) for r in rows]}
    finally:
        conn.close()


@app.patch("/medicines/{med_id}/restock")
def restock_medicine(med_id: int, body: RestockIn):
    conn = database.get_connection()
    try:
        row = conn.execute("SELECT * FROM medicines WHERE id = ?", [med_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Medicine not found")
        med = row_to_dict(row)
        new_stock = med["current_stock"] + body.added_qty
        new_original = med["original_stock"] + body.added_qty
        today = date.today()
        finish_date, restock_date = calc_dates(new_stock, med["doses_per_day"], today)
        conn.execute("""
            UPDATE medicines
            SET current_stock = ?, original_stock = ?,
                finish_date = ?, restock_date = ?, added_date = ?, is_active = TRUE
            WHERE id = ?
        """, [new_stock, new_original, finish_date, restock_date, today, med_id])
        return row_to_dict(conn.execute(
            "SELECT * FROM medicines WHERE id = ?", [med_id]).fetchone())
    finally:
        conn.close()


@app.patch("/medicines/{med_id}/toggle")
def toggle_medicine(med_id: int):
    conn = database.get_connection()
    try:
        row = conn.execute("SELECT is_active FROM medicines WHERE id = ?", [med_id]).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Medicine not found")
        new_state = not row[0]
        conn.execute("UPDATE medicines SET is_active = ? WHERE id = ?", [new_state, med_id])
        return {"is_active": new_state}
    finally:
        conn.close()
