import os
import secrets
from decimal import Decimal
from fastapi import Header, HTTPException
from pydantic import BaseModel, Field


def internal_auth(x_internal_key: str = Header(default='')):
    key = os.getenv('INTERNAL_KEY', '')
    if not key or not secrets.compare_digest(key, x_internal_key):
        raise HTTPException(403, 'Internal API only')


class MoneyOperation(BaseModel):
    transaction_code: str = Field(min_length=1, max_length=64)
    user_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class MarkPaid(BaseModel):
    transaction_code: str = Field(min_length=1, max_length=64)
    tuition_fee_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
