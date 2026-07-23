const STRINGS = {
  en: {
    subtitle: 'composite anomaly index — six independent channels, one reading',
    alertLevel: 'alert level',
    avgZ: 'avg z',
    lastUpdated: 'last updated',
    dataUnavailable: 'data unavailable — check data/dashboard.json',
    unavailable: 'unavailable',
    ch1_title: 'Insider filings',
    ch1_desc: 'Daily count of SEC Form 4 filings — insider transactions reported by public-company officers and directors.',
    ch2_title: 'Search-panic basket',
    ch2_desc: 'Average Google Trends interest across a fixed keyword basket: bunker, gold storage, potassium iodide, evacuation route.',
    ch3_title: 'Market volatility',
    ch3_desc: "CBOE VIX close — the market's own 30-day forward volatility estimate, priced by option traders.",
    ch4_title: 'Airborne command post',
    ch4_desc: 'How many of the 4 E-4B "Nightwatch" aircraft — the Air Force\'s airborne nuclear command posts — are airborne right now, via public ADS-B data.',
    ch5_title: 'Prediction-market odds',
    ch5_desc: 'Highest live probability, across a watchlist of nuclear-war / recession / pandemic / NATO-Russia-war questions on Polymarket — real money betting on the exact things this dashboard tracks.',
    ch6_title: 'Billionaire fleet',
    ch6_desc: 'How many of 11 tracked billionaire/oligarch superyachts are currently clustered in known sanctions-indifferent or "bolt-hole" waters, via public AIS data — aggregate count only, no individual vessel singled out.',
    today: 'today',
    baseline: 'baseline',
    baseline30: '30-day baseline',
    latestClose: 'latest close',
    airborneNow: 'airborne now',
    typical: 'typical',
    currentOdds: 'current odds',
    inHavenNow: 'in safe-haven waters',
    recentReadings: 'Recent readings',
    methodology: "Each channel is scored as a z-score against its own trailing baseline, then averaged. This is a rough composite signal, not a forecast — markets, filings, and search trends all have mundane explanations most of the time. Companion project:",
    methodologyEnd: 'by Kyle McDonald, which tracks private-jet activity the same way.',
    footer: 'data refreshed on a schedule — see /data/dashboard.json',
    timeMinAgo: (n) => `${n}m ago`,
    timeHourAgo: (n) => `${n}h ago`,
    timeDayAgo: (n) => `${n}d ago`,
    sourceQuestionNote: '(source question, shown as reported)',
  },
  ru: {
    subtitle: 'составной индекс аномалий — шесть независимых каналов, одно значение',
    alertLevel: 'уровень тревоги',
    avgZ: 'средний z',
    lastUpdated: 'обновлено',
    dataUnavailable: 'данные недоступны — проверьте data/dashboard.json',
    unavailable: 'недоступно',
    ch1_title: 'Инсайдерские сделки',
    ch1_desc: 'Количество форм SEC Form 4 за день — сделки инсайдеров, о которых обязаны отчитываться руководители публичных компаний.',
    ch2_title: 'Поисковая «паника»',
    ch2_desc: 'Средний интерес Google Trends по набору слов: бункер, хранение золота, йодид калия, маршрут эвакуации.',
    ch3_title: 'Волатильность рынка',
    ch3_desc: 'Индекс VIX (CBOE) — собственная оценка рынком волатильности на 30 дней вперёд, по ценам опционов.',
    ch4_title: 'Воздушный командный пункт',
    ch4_desc: 'Сколько из 4 самолётов E-4B «Nightwatch» — воздушных командных пунктов на случай ядерной войны — сейчас в воздухе, по открытым данным ADS-B.',
    ch5_title: 'Котировки рынков предсказаний',
    ch5_desc: 'Максимальная текущая вероятность по набору вопросов на Polymarket (ядерная война / рецессия в США / пандемия / конфликт НАТО-Россия) — реальные деньги ставят именно на то, что отслеживает этот дашборд.',
    ch6_title: 'Флот миллиардеров',
    ch6_desc: 'Сколько из 11 отслеживаемых суперъяхт миллиардеров и олигархов сейчас находятся в водах, известных как «безопасная гавань» от санкций, по открытым данным AIS — только агрегированное число, без указания конкретных судов.',
    today: 'сегодня',
    baseline: 'обычный уровень',
    baseline30: 'средний за 30 дней',
    latestClose: 'последнее закрытие',
    airborneNow: 'в воздухе сейчас',
    typical: 'обычно',
    currentOdds: 'текущие котировки',
    inHavenNow: 'в «тихой гавани»',
    recentReadings: 'История показаний',
    methodology: 'Каждый канал оценивается как z-score относительно собственной недавней истории, затем усредняется. Это грубый составной сигнал, а не прогноз — у рынков, отчётности и поисковых трендов почти всегда есть банальное объяснение. Проект-компаньон:',
    methodologyEnd: 'от Кайла Макдональда, который так же отслеживает активность частных джетов.',
    footer: 'данные обновляются по расписанию — см. /data/dashboard.json',
    timeMinAgo: (n) => `${n} мин назад`,
    timeHourAgo: (n) => `${n} ч назад`,
    timeDayAgo: (n) => `${n} дн назад`,
    sourceQuestionNote: '(вопрос источника приведён как есть, на английском)',
  },
};

