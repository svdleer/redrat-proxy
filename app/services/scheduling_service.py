"""
Scheduling Service
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.database import get_db
from app.utils.logger import logger
from app.models.schedule import ScheduledTask
from app.services.sequence_service import SequenceService

class SchedulingService:
    @staticmethod
    def schedule_task(task_type: str, target_id: str, schedule_type: str, 
                      schedule_data: Dict[str, Any], user_id: str) -> ScheduledTask:
        """Schedule a new task"""
        task = ScheduledTask(
            type=task_type,
            target_id=target_id,
            schedule_type=schedule_type,
            schedule_data=schedule_data,
            created_by=user_id
        )
        
        # Calculate the next run time
        task.next_run = task._calculate_next_run()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scheduled_tasks
                (id, type, target_id, schedule_type, schedule_data, next_run, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (task.id, task.type, task.target_id, task.schedule_type, 
                  json.dumps(task.schedule_data), task.next_run, task.created_by, task.created_at))
            conn.commit()
            
        logger.info(f"Task scheduled: {task_type} {target_id} for {task.next_run}")
        return task
    
    @staticmethod
    def get_task(task_id: str) -> Optional[ScheduledTask]:
        """Get a scheduled task by ID"""
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM scheduled_tasks WHERE id = %s
            """, (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return ScheduledTask.from_db_row(row)
    
    @staticmethod
    def get_all_tasks(user_id: Optional[str] = None) -> List[ScheduledTask]:
        """Get all scheduled tasks, optionally filtered by user"""
        tasks = []
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            if user_id:
                cursor.execute("""
                    SELECT * FROM scheduled_tasks WHERE created_by = %s
                    ORDER BY next_run
                """, (user_id,))
            else:
                cursor.execute("SELECT * FROM scheduled_tasks ORDER BY next_run")
                
            rows = cursor.fetchall()
            
            for row in rows:
                tasks.append(ScheduledTask.from_db_row(row))
                
        return tasks
    
    @staticmethod
    def get_due_tasks() -> List[ScheduledTask]:
        """Get tasks that are due for execution"""
        tasks = []
        now = datetime.now()
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM scheduled_tasks 
                WHERE next_run <= %s
                ORDER BY next_run
            """, (now,))
            
            rows = cursor.fetchall()
            
            for row in rows:
                tasks.append(ScheduledTask.from_db_row(row))
                
        return tasks
    
    @staticmethod
    def process_due_tasks() -> int:
        """Process tasks that are due for execution and return the count"""
        tasks = SchedulingService.get_due_tasks()
        count = 0
        
        for task in tasks:
            try:
                # Execute the task based on its type
                if task.type == 'command':
                    # For a command, update its status to 'queued'
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE commands
                            SET status = 'queued'
                            WHERE id = %s
                        """, (task.target_id,))
                        conn.commit()
                        
                    logger.info(f"Scheduled command {task.target_id} queued")
                    
                elif task.type == 'sequence':
                    # For a sequence, execute all its commands
                    SequenceService.execute_sequence(task.target_id)
                    logger.info(f"Scheduled sequence {task.target_id} executed")
                
                # Update the next run time for recurring tasks
                if task.schedule_type != 'once':
                    task.update_next_run()
                    
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE scheduled_tasks
                            SET next_run = %s
                            WHERE id = %s
                        """, (task.next_run, task.id))
                        conn.commit()
                else:
                    # Delete one-time tasks after execution
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            DELETE FROM scheduled_tasks
                            WHERE id = %s
                        """, (task.id,))
                        conn.commit()
                
                count += 1
                
            except Exception as e:
                logger.error(f"Error processing scheduled task {task.id}: {e}")
                
        return count
    
    @staticmethod
    def delete_task(task_id: str) -> bool:
        """Delete a scheduled task"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM scheduled_tasks
                WHERE id = %s
            """, (task_id,))
            conn.commit()
            
        logger.info(f"Task {task_id} deleted")
        return True
