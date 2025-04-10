from fastapi import FastAPI, HTTPException, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import hashlib
from fastapi.staticfiles import StaticFiles
from fastapi import Cookie
import json

DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True)
    password = Column(String)
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

# Pydantic model for registering a user (JSON approach)
class RegisterUserRequest(BaseModel):
    login: str
    password: str
    first_name: str
    last_name: str
    birth_date: str

# Endpoint for displaying the registration form
@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Endpoint for processing the registration form (Form data)
@app.post("/register")
def register_user(
    response: Response,
    login: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: str = Form(...),
    db: Session = Depends(get_db)
):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    new_user = UserDB(
        login=login,
        password=hashed_password,
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

# Endpoint for processing the registration (JSON approach)
@app.post("/register/json")
def register_user_json(
    user: RegisterUserRequest,  # Data is received as JSON
    db: Session = Depends(get_db)
):
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    new_user = UserDB(
        login=user.login,
        password=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        birth_date=user.birth_date
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=303)

# Endpoint for displaying the login form
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Endpoint for processing the login (Form data)
@app.post("/login")
def login_user(
    response: Response,
    login: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    user = db.query(UserDB).filter_by(login=login, password=hashed_password).first()
    if user:
        response = RedirectResponse(url="/products", status_code=303)
        response.set_cookie(key="user_login", value=user.login)
        return response
    raise HTTPException(status_code=401, detail="Invalid credentials")

# Endpoint for displaying users (after successful login)
@app.get("/user/view", response_class=HTMLResponse)
def view_users(request: Request, db: Session = Depends(get_db)):
    user_login = request.cookies.get("user_login")
    if not user_login:
        return RedirectResponse("/login", status_code=303)
    users = db.query(UserDB).all()
    return templates.TemplateResponse("view_users.html", {"request": request, "users": users})

@app.get("/main/page", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/products", response_class=HTMLResponse)
def products(request: Request):
    return templates.TemplateResponse("products.html", {"request": request})

@app.post("/add-to-cart")
def add_to_cart(
    response: Response,
    request: Request,
    item: str = Form(...),
    cart: str = Cookie(default="[]")
):
    cart_items = json.loads(cart)
    cart_items.append(item)
    response = RedirectResponse(url="/products", status_code=303)
    response.set_cookie(key="cart", value=json.dumps(cart_items))
    return response

@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, cart: str = Cookie(default="[]")):
    cart_items = json.loads(cart)
    return templates.TemplateResponse("cart.html", {"request": request, "cart": cart_items})

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, db: Session = Depends(get_db)):
    user_login = request.cookies.get("user_login")
    if not user_login:
        return RedirectResponse("/login", status_code=303)
    user = db.query(UserDB).filter_by(login=user_login).first()
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.post("/profile/change-password")
def change_password(
    request: Request,
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    user_login = request.cookies.get("user_login")
    if not user_login:
        return RedirectResponse("/login", status_code=303)

    user = db.query(UserDB).filter_by(login=user_login).first()
    if user:
        user.password = hashlib.sha256(new_password.encode()).hexdigest()
        db.commit()
    return RedirectResponse("/profile", status_code=303)


@app.post("/remove-from-cart")
def remove_from_cart(
    request: Request,
    response: Response,
    item: str = Form(...),
    cart: str = Cookie(default="[]")
):
    cart_items = json.loads(cart)
    if item in cart_items:
        cart_items.remove(item)
    response = RedirectResponse("/cart", status_code=303)
    response.set_cookie(key="cart", value=json.dumps(cart_items))
    return response