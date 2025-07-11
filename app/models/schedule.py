"""
Schedule Model
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ScheduledTask:
    TYPES = ['command', 'sequence']
    SCHEDULE_TYPES = ['once', 'daily', 'weekly', 'monthly']
    
    def __init__(self, id=None, type=None, target_id=None, schedule_type=None, 
                 schedule_data=None, next_run=None, created_by=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        
        if type not in self.TYPES:
            raise ValueError(f"Task type must be one of {self.TYPES}")
        self.type = type
        
        self.target_id = target_id
        
        if schedule_type not in self.SCHEDULE_TYPES:
            raise ValueError(f"Schedule type must be one of {self.SCHEDULE_TYPES}")
        self.schedule_type = schedule_type
        
        # Schedule data format depends on schedule_type
        # once: {'datetime': 'YYYY-MM-DD HH:MM:SS'}
        # daily: {'time': 'HH:MM:SS'}
        # weekly: {'day': 0-6, 'time': 'HH:MM:SS'} (0=Monday)
        # monthly: {'day': 1-31, 'time': 'HH:MM:SS'}
        self.schedule_data = schedule_data or {}
        self.next_run = next_run or self._calculate_next_run()
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_db_row(cls, row):
        """Create a ScheduledTask from a database row"""
        if not row:
            return None
            
        # Parse JSON from the database
        schedule_data = json.loads(row['schedule_data']) if isinstance(row['schedule_data'], str) else row['schedule_data']
        
        return cls(
            id=row['id'],
            type=row['type'],
            target_id=row['target_id'],
            schedule_type=row['schedule_type'],
            schedule_data=schedule_data,
            next_run=row['next_run'],
            created_by=row['created_by'],
            created_at=row['created_at']
        )
    
    def to_dict(self):
        """Convert to a dictionary for API responses"""
        return {
            'id': self.id,
            'type': self.type,
            'target_id': self.target_id,
            'schedule_type': self.schedule_type,
            'schedule_data': self.schedule_data,
            'next_run': self.next_run.isoformat() if isinstance(self.next_run, datetime) else self.next_run,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }
    
    def _calculate_next_run(self) -> Optional[datetime]:
        """Calculate the next run time based on the schedule type and data"""
        now = datetime.now()
        
        if self.schedule_type == 'once':
            if 'datetime' in self.schedule_data:
                return datetime.fromisoformat(self.schedule_data['datetime'])
            return now + timedelta(minutes=5)  # Default to 5 minutes from now
            
        elif self.schedule_type == 'daily':
            if 'time' in self.schedule_data:
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                hour, minute, second = map(int, self.schedule_data['time'].split(':'))
                next_run = today.replace(hour=hour, minute=minute, second=second)
                if next_run <= now:
                    next_run = next_run + timedelta(days=1)
                return next_run
            return now + timedelta(days=1)
            
        elif self.schedule_type == 'weekly':
            if 'day' in self.schedule_data and 'time' in self.schedule_data:
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                day_diff = (self.schedule_data['day'] - today.weekday()) % 7
                next_date = today + timedelta(days=day_diff)
                hour, minute, second = map(int, self.schedule_data['time'].split(':'))
                next_run = next_date.replace(hour=hour, minute=minute, second=second)
                if next_run <= now:
                    next_run = next_run + timedelta(days=7)
                return next_run
            return now + timedelta(weeks=1)
            
        elif self.schedule_type == 'monthly':
            if 'day' in self.schedule_data and 'time' in self.schedule_data:
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                day = min(self.schedule_data['day'], 28)  # Ensure valid day for all months
                if now.day > day:
                    next_month = now.replace(day=1) + timedelta(days=32)
                    next_date = next_month.replace(day=day)
                else:
                    next_date = now.replace(day=day)
                hour, minute, second = map(int, self.schedule_data['time'].split(':'))
                next_run = next_date.replace(hour=hour, minute=minute, second=second)
                if next_run <= now:
                    next_month = next_run.replace(day=1) + timedelta(days=32)
                    next_run = next_month.replace(day=day, hour=hour, minute=minute, second=second)
                return next_run
            return now + timedelta(days=30)
            
        return None
    
    def update_next_run(self):
        """Update the next run time based on the schedule type"""
        if self.schedule_type == 'once':
            self.next_run = None  # One-time tasks don't repeat
        else:
            self.next_run = self._calculate_next_run()