function detectLang() {
  const langs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'en'];
  return langs.some((l) => l.toLowerCase().startsWith('ru')) ? 'ru' : 'en';
}

const LANG = detectLang();
const T = STRINGS[LANG];

function applyStaticTranslations() {
  document.documentElement.lang = LANG;
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.dataset.i18n;
    if (T[key]) el.textContent = T[key];
  });
}

// A few fixed data strings coming from the backend script are still in
// English (e.g. "0-1 (typical)") since they're generated in Python, not
// pulled from this dictionary. Translate the known ones here so the whole
// page reads consistently; anything not in this map (like a live Polymarket
// question, which is arbitrary external text) is left as-is.
const DATA_STRING_TRANSLATIONS = {
  ru: {
    '0-1 (typical)': '0–1 (обычно)',
    'low single digits (typical)': 'низкие однозначные % (обычно)',
  },
};

function translateDataString(value) {
  if (LANG === 'en') return value;
  const map = DATA_STRING_TRANSLATIONS.ru;
  return typeof value === 'string' && map[value] ? map[value] : value;
}


const LEVEL_COLORS = {
  1: 'var(--accent-calm)',
  2: 'var(--accent-mid)',
  3: 'var(--accent-warn)',
  4: 'var(--accent-danger)',
  5: 'var(--accent-danger)',
};

function fmt(n) {
  if (n === null || n === undefined) return '—';
  if (typeof n === 'number') {
    return n.toLocaleString(LANG === 'ru' ? 'ru-RU' : 'en-US', { maximumFractionDigits: 2 });
  }
  return translateDataString(n);
}

function timeAgo(iso) {
  if (!iso) return '—';
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return T.timeMinAgo(mins);
  const hours = Math.round(mins / 60);
  if (hours < 48) return T.timeHourAgo(hours);
  return T.timeDayAgo(Math.round(hours / 24));
}

function setNeedle(level) {
  const angle = (level - 3) * 45; // level 1 -> -90deg, level 5 -> +90deg
  const needle = document.getElementById('needle');
  needle.style.transform = `rotate(${angle}deg)`;
  needle.style.stroke = LEVEL_COLORS[level] || 'var(--text-primary)';
}

function renderChannel(key, data) {
  const el = document.querySelector(`.channel[data-channel="${key}"]`);
  if (!el) return;
  if (!data) {
    el.querySelectorAll('[data-field]').forEach((f) => (f.textContent = T.unavailable));
    return;
  }
  el.querySelectorAll('[data-field]').forEach((f) => {
    const field = f.dataset.field;
    let value = fmt(data[field]);
    if (field === 'matched_question' && value && value !== '—' && LANG === 'ru') {
      value = `«${value}» ${T.sourceQuestionNote}`;
    }
    f.textContent = value;
  });
}

function drawHistory(history) {
  const svg = document.getElementById('history-chart');
  if (!history || history.length < 2) return;
  const w = 600, h = 100, pad = 6;
  const maxLevel = 5, minLevel = 1;
  const step = (w - pad * 2) / (history.length - 1);
  const points = history.map((pt, i) => {
    const x = pad + i * step;
    const y = h - pad - ((pt.level - minLevel) / (maxLevel - minLevel)) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const path = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  path.setAttribute('points', points.join(' '));
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke', 'var(--accent-calm)');
  path.setAttribute('stroke-width', '2');
  svg.appendChild(path);

  const last = history[history.length - 1];
  const lastPoint = points[points.length - 1].split(',');
  const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  dot.setAttribute('cx', lastPoint[0]);
  dot.setAttribute('cy', lastPoint[1]);
  dot.setAttribute('r', '3.5');
  dot.setAttribute('fill', LEVEL_COLORS[last.level] || 'var(--text-primary)');
  svg.appendChild(dot);
}

async function loadDashboard() {
  applyStaticTranslations();
  try {
    const res = await fetch('./data/dashboard.json', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const dash = await res.json();

    document.getElementById('level-value').textContent = dash.level;
    document.getElementById('z-value').textContent = `${T.avgZ} ${fmt(dash.avg_z_score)}`;
    document.getElementById('generated-at').textContent = `${T.lastUpdated} ${timeAgo(dash.generated_at)}`;
    setNeedle(dash.level);

    Object.entries(dash.signals || {}).forEach(([key, data]) => renderChannel(key, data));
    drawHistory(dash.history || []);
  } catch (err) {
    console.error('Failed to load dashboard.json', err);
    document.getElementById('generated-at').textContent = T.dataUnavailable;
  }
}

loadDashboard();
