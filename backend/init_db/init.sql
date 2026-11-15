-- Таблица игры
CREATE TABLE IF NOT EXISTS games (
    id SERIAL PRIMARY KEY,
    room_code VARCHAR(6) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'LOBBY',
    current_round INT DEFAULT 0,
    total_rounds INT DEFAULT 5,
    round_duration_mins INT DEFAULT 10,
    starting_capital INT DEFAULT 600,
    state_end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Таблица команд (игроков)
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    game_id INT REFERENCES games(id),
    name VARCHAR(50) NOT NULL,
    cash INT NOT NULL,
    is_ready BOOLEAN DEFAULT FALSE,
    session_token VARCHAR(100)
);

-- Таблица стартапов
CREATE TABLE IF NOT EXISTS startups (
    id SERIAL PRIMARY KEY,
    game_id INT REFERENCES games(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    current_price INT DEFAULT 10
);

-- Портфели (сколько акций у кого)
CREATE TABLE IF NOT EXISTS portfolios (
    team_id INT REFERENCES teams(id),
    startup_id INT REFERENCES startups(id),
    shares INT DEFAULT 0,
    PRIMARY KEY (team_id, startup_id)
);

-- Пул новостей (генерируется админом)
CREATE TABLE IF NOT EXISTS news_pool (
    id SERIAL PRIMARY KEY,
    game_id INT REFERENCES games(id),
    startup_id INT REFERENCES startups(id),
    text TEXT NOT NULL,
    multiplier DECIMAL(3,2) NOT NULL,
    is_used BOOLEAN DEFAULT FALSE
);

-- Пул инсайдов (генерируется админом)
CREATE TABLE IF NOT EXISTS insider_pool (
    id SERIAL PRIMARY KEY,
    game_id INT REFERENCES games(id),
    startup_id INT REFERENCES startups(id),
    text TEXT NOT NULL
);

-- История купленных инсайдов
CREATE TABLE IF NOT EXISTS team_insiders (
    team_id INT REFERENCES teams(id),
    insider_id INT REFERENCES insider_pool(id),
    PRIMARY KEY (team_id, insider_id)
);