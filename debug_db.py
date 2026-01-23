from app import create_app, db
from app.models import User

app = create_app()
app.app_context().push()

u = User.query.filter_by(email="mororoma555@gmail.com").first()  # или по email
u.is_admin = True
db.session.commit()