class ReplicaRouter:
    """Route read queries to replica database"""
    
    def db_for_read(self, model, **hints):
        """Send read queries to replica"""
        # Analytics queries should use replica
        if model._meta.app_label == 'analytics':
            return 'replica'
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Send all writes to primary database"""
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between objects on the same database"""
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only run on primary database"""
        return db == 'default'