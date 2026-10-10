from uuid import UUID

from fastapi import APIRouter, Depends

from app.dictionary_routes import translate_error
from app.services.dictionary_service import DictionaryError, get_dictionary_service
from app.services.enrichment_service import enrich_entry

router = APIRouter(prefix='/entries', tags=['enrichment'])


@router.post('/{entry_id}/enrich')
def enrich(entry_id: UUID, dictionary=Depends(get_dictionary_service)):
    try:
        return enrich_entry(entry_id, dictionary)
    except DictionaryError as exc:
        raise translate_error(exc) from exc
