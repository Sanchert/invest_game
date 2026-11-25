/** Language detection and dictionary — no React dependency. */

const en = {
  appName: 'Invest Game',
  // landing
  hostTitle: 'Open a board',
  hostText: 'Put this on the projector. Teams join from their phones.',
  turns: 'Number of turns',
  turnLength: 'Length of each turn',
  minutes: 'min',
  seconds: 'sec',
  startupCount: 'Startups in the game',
  createGame: 'Create game',
  joinTitle: 'Join as a team',
  roomCode: 'Room code',
  teamName: 'Team name',
  joinGame: 'Join game',
  turnTooShort: 'A turn must last at least 10 seconds.',
  // lobby
  scanToJoin: 'Scan to join',
  orOpen: 'Or open {address} and enter the code',
  playersJoinAt: 'Players join at',
  copy: 'Copy',
  copied: 'Copied',
  localOnlyHint: 'This address works only on this computer. Start the game with start.py, or open the board at the computer\'s network address.',
  teamsJoined: 'Teams in the lobby',
  noTeamsYet: 'No teams yet. Join from your phone.',
  needTeams: 'Waiting for at least {n} teams.',
  waitingReady: 'The game starts when every team is ready.',
  startingIn: 'Starting in {n}',
  imReady: 'We are ready',
  notReady: 'Not ready yet',
  leaveGame: 'Leave game',
  ready: 'Ready',
  waiting: 'Waiting',
  // turn
  turnOf: 'Turn {n} of {total}',
  introTurn: 'Read about the startups and buy your first shares. News start in turn 2.',
  cash: 'Cash',
  capital: 'Capital',
  shares: 'shares',
  price: 'Price per share',
  priceShort: 'Price',
  closed: 'Closed',
  closedText: 'This startup has finished its story.',
  news: 'News',
  about: 'About the startup',
  worthless: 'Worthless',
  buy: 'Buy',
  sell: 'Sell',
  confirmDone: 'We are done',
  confirmAgain: 'Tap again to confirm. This cannot be undone.',
  waitingOthers: 'Waiting for the other teams',
  teamsDone: '{n} of {total} teams done',
  tips: 'Insider tips',
  tipsHelp: 'Each tip is true and about one startup. You get a random one.',
  buyTip: 'Buy a tip for {cost}',
  noTipsLeft: 'No more tips are available this turn.',
  yourTips: 'Your tips',
  earlierTips: 'Earlier tips',
  timeLeft: 'Time left',
  // results
  resultsTitle: 'Turn {n} results',
  newPrices: 'New prices after the turn',
  finalPrices: 'Final prices',
  ranking: 'Standings',
  yourPlace: 'Your place',
  nextTurnIn: 'Next turn in {n}',
  place: 'Place {n}',
  // final
  gameOver: 'Game over',
  finalStandings: 'Final standings',
  profit: 'Total profit',
  chartTitle: 'Profit by turn',
  turnAxis: 'Turn',
  // errors
  gameNotFound: 'Game not found. Check the room code.',
  connectionLost: 'Connection lost. Retrying…',
  sessionLost: 'This team is no longer in the game.',
  startOver: 'Back to start',
  loading: 'Loading…',
  leaveBoard: 'Leave board',
  leaveBoardConfirm: 'The game keeps running. You can reopen this board with the same room code. Leave the board?',

  // validation
  errRequired: 'Fill this in.',
  errWhole: 'Enter a whole number.',
  errRange: 'From {min} to {max}.',
  errTurnsLibrary: 'The startup library allows at most {n} turns.',
  errStartupsLibrary: 'The library has only {n} startups.',
  errTurnShort: 'A turn must last at least {n} seconds.',
  errTurnLong: 'A turn can last at most 60 minutes.',
  errCode: 'The code has 5 letters or digits (no 0, 1, I, L, O).',
  errName: 'At most {max} characters.',
  errNameTaken: 'This name is already taken in this game.',
  errRoomNotFound: 'No game with this code.',
  errRoomStarted: 'This game has already started.',
  checkingRoom: 'Looking for the game…',
  roomFound: 'Game found.',
  gameLasts: 'The game will last about {n} min.',
  libraryHint: 'Up to {turns} turns and {startups} startups are available.',
  // phone: tabs and results
  tabNews: 'News',
  tabTrade: 'Trading',
  turnGain: 'What the turn brought you',
  turnTotal: 'Total for the turn',
  noShares: 'no shares',
  language: 'Language',
};

