from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class VisitListEntry(BaseModel):
    name: str


@router.get('/api/visits', response_model=list[VisitListEntry])
def list_visits():
    return [
        VisitListEntry(name='raw:broccoli'),
        VisitListEntry(name='calexp:192350'),
    ]
