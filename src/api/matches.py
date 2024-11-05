from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import datetime
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/matches",
    tags=["matches"],
    dependencies=[Depends(auth.get_api_key)],
)

