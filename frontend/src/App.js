import React, { useState } from 'react';

function App() {
  const [query, setQuery] = useState('');
  const [videos, setVideos] = useState([]);
  const [filter, setFilter] = useState('all');

  const search = async () => {
    const params = new URLSearchParams({ q: query, filter });
    const res = await fetch(`http://localhost:5000/api/videos?${params}`);
    const data = await res.json();
    setVideos(data);
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'Arial, sans-serif' }}>
      <h1>YouTube Focus</h1>
      <div>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search videos"
        />
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="all">All</option>
          <option value="short">Short</option>
          <option value="medium">Medium</option>
          <option value="long">Long</option>
        </select>
        <button onClick={search}>Search</button>
      </div>
      <ul>
        {videos.map((v) => (
          <li key={v.id} style={{ marginTop: '1rem' }}>
            <img src={v.thumb} alt="thumbnail" width="120" />
            <div>{v.title}</div>
            <a href={`http://localhost:5000/api/download/${v.id}?fmt=mp4`}>MP4</a>
            {' | '}
            <a href={`http://localhost:5000/api/download/${v.id}?fmt=mp3`}>MP3</a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
