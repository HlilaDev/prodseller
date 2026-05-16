from database import SessionLocal
from models import Client


def create_client(user):
    db = SessionLocal()
    client = db.query(Client).filter(Client.telegram_id == str(user.id)).first()
    if not client:
        client = Client(
            telegram_id=str(user.id),
            username=user.username,
            first_name=user.first_name,
            lang="en"
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    db.close()
    return client


def get_client(telegram_id: str):
    db = SessionLocal()
    client = db.query(Client).filter(Client.telegram_id == str(telegram_id)).first()
    db.close()
    return client


def set_client_lang(telegram_id: str, lang: str):
    db = SessionLocal()
    client = db.query(Client).filter(Client.telegram_id == str(telegram_id)).first()
    if client:
        client.lang = lang
        db.commit()
    db.close()


def get_client_lang(telegram_id: str) -> str:
    db = SessionLocal()
    client = db.query(Client).filter(Client.telegram_id == str(telegram_id)).first()
    lang = client.lang if client and client.lang else "en"
    db.close()
    return lang


def get_all_clients():
    db = SessionLocal()
    clients = db.query(Client).all()
    db.close()
    return clients
