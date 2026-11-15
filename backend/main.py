import random
import string
import asyncio
import secrets
import models
import schemas
from datetime import datetime, timezone, timedelta
from typing import List
from contextlib import asynccontextmanager
from database import engine, get_db, SessionLocal
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware


# models.Base.metadata.create_all(bind=engine)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запускаем фоновую задачу при старте сервера
    task = asyncio.create_task(game_timer_loop())
    yield
    # Отменяем задачу при остановке сервера
    task.cancel()

app = FastAPI(title="Invest Game API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых адресов (для разработки это удобно)
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешаем любые заголовки
)

async def game_timer_loop():
    """Фоновый цикл, который проверяет таймеры каждые 5 секунд"""
    while True:
        try:
            db = SessionLocal()
            # Ищем активные игры, у которых истекло время текущей фазы
            now = datetime.now(timezone.utc)
            expired_games = db.query(models.Game).filter(
                models.Game.state_end_time <= now,
                models.Game.status != models.GameStatus.FINISHED,
                models.Game.status != models.GameStatus.LOBBY
            ).all()

            for game in expired_games:
                await force_next_phase(game, db)
            
            db.close()
        except Exception as e:
            print(f"Error in timer loop: {e}")
        
        await asyncio.sleep(5) # Проверка каждые 5 секунд

async def force_next_phase(game: models.Game, db: Session):
    """Принудительный переход в следующую фазу по истечении времени"""
    print(f"Force transition for game {game.room_code} from {game.status}")
    
    # Логика переходов (пока просто переключаем статусы, добавим бизнес-логику позже)
    if game.status == models.GameStatus.INVESTING:
        game.status = models.GameStatus.SHOW_NEWS
    elif game.status == models.GameStatus.SHOW_NEWS:
        game.status = models.GameStatus.BUY_INSIDER
    elif game.status == models.GameStatus.BUY_INSIDER:
        game.status = models.GameStatus.REBALANCING
    elif game.status == models.GameStatus.REBALANCING:
        game.current_round += 1
        if game.current_round > game.total_rounds:
            game.status = models.GameStatus.FINISHED
            game.state_end_time = None
        else:
            game.status = models.GameStatus.SHOW_NEWS # Новый раунд начинается с новостей

    # Если игра не закончена, ставим новый таймер на 10 минут
    if game.status != models.GameStatus.FINISHED:
        game.state_end_time = datetime.now(timezone.utc) + timedelta(minutes=game.round_duration_mins)
    
    # Сбрасываем флаг готовности у команд
    for team in game.teams:
        team.is_ready = False
        
    db.commit()

