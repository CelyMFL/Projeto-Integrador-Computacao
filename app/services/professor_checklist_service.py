from app.models import ProfessorChecklist, Task, User, ProfessorTrilha, StatusEnum
from app import db
from datetime import datetime


class ProfessorChecklistService:
    """Service for managing task completion status per professor."""

    @staticmethod
    def mark_task_complete(professor_id, task_id):
        """
        Mark a task as complete for a professor.
        
        If all tasks in a trilha are completed and trilha is mandatory,
        auto-update trilha status to CONCLUIDO.
        
        Args:
            professor_id: Professor user ID
            task_id: Task ID
            
        Returns:
            ProfessorChecklist object or raises ValueError
        """
        # Validation
        professor = User.query.get(professor_id)
        if not professor:
            raise ValueError(f"Professor with ID {professor_id} not found")
        
        task = Task.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Check if already marked complete
        existing = ProfessorChecklist.query.filter_by(
            professor_id=professor_id,
            task_id=task_id
        ).first()
        
        if existing:
            if existing.concluido:
                return existing  # Already complete, idempotent
            else:
                # Update existing incomplete record
                existing.concluido = True
                existing.data_conclusao = datetime.utcnow()
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    raise ValueError(f"Error updating task completion: {str(e)}")
                
                # Check if trilha should be auto-completed
                ProfessorChecklistService._check_and_update_trilha_status(
                    professor_id, task.checklist_id
                )
                return existing
        
        try:
            prof_checklist = ProfessorChecklist(
                professor_id=professor_id,
                task_id=task_id,
                concluido=True,
                data_conclusao=datetime.utcnow()
            )
            db.session.add(prof_checklist)
            db.session.commit()
            
            # Check if trilha should be auto-completed
            ProfessorChecklistService._check_and_update_trilha_status(
                professor_id, task.checklist_id
            )
            
            return prof_checklist
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error marking task complete: {str(e)}")

    @staticmethod
    def mark_task_incomplete(professor_id, task_id):
        """
        Mark a task as incomplete for a professor.
        
        Also resets the trilha status to EM_ANDAMENTO if it was CONCLUIDO.
        
        Args:
            professor_id: Professor user ID
            task_id: Task ID
            
        Returns:
            ProfessorChecklist object or raises ValueError
        """
        prof_checklist = ProfessorChecklistService.get_professor_task_status(
            professor_id, task_id
        )
        if not prof_checklist:
            raise ValueError(f"No completion record for task {task_id}")
        
        try:
            prof_checklist.concluido = False
            prof_checklist.data_conclusao = None
            db.session.commit()
            
            # Reset trilha to em_andamento if needed
            task = Task.query.get(task_id)
            prof_trilha = ProfessorTrilha.query.filter_by(
                professor_id=professor_id,
                trilha_id=task.checklist_id
            ).first()
            
            if prof_trilha and prof_trilha.status == StatusEnum.CONCLUIDO:
                prof_trilha.status = StatusEnum.EM_ANDAMENTO
                prof_trilha.data_conclusao = None
                db.session.commit()
            
            return prof_checklist
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error marking task incomplete: {str(e)}")

    @staticmethod
    def get_professor_task_status(professor_id, task_id):
        """Get completion status of a task for a professor."""
        return ProfessorChecklist.query.filter_by(
            professor_id=professor_id,
            task_id=task_id
        ).first()

    @staticmethod
    def get_trilha_completion_status(professor_id, checklist_id):
        """
        Get detailed completion status for a trilha.
        
        Returns dict with completion info.
        """
        professor = User.query.get(professor_id)
        if not professor:
            raise ValueError(f"Professor with ID {professor_id} not found")
        
        trilha = Task.query.filter_by(checklist_id=checklist_id).all()
        if not trilha:
            raise ValueError(f"Trilha with ID {checklist_id} not found")
        
        # Get all tasks in trilha
        all_tasks = Task.query.filter_by(checklist_id=checklist_id).all()
        total_tasks = len(all_tasks)
        
        # Get completed tasks
        completed_tasks = ProfessorChecklist.query.filter(
            ProfessorChecklist.professor_id == professor_id,
            ProfessorChecklist.task_id.in_([t.id for t in all_tasks]),
            ProfessorChecklist.concluido == True
        ).count()
        
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'professor_id': professor_id,
            'trilha_id': checklist_id,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_percentage': completion_percentage,
            'is_complete': completed_tasks == total_tasks
        }

    @staticmethod
    def _check_and_update_trilha_status(professor_id, checklist_id):
        """
        Internal method to check if all tasks are complete
        and auto-update trilha status if needed.
        """
        try:
            # Get trilha enrollment
            prof_trilha = ProfessorTrilha.query.filter_by(
                professor_id=professor_id,
                trilha_id=checklist_id
            ).first()
            
            if not prof_trilha:
                return  # Professor not enrolled in this trilha

            # First completed task moves an allocated trilha to EM_ANDAMENTO
            if prof_trilha.status == StatusEnum.NAO_INICIADO:
                prof_trilha.status = StatusEnum.EM_ANDAMENTO
                prof_trilha.data_inicio = prof_trilha.data_inicio or datetime.utcnow()
                db.session.commit()

            # Get all tasks in trilha
            all_tasks = Task.query.filter_by(checklist_id=checklist_id).all()
            if not all_tasks:
                return  # No tasks to complete
            
            # Count completed tasks
            completed_tasks = ProfessorChecklist.query.filter(
                ProfessorChecklist.professor_id == professor_id,
                ProfessorChecklist.task_id.in_([t.id for t in all_tasks]),
                ProfessorChecklist.concluido == True
            ).count()
            
            # If all tasks completed and trilha not already concluded
            if completed_tasks == len(all_tasks) and prof_trilha.status != StatusEnum.CONCLUIDO:
                prof_trilha.status = StatusEnum.CONCLUIDO
                prof_trilha.data_conclusao = datetime.utcnow()
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Log error but don't raise, since this is a side effect

    @staticmethod
    def get_professor_all_tasks_status(professor_id):
        """Get completion status for all tasks a professor has started."""
        professor = User.query.get(professor_id)
        if not professor:
            raise ValueError(f"Professor with ID {professor_id} not found")
        
        return ProfessorChecklist.query.filter_by(professor_id=professor_id).all()

    @staticmethod
    def delete_task_completion(professor_id, task_id):
        """Delete task completion record."""
        prof_checklist = ProfessorChecklistService.get_professor_task_status(
            professor_id, task_id
        )
        if not prof_checklist:
            raise ValueError(f"No completion record for task {task_id}")
        
        try:
            db.session.delete(prof_checklist)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error deleting task completion: {str(e)}")
