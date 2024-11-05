from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
from sqlalchemy import text
from src import database as db

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(auth.get_api_key)],
)

# In the current state, contributions cannot be made unless already requested (foreign key violation otherwise).
# Consider how we might want to handle this (allow / disallow based on event & table logic?)

# Should deletion of users items happen separately in the Users endpoint? URL setup doesn't lend well to deleting
# by items here.

class Item(BaseModel):
    name: str
    type: str
    quantity: int
    payment: int

# Insert item requests for an event, or update if it's been added
@router.post("/{event_id}/requests")
def request_item(event_id: int, item: Item):
    request = text('''INSERT INTO event_items (event_id, name, type, requested, cost)
                      VALUES (:event_id, :name, :type, :quantity, :payment)
                      ON CONFLICT (event_id, name)
                      DO UPDATE SET (type, requested, cost) = (EXCLUDED.type, EXCLUDED.requested, EXCLUDED.cost)''')
    
    with db.engine.begin() as connection:
        connection.execute(request, dict(item) | {'event_id': event_id})

    return "OK"


# Insert an individual contribution, or update if it's been added
@router.post("/{event_id}/contributions/user/{username}")
def contribute_item(event_id: int, username: str, item: Item):
    contribute = text('''INSERT INTO items_ledger (event_id, username, item_name, quantity, payment)
                         VALUES (:event_id, :username, :name, :quantity, :payment)
                         ON CONFLICT (event_id, username, item_name)
                         DO UPDATE SET (quantity, payment) = (EXCLUDED.quantity, EXCLUDED.payment)''')

    with db.engine.begin() as connection:
        connection.execute(contribute, dict(item) | {'event_id': event_id, 'username': username})

    return "OK"


# Get contributions overall, grouped by item
@router.get("/{event_id}/contributions/")
def contributions(event_id: int):
    get_contributions = text('''SELECT item_name, SUM(quantity)::INTEGER AS total, SUM(payment)::INTEGER AS contribution
                                FROM items_ledger
                                WHERE event_id = :event_id
                                GROUP BY item_name''')
    
    with db.engine.begin() as connection:
        contributions = connection.execute(get_contributions, {'event_id': event_id}).mappings().all()

    return contributions


# Get contributions from a single user
@router.get("/{event_id}/contributions/user/{username}")
def user_contribution(event_id: int, username: str):
    get_contributions = text('''SELECT item_name, SUM(quantity)::INTEGER AS total, SUM(payment)::INTEGER AS contribution
                                FROM items_ledger
                                WHERE (event_id, username) IN ((:event_id, :username))
                                GROUP BY item_name''')
    
    with db.engine.begin() as connection:
        contributions = connection.execute(get_contributions, {'event_id': event_id, 'username': username}).mappings().all()

    return contributions


# Delete all contributions by an individual
@router.delete("/{event_id}/contributions/user/{username}")
def remove_user_contributions(event_id: int, username: str):
    remove_contributions = text('''UPDATE items_ledger
                                   SET deleted = TRUE
                                   WHERE (event_id, username) IN ((:event_id, :username))''')
    
    with db.engine.begin() as connection:
        connection.execute(remove_contributions, {'event_id': event_id, 'username': username})

    return "OK"


# Delete all event contributions
@router.delete("/{event_id}/contributions")
def remove_event_contribution(event_id: int):
    remove_contributions = text('''UPDATE items_ledger
                                   SET deleted = TRUE
                                   WHERE event_id = :event_id''')
    
    with db.engine.begin() as connection:
        connection.execute(remove_contributions, {'event_id': event_id})

    return "OK"

# print(contribute_item(4, "CorbynR", Item(name = "Cheetoes", type = "Snacks", quantity = 10, payment = 500)))
# print(request_item(4, Item(name = "Cheetoes", type = "Snacks", quantity = 5, payment = 500)))


    # add_item = text('''INSERT INTO event_items (event_id, name, type, requested, cost)
    #                    SELECT :event_id, :name, :type, :requested, :cost
    #                    WHERE NOT EXISTS (
    #                        SELECT 1
    #                        FROM event_items
    #                        WHERE (event_id, name) IN ((:event_id, :name))
    #                    )
    #                    RETURNING id;''')