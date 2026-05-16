from database import SessionLocal
from models import Client


def create_client(user):
    db = SessionLocal()

    existing_client = db.query(Client).filter(
        Client.telegram_id == str(user.id)
    ).first()

    if existing_client:
        db.close()
        return existing_client

    client = Client(
        telegram_id=str(user.id),
        username=user.username,
        first_name=user.first_name
    )

    db.add(client)
    db.commit()
    db.refresh(client)
    db.close()

    return client


def get_client(telegram_id: str):
    db = SessionLocal()

    client = db.query(Client).filter(
        Client.telegram_id == telegram_id
    ).first()

    db.close()

    return client


def get_all_clients():
    db = SessionLocal()

    clients = db.query(Client).all()

    db.close()

    return clients