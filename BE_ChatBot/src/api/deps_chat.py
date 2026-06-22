from fastapi import HTTPException, Request

from src.pipeline.inference import RAGInference


def get_inference_service(request: Request) -> RAGInference:
    inference = getattr(request.app.state, "inference", None)
    if inference is None:
        raise HTTPException(status_code=503, detail="Inferecne Pipeline chua san sang")

    return inference
