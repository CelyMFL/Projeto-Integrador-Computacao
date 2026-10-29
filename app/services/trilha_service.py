from app.models import Checklist, TipoEnum, Task, ProfessorTrilha, ProfessorChecklist, Feedback
from app import db
from app.utils import titulo_ptbr


class TrilhaService:
    """Service for trilha (track) management."""

    @staticmethod
    def create_trilha(nome, descricao="", tipo=TipoEnum.PEDAGOGICA, obrigatoria=False):
        """
        Create a new trilha.
        
        Args:
            nome: Trilha name
            descricao: Trilha description
            tipo: Trilha type (TipoEnum)
            obrigatoria: Whether trilha is mandatory
            
        Returns:
            Checklist object (representing trilha) or raises ValueError
        """
        # Validation
        if not nome or not nome.strip():
            raise ValueError("Nome cannot be empty")
        
        if not isinstance(tipo, TipoEnum):
            raise ValueError(f"Invalid tipo: {tipo}")
        
        if not isinstance(obrigatoria, bool):
            raise ValueError("Obrigatoria must be boolean")
        
        try:
            trilha = Checklist(
                nome=titulo_ptbr(nome.strip()),
                descricao=descricao.strip() if descricao else "",
                tipo=tipo,
                obrigatoria=obrigatoria
            )
            db.session.add(trilha)
            db.session.commit()
            return trilha
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error creating trilha: {str(e)}")

    @staticmethod
    def get_trilha(trilha_id):
        """Get trilha by ID."""
        return Checklist.query.get(trilha_id)

    @staticmethod
    def list_trilhas():
        """Get all trilhas."""
        return Checklist.query.all()

    @staticmethod
    def list_trilhas_by_type(tipo):
        """List trilhas by type."""
        if not isinstance(tipo, TipoEnum):
            raise ValueError(f"Invalid tipo: {tipo}")
        return Checklist.query.filter_by(tipo=tipo).all()

    @staticmethod
    def list_obrigatorias():
        """Get all mandatory trilhas."""
        return Checklist.query.filter_by(obrigatoria=True).all()

    @staticmethod
    def update_trilha(trilha_id, nome=None, descricao=None, tipo=None, obrigatoria=None):
        """
        Update trilha information.
        
        Args:
            trilha_id: Trilha ID
            nome: New name (optional)
            descricao: New description (optional)
            tipo: New type (optional)
            obrigatoria: New obrigatoria flag (optional)
            
        Returns:
            Updated Checklist object or raises ValueError
        """
        trilha = TrilhaService.get_trilha(trilha_id)
        if not trilha:
            raise ValueError(f"Trilha with ID {trilha_id} not found")
        
        # Validation for provided fields
        if nome is not None:
            if not nome or not nome.strip():
                raise ValueError("Nome cannot be empty")
            trilha.nome = titulo_ptbr(nome.strip())
        
        if descricao is not None:
            trilha.descricao = descricao.strip() if descricao else ""
        
        if tipo is not None:
            if not isinstance(tipo, TipoEnum):
                raise ValueError(f"Invalid tipo: {tipo}")
            trilha.tipo = tipo
        
        if obrigatoria is not None:
            if not isinstance(obrigatoria, bool):
                raise ValueError("Obrigatoria must be boolean")
            trilha.obrigatoria = obrigatoria
        
        try:
            db.session.commit()
            return trilha
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error updating trilha: {str(e)}")

    @staticmethod
    def delete_trilha(trilha_id):
        """Delete trilha and all associated tasks."""
        trilha = TrilhaService.get_trilha(trilha_id)
        if not trilha:
            raise ValueError(f"Trilha with ID {trilha_id} not found")
        
        try:
            task_ids = [task.id for task in Task.query.filter_by(checklist_id=trilha_id).all()]

            if task_ids:
                ProfessorChecklist.query.filter(ProfessorChecklist.task_id.in_(task_ids)).delete(synchronize_session=False)

            Feedback.query.filter_by(trilha_id=trilha_id).delete(synchronize_session=False)
            ProfessorTrilha.query.filter_by(trilha_id=trilha_id).delete(synchronize_session=False)

            # Delete all tasks in trilha first
            Task.query.filter_by(checklist_id=trilha_id).delete()
            db.session.delete(trilha)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Error deleting trilha: {str(e)}")

    @staticmethod
    def get_trilha_tasks_count(trilha_id):
        """Get number of tasks in trilha."""
        trilha = TrilhaService.get_trilha(trilha_id)
        if not trilha:
            raise ValueError(f"Trilha with ID {trilha_id} not found")
        return len(trilha.tasks) if trilha.tasks else 0
