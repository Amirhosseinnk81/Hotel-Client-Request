from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "Hotel Client Request API",
        "version": "0.1.0",
    }
    
    
@router.get("/error", tags=["Health"])
def test_error():
    raise Exception("This is a test exception")