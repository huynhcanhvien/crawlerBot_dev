"""
Utility decorator to add Swagger documentation to endpoints
"""

def swag_from(doc_string):
    """Decorator to add Swagger documentation to a function"""
    def decorator(func):
        func.__doc__ = doc_string
        return func
    return decorator