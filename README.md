# Personal Electricity Meter Tracker

A microservices-based web application to track daily electricity meter readings and consumption for three separate meters in your house.

## Features

- **Home Page**: Enter daily readings for three electric meters
- **Configure Page**: Set base meter readings for consumption tracking
- **Report Page**: Advanced usage dashboard with consumption charts and monthly tracking
- **Meter Reading Lookup**: Select any date to view actual meter readings and consumption values
- **Meter Information**: Reference section with switch settings and generator configuration
- **Monthly Usage Limits**: Track 200 units per meter with visual progress indicators
- **Consumption Tracking**: Track units consumed from base readings (not raw meter readings)
- **Usage Analytics**: Daily averages, remaining units, and efficiency scoring
- **Progress Visualization**: Color-coded progress bars and usage alerts
- **Data Management**: Delete old data before base readings and remove specific day readings
- **Database Backup**: Automatic backup on stop with restore functionality
- **Network Access**: Access from other devices on same Wi-Fi network
- **Global CLI**: `emt` command for easy management from any directory
- **Persistent Storage**: PostgreSQL database with dedicated container
- **Microservices Architecture**: Fully containerized with service isolation
- **Environment-based Configuration**: Easy deployment across different environments

## Microservices Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│ (PostgreSQL)    │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Technology Stack

- **Backend**: FastAPI (Python) with PostgreSQL driver
- **Frontend**: React with Vite and environment-based configuration
- **Database**: PostgreSQL 15 with automated initialization
- **Charts**: Chart.js with react-chartjs-2
- **Containerization**: Docker & Docker Compose with health checks
- **Configuration**: Environment variables for all services

## Quick Start

### Prerequisites
- Docker and Docker Compose installed on your system

### Setup and Run

1. Clone or download this project
2. Navigate to the project directory
3. Copy the environment template:
```bash
cp .env.example .env
```
4. (Optional) Modify `.env` file with your preferred settings
5. Start the application using the global EMT command:
```bash
emt start
```

6. Access the application:
   - Frontend: http://localhost:3000
   - Network Access: http://YOUR_IP:3000 (auto-detected by `emt status`)
   - Backend API: Internal only (not exposed for security)
   - Database: Internal only (not exposed for security)

### EMT Global Command System

The project includes a comprehensive command-line interface for easy management:

```bash
# Primary application management
emt start      # Start application with status checks and URLs
emt stop       # Stop application gracefully (creates automatic backup)
emt restart    # Restart entire application
emt rebuild    # Rebuild Docker images and restart
emt status     # Show detailed status, resource usage, and URLs
emt logs       # View application logs (live or historical)
emt backup     # Create database backup on-demand
emt restore    # Restore database from backup (with confirmation)
emt help       # Show comprehensive help information
```

#### EMT Command Features
- **Universal Access**: Run from any directory on the system
- **Colored Output**: Enhanced readability with status indicators
- **Auto-Discovery**: Automatic local IP detection for network access
- **Resource Monitoring**: Real-time container resource usage
- **Automatic Backup**: Database backup created on every stop
- **Restore Safety**: Confirmation prompts before database restoration
- **Docker Integration**: Built-in health checks and status monitoring


### Environment Configuration

The application uses environment variables for configuration. See `.env.example` for all available options:

```bash
# Database Configuration
DB_HOST=database
DB_PORT=5432
DB_NAME=meter_tracker
DB_USER=meter_user
DB_PASSWORD=your_secure_password

# Backend Configuration
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://192.168.*:3000,http://10.*:3000

# Frontend Configuration
VITE_API_URL=/api
FRONTEND_PORT=3000

# Security Configuration
TRUSTED_HOSTS=your.local.ip,your-hostname.local

# Usage Tracking Configuration
MONTHLY_LIMIT_PER_METER=200
TOTAL_MONTHLY_LIMIT=600
# Note: Uses same-date monthly cycles (e.g., 4th to 4th of each month)
```

### Manual Setup (without Docker)

#### Database Setup
```bash
# Install PostgreSQL and create database
createdb meter_tracker
psql meter_tracker < database/init.sql
```

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
# Set environment variables
export DB_HOST=localhost
export DB_USER=your_user
export DB_PASSWORD=your_password
python main.py
```

#### Frontend Setup
```bash
cd frontend
npm install
# Set environment variables
export VITE_API_URL=http://localhost:8000
npm run dev
```

## Usage

### Initial Setup
1. Go to the Configure page (/configure)
2. Set your base meter readings (starting point for consumption tracking)
3. Enter the base date when you took these readings
4. Click "Set Base Readings"

### Adding Daily Readings
1. Go to the Home page (/)
2. Enter the current readings for each of your three meters
3. Click "Submit Readings"
4. The app automatically calculates consumption from your base readings
5. The form will remember your last entered values for convenience

### Viewing Reports
1. Go to the Report page (/report)
2. View the **Usage Dashboard** with:
   - **Summary Cards**: Total Consumed, Remaining, Daily Averages, Days Elapsed/Remaining
   - **Progress Bars**: Visual progress for each meter with color-coded alerts
   - **Usage Alerts**: Automatic warnings at 70%, 80%, 90% usage thresholds
3. View **Meter Information** section with:
   - **Switch Settings**: Meter 1 (100), Meter 2 (202), Meter 3 (2N1), Generator (241)
   - **Type Information**: SinglePhase New/Old, ThreePhase specifications
4. View **Individual Meter Cards** showing current usage for each meter
5. View detailed charts:
   - **Total Consumption Over Time**: Cumulative consumption from base date
   - **Daily Usage**: Units consumed each day (stacked bars)
6. Use **Meter Reading Lookup** to:
   - **Select any date** from the dropdown to view historical readings
   - **View actual meter readings** and consumption values for that specific day
   - **See timestamp** when the reading was recorded
7. **Monthly Tracking**: Same-date monthly cycles (e.g., 4th to 4th of each month) based on base reading date
8. Each meter is displayed in a different color for easy identification

### Data Management
1. Go to the Configure page (/configure)
2. **Delete Specific Day**: Select a specific date from dropdown to remove individual readings
3. **Delete Old Data**: Remove all readings older than your base date
4. Both options include confirmation prompts to prevent accidental data loss
5. This keeps your database clean and focused on current tracking period

### Database Backup & Restore
The application automatically creates database backups:

1. **Automatic Backup**: Every time you run `emt stop`, a backup is created
2. **Backup Location**: `backups/meter_tracker_backup.sql` in project directory
3. **Single Backup Policy**: Only one backup is kept (newest overwrites oldest)
4. **Restore Process**: Use `emt restore` to restore from backup
5. **Safety Features**: Confirmation prompt before restoring to prevent accidental data loss

```bash
# Stop application (creates backup automatically)
emt stop

