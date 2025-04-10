from fastapi import FastAPI, HTTPException, Form, Request,  Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from  starlette.responses import RedirectResponse
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session


DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

user = []

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    birth_date = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(BaseModel):
    login: str
    first_name: str
    last_name: str
    birth_date: str

@app.get("/user/add", response_class=HTMLResponse)

def add_user_form(request: Request):
    return templates.TemplateResponse("add_user.html", {"request": request})

@app.post("/user/add", response_class=HTMLResponse)

def add_user(login: str = Form(...), first_name: str = Form(...), last_name: str = Form(...),
             birth_date: str = Form(...)
             , db: Session = Depends(get_db)):
    user = UserDB(login=login, first_name=first_name, last_name=last_name, birth_date=birth_date)
    db.add(user)
    db.commit()
    return RedirectResponse(url="/user/view", status_code=303)

@app.get("/user/view", response_class=HTMLResponse)
def view_users(request: Request, db: Session = Depends(get_db)):
    user = db.query(UserDB).all()
    return templates.TemplateResponse("view_users.html", {"request": request, "users": user})