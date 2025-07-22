from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, date
from typing import List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Electricity Meter Tracker API", version="1.0.0")

# Get CORS origins from environment - allow local network access
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")

# Check if we're in development mode (indicated by wildcard patterns)
is_development = "192.168.*" in cors_origins_env or "10.*" in cors_origins_env

if is_development:
    # In development, use a custom function to validate origins
    def is_local_network_origin(origin: str) -> bool:
        import re
        local_patterns = [
            r'^http://localhost:3000$',
            r'^http://127\.0\.0\.1:3000$',
            r'^http://192\.168\.\d{1,3}\.\d{1,3}:3000$',
            r'^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:3000$'
        ]
        return any(re.match(pattern, origin) for pattern in local_patterns)
    
    # Use wildcard for development but add origin validation
    cors_origins = ["*"]
else:
    # In production, use specific origins only
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
# Get additional trusted hosts from environment
additional_hosts = os.getenv("TRUSTED_HOSTS", "").split(",") if os.getenv("TRUSTED_HOSTS") else []
default_hosts = ["localhost", "127.0.0.1", "*.localhost", "backend", "meter_tracker_backend"]
allowed_hosts = default_hosts + [host.strip() for host in additional_hosts if host.strip()]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# Database setup from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "meter_tracker")
DB_USER = os.getenv("DB_USER", "meter_user")
DB_PASSWORD = os.getenv("DB_PASSWORD")
if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD environment variable is required")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BaseReading(Base):
    __tablename__ = "base_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    meter1_base = Column(Integer)
    meter2_base = Column(Integer)
    meter3_base = Column(Integer)
    base_date = Column(Date, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MeterReading(Base):
    __tablename__ = "meter_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    reading_date = Column(Date, index=True)
    meter1_current = Column(Integer)
    meter2_current = Column(Integer)
    meter3_current = Column(Integer)
    meter1_consumption = Column(Integer, default=0)
    meter2_consumption = Column(Integer, default=0)
    meter3_consumption = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydantic models
class BaseReadingCreate(BaseModel):
    meter1_base: int
    meter2_base: int
    meter3_base: int
    base_date: str

class ReadingCreate(BaseModel):
    meter1_current: int
    meter2_current: int
    meter3_current: int
    reading_date: str

class BaseReadingResponse(BaseModel):
    meter1_base: int
    meter2_base: int
    meter3_base: int
    base_date: str
    created_at: datetime

class ReadingResponse(BaseModel):
    reading_date: str
    meter1_current: int
    meter2_current: int
    meter3_current: int
    meter1_consumption: int
    meter2_consumption: int
    meter3_consumption: int
    timestamp: datetime

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/base-readings")
async def set_base_readings(base_readings: BaseReadingCreate, db: Session = Depends(get_db)):
    try:
        # Parse date string to date object
        parsed_date = datetime.strptime(base_readings.base_date, "%Y-%m-%d").date()
        
        # Create new base reading
        db_base = BaseReading(
            meter1_base=base_readings.meter1_base,
            meter2_base=base_readings.meter2_base,
            meter3_base=base_readings.meter3_base,
            base_date=parsed_date
        )
        db.add(db_base)
        db.commit()
        return {"message": "Base readings set successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error setting base readings: {str(e)}")

@app.post("/readings")
async def submit_readings(readings: ReadingCreate, db: Session = Depends(get_db)):
    try:
        # Parse date string to date object
        parsed_date = datetime.strptime(readings.reading_date, "%Y-%m-%d").date()
        
        # Get latest base readings
        base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
        
        if not base_reading:
            raise HTTPException(status_code=400, detail="No base readings found. Please set base readings first.")
        
        # Validate that current readings are not less than base readings
        if (readings.meter1_current < base_reading.meter1_base or 
            readings.meter2_current < base_reading.meter2_base or 
            readings.meter3_current < base_reading.meter3_base):
            raise HTTPException(status_code=400, detail="Current readings cannot be less than base readings.")
        
        # Calculate consumption
        meter1_consumption = readings.meter1_current - base_reading.meter1_base
        meter2_consumption = readings.meter2_current - base_reading.meter2_base
        meter3_consumption = readings.meter3_current - base_reading.meter3_base
        
        # Check if reading already exists for this date
        existing = db.query(MeterReading).filter(MeterReading.reading_date == parsed_date).first()
        
        if existing:
            # Update existing reading
            existing.meter1_current = readings.meter1_current
            existing.meter2_current = readings.meter2_current
            existing.meter3_current = readings.meter3_current
            existing.meter1_consumption = meter1_consumption
            existing.meter2_consumption = meter2_consumption
            existing.meter3_consumption = meter3_consumption
            existing.timestamp = datetime.utcnow()
        else:
            # Create new reading
            db_reading = MeterReading(
                reading_date=parsed_date,
                meter1_current=readings.meter1_current,
                meter2_current=readings.meter2_current,
                meter3_current=readings.meter3_current,
                meter1_consumption=meter1_consumption,
                meter2_consumption=meter2_consumption,
                meter3_consumption=meter3_consumption
            )
            db.add(db_reading)
        
        db.commit()
        return {"message": "Readings saved successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving readings: {str(e)}")

@app.get("/base-readings/latest")
async def get_latest_base_readings(db: Session = Depends(get_db)):
    latest = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
    
    if latest:
        return {
            "meter1_base": latest.meter1_base,
            "meter2_base": latest.meter2_base,
            "meter3_base": latest.meter3_base,
            "base_date": latest.base_date.strftime("%Y-%m-%d")
        }
    else:
        return None

@app.get("/readings")
async def get_readings(db: Session = Depends(get_db)):
    # Get base reading to determine start date
    base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
    
    if not base_reading:
        return []
    
    # Get readings from base date onwards
    query = db.query(MeterReading).filter(
        MeterReading.reading_date >= base_reading.base_date
    ).order_by(MeterReading.reading_date.asc())
    
    readings = query.all()
    
    return [
        {
            "reading_date": reading.reading_date.strftime("%Y-%m-%d"),
            "meter1_current": reading.meter1_current,
            "meter2_current": reading.meter2_current,
            "meter3_current": reading.meter3_current,
            "meter1_consumption": reading.meter1_consumption,
            "meter2_consumption": reading.meter2_consumption,
            "meter3_consumption": reading.meter3_consumption,
            "timestamp": reading.timestamp
        }
        for reading in readings
    ]

@app.get("/readings/latest")
async def get_latest_readings(db: Session = Depends(get_db)):
    latest = db.query(MeterReading).order_by(MeterReading.reading_date.desc()).first()
    
    if latest:
        return {
            "meter1_current": latest.meter1_current,
            "meter2_current": latest.meter2_current,
            "meter3_current": latest.meter3_current,
            "reading_date": latest.reading_date.strftime("%Y-%m-%d")
        }
    else:
        return {
            "meter1_current": 0,
            "meter2_current": 0,
            "meter3_current": 0,
            "reading_date": datetime.now().strftime("%Y-%m-%d")
        }

@app.get("/readings/dates")
async def get_reading_dates(db: Session = Depends(get_db)):
    try:
        # Get all unique reading dates ordered by date descending
        dates = db.query(MeterReading.reading_date).distinct().order_by(MeterReading.reading_date.desc()).all()
        
        # Convert to list of date strings
        date_strings = [date[0].strftime("%Y-%m-%d") for date in dates]
        
        return {"dates": date_strings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reading dates: {str(e)}")

@app.get("/consumption-summary")
async def get_consumption_summary(db: Session = Depends(get_db)):
    # Get base reading
    base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
    
    if not base_reading:
        return {"error": "No base readings found"}
    
    # Get latest reading
    latest_reading = db.query(MeterReading).order_by(MeterReading.reading_date.desc()).first()
    
    if not latest_reading:
        return {
            "base_date": base_reading.base_date.strftime("%Y-%m-%d"),
            "total_consumption": {
                "meter1": 0,
                "meter2": 0,
                "meter3": 0
            }
        }
    
    return {
        "base_date": base_reading.base_date.strftime("%Y-%m-%d"),
        "latest_date": latest_reading.reading_date.strftime("%Y-%m-%d"),
        "total_consumption": {
            "meter1": latest_reading.meter1_consumption,
            "meter2": latest_reading.meter2_consumption,
            "meter3": latest_reading.meter3_consumption
        }
    }

@app.get("/usage-metrics")
async def get_usage_metrics(db: Session = Depends(get_db)):
    # Constants from environment variables
    MONTHLY_LIMIT_PER_METER = int(os.getenv("MONTHLY_LIMIT_PER_METER", "200"))
    TOTAL_MONTHLY_LIMIT = int(os.getenv("TOTAL_MONTHLY_LIMIT", "600"))
    DAYS_IN_MONTH = int(os.getenv("DAYS_IN_MONTH", "30"))
    
    # Get base reading
    base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
    
    if not base_reading:
        return {"error": "No base readings found"}
    
    # Use base_date as the start of the monthly cycle
    month_start_date = base_reading.base_date
    current_date = datetime.now().date()
    
    # Calculate current month cycle (base_date + 30 days cycles)
    days_since_base = (current_date - month_start_date).days
    current_month_cycle = days_since_base // DAYS_IN_MONTH
    
    # Calculate current month boundaries
    current_month_start = month_start_date + timedelta(days=current_month_cycle * DAYS_IN_MONTH)
    current_month_end = current_month_start + timedelta(days=DAYS_IN_MONTH - 1)
    
    # Get readings for current month cycle only
    readings = db.query(MeterReading).filter(
        MeterReading.reading_date >= current_month_start,
        MeterReading.reading_date <= min(current_date, current_month_end)
    ).order_by(MeterReading.reading_date.asc()).all()
    
    # Get base consumption for current month (consumption at start of current month)
    base_consumption = {"meter1": 0, "meter2": 0, "meter3": 0}
    if current_month_cycle > 0:
        # Get the last reading before current month started
        base_reading_for_month = db.query(MeterReading).filter(
            MeterReading.reading_date < current_month_start
        ).order_by(MeterReading.reading_date.desc()).first()
        
        if base_reading_for_month:
            base_consumption = {
                "meter1": base_reading_for_month.meter1_consumption,
                "meter2": base_reading_for_month.meter2_consumption,
                "meter3": base_reading_for_month.meter3_consumption
            }
    
    if not readings:
        return {
            "error": "No readings found for current month cycle",
            "current_month_start": current_month_start.strftime("%Y-%m-%d"),
            "current_month_end": current_month_end.strftime("%Y-%m-%d"),
            "month_cycle": current_month_cycle + 1
        }
    
    latest_reading = readings[-1]
    
    # Calculate monthly consumption (subtract base consumption for the month)
    monthly_consumed = {
        "meter1": latest_reading.meter1_consumption - base_consumption["meter1"],
        "meter2": latest_reading.meter2_consumption - base_consumption["meter2"],
        "meter3": latest_reading.meter3_consumption - base_consumption["meter3"]
    }
    monthly_consumed["total"] = monthly_consumed["meter1"] + monthly_consumed["meter2"] + monthly_consumed["meter3"]
    
    # Calculate daily usage within current month
    daily_usage = []
    prev_consumption = base_consumption
    
    for reading in readings:
        daily_consumption = {
            "date": reading.reading_date.strftime("%Y-%m-%d"),
            "meter1": reading.meter1_consumption - prev_consumption["meter1"],
            "meter2": reading.meter2_consumption - prev_consumption["meter2"],
            "meter3": reading.meter3_consumption - prev_consumption["meter3"]
        }
        daily_consumption["total"] = daily_consumption["meter1"] + daily_consumption["meter2"] + daily_consumption["meter3"]
        daily_usage.append(daily_consumption)
        
        prev_consumption = {
            "meter1": reading.meter1_consumption,
            "meter2": reading.meter2_consumption,
            "meter3": reading.meter3_consumption
        }
    
    # Calculate days in current month cycle
    days_elapsed_in_month = (current_date - current_month_start).days + 1
    days_remaining_in_month = max(0, DAYS_IN_MONTH - days_elapsed_in_month)
    
    # Remaining units in current month
    remaining = {
        "meter1": MONTHLY_LIMIT_PER_METER - monthly_consumed["meter1"],
        "meter2": MONTHLY_LIMIT_PER_METER - monthly_consumed["meter2"],
        "meter3": MONTHLY_LIMIT_PER_METER - monthly_consumed["meter3"],
        "total": TOTAL_MONTHLY_LIMIT - monthly_consumed["total"]
    }
    
    # Daily averages for current month
    daily_avg_used = {
        "meter1": round(monthly_consumed["meter1"] / days_elapsed_in_month, 2),
        "meter2": round(monthly_consumed["meter2"] / days_elapsed_in_month, 2),
        "meter3": round(monthly_consumed["meter3"] / days_elapsed_in_month, 2),
        "total": round(monthly_consumed["total"] / days_elapsed_in_month, 2)
    }
    
    # Daily average remaining for current month
    daily_avg_remaining = {
        "meter1": round(remaining["meter1"] / days_remaining_in_month, 2) if days_remaining_in_month > 0 else 0,
        "meter2": round(remaining["meter2"] / days_remaining_in_month, 2) if days_remaining_in_month > 0 else 0,
        "meter3": round(remaining["meter3"] / days_remaining_in_month, 2) if days_remaining_in_month > 0 else 0,
        "total": round(remaining["total"] / days_remaining_in_month, 2) if days_remaining_in_month > 0 else 0
    }
    
    # Usage percentage for current month
    usage_percentage = {
        "meter1": round((monthly_consumed["meter1"] / MONTHLY_LIMIT_PER_METER) * 100, 1),
        "meter2": round((monthly_consumed["meter2"] / MONTHLY_LIMIT_PER_METER) * 100, 1),
        "meter3": round((monthly_consumed["meter3"] / MONTHLY_LIMIT_PER_METER) * 100, 1),
        "total": round((monthly_consumed["total"] / TOTAL_MONTHLY_LIMIT) * 100, 1)
    }
    
    # Monthly projection for current month
    monthly_projection = {
        "meter1": round(daily_avg_used["meter1"] * DAYS_IN_MONTH, 1),
        "meter2": round(daily_avg_used["meter2"] * DAYS_IN_MONTH, 1),
        "meter3": round(daily_avg_used["meter3"] * DAYS_IN_MONTH, 1),
        "total": round(daily_avg_used["total"] * DAYS_IN_MONTH, 1)
    }
    
    # Days until limit reached in current month
    days_until_limit = {}
    for meter in ["meter1", "meter2", "meter3", "total"]:
        if daily_avg_used[meter] > 0:
            limit = MONTHLY_LIMIT_PER_METER if meter != "total" else TOTAL_MONTHLY_LIMIT
            days_until_limit[meter] = max(0, round((limit - monthly_consumed[meter]) / daily_avg_used[meter], 1))
        else:
            days_until_limit[meter] = float('inf')
    
    # Peak usage day in current month
    peak_day = max(daily_usage, key=lambda x: x["total"]) if daily_usage else None
    
    # Efficiency score (how well you're pacing for the month)
    efficiency_score = {}
    month_progress_percentage = (days_elapsed_in_month / DAYS_IN_MONTH) * 100
    for meter in ["meter1", "meter2", "meter3", "total"]:
        efficiency_score[meter] = round(100 - (usage_percentage[meter] - month_progress_percentage), 1)
    
    return {
        "limits": {
            "per_meter": MONTHLY_LIMIT_PER_METER,
            "total": TOTAL_MONTHLY_LIMIT,
            "days_in_month": DAYS_IN_MONTH
        },
        "tracking_period": {
            "base_date": month_start_date.strftime("%Y-%m-%d"),
            "current_month_start": current_month_start.strftime("%Y-%m-%d"),
            "current_month_end": current_month_end.strftime("%Y-%m-%d"),
            "current_date": current_date.strftime("%Y-%m-%d"),
            "month_cycle": current_month_cycle + 1,
            "days_elapsed": days_elapsed_in_month,
            "days_remaining": days_remaining_in_month
        },
        "total_consumed": monthly_consumed,
        "remaining": remaining,
        "daily_avg_used": daily_avg_used,
        "daily_avg_remaining": daily_avg_remaining,
        "usage_percentage": usage_percentage,
        "monthly_projection": monthly_projection,
        "days_until_limit": days_until_limit,
        "peak_usage_day": peak_day,
        "daily_usage": daily_usage,
        "efficiency_score": efficiency_score
    }

@app.delete("/readings/{date}")
async def delete_reading_by_date(date: str, db: Session = Depends(get_db)):
    try:
        # Parse date string to date object
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Find and delete the reading for the specific date
        reading = db.query(MeterReading).filter(MeterReading.reading_date == parsed_date).first()
        
        if not reading:
            raise HTTPException(status_code=404, detail=f"No reading found for date {date}")
        
        db.delete(reading)
        db.commit()
        
        return {"message": f"Successfully deleted reading for {date}"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting reading: {str(e)}")

@app.delete("/readings/delete-old-data")
async def delete_old_data(request: dict, db: Session = Depends(get_db)):
    cutoff_date = request.get('cutoff_date')
    if not cutoff_date:
        raise HTTPException(status_code=400, detail="cutoff_date is required")
    
    try:
        # Parse cutoff date string to date object
        parsed_cutoff_date = datetime.strptime(cutoff_date, "%Y-%m-%d").date()
        
        # Delete readings older than cutoff date
        result = db.query(MeterReading).filter(MeterReading.reading_date < parsed_cutoff_date).delete()
        db.commit()
        
        return {"message": f"Successfully deleted {result} old records", "deleted_count": result}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid cutoff_date format. Use YYYY-MM-DD")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting old data: {str(e)}")

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection using ORM query
        db.query(BaseReading).first()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)