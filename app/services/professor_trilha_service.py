from app.models import ProfessorTrilha, ProfessorChecklist, StatusEnum, User, Checklist, Task, RoleEnum
from app import db
from datetime import datetime


class ProfessorTrilhaService:
    """Service for managing professor trilha progress."""

    @staticmethod
    def start_trilha(professor_id, trilha_id):
        """
        Start a trilha for a professor.
        
        Args:
            professor_id: Professor user ID
            trilha_id: Trilha ID
            
        Returns:
            ProfessorTrilha object or raises ValueError
        """
        # Validation
        professor = User.query.get(professor_id)
        if not professor:
            raise ValueError(f"Professor with ID {professor_id} not found")
        
        trilha = Checklist.query.get(trilha_id)
        if not trilha:
            raise ValueError(f"Trilha with ID {trilha_id} not found")
        
        # Check if professor already has this trilha
        existing = ProfessorTrilha.query.filter_by(
            professor_id=professor_id,
            trilha_id=trilha_id
        ).first()
        
        if existing:
            # A trilha allocated by an admin (NAO_INICIADO) can still be started by the professor
            if existing.status != StatusEnum.NAO_INICIADO:
                raise ValueError(f"Professor already has trilha {trilha_id}")
            try:
                existing.status = StatusEnum.EM_ANDAMENTO
                existing.data_inicio = existing.data_inicio or datetime.utcnow()
                db.session.commit()
                return existing
            except Exception as e:
                db.session.rollback()
                raise ValueError(f"Error starting trilha: {str(e)}")

        try:
            prof_trilha = ProfessorTrilha(
                professor_id=professor_id,
                trilha_id=trilha_id,
                status=StatusEnum.EM_ANDAMENTO,
                data_inicio=datetime.utcnow()
            )
            db.session.add(prof_trilha)
            db.session.commit()
            return prof_trilha
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error starting trilha: {str(e)}")

    @staticmethod
    def get_professor_trilha(professor_id, trilha_id):
        """Get professor-trilha relationship."""
        return ProfessorTrilha.query.filter_by(
            professor_id=professor_id,
            trilha_id=trilha_id
        ).first()

    @staticmethod
    def get_professor_trilhas(professor_id):
        """Get all trilhas for a professor."""
        professor = User.query.get(professor_id)
        if not professor:
            raise ValueError(f"Professor with ID {professor_id} not found")
        
        return ProfessorTrilha.query.filter_by(professor_id=professor_id).all()

    @staticmethod
    def get_trilha_professors(trilha_id):
        """Get all professors enrolled in a trilha."""
        trilha = Checklist.query.get(trilha_id)
        if not trilha:
            raise ValueError(f"Trilha with ID {trilha_id} not found")
        
        return ProfessorTrilha.query.filter_by(trilha_id=trilha_id).all()

    @staticmethod
    def update_trilha_status(professor_id, trilha_id, new_status):
        """
        Update trilha status for professor.
        
        Valid transitions:
        - NAO_INICIADO -> EM_ANDAMENTO -> CONCLUIDO
        
        Args:
            professor_id: Professor user ID
            trilha_id: Trilha ID
            new_status: New status (StatusEnum)
            
        Returns:
            Updated ProfessorTrilha or raises ValueError
        """
        if not isinstance(new_status, StatusEnum):
            raise ValueError(f"Invalid status: {new_status}")
        
        prof_trilha = ProfessorTrilhaService.get_professor_trilha(professor_id, trilha_id)
        if not prof_trilha:
            raise ValueError(f"Professor {professor_id} not enrolled in trilha {trilha_id}")
        
        # Validate state transitions
        current_status = prof_trilha.status
        
        # Allow same status (idempotent)
        if current_status == new_status:
            return prof_trilha
        
        # Only allow forward transitions
        if current_status == StatusEnum.NAO_INICIADO and new_status == StatusEnum.EM_ANDAMENTO:
            pass  # Valid
        elif current_status == StatusEnum.NAO_INICIADO and new_status == StatusEnum.CONCLUIDO:
            raise ValueError("Cannot jump from nao_iniciado to concluido")
        elif current_status == StatusEnum.EM_ANDAMENTO and new_status == StatusEnum.CONCLUIDO:
            pass  # Valid
        elif current_status == StatusEnum.CONCLUIDO:
            raise ValueError("Cannot change status of completed trilha")
        else:
            raise ValueError(f"Invalid status transition: {current_status} -> {new_status}")
        
        try:
            prof_trilha.status = new_status
            
            # Set data_conclusao if completing
            if new_status == StatusEnum.CONCLUIDO:
                prof_trilha.data_conclusao = datetime.utcnow()
            
            db.session.commit()
            return prof_trilha
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error updating trilha status: {str(e)}")

    @staticmethod
    def get_trilha_progress(professor_id, trilha_id):
        """
        Get completion progress for a trilha.
        
        Returns dict with:
        - status: Current status
        - total_tasks: Total tasks in trilha
        - completed_tasks: Number of completed tasks
        - completion_percentage: % completed
        """
        prof_trilha = ProfessorTrilhaService.get_professor_trilha(professor_id, trilha_id)
        if not prof_trilha:
            raise ValueError(f"Professor {professor_id} not enrolled in trilha {trilha_id}")
        
        trilha = Checklist.query.get(trilha_id)
        total_tasks = len(trilha.tasks) if trilha.tasks else 0
        
        from app.models import ProfessorChecklist
        completed_tasks = ProfessorChecklist.query.filter_by(
            professor_id=professor_id,
            task_id=None  # Will be updated when checking actual tasks
        ).count()
        
        # Better way: count completed tasks for this trilha's tasks
        if trilha.tasks:
            completed_tasks = ProfessorChecklist.query.filter(
                ProfessorChecklist.professor_id == professor_id,
                ProfessorChecklist.task_id.in_([t.id for t in trilha.tasks]),
                ProfessorChecklist.concluido == True
            ).count()
        
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            'status': prof_trilha.status.value,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'completion_percentage': completion_percentage,
            'data_inicio': prof_trilha.data_inicio,
            'data_conclusao': prof_trilha.data_conclusao
        }

    @staticmethod
    def is_trilha_required_complete(professor_id, trilha_id):
        """
        Check if mandatory trilha is complete.
        
        Returns True if trilha is not mandatory OR is completed.
        """
        trilha = Checklist.query.get(trilha_id)
        if not trilha:
            raise ValueError(f"Trilha with ID {trilha_id} not found")
        
        if not trilha.obrigatoria:
            return True  # Not mandatory, so "required" completion is satisfied
        
        prof_trilha = ProfessorTrilhaService.get_professor_trilha(professor_id, trilha_id)
        if not prof_trilha:
            return False
        
        return prof_trilha.status == StatusEnum.CONCLUIDO

    @staticmethod
    def delete_enrollement(professor_id, trilha_id):
        """Remove professor from trilha."""
        prof_trilha = ProfessorTrilhaService.get_professor_trilha(professor_id, trilha_id)
        if not prof_trilha:
            raise ValueError(f"Enrollment not found for professor {professor_id} and trilha {trilha_id}")
        
        try:
            db.session.delete(prof_trilha)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error deleting enrollment: {str(e)}")

    # ------------------------------------------------------------------
    # Admin allocation
    # ------------------------------------------------------------------

    @staticmethod
    def count_completed_tasks(professor_id, trilha_id):
        """Count tasks of a trilha already completed by a professor."""
        task_ids = [task.id for task in Task.query.filter_by(checklist_id=trilha_id).all()]
        if not task_ids:
            return 0
        return ProfessorChecklist.query.filter(
            ProfessorChecklist.professor_id == professor_id,
            ProfessorChecklist.task_id.in_(task_ids),
            ProfessorChecklist.concluido == True,
        ).count()

    @staticmethod
    def _parse_status(value):
        try:
            return StatusEnum(value)
        except ValueError:
            raise ValueError(f"Invalid status: {value}")

    @staticmethod
    def _apply_status(prof_trilha, new_status):
        """Apply an admin-chosen status to an existing enrollment (no commit).

        Returns True when something changed.
        """
        if new_status == prof_trilha.status:
            return False

        if new_status == StatusEnum.CONCLUIDO:
            raise ValueError("Status concluido is set automatically when all tasks are completed")

        if new_status == StatusEnum.NAO_INICIADO:
            if ProfessorTrilhaService.count_completed_tasks(prof_trilha.professor_id, prof_trilha.trilha_id):
                raise ValueError("Cannot set nao_iniciado: professor already completed tasks of this trilha")
            prof_trilha.data_inicio = None
            prof_trilha.data_conclusao = None
        else:  # EM_ANDAMENTO, including reopening a concluded trilha
            prof_trilha.data_inicio = prof_trilha.data_inicio or datetime.utcnow()
            prof_trilha.data_conclusao = None

        prof_trilha.status = new_status
        return True

    @staticmethod
    def _delete_enrollment(prof_trilha):
        """Delete an enrollment and the task completions tied to it (no commit)."""
        task_ids = [task.id for task in Task.query.filter_by(checklist_id=prof_trilha.trilha_id).all()]
        if task_ids:
            ProfessorChecklist.query.filter(
                ProfessorChecklist.professor_id == prof_trilha.professor_id,
                ProfessorChecklist.task_id.in_(task_ids),
            ).delete(synchronize_session=False)
        db.session.delete(prof_trilha)

    @staticmethod
    def _sync(existing, desired, key_of, make_pair):
        """Shared add/update/remove logic for both allocation screens.

        existing: enrollments inside the scope being edited.
        desired: {key: status_value}, where key identifies the other side of the pair.
        Returns {'added': n, 'updated': n, 'removed': n}; commits once or rolls back.
        """
        parsed = {key: ProfessorTrilhaService._parse_status(value) for key, value in desired.items()}
        current = {key_of(item): item for item in existing}
        summary = {'added': 0, 'updated': 0, 'removed': 0}

        try:
            for key, item in current.items():
                if key not in parsed:
                    ProfessorTrilhaService._delete_enrollment(item)
                    summary['removed'] += 1

            for key, status in parsed.items():
                if key in current:
                    if ProfessorTrilhaService._apply_status(current[key], status):
                        summary['updated'] += 1
                    continue

                if status == StatusEnum.CONCLUIDO:
                    raise ValueError("Cannot allocate a trilha as concluido")
                professor_id, trilha_id = make_pair(key)
                db.session.add(ProfessorTrilha(
                    professor_id=professor_id,
                    trilha_id=trilha_id,
                    status=status,
                    data_inicio=datetime.utcnow() if status == StatusEnum.EM_ANDAMENTO else None,
                ))
                summary['added'] += 1

            db.session.commit()
            return summary
        except ValueError:
            db.session.rollback()
            raise
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error saving allocations: {str(e)}")

    @staticmethod
    def sync_professor_trilhas(professor_id, desired):
        """Make the trilhas of one professor match `desired` ({trilha_id: status})."""
        professor = User.query.get(professor_id)
        if not professor or professor.role != RoleEnum.PROFESSOR:
            raise ValueError(f"Professor with ID {professor_id} not found")
        for trilha_id in desired:
            if not Checklist.query.get(trilha_id):
                raise ValueError(f"Trilha with ID {trilha_id} not found")

        existing = ProfessorTrilha.query.filter_by(professor_id=professor_id).all()
        return ProfessorTrilhaService._sync(
            existing, desired, lambda item: item.trilha_id, lambda trilha_id: (professor_id, trilha_id)
        )

    @staticmethod
    def sync_trilha_professores(trilha_id, desired):
        """Make the professors of one trilha match `desired` ({professor_id: status})."""
        if not Checklist.query.get(trilha_id):
            raise ValueError(f"Trilha with ID {trilha_id} not found")
        for professor_id in desired:
            professor = User.query.get(professor_id)
            if not professor or professor.role != RoleEnum.PROFESSOR:
                raise ValueError(f"Professor with ID {professor_id} not found")

        existing = ProfessorTrilha.query.filter_by(trilha_id=trilha_id).all()
        return ProfessorTrilhaService._sync(
            existing, desired, lambda item: item.professor_id, lambda professor_id: (professor_id, trilha_id)
        )
