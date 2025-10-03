from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, date, timezone
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
    end_date = Column(Date, index=True)
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
    end_date: str = None  # Make end_date optional

class EndDateUpdate(BaseModel):
    end_date: str

class ReadingCreate(BaseModel):
    meter1_current: int
    meter2_current: int
    meter3_current: int
    reading_date: str

class GapInfo(BaseModel):
    gap_start: str
    gap_end: str
    missing_dates: List[str]
    total_consumption: dict
    per_day_consumption: dict
    start_readings: dict
    end_readings: dict

class GapAnalysisResponse(BaseModel):
    gaps_found: int
    gaps: List[GapInfo]
    total_missing_days: int

class GapFillResponse(BaseModel):
    success: bool
    filled_days: int
    filled_dates: List[str]
    message: str

class BaseReadingResponse(BaseModel):
    meter1_base: int
    meter2_base: int
    meter3_base: int
    base_date: str
    end_date: str
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
        # Parse base date
        parsed_base_date = datetime.strptime(base_readings.base_date, "%Y-%m-%d").date()
        
        # Handle end_date - use provided value or default to next month
        if base_readings.end_date:
            parsed_end_date = datetime.strptime(base_readings.end_date, "%Y-%m-%d").date()
            # Validate that end_date is not older than base_date
            if parsed_end_date < parsed_base_date:
                raise HTTPException(status_code=400, detail="End date cannot be older than base date")
        else:
            # Default end_date to one month after base_date
            if parsed_base_date.month == 12:
                parsed_end_date = parsed_base_date.replace(year=parsed_base_date.year + 1, month=1)
            else:
                parsed_end_date = parsed_base_date.replace(month=parsed_base_date.month + 1)
        
        # Create new base reading
        db_base = BaseReading(
            meter1_base=base_readings.meter1_base,
            meter2_base=base_readings.meter2_base,
            meter3_base=base_readings.meter3_base,
            base_date=parsed_base_date,
            end_date=parsed_end_date
        )
        db.add(db_base)
        db.commit()
        return {"message": "Base readings set successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error setting base readings: {str(e)}")

@app.patch("/base-readings/end-date")
async def update_end_date(end_date_update: EndDateUpdate, db: Session = Depends(get_db)):
    try:
        # Get the latest base reading
        latest_base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
        
        if not latest_base_reading:
            raise HTTPException(status_code=404, detail="No base readings found to update")
        
        # Parse and validate the new end date
        parsed_end_date = datetime.strptime(end_date_update.end_date, "%Y-%m-%d").date()
        
        # Validate that end_date is not older than base_date
        if parsed_end_date < latest_base_reading.base_date:
            raise HTTPException(status_code=400, detail="End date cannot be older than base date")
        
        # Update the end date
        latest_base_reading.end_date = parsed_end_date
        db.commit()
        
        return {"message": "End date updated successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating end date: {str(e)}")

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
            "base_date": latest.base_date.strftime("%Y-%m-%d"),
            "end_date": latest.end_date.strftime("%Y-%m-%d")
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
            "meter1_consumption": reading.meter1_current - base_reading.meter1_base,
            "meter2_consumption": reading.meter2_current - base_reading.meter2_base,
            "meter3_consumption": reading.meter3_current - base_reading.meter3_base,
            "timestamp": reading.timestamp.replace(tzinfo=timezone.utc).isoformat()
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
            "meter1": latest_reading.meter1_current - base_reading.meter1_base,
            "meter2": latest_reading.meter2_current - base_reading.meter2_base,
            "meter3": latest_reading.meter3_current - base_reading.meter3_base
        }
    }

