from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["chromadb"])

@router.get('/test')
async def test():
    return "testing!"
    
# Compute embedding vector values of input
    
# Compute Recent Context Weighted Average:
# 1. if X=5, create a range of weights with sum=1 (ex: [0.1, 0.2, 0.3, 0.4])
# 2. Multiply each embedding of recent message entries by it's weight, more recent the entry, the higher weight
# 3. Sum the resulting vectors


# FUNCTION: Assemble context
# 1. Compute weighted_average_recent_context using above function
# 2. Use the summed vector to query ChromaDB for similar entries
# ...