class IncrementalScheduler:
    """Tracks affected sessions; callers regenerate only the returned session keys."""

    @staticmethod
    def affected_sessions(old_assignment, new_assignment):
        affected = set()
        if old_assignment:
            affected.add((old_assignment.date, old_assignment.session))
        if new_assignment:
            affected.add((new_assignment.date, new_assignment.session))
        return affected
