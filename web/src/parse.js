// Sundial — parser for Slay the Spire 2 .run history files (schema v8–v11).
// Pure functions: usable in the browser and in Node (build step).

const FIGHT_ROOMS = ['monster', 'elite', 'boss'];
const ROOM = { monster: 'H', elite: 'E', boss: 'B', unknown: '?', rest_site: 'R', shop: 'S', treasure: 'T', ancient: 'A' };

function stripPrefix(id) {
  if (!id || typeof id !== 'string') return '';
  const i = id.indexOf('.');
  return i >= 0 ? id.slice(i + 1) : id;
}

const SMALL = new Set(['of', 'the', 'a', 'an', 'and', 'in', 'on', 'to', 'for', 'with']);
function titleCase(raw) {
  return raw.toLowerCase().split('_').filter(Boolean).map((w, i) =>
    (i > 0 && SMALL.has(w)) ? w : w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

// "ENCOUNTER.PHROG_PARASITE_ELITE" -> "Phrog Parasite"; "CARD.STRIKE_IRONCLAD" -> "Strike"
function pretty(id) {
  let s = stripPrefix(id);
  if (!s || s === 'NONE') return '';
  s = s.replace(/_(WEAK|NORMAL|ELITE|BOSS)$/, '');
  s = s.replace(/^(STRIKE|DEFEND)_(IRONCLAD|SILENT|DEFECT|NECROBINDER|REGENT|FOOL|WATCHER)$/, '$1');
  return titleCase(s);
}

function encounterKind(id) {
  const s = stripPrefix(id);
  if (/_BOSS$/.test(s)) return 'boss';
  if (/_ELITE$/.test(s)) return 'elite';
  if (/_(WEAK|NORMAL)$/.test(s)) return 'monster';
  return '';
}

// Event choice keys look like "SUNKEN_STATUE.pages.INITIAL.options.DIVE_INTO_WATER.title"
// or "PHIAL_HOLSTER.title" (relic table). Return the readable last option.
function choiceLabel(c) {
  const key = c && c.title && typeof c.title === 'object' ? c.title.key : '';
  if (!key || typeof key !== 'string') return '';
  const m = key.match(/options\.([A-Z0-9_]+)\.title$/);
  if (m) return titleCase(m[1]);
  return titleCase(key.replace(/\.title$/, '').split('.').pop());      // 'BLITZ.NEOW.title' -> 'Neow'
}

// A Blitz merchant service: 'card_removal', or 'prismatic_card_reward:SILENT' when it names a model.
function service(c) {
  const t = typeof c.type === 'string' ? c.type : '';
  const m = ref(c.model_id);
  return t && m ? `${t}:${m}` : t;
}

// Readers for save-file fields, kept in step with parse.py: a list where an object was expected, an id stored as
// an object or a string, or a null must cost only that entry, never the run (or the whole import).
const list = v => Array.isArray(v) ? v : [];
const objs = v => list(v).filter(x => x && typeof x === 'object' && !Array.isArray(x));
const ref = v => stripPrefix(v && typeof v === 'object' ? v.id : v);
const refs = v => list(v).map(ref).filter(Boolean);
const int = v => { const n = typeof v === 'string' ? Number(v) : v; return typeof n === 'number' && isFinite(n) ? Math.trunc(n) : 0; };
const optInt = v => typeof v === 'number' && isFinite(v) ? Math.trunc(v) : null;
const firstStr = v => typeof v === 'string' ? v : (list(v).find(x => typeof x === 'string') || '');
const str = v => typeof v === 'string' ? v : '';

function cardRef(c) {
  return { id: ref(c), up: int(c.current_upgrade_level), en: ref(c.enchantment) };
}

const MODE_NAME = { standard: 'Standard', daily: 'Daily', blitz: 'Blitz', dread: 'Dread', custom: 'Custom' };

function parseRun(d, meta) {
  meta = meta || {};
  const players = objs(d.players);
  const player = players[0] || {};
  const pid = player.id;
  const acts = list(d.map_point_history);
  const path = [];
  const offers = [];
  let floor = 0, totalDmg = 0, totalTurns = 0, elites = 0;
  const mode = typeof d.game_mode === 'string' && d.game_mode ? d.game_mode.toLowerCase() : 'standard';
  acts.forEach((act, ai) => {
    objs(act).forEach((pt) => {
      floor++;
      const stats = objs(pt.player_stats);
      const ps = stats.find(p => p.player_id === pid) || stats[0] || {};
      const rooms = objs(pt.rooms);
      const room = rooms[0] || {};
      const turns = rooms.reduce((a, r) => a + int(r.turns_taken), 0);
      const t = ROOM[pt.map_point_type] || '?';
      // a fight is a room of a fight type (some encounter ids have no _WEAK/_NORMAL suffix); a ? map point can
      // turn out to be a shop, a treasure or a fight, so the last room's type is kept too
      const fightRooms = rooms.filter(r => FIGHT_ROOMS.includes(r.room_type) && ref(r.model_id));
      const fight = fightRooms[fightRooms.length - 1];
      const lastRoom = rooms.length && typeof rooms[rooms.length - 1].room_type === 'string' ? rooms[rooms.length - 1].room_type : '';
      const ancO = objs(ps.ancient_choice);
      const anc = ancO.find(x => x.was_chosen);
      const gained = refs(ps.cards_gained);
      const cc = objs(ps.card_choices);
      let picked = cc.filter(c => c.was_picked).map(c => ref(c.card)).filter(Boolean);
      const skipped = cc.filter(c => !c.was_picked).map(c => ref(c.card)).filter(Boolean);
      // choose-N screens at events (Room Full of Cheese, Brain Leech, Blitz Neow) list only the cards left behind;
      // the ones taken are in cards_gained
      if ((t === 'A' || t === '?') && lastRoom !== 'shop' && !fight && !anc && skipped.length && !picked.length) picked = gained.filter(x => !skipped.includes(x));
      // a Blitz merchant's card choices come from a service you bought: rewards, not shop stock
      const mer = t === 'S' && (mode === 'blitz' || Array.isArray(ps.blitz_merchant_choices));
      const stock = (t === 'S' || lastRoom === 'shop') && !mer;
      // a choice given by an Ancient's relic (Hefty Tablet and the like) marks no pick: not a skip either
      const unmarked = (t === 'A' || t === '?') && !picked.length && gained.some(x => !picked.includes(x));
      const sv = objs(ps.blitz_merchant_choices);
      if (cc.length && !stock && !unmarked) { const o = cc.map(c => ref(c.card)).filter(Boolean); offers.push({ f: floor, a: ai + 1, o: o.concat(picked.filter(x => !o.includes(x))), p: picked }); }
      const models = rooms.map(r => ref(r.model_id)).filter(Boolean);
      if (t === 'E') elites++;
      totalDmg += int(ps.damage_taken);
      totalTurns += turns;
      path.push({
        f: floor, a: ai + 1, t,
        rt: str(room.room_type), room: lastRoom,
        m: models,
        enc: fight ? ref(fight.model_id) : '', ek: fight ? fight.room_type : '',
        hp: optInt(ps.current_hp), mhp: optInt(ps.max_hp), g: optInt(ps.current_gold),
        dmg: int(ps.damage_taken), heal: int(ps.hp_healed), tn: turns,
        gg: int(ps.gold_gained), gs: int(ps.gold_spent),
        cp: picked, cs: skipped, mer,
        svp: sv.filter(c => c.was_picked).map(service).filter(Boolean),
        svs: sv.filter(c => !c.was_picked).map(service).filter(Boolean),
        rp: objs(ps.relic_choices).filter(r => r.was_picked).map(r => ref(r.choice)).filter(Boolean),
        br: refs(ps.bought_relics),
        pp: objs(ps.potion_choices).filter(r => r.was_picked).map(r => ref(r.choice)).filter(Boolean),
        pu: refs(ps.potion_used),
        rest: firstStr(ps.rest_site_choices),
        up: refs(ps.upgraded_cards),
        rm: refs(ps.cards_removed),
        tr: objs(ps.cards_transformed).map(c => [ref(c.original_card), ref(c.final_card)]),
        ev: objs(ps.event_choices).map(choiceLabel).filter(Boolean),
        anc: anc ? str(anc.TextKey) : '',
        ancO: ancO.map(x => str(x.TextKey)).filter(Boolean),
      });
    });
  });

  const killedEnc = typeof d.killed_by_encounter === 'string' && d.killed_by_encounter !== 'NONE.NONE' ? d.killed_by_encounter : '';
  const killedEv = typeof d.killed_by_event === 'string' && d.killed_by_event !== 'NONE.NONE' ? d.killed_by_event : '';
  const outcome = d.win ? 'win' : (d.was_abandoned ? 'abandoned' : 'death');
  const last = path[path.length - 1] || {};
  const ancients = path.filter(p => p.t === 'A').map(p => ({ a: p.a, who: p.m[0] || '', pick: p.anc, opts: p.ancO }));
  const start = int(d.start_time);

  return {
    key: `${d.seed || ''}-${start}`,
    profile: meta.profile || '',
    file: meta.file || '',
    char: ref(player.character),
    players: players.length,
    asc: int(d.ascension),
    mode,
    custom: d.is_custom_game === true,
    build: str(d.build_id),
    schema: int(d.schema_version),
    seed: str(d.seed),
    start,
    time: int(d.run_time),
    acts: refs(d.acts),
    outcome,
    floors: floor,
    actReached: acts.filter(a => objs(a).length).length,
    killer: killedEnc ? stripPrefix(killedEnc) : (killedEv ? stripPrefix(killedEv) : ''),
    killerKind: killedEnc ? (encounterKind(killedEnc) || 'monster') : (killedEv ? 'event' : ''),
    deathAct: outcome === 'death' ? last.a : null,
    deathType: outcome === 'death' ? last.t : null,
    hpEnd: last.hp ?? null, mhpEnd: last.mhp ?? null,
    dmg: totalDmg, turns: totalTurns, elites,
    deck: objs(player.deck).filter(c => ref(c)).map(cardRef),
    relics: objs(player.relics).filter(r => ref(r)).map(r => ({ id: ref(r), f: int(r.floor_added_to_deck) })),
    potions: refs(player.potions),
    badges: refs(player.badges),
    ancients,
    offers,
    path,
  };
}

function looksLikeRun(d) {
  return d && typeof d === 'object' && Array.isArray(d.map_point_history) && Array.isArray(d.players) && 'start_time' in d;
}

const STS2 = { parseRun, looksLikeRun, pretty, stripPrefix, titleCase, encounterKind, ROOM, MODE_NAME };
if (typeof module !== 'undefined') module.exports = STS2;
if (typeof window !== 'undefined') window.STS2 = STS2;