# Create backup manually at any time
emt backup

# Restore from backup (with confirmation)
emt restore
```

## API Endpoints

- `POST /base-readings` - Set base meter readings for consumption tracking
- `GET /base-readings/latest` - Get the current base readings
- `POST /readings` - Submit new daily meter readings
- `GET /readings` - Get all readings from base date forward
- `GET /readings/latest` - Get the most recent readings
- `GET /readings/{date}` - **NEW**: Get specific date reading with actual meter values and consumption
- `GET /readings/dates` - Get all available reading dates for lookup and deletion
- `GET /consumption-summary` - Get consumption summary and totals
- `GET /usage-metrics` - Get comprehensive monthly usage metrics with same-date monthly cycle tracking
- `DELETE /readings/{date}` - Delete reading for a specific date
- `DELETE /readings/delete-old-data` - Delete readings older than specified date
- `GET /health` - Health check endpoint for monitoring

## Project Structure

```
electricity-meter-tracker/
├── backend/
│   ├── main.py              # FastAPI application with usage metrics API
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile          # Backend container config
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Home.jsx      # Daily readings input form
│   │   │   ├── Configure.jsx # Base readings setup & data management
│   │   │   └── Report.jsx    # Advanced usage dashboard with monthly tracking
│   │   ├── config.js         # Environment configuration
│   │   ├── App.jsx           # Main React component with routing
│   │   ├── main.jsx          # React entry point
│   │   └── index.css         # Responsive styling
│   ├── package.json          # Node dependencies
│   ├── .env                  # Frontend environment variables
│   └── Dockerfile           # Frontend container config
├── database/
│   └── init.sql            # Database initialization script
├── backups/
│   └── meter_tracker_backup.sql # Automatic database backup (created on stop)
├── .env                    # Main environment configuration
├── .env.example           # Environment template
├── emt                     # Global command-line interface
├── docker-compose.yml     # Multi-container orchestration
├── CLAUDE.md              # Development context and session history
└── README.md             # This file
```

## Data Storage

The application uses PostgreSQL database with persistent volumes. The database stores:

### Base Readings Table
- Base meter readings (starting point for consumption tracking)
- Base date when readings were taken
- Creation timestamp

### Meter Readings Table
- Date of daily reading
- Current values for all three meters
- Calculated consumption from base readings
- Timestamp of when the reading was recorded
- Automatic indexing for optimized queries

### View Database Data
```bash
# View all base readings
docker exec meter_tracker_db psql -U meter_user -d meter_tracker -c "SELECT * FROM base_readings ORDER BY created_at DESC;"

# View all meter readings
docker exec meter_tracker_db psql -U meter_user -d meter_tracker -c "SELECT * FROM meter_readings ORDER BY reading_date DESC;"
```

## Microservices Benefits

✅ **Independent Deployments** - Update any service without affecting others  
✅ **Service Isolation** - Failures in one service don't break the entire application  
✅ **Environment Flexibility** - Easy configuration for dev/staging/production  
✅ **Database Persistence** - Data survives container restarts and updates  
✅ **Scalability** - Scale individual services based on demand  
✅ **Health Monitoring** - Built-in health checks for all services  
✅ **Maximum Security** - Only frontend exposed externally, internal communication via Docker network  

## Troubleshooting

### Find Your IP Address
```bash
# Use EMT to automatically detect your IP
emt status

# Or find manually
ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}'
```

### Health Checks

Monitor service health using EMT commands:
```bash
# Check all services status with resource usage
emt status

# View application logs
emt logs

# Check specific service logs (if needed)
docker-compose logs backend
docker-compose logs frontend
docker-compose logs database

# Check backend health endpoint (via container)
docker-compose exec backend curl http://localhost:8000/health
```

### Development Mode

For development with hot-reload:
```bash
# Start only database
docker-compose up database

# Run backend locally (with environment variables)
cd backend
export DB_HOST=localhost DB_USER=meter_user DB_PASSWORD=secure_password123
python main.py

# Run frontend locally  
cd frontend && npm run dev
```

### Temporary API Access (Development Only)
```bash
# If you need direct API access for testing
docker-compose exec backend bash
# Or temporarily expose backend port by adding to docker-compose.yml:
# ports:
#   - "8000:8000"
```

## License

This project is open source and available under the MIT License.