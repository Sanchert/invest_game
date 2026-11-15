import { useState, useEffect } from 'react';
import './App.css';

const API_URL = '/api';

function App() {
  const [startups, setStartups] = useState([]);
  const [investments, setInvestments] = useState({}); // { startup_id: количество }
  const [myCash, setMyCash] = useState(0); // Локальный кэш для отображения

  const [view, setView] = useState('home'); // 'home', 'host', 'player'
  const [gameCode, setGameCode] = useState('');
  const [gameStatus, setGameStatus] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  
  const [createForm, setCreateForm] = useState({ total_rounds: 5, round_duration_seconds: 600, starting_capital: 600 });
  const [joinForm, setJoinForm] = useState({ name: '', room_code: '' });
  const [myTeamId, setMyTeamId] = useState(null);
  
  const [importText, setImportText] = useState('');

  // Пример JSON для кнопки "Вставить пример"
  const sampleData = JSON.stringify({
    startups: [
      {
        name: "ИИ-Пекарня",
        description: "Роботы пекут хлеб круглосуточно",
        base_price: 10,
        news: [
          { text: "Робот сломался, выпечка встала", multiplier: 0.5 },
          { text: "Заключен контракт с сетью супермаркетов", multiplier: 2.0 }
        ]
      },
      {
        name: "Доставка на дронах",
        description: "Быстрая доставка еды по воздуху",
        base_price: 15,
        news: [
          { text: "Запрет на полеты в центре города", multiplier: 0.2 },
          { text: "Инвестиции от крупного фонда", multiplier: 3.0 }
        ]
      }
    ]
  }, null, 2);

  const handleImport = async () => {
    try {
      const parsedData = JSON.parse(importText);
      const res = await fetch(`${API_URL}/games/${gameCode}/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsedData)
      });
      if (res.ok) {
        alert("Контент успешно загружен в игру!");
        setImportText('');
      } else {
        const err = await res.json();
        alert(`Ошибка импорта: ${err.detail}`);
      }
    } catch (e) {
      alert("Ошибка парсинга JSON. Проверьте, что вы вставили корректный текст.");
    }
  };
  // --- API ФУНКЦИИ ---
  const handleCreateGame = async (e) => {
    e.preventDefault();
    const res = await fetch(`${API_URL}/games`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(createForm)
    });
    const data = await res.json();
    setGameCode(data.room_code);
    setView('host');
  };

  const handleJoinGame = async (e) => {
    e.preventDefault();
    try {
      console.log("Попытка подключения к:", `${API_URL}/games/${joinForm.room_code}/join`);
      
      const res = await fetch(`${API_URL}/games/${joinForm.room_code}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: joinForm.name })
      });
      
      const data = await res.json();

      if (!res.ok) {
        alert(`Ошибка: ${data.detail || JSON.stringify(data)}`);
        return;
      }
      
      setMyTeamId(data.id);
      setGameCode(joinForm.room_code);
      setView('player');
    } catch (err) {
      console.error("Детали ошибки:", err);
      alert(`Сетевая ошибка: ${err.message}`);
    }
  };

  const handleStartGame = async () => {
    await fetch(`${API_URL}/games/${gameCode}/start`, { method: 'POST' });
  };

  const handleBuy = async (startupId) => {
    const amount = parseInt(investments[startupId] || 0);
    if (amount <= 0) return;

    try {
      const res = await fetch(`${API_URL}/games/${gameCode}/invest?team_id=${myTeamId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ startup_id: startupId, shares_to_buy: amount })
      });
      if (res.ok) {
        // Сбрасываем поле ввода для этого стартапа
        setInvestments({ ...investments, [startupId]: 0 }); 
      } else {
        const err = await res.json();
        alert(err.detail || "Ошибка покупки");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // --- ОПРОС СТАТУСА ---
  // 1. Опрос статуса игры и лидерборда (каждые 2 сек)
  useEffect(() => {
    let interval;
    if (view === 'host' || view === 'player') {
      interval = setInterval(async () => {
        const res = await fetch(`${API_URL}/games/${gameCode}/status`);
        if (res.ok) {
          const data = await res.json();
          setGameStatus(data);
          
          if (data.status !== 'LOBBY' && data.status !== 'FINISHED') {
            const lbRes = await fetch(`${API_URL}/games/${gameCode}/leaderboard`);
            if (lbRes.ok) setLeaderboard(await lbRes.json());
          }

          // Обновляем кэш игрока
          if (data.teams && myTeamId) {
            const me = data.teams.find(t => t.id === myTeamId);
            if (me) setMyCash(me.cash);
          }
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [view, gameCode, myTeamId]); // Добавили myTeamId

  // 2. Загрузка стартапов (срабатывает только когда началось инвестирование)
  useEffect(() => {
    if (gameStatus?.status === 'INVESTING' && startups.length === 0) {
      fetch(`${API_URL}/games/${gameCode}/startups`)
        .then(res => res.json())
        .then(data => setStartups(data))
        .catch(err => console.error("Ошибка загрузки стартапов:", err));
    }
  }, [gameStatus?.status, gameCode, startups.length]);

  // --- ЭКРАНЫ ---

  // 1. ГЛАВНЫЙ ЭКРАН
  if (view === 'home') {
    return (
      <div className="container" style={{ marginTop: '10vh' }}>
        <h1 style={{ fontSize: '3rem' }}>Инвестиционная игра</h1>
        <div style={{ display: 'flex', gap: '20px', marginTop: '30px' }}>
          <div style={{ flex: 1, borderRight: '1px solid #ccc', paddingRight: '20px' }}>
            <h2>Я Ведущий (ПК)</h2>
            <form onSubmit={handleCreateGame}>
              <button type="submit" style={{ backgroundColor: '#6f42c1', padding: '20px', fontSize: '1.2rem' }}>
                Создать новую игру
              </button>
            </form>
          </div>
          <div style={{ flex: 1 }}>
            <h2>Я Игрок (Смартфон)</h2>
            <form onSubmit={handleJoinGame}>
              <div className="form-group">
                <input type="text" placeholder="КОД" required value={joinForm.room_code} onChange={e => setJoinForm({...joinForm, room_code: e.target.value.toUpperCase()})} style={{ fontSize: '1.5rem', textAlign: 'center' }} />
              </div>
              <div className="form-group">
                <input type="text" placeholder="Название команды" required value={joinForm.name} onChange={e => setJoinForm({...joinForm, name: e.target.value})} />
              </div>
              <button type="submit">Войти в игру</button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // 2. ЭКРАН ВЕДУЩЕГО (БОЛЬШОЙ ЭКРАН)
  if (view === 'host') {
    return (
      <div className="container host-screen" style={{ maxWidth: '1200px', minHeight: '80vh', backgroundColor: '#222', color: 'white' }}>
        <h1 style={{ fontSize: '3rem' }}>Экран ведущего</h1>
        
        {gameStatus?.status === 'LOBBY' ? (
          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <h2 style={{ fontSize: '2rem' }}>Подключитесь к игре</h2>
            <div className="room-code" style={{ fontSize: '6rem', backgroundColor: '#444', color: '#00ff00', padding: '20px', borderRadius: '20px', margin: '20px auto', width: 'fit-content' }}>
              {gameCode}
            </div>
            
            {/* Блок Импорта Данных */}
            <div style={{ textAlign: 'left', backgroundColor: '#333', padding: '20px', borderRadius: '10px', marginBottom: '20px' }}>
              <h3 style={{ marginTop: 0 }}>Загрузка контента (Стартапы и Новости)</h3>
              <textarea 
                placeholder="Вставьте сюда JSON с данными..."
                style={{ width: '100%', height: '150px', fontFamily: 'monospace', padding: '10px', marginBottom: '10px' }}
                value={importText}
                onChange={(e) => setImportText(e.target.value)}
              />
              <button 
                onClick={handleImport}
                style={{ width: '200px', backgroundColor: '#17a2b8', marginTop: 0 }}
              >
                Импортировать JSON
              </button>
              <button 
                onClick={() => setImportText(sampleData)}
                style={{ width: '200px', backgroundColor: '#6c757d', marginLeft: '10px', marginTop: 0 }}
              >
                Вставить пример
              </button>
            </div>

            <p style={{ fontSize: '1.5rem' }}>Подключено команд: {gameStatus.teams.length}</p>
            <button onClick={handleStartGame} disabled={gameStatus.teams.length === 0} style={{ width: '300px', padding: '20px', fontSize: '1.5rem', backgroundColor: '#28a745' }}>
              Начать игру
            </button>
          </div>
        ) : (
          <div>
            <h2 style={{ color: '#ffc107', textAlign: 'center', fontSize: '2rem' }}>Раунд {gameStatus?.current_round} из {createForm.total_rounds}</h2>
            <div style={{ display: 'flex', gap: '20px', marginTop: '30px' }}>
              {/* Лидерборд */}
              <div style={{ flex: 1, backgroundColor: '#333', padding: '20px', borderRadius: '10px' }}>
                <h3>Таблица лидеров</h3>
                <ul className="team-list">
                  {leaderboard.map((team, index) => (
                    <li key={team.team_id} style={{ fontSize: '1.2rem', padding: '15px', backgroundColor: index === 0 ? '#ffd700' : '#444', color: index === 0 ? 'black' : 'white' }}>
                      <span><strong>{index + 1}.</strong> {team.name}</span>
                      <span>{team.total_wealth} у.е.</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              {/* Статус игры */}
              <div style={{ flex: 1, backgroundColor: '#333', padding: '20px', borderRadius: '10px', textAlign: 'center' }}>
                <h3>Текущая фаза</h3>
                <h1 style={{ color: '#17a2b8', fontSize: '3rem' }}>{gameStatus?.status}</h1>
                <p>Ждем действий команд...</p>
                {/* Можно добавить вывод новостей для всех */}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 3. ЭКРАН ИГРОКА (СМАРТФОН)
  if (view === 'player') {
    return (
      <div className="container player-screen" style={{ maxWidth: '500px' }}>
        <h1 style={{ fontSize: '1.5rem', textAlign: 'center' }}>Комната: {gameCode}</h1>
        <p style={{ textAlign: 'center', color: '#666' }}>Статус: <strong>{gameStatus?.status}</strong></p>
        
        {/* 1. ЛОББИ */}
        {gameStatus?.status === 'LOBBY' && (
          <div style={{ textAlign: 'center', marginTop: '50px' }}>
            <h2>Ожидание ведущего...</h2>
            <p>Приготовьтесь инвестировать!</p>
          </div>
        )}

        {/* 2. ИНВЕСТИРОВАНИЕ */}
        {gameStatus?.status === 'INVESTING' && (
          <div style={{ marginTop: '20px' }}>
            <div style={{ textAlign: 'center', marginBottom: '20px', padding: '10px', backgroundColor: '#e9ecef', borderRadius: '8px' }}>
              <h3>Ваш кэш: <span style={{ color: '#28a745' }}>{myCash} у.е.</span></h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              {startups.map(startup => (
                <div key={startup.id} style={{ border: '1px solid #ccc', padding: '15px', borderRadius: '8px' }}>
                  <h3 style={{ margin: '0 0 10px 0' }}>{startup.name} <span style={{ color: '#007bff' }}>({startup.current_price} у.е.)</span></h3>
                  <p style={{ fontSize: '14px', color: '#666', margin: '0 0 15px 0' }}>{startup.description}</p>
                  
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <input 
                      type="number" 
                      min="0"
                      placeholder="Кол-во"
                      value={investments[startup.id] || ''}
                      onChange={(e) => setInvestments({...investments, [startup.id]: e.target.value})}
                      style={{ width: '100px', margin: 0 }}
                    />
                    <button 
                      onClick={() => handleBuy(startup.id)}
                      style={{ flex: 1, margin: 0, padding: '10px' }}
                    >
                      Купить за {(investments[startup.id] || 0) * startup.current_price} у.е.
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <button 
              onClick={async () => {
                await fetch(`${API_URL}/games/${gameCode}/ready?team_id=${myTeamId}`, { method: 'POST' });
                alert("Вы завершили инвестирование! Ждем остальных.");
              }}
              style={{ marginTop: '30px', backgroundColor: '#28a745', padding: '15px', fontSize: '1.1rem' }}
            >
              Я всё купил (Готов)
            </button>
          </div>
        )}
      </div>
    );
  }
}

export default App;