@app.get("/usage-metrics")
async def get_usage_metrics(db: Session = Depends(get_db)):
    # Constants from environment variables
    MONTHLY_LIMIT_PER_METER = int(os.getenv("MONTHLY_LIMIT_PER_METER", "200"))
    TOTAL_MONTHLY_LIMIT = int(os.getenv("TOTAL_MONTHLY_LIMIT", "600"))
    
    # Get base reading
    base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
    
    if not base_reading:
        return {"error": "No base readings found"}
    
    # Use base_date and end_date from base reading
    base_date = base_reading.base_date
    end_date = base_reading.end_date
    current_date = datetime.now().date()
    
    # Calculate total days in the custom period (inclusive of both dates)
    total_days_in_period = (end_date - base_date).days + 1
    
    # Calculate days elapsed and remaining
    if current_date > end_date:
        days_elapsed = total_days_in_period
        days_remaining = 0
    elif current_date < base_date:
        days_elapsed = 0
        days_remaining = total_days_in_period
    else:
        days_elapsed = (current_date - base_date).days + 1
        days_remaining = max(0, total_days_in_period - days_elapsed)
    
    # Get readings for the custom period (from base_date to current_date or end_date, whichever is earlier)
    period_end_date = min(current_date, end_date)
    readings = db.query(MeterReading).filter(
        MeterReading.reading_date >= base_date,
        MeterReading.reading_date <= period_end_date
    ).order_by(MeterReading.reading_date.asc()).all()
    
    if not readings:
        return {
            "error": "No readings found for custom period",
            "period_start": base_date.strftime("%Y-%m-%d"),
            "period_end": end_date.strftime("%Y-%m-%d"),
            "current_date": current_date.strftime("%Y-%m-%d")
        }
    
    latest_reading = readings[-1]
    
    # Calculate total consumption from base readings
    total_consumed = {
        "meter1": latest_reading.meter1_current - base_reading.meter1_base,
        "meter2": latest_reading.meter2_current - base_reading.meter2_base,
        "meter3": latest_reading.meter3_current - base_reading.meter3_base
    }
    total_consumed["total"] = total_consumed["meter1"] + total_consumed["meter2"] + total_consumed["meter3"]
    
    # Calculate daily usage within the period
    daily_usage = []
    prev_consumption = {"meter1": 0, "meter2": 0, "meter3": 0}
    
    for reading in readings:
        # Calculate actual consumption dynamically
        actual_consumption = {
            "meter1": reading.meter1_current - base_reading.meter1_base,
            "meter2": reading.meter2_current - base_reading.meter2_base,
            "meter3": reading.meter3_current - base_reading.meter3_base
        }
        
        daily_consumption = {
            "date": reading.reading_date.strftime("%Y-%m-%d"),
            "meter1": actual_consumption["meter1"] - prev_consumption["meter1"],
            "meter2": actual_consumption["meter2"] - prev_consumption["meter2"],
            "meter3": actual_consumption["meter3"] - prev_consumption["meter3"]
        }
        daily_consumption["total"] = daily_consumption["meter1"] + daily_consumption["meter2"] + daily_consumption["meter3"]
        daily_usage.append(daily_consumption)
        
        prev_consumption = actual_consumption
    
    # Remaining units in custom period
    remaining = {
        "meter1": MONTHLY_LIMIT_PER_METER - total_consumed["meter1"],
        "meter2": MONTHLY_LIMIT_PER_METER - total_consumed["meter2"],
        "meter3": MONTHLY_LIMIT_PER_METER - total_consumed["meter3"],
        "total": TOTAL_MONTHLY_LIMIT - total_consumed["total"]
    }
    
    # Daily averages
    daily_avg_used = {
        "meter1": round(total_consumed["meter1"] / days_elapsed, 2) if days_elapsed > 0 else 0,
        "meter2": round(total_consumed["meter2"] / days_elapsed, 2) if days_elapsed > 0 else 0,
        "meter3": round(total_consumed["meter3"] / days_elapsed, 2) if days_elapsed > 0 else 0,
        "total": round(total_consumed["total"] / days_elapsed, 2) if days_elapsed > 0 else 0
    }
    
    # Daily average remaining
    daily_avg_remaining = {
        "meter1": round(remaining["meter1"] / days_remaining, 2) if days_remaining > 0 else 0,
        "meter2": round(remaining["meter2"] / days_remaining, 2) if days_remaining > 0 else 0,
        "meter3": round(remaining["meter3"] / days_remaining, 2) if days_remaining > 0 else 0,
        "total": round(remaining["total"] / days_remaining, 2) if days_remaining > 0 else 0
    }
    
    # Usage percentage
    usage_percentage = {
        "meter1": round((total_consumed["meter1"] / MONTHLY_LIMIT_PER_METER) * 100, 1),
        "meter2": round((total_consumed["meter2"] / MONTHLY_LIMIT_PER_METER) * 100, 1),
        "meter3": round((total_consumed["meter3"] / MONTHLY_LIMIT_PER_METER) * 100, 1),
        "total": round((total_consumed["total"] / TOTAL_MONTHLY_LIMIT) * 100, 1)
    }
    
    # Period projection (what consumption would be if we continue at current rate)
    period_projection = {
        "meter1": round(daily_avg_used["meter1"] * total_days_in_period, 1),
        "meter2": round(daily_avg_used["meter2"] * total_days_in_period, 1),
        "meter3": round(daily_avg_used["meter3"] * total_days_in_period, 1),
        "total": round(daily_avg_used["total"] * total_days_in_period, 1)
    }
    
    # Days until limit reached
    days_until_limit = {}
    for meter in ["meter1", "meter2", "meter3", "total"]:
        if daily_avg_used[meter] > 0:
            limit = MONTHLY_LIMIT_PER_METER if meter != "total" else TOTAL_MONTHLY_LIMIT
            days_until_limit[meter] = max(0, round((limit - total_consumed[meter]) / daily_avg_used[meter], 1))
        else:
            days_until_limit[meter] = 999999
    
    # Peak usage day
    peak_day = max(daily_usage, key=lambda x: x["total"]) if daily_usage else None
    
    # Efficiency score (how well you're pacing for the period)
    efficiency_score = {}
    time_progress_percentage = (days_elapsed / total_days_in_period) * 100 if total_days_in_period > 0 else 0
    for meter in ["meter1", "meter2", "meter3", "total"]:
        efficiency_score[meter] = round(100 - (usage_percentage[meter] - time_progress_percentage), 1)
    
    return {
        "limits": {
            "per_meter": MONTHLY_LIMIT_PER_METER,
            "total": TOTAL_MONTHLY_LIMIT,
            "days_in_period": total_days_in_period
        },
        "tracking_period": {
            "base_date": base_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "current_date": current_date.strftime("%Y-%m-%d"),
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "period_description": f"{base_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
        },
        "total_consumed": total_consumed,
        "remaining": remaining,
        "daily_avg_used": daily_avg_used,
        "daily_avg_remaining": daily_avg_remaining,
        "usage_percentage": usage_percentage,
        "period_projection": period_projection,
        "days_until_limit": days_until_limit,
        "peak_usage_day": peak_day,
        "daily_usage": daily_usage,
        "efficiency_score": efficiency_score
    }

