from fastapi import APIRouter, Depends, HTTPException, Response

from app.dictionary_models import LookupRequest, LookupResponse
from app.services.dictionary_service import DictionaryError, get_dictionary_service

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


def translate_error(exc: DictionaryError):
    return HTTPException(
        status_code=exc.status, detail=exc.message,
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else None,
    )


@router.post("/lookup", response_model=LookupResponse)
def lookup(request: LookupRequest, service=Depends(get_dictionary_service)):
    try:
        return service.lookup(request.term)
    except DictionaryError as exc:
        raise translate_error(exc) from exc


@router.post("/audio")
def audio(request: LookupRequest, service=Depends(get_dictionary_service)):
    try:
        return Response(service.audio(request.term), media_type="audio/wav")
    except DictionaryError as exc:
        raise translate_error(exc) from exc