def generate_room_code() -> str:
    """Генерирует 6-значный код комнаты (например, 'A7B2X9')"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def apply_news_for_round(game: models.Game, db: Session):
    """Выбирает новости из пула, обновляет цены стартапов и помечает новости использованными"""
    for startup in game.startups:
        # Ищем неиспользованную новость для этого стартапа
        news = db.query(models.News).filter(
            models.News.game_id == game.id,
            models.News.startup_id == startup.id,
            models.News.is_used == False
        ).first()

        if news:
            # Применяем мультипликатор к цене (округляем до целого)
            startup.current_price = int(startup.current_price * news.multiplier)
            # Помечаем новость как использованную
            news.is_used = True
        else:
            # Если новости нет, цена остается прежней
            pass
            
    db.commit()

async def force_next_phase(game: models.Game, db: Session):
    """Принудительный переход в следующую фазу по истечении времени"""
    print(f"Force transition for game {game.room_code} from {game.status}")
    
    if game.status == models.GameStatus.INVESTING:
        game.status = models.GameStatus.SHOW_NEWS
        apply_news_for_round(game, db) # <--- ПРИМЕНЯЕМ НОВОСТИ ПЕРЕД ПОКАЗОМ
        
    elif game.status == models.GameStatus.SHOW_NEWS:
        game.status = models.GameStatus.BUY_INSIDER
        
    elif game.status == models.GameStatus.BUY_INSIDER:
        game.status = models.GameStatus.REBALANCING
        
    elif game.status == models.GameStatus.REBALANCING:
        game.current_round += 1
        if game.current_round > game.total_rounds:
            game.status = models.GameStatus.FINISHED
            game.state_end_time = None
        else:
            game.status = models.GameStatus.SHOW_NEWS
            apply_news_for_round(game, db) # <--- НОВЫЙ РАУНД, СНОВА НОВОСТИ

    if game.status != models.GameStatus.FINISHED:
        game.state_end_time = datetime.now(timezone.utc) + timedelta(seconds=game.round_duration_seconds)
    
    for team in game.teams:
        team.is_ready = False
        
    db.commit()

@app.post("/api/games", response_model=schemas.GameResponse)
def create_game(game_data: schemas.GameCreate, db: Session = Depends(get_db)):
    """Создание новой игры (делает Админ)"""

    room_code = generate_room_code()
    while db.query(models.Game).filter(models.Game.room_code == room_code).first():
        room_code = generate_room_code()

    new_game = models.Game(
        room_code=room_code,
        total_rounds=game_data.total_rounds,
        round_duration_mins=game_data.round_duration_mins,
        starting_capital=game_data.starting_capital
    )
    db.add(new_game)
    db.commit()
    db.refresh(new_game)
    return new_game

@app.post("/api/games/{room_code}/join", response_model=schemas.TeamResponse)
def join_game(room_code: str, team_data: schemas.TeamCreate, db: Session = Depends(get_db)):
    """Подключение команды к игре (делает Игрок)"""
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Игра с таким кодом не найдена")
    if game.status != models.GameStatus.LOBBY:
        raise HTTPException(status_code=400, detail="Игра уже началась")
    
    existing_team = db.query(models.Team).filter(
        models.Team.game_id == game.id, 
        models.Team.name == team_data.name
    ).first()
    if existing_team:
        raise HTTPException(status_code=400, detail="Команда с таким именем уже существует")

    new_team = models.Team(
        game_id=game.id,
        name=team_data.name,
        cash=game.starting_capital,
        session_token=secrets.token_hex(16)
    )
    db.add(new_team)
    db.commit()
    db.refresh(new_team)
    return new_team

@app.get("/api/games/{room_code}/status", response_model=schemas.GameStatusResponse)
def get_game_status(room_code: str, db: Session = Depends(get_db)):
    """Получение статуса игры и списка подключенных команд (для лобби)"""
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    
    return game

@app.post("/api/games/{room_code}/start", response_model=schemas.GameStartResponse)
def start_game(room_code: str, db: Session = Depends(get_db)):
    """Админ запускает игру (Переход из LOBBY в INVESTING)"""
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    if game.status != models.GameStatus.LOBBY:
        raise HTTPException(status_code=400, detail="Игра уже запущена")
    
    # Меняем статус
    game.status = models.GameStatus.INVESTING
    game.current_round = 1
    
    # Ставим таймер на первую фазу (Инвестирование)
    game.state_end_time = datetime.now(timezone.utc) + timedelta(minutes=game.round_duration_mins)
    
    db.commit()
    return {"status": "success", "message": "Игра началась!", "state_end_time": game.state_end_time}

@app.post("/api/games/{room_code}/invest")
def make_investment(room_code: str, team_id: int, action: schemas.InvestmentAction, db: Session = Depends(get_db)):
    """Команда покупает акции на первичном раунде"""
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    
    if not game or game.status != models.GameStatus.INVESTING:
        raise HTTPException(status_code=400, detail="Сейчас нельзя инвестировать")
    
    team = db.query(models.Team).filter(models.Team.id == team_id, models.Team.game_id == game.id).first()
    startup = db.query(models.Startup).filter(models.Startup.id == action.startup_id, models.Startup.game_id == game.id).first()
    
    if not team or not startup:
        raise HTTPException(status_code=404, detail="Команда или стартап не найдены")

    total_cost = action.shares_to_buy * startup.current_price
    
    if team.cash < total_cost:
        raise HTTPException(status_code=400, detail="Недостаточно средств")

    # Списываем деньги
    team.cash -= total_cost
    
    # Добавляем акции в портфель (или обновляем, если уже есть)
    portfolio = db.query(models.Portfolio).filter(
        models.Portfolio.team_id == team.id,
        models.Portfolio.startup_id == startup.id
    ).first()
    
    if portfolio:
        portfolio.shares += action.shares_to_buy
    else:
        new_portfolio = models.Portfolio(team_id=team.id, startup_id=startup.id, shares=action.shares_to_buy)
        db.add(new_portfolio)
        
    db.commit()
    return {"message": "Успешно куплено", "cash_left": team.cash}

@app.get("/api/games/{room_code}/startups", response_model=List[schemas.StartupWithNewsResponse])
def get_startups_with_news(room_code: str, db: Session = Depends(get_db)):
    """Получить список стартапов с их текущими ценами и свежими новостями"""
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")

    # Формируем ответ вручную, чтобы подтянуть последнюю новость
    result = []
    for startup in game.startups:
        # Находим новость, которая только что применилась (последняя использованная)
        latest_news = db.query(models.News).filter(
            models.News.startup_id == startup.id,
            models.News.is_used == True
        ).order_by(models.News.id.desc()).first()

        startup_data = schemas.StartupWithNewsResponse(
            id=startup.id,
            name=startup.name,
            description=startup.description,
            current_price=startup.current_price,
            current_news=schemas.NewsResponse(text=latest_news.text, multiplier=latest_news.multiplier) if latest_news else None
        )
        result.append(startup_data)
        
    return result

@app.get("/api/games/{room_code}/startups", response_model=List[schemas.StartupBasicResponse])
def get_startups(room_code: str, db: Session = Depends(get_db)):
    """Получить список стартапов для инвестирования"""
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")
    return game.startups

@app.post("/api/games/{room_code}/ready")
def team_is_ready(room_code: str, team_id: int, db: Session = Depends(get_db)):
    """Команда нажимает 'Готово' (завершает свой ход)"""
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    team = db.query(models.Team).filter(models.Team.id == team_id, models.Team.game_id == game.id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Команда не найдена")
        
    team.is_ready = True
    db.commit()

    # Проверяем, все ли команды готовы
    all_teams = db.query(models.Team).filter(models.Team.game_id == game.id).all()
    if all(t.is_ready for t in all_teams):
        # Если все готовы — принудительно переключаем фазу
        force_next_phase(game, db)
        
    return {"message": "Вы готовы!"}

@app.get("/api/games/{room_code}/leaderboard", response_model=List[schemas.LeaderboardEntry])
def get_leaderboard(room_code: str, db: Session = Depends(get_db)):
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")

    leaderboard = []
    for team in game.teams:
        portfolio_value = 0
        # Получаем все акции команды
        portfolios = db.query(models.Portfolio).filter(models.Portfolio.team_id == team.id).all()
        for p in portfolios:
            startup = db.query(models.Startup).filter(models.Startup.id == p.startup_id).first()
            if startup:
                portfolio_value += p.shares * startup.current_price
        
        total_wealth = team.cash + portfolio_value
        leaderboard.append(LeaderboardEntry(
            team_id=team.id,
            name=team.name,
            cash=team.cash,
            portfolio_value=portfolio_value,
            total_wealth=total_wealth
        ))
    
    # Сортируем по убыванию капитала
    leaderboard.sort(key=lambda x: x.total_wealth, reverse=True)
    return leaderboard

@app.post("/api/games/{room_code}/import")
def import_game_data(room_code: str, data: schemas.GameImport, db: Session = Depends(get_db)):
    game = db.query(models.Game).filter(models.Game.room_code == room_code).first()
    if not game:
        raise HTTPException(status_code=404, detail="Игра не найдена")

    for s_data in data.startups:
        # Создаем стартап
        new_startup = models.Startup(
            game_id=game.id,
            name=s_data.name,
            description=s_data.description,
            current_price=s_data.base_price
        )
        db.add(new_startup)
        db.flush() # Чтобы получить ID стартапа до коммита
        
        # Создаем новости для этого стартапа
        for n_data in s_data.news:
            new_news = models.News(
                game_id=game.id,
                startup_id=new_startup.id,
                text=n_data.get("text", "Без новостей"),
                multiplier=n_data.get("multiplier", 1.0)
            )
            db.add(new_news)
            
    db.commit()
    return {"message": "Данные успешно загружены!"}