@app.delete("/readings/delete-old-data")
async def delete_old_data(cutoff_date: str, db: Session = Depends(get_db)):
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

@app.get("/readings/analyze-gaps")
async def analyze_data_gaps(db: Session = Depends(get_db)):
    try:
        # Get base reading
        base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
        
        if not base_reading:
            raise HTTPException(status_code=400, detail="No base readings found. Please set base readings first.")
        
        # Get all readings from base date onwards, ordered by date
        readings = db.query(MeterReading).filter(
            MeterReading.reading_date >= base_reading.base_date
        ).order_by(MeterReading.reading_date.asc()).all()
        
        if len(readings) < 2:
            return GapAnalysisResponse(gaps_found=0, gaps=[], total_missing_days=0)
        
        gaps = []
        total_missing_days = 0
        
        # Check for gaps between consecutive readings
        for i in range(len(readings) - 1):
            current_reading = readings[i]
            next_reading = readings[i + 1]
            
            # Calculate days between readings
            current_date = current_reading.reading_date
            next_date = next_reading.reading_date
            days_diff = (next_date - current_date).days
            
            # If gap is more than 1 day, we have missing readings
            if days_diff > 1:
                missing_dates = []
                current_temp = current_date
                
                # Generate list of missing dates
                for day_offset in range(1, days_diff):
                    missing_date = current_temp + timedelta(days=day_offset)
                    missing_dates.append(missing_date.strftime("%Y-%m-%d"))
                
                # Calculate consumption for each meter
                total_consumption = {
                    "meter1": next_reading.meter1_current - current_reading.meter1_current,
                    "meter2": next_reading.meter2_current - current_reading.meter2_current,
                    "meter3": next_reading.meter3_current - current_reading.meter3_current
                }
                
                # Calculate per-day consumption (equal distribution) - rounded to whole numbers
                per_day_consumption = {
                    "meter1": round(total_consumption["meter1"] / days_diff),
                    "meter2": round(total_consumption["meter2"] / days_diff),
                    "meter3": round(total_consumption["meter3"] / days_diff)
                }
                
                gap_info = GapInfo(
                    gap_start=current_date.strftime("%Y-%m-%d"),
                    gap_end=next_date.strftime("%Y-%m-%d"),
                    missing_dates=missing_dates,
                    total_consumption=total_consumption,
                    per_day_consumption=per_day_consumption,
                    start_readings={
                        "meter1": current_reading.meter1_current,
                        "meter2": current_reading.meter2_current,
                        "meter3": current_reading.meter3_current
                    },
                    end_readings={
                        "meter1": next_reading.meter1_current,
                        "meter2": next_reading.meter2_current,
                        "meter3": next_reading.meter3_current
                    }
                )
                
                gaps.append(gap_info)
                total_missing_days += len(missing_dates)
        
        return GapAnalysisResponse(
            gaps_found=len(gaps),
            gaps=gaps,
            total_missing_days=total_missing_days
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing data gaps: {str(e)}")

@app.post("/readings/fill-gaps")
async def fill_data_gaps(db: Session = Depends(get_db)):
    try:
        # First, analyze gaps
        analysis = await analyze_data_gaps(db)
        
        if analysis.gaps_found == 0:
            return GapFillResponse(
                success=True,
                filled_days=0,
                filled_dates=[],
                message="No data gaps found to fill."
            )
        
        # Get base reading for consumption calculations
        base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
        
        filled_dates = []
        filled_days = 0
        
        # Fill each gap
        for gap in analysis.gaps:
            for i, missing_date in enumerate(gap.missing_dates):
                parsed_date = datetime.strptime(missing_date, "%Y-%m-%d").date()
                
                # Calculate cumulative readings for this missing day
                # Start from the gap start reading and add incremental consumption
                days_from_start = i + 1
                
                interpolated_meter1 = int(gap.start_readings["meter1"] + (gap.per_day_consumption["meter1"] * days_from_start))
                interpolated_meter2 = int(gap.start_readings["meter2"] + (gap.per_day_consumption["meter2"] * days_from_start))
                interpolated_meter3 = int(gap.start_readings["meter3"] + (gap.per_day_consumption["meter3"] * days_from_start))
                
                # Calculate consumption from base readings
                meter1_consumption = interpolated_meter1 - base_reading.meter1_base
                meter2_consumption = interpolated_meter2 - base_reading.meter2_base
                meter3_consumption = interpolated_meter3 - base_reading.meter3_base
                
                # Check if reading already exists (shouldn't happen, but safety check)
                existing = db.query(MeterReading).filter(MeterReading.reading_date == parsed_date).first()
                
                if not existing:
                    # Create new interpolated reading
                    new_reading = MeterReading(
                        reading_date=parsed_date,
                        meter1_current=interpolated_meter1,
                        meter2_current=interpolated_meter2,
                        meter3_current=interpolated_meter3,
                        meter1_consumption=meter1_consumption,
                        meter2_consumption=meter2_consumption,
                        meter3_consumption=meter3_consumption
                    )
                    db.add(new_reading)
                    filled_dates.append(missing_date)
                    filled_days += 1
        
        # Commit all changes
        db.commit()
        
        return GapFillResponse(
            success=True,
            filled_days=filled_days,
            filled_dates=filled_dates,
            message=f"Successfully filled {filled_days} missing days with interpolated readings."
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error filling data gaps: {str(e)}")

@app.get("/readings/{date}")
async def get_reading_by_date(date: str, db: Session = Depends(get_db)):
    try:
        # Parse date string to date object
        parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Find the reading for the specific date
        reading = db.query(MeterReading).filter(MeterReading.reading_date == parsed_date).first()
        
        if not reading:
            raise HTTPException(status_code=404, detail=f"No reading found for date {date}")
        
        # Get base reading for dynamic consumption calculation
        base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
        
        return {
            "reading_date": reading.reading_date.strftime("%Y-%m-%d"),
            "meter1_current": reading.meter1_current,
            "meter2_current": reading.meter2_current,
            "meter3_current": reading.meter3_current,
            "meter1_consumption": reading.meter1_current - base_reading.meter1_base if base_reading else 0,
            "meter2_consumption": reading.meter2_current - base_reading.meter2_base if base_reading else 0,
            "meter3_consumption": reading.meter3_current - base_reading.meter3_base if base_reading else 0,
            "timestamp": reading.timestamp.replace(tzinfo=timezone.utc).isoformat()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reading: {str(e)}")

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
        
        gaps = []
        total_missing_days = 0
        
        # Check for gaps between consecutive readings
        for i in range(len(readings) - 1):
            current_reading = readings[i]
            next_reading = readings[i + 1]
            
            # Calculate days between readings
            current_date = current_reading.reading_date
            next_date = next_reading.reading_date
            days_diff = (next_date - current_date).days
            
            # If gap is more than 1 day, we have missing readings
            if days_diff > 1:
                missing_dates = []
                current_temp = current_date
                
                # Generate list of missing dates
                for day_offset in range(1, days_diff):
                    missing_date = current_temp + timedelta(days=day_offset)
                    missing_dates.append(missing_date.strftime("%Y-%m-%d"))
                
                # Calculate consumption for each meter
                total_consumption = {
                    "meter1": next_reading.meter1_current - current_reading.meter1_current,
                    "meter2": next_reading.meter2_current - current_reading.meter2_current,
                    "meter3": next_reading.meter3_current - current_reading.meter3_current
                }
                
                # Calculate per-day consumption (equal distribution) - rounded to whole numbers
                per_day_consumption = {
                    "meter1": round(total_consumption["meter1"] / days_diff),
                    "meter2": round(total_consumption["meter2"] / days_diff),
                    "meter3": round(total_consumption["meter3"] / days_diff)
                }
                
                gap_info = GapInfo(
                    gap_start=current_date.strftime("%Y-%m-%d"),
                    gap_end=next_date.strftime("%Y-%m-%d"),
                    missing_dates=missing_dates,
                    total_consumption=total_consumption,
                    per_day_consumption=per_day_consumption,
                    start_readings={
                        "meter1": current_reading.meter1_current,
                        "meter2": current_reading.meter2_current,
                        "meter3": current_reading.meter3_current
                    },
                    end_readings={
                        "meter1": next_reading.meter1_current,
                        "meter2": next_reading.meter2_current,
                        "meter3": next_reading.meter3_current
                    }
                )
                
                gaps.append(gap_info)
                total_missing_days += len(missing_dates)
        
        return GapAnalysisResponse(
            gaps_found=len(gaps),
            gaps=gaps,
            total_missing_days=total_missing_days
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing data gaps: {str(e)}")

@app.post("/readings/fill-gaps")
async def fill_data_gaps(db: Session = Depends(get_db)):
    try:
        # First, analyze gaps
        analysis = await analyze_data_gaps(db)
        
        if analysis.gaps_found == 0:
            return GapFillResponse(
                success=True,
                filled_days=0,
                filled_dates=[],
                message="No data gaps found to fill."
            )
        
        # Get base reading for consumption calculations
        base_reading = db.query(BaseReading).order_by(BaseReading.created_at.desc()).first()
        
        filled_dates = []
        filled_days = 0
        
        # Fill each gap
        for gap in analysis.gaps:
            for i, missing_date in enumerate(gap.missing_dates):
                parsed_date = datetime.strptime(missing_date, "%Y-%m-%d").date()
                
                # Calculate cumulative readings for this missing day
                # Start from the gap start reading and add incremental consumption
                days_from_start = i + 1
                
                interpolated_meter1 = int(gap.start_readings["meter1"] + (gap.per_day_consumption["meter1"] * days_from_start))
                interpolated_meter2 = int(gap.start_readings["meter2"] + (gap.per_day_consumption["meter2"] * days_from_start))
                interpolated_meter3 = int(gap.start_readings["meter3"] + (gap.per_day_consumption["meter3"] * days_from_start))
                
                # Calculate consumption from base readings
                meter1_consumption = interpolated_meter1 - base_reading.meter1_base
                meter2_consumption = interpolated_meter2 - base_reading.meter2_base
                meter3_consumption = interpolated_meter3 - base_reading.meter3_base
                
                # Check if reading already exists (shouldn't happen, but safety check)
                existing = db.query(MeterReading).filter(MeterReading.reading_date == parsed_date).first()
                
                if not existing:
                    # Create new interpolated reading
                    new_reading = MeterReading(
                        reading_date=parsed_date,
                        meter1_current=interpolated_meter1,
                        meter2_current=interpolated_meter2,
                        meter3_current=interpolated_meter3,
                        meter1_consumption=meter1_consumption,
                        meter2_consumption=meter2_consumption,
                        meter3_consumption=meter3_consumption
                    )
                    db.add(new_reading)
                    filled_dates.append(missing_date)
                    filled_days += 1
        
        # Commit all changes
        db.commit()
        
        return GapFillResponse(
            success=True,
            filled_days=filled_days,
            filled_dates=filled_dates,
            message=f"Successfully filled {filled_days} missing days with interpolated readings."
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error filling data gaps: {str(e)}")

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