const ru = {
  appName: 'Инвест-игра',
  hostTitle: 'Открыть табло',
  hostText: 'Выведите его на проектор. Команды заходят с телефонов.',
  turns: 'Количество ходов',
  turnLength: 'Длительность хода',
  minutes: 'мин',
  seconds: 'сек',
  startupCount: 'Стартапов в игре',
  createGame: 'Создать игру',
  joinTitle: 'Войти командой',
  roomCode: 'Код комнаты',
  teamName: 'Название команды',
  joinGame: 'Войти в игру',
  turnTooShort: 'Ход должен длиться не меньше 10 секунд.',
  scanToJoin: 'Сканируйте, чтобы войти',
  orOpen: 'Или откройте {address} и введите код комнаты',
  playersJoinAt: 'Игроки заходят по адресу',
  copy: 'Копировать',
  copied: 'Скопировано',
  localOnlyHint: 'Этот адрес работает только на этом компьютере. Запустите игру через start.py или откройте табло по сетевому адресу компьютера.',
  teamsJoined: 'Команды в лобби',
  noTeamsYet: 'Пока никого. Заходите с телефона.',
  needTeams: 'Ждём минимум {n} команды.',
  waitingReady: 'Игра начнётся, когда все команды будут готовы.',
  startingIn: 'Старт через {n}',
  imReady: 'Мы готовы',
  notReady: 'Ещё не готовы',
  leaveGame: 'Выйти из игры',
  ready: 'Готова',
  waiting: 'Ждём',
  turnOf: 'Ход {n} из {total}',
  introTurn: 'Изучите стартапы и купите первые акции. Новости появятся со 2-го хода.',
  cash: 'Наличные',
  capital: 'Капитал',
  shares: 'акций',
  price: 'Цена акции',
  priceShort: 'Цена',
  closed: 'Закрыт',
  closedText: 'История этого стартапа закончилась.',
  news: 'Новости',
  about: 'О стартапе',
  worthless: 'Обесценился',
  buy: 'Купить',
  sell: 'Продать',
  confirmDone: 'Мы закончили',
  confirmAgain: 'Нажмите ещё раз для подтверждения. Отменить нельзя.',
  waitingOthers: 'Ждём остальные команды',
  teamsDone: 'Закончили {n} из {total} команд',
  tips: 'Инсайды',
  tipsHelp: 'Каждый инсайд правдив и касается одного стартапа. Вы получаете случайный.',
  buyTip: 'Купить инсайд за {cost}',
  noTipsLeft: 'В этом ходу инсайдов больше нет.',
  yourTips: 'Ваши инсайды',
  earlierTips: 'Прошлые инсайды',
  timeLeft: 'Осталось',
  resultsTitle: 'Итоги хода {n}',
  newPrices: 'Новые цены по итогам хода',
  finalPrices: 'Итоговые цены',
  ranking: 'Рейтинг',
  yourPlace: 'Ваше место',
  nextTurnIn: 'Следующий ход через {n}',
  place: '{n} место',
  gameOver: 'Игра окончена',
  finalStandings: 'Итоговый рейтинг',
  profit: 'Общая прибыль',
  chartTitle: 'Прибыль по ходам',
  turnAxis: 'Ход',
  gameNotFound: 'Игра не найдена. Проверьте код комнаты.',
  connectionLost: 'Связь потеряна. Пробуем снова…',
  sessionLost: 'Этой команды больше нет в игре.',
  startOver: 'В начало',
  loading: 'Загрузка…',
  leaveBoard: 'Выйти с табло',
  leaveBoardConfirm: 'Игра продолжится. Табло можно открыть снова по тому же коду комнаты. Выйти с табло?',

  // validation
  errRequired: 'Заполните поле.',
  errWhole: 'Введите целое число.',
  errRange: 'От {min} до {max}.',
  errTurnsLibrary: 'В библиотеке стартапов не больше {n} ходов.',
  errStartupsLibrary: 'В библиотеке только {n} стартапов.',
  errTurnShort: 'Ход должен длиться не меньше {n} секунд.',
  errTurnLong: 'Ход может длиться не больше 60 минут.',
  errCode: 'Код состоит из 5 букв или цифр (без 0, 1, I, L, O).',
  errName: 'Не больше {max} символов.',
  errNameTaken: 'Такое название уже занято в этой игре.',
  errRoomNotFound: 'Игры с таким кодом нет.',
  errRoomStarted: 'Игра уже началась.',
  checkingRoom: 'Ищем игру…',
  roomFound: 'Игра найдена.',
  gameLasts: 'Игра продлится примерно {n} мин.',
  libraryHint: 'Доступно до {turns} ходов и {startups} стартапов.',
  // phone: tabs and results
  tabNews: 'Новости',
  tabTrade: 'Торговля',
  turnGain: 'Что принёс ход',
  turnTotal: 'Итого за ход',
  noShares: 'нет акций',
  language: 'Язык',
};

const dictionaries = { en, ru };
const LANGUAGES = ['en', 'ru'];

/** Detect the initial language from URL, sessionStorage, or browser locale. */
export function initialLang() {
  try {
    const saved = sessionStorage.getItem('game_lang');
    if (saved && LANGUAGES.includes(saved)) return saved;
  } catch {}
  const requested = new URLSearchParams(window.location.search).get('lang');
  if (requested && LANGUAGES.includes(requested)) return requested;
  const browser = (navigator.language || 'en').slice(0, 2);
  return LANGUAGES.includes(browser) ? browser : 'en';
}

let currentLang = initialLang();

export function setLang(lang) {
  if (dictionaries[lang]) currentLang = lang;
}

export function getLang() {
  return currentLang;
}

export function t(key, vars) {
  const dict = dictionaries[currentLang] || dictionaries.en;
  let text = dict[key] ?? en[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.replaceAll(`{${name}}`, String(value));
    }
  }
  return text;
}
