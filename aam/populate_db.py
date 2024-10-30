from aam.models import Account, db

db.create_tables([Account])

events_list = [
    Account(name="Test", account_id="012345678901", account_status="Live"),
    Account(name="Peter", account_id="223344556677", account_status="Live"),
    Account(name="CFHH", account_id="654321987321", account_status="Suspended")
]
for event in events_list:
    event.save()
