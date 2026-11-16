import Board from './Board.jsx';
import Landing from './Landing.jsx';
import Player from './Player.jsx';

export default function App() {
  const path = window.location.pathname;
  const board = path.match(/^\/board\/([A-Za-z0-9]+)\/?$/);
  if (board) return <Board code={board[1].toUpperCase()} />;
  const play = path.match(/^\/play\/([A-Za-z0-9]+)\/?$/);
  if (play) return <Player code={play[1].toUpperCase()} />;
  return <Landing />;
}
