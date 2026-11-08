// Sundial — parser for Slay the Spire 2 .run history files (schema v9/v10).
// Pure functions: usable in the browser and in Node (build step).

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
  s = s.replace(/^(STRIKE|DEFEND)_(IRONCLAD|SILENT|DEFECT|NECROBINDER|REGENT|WATCHER)$/, '$1');
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
  const key = c && c.title && c.title.key;
  if (!key) return '';
  const m = key.match(/options\.([A-Z0-9_]+)\.title$/);
  if (m) return titleCase(m[1]);
  return titleCase(key.replace(/\.title$/, ''));
}

function cardRef(c) {
  if (!c) return null;
  return { id: stripPrefix(c.id), up: c.current_upgrade_level || 0, en: c.enchantment ? stripPrefix(c.enchantment.id) : '' };
}

function parseRun(d, meta) {
  meta = meta || {};
  const player = (d.players && d.players[0]) || {};
  const pid = player.id;
  const acts = d.map_point_history || [];
  const path = [];
  const offers = [];
  let floor = 0, totalDmg = 0, totalTurns = 0, elites = 0;
  acts.forEach((act, ai) => {
    (act || []).forEach((pt) => {
      floor++;
      const ps = (pt.player_stats || []).find(p => p.player_id === pid) || (pt.player_stats || [])[0] || {};
      const room = (pt.rooms || [])[0] || {};
      const turns = (pt.rooms || []).reduce((a, r) => a + (r.turns_taken || 0), 0);
      const cc = ps.card_choices || [];
      const picked = cc.filter(c => c.was_picked).map(c => stripPrefix(c.card.id));
      const skipped = cc.filter(c => !c.was_picked).map(c => stripPrefix(c.card.id));
      if (cc.length && pt.map_point_type !== 'shop') offers.push({ f: floor, a: ai + 1, o: cc.map(c => stripPrefix(c.card.id)), p: picked });
      const anc = (ps.ancient_choice || []).find(x => x.was_chosen);
      const models = (pt.rooms || []).map(r => r.model_id).filter(Boolean);
      const t = ROOM[pt.map_point_type] || '?';
      if (t === 'E') elites++;
      totalDmg += ps.damage_taken || 0;
      totalTurns += turns;
      path.push({
        f: floor, a: ai + 1, t,
        rt: room.room_type || '',
        m: models.map(stripPrefix),
        hp: ps.current_hp ?? null, mhp: ps.max_hp ?? null, g: ps.current_gold ?? null,
        dmg: ps.damage_taken || 0, heal: ps.hp_healed || 0, tn: turns,
        gg: ps.gold_gained || 0, gs: ps.gold_spent || 0,
        cp: picked, cs: skipped,
        rp: (ps.relic_choices || []).filter(r => r.was_picked).map(r => stripPrefix(r.choice)),
        br: (ps.bought_relics || []).map(stripPrefix),
        pp: (ps.potion_choices || []).filter(r => r.was_picked).map(r => stripPrefix(r.choice)),
        pu: (ps.potion_used || []).map(stripPrefix),
        rest: (ps.rest_site_choices || [])[0] || '',
        up: (ps.upgraded_cards || []).map(stripPrefix),
        rm: (ps.cards_removed || []).map(c => stripPrefix(c.id)),
        tr: (ps.cards_transformed || []).map(c => [stripPrefix(c.original_card.id), stripPrefix(c.final_card.id)]),
        ev: (ps.event_choices || []).map(choiceLabel).filter(Boolean),
        anc: anc ? anc.TextKey : '',
        ancO: (ps.ancient_choice || []).map(x => x.TextKey),
      });
    });
  });

  const killedEnc = d.killed_by_encounter && d.killed_by_encounter !== 'NONE.NONE' ? d.killed_by_encounter : '';
  const killedEv = d.killed_by_event && d.killed_by_event !== 'NONE.NONE' ? d.killed_by_event : '';
  const outcome = d.win ? 'win' : (d.was_abandoned ? 'abandoned' : 'death');
  const last = path[path.length - 1] || {};
  const ancients = path.filter(p => p.t === 'A').map(p => ({ a: p.a, who: p.m[0] || '', pick: p.anc, opts: p.ancO }));

  return {
    key: `${d.seed || ''}-${d.start_time || 0}`,
    profile: meta.profile || '',
    file: meta.file || '',
    char: stripPrefix(player.character || ''),
    players: (d.players || []).length,
    asc: d.ascension ?? 0,
    mode: d.game_mode || 'standard',
    build: d.build_id || '',
    schema: d.schema_version || 0,
    seed: d.seed || '',
    start: d.start_time || 0,
    time: d.run_time || 0,
    acts: (d.acts || []).map(stripPrefix),
    outcome,
    floors: floor,
    actReached: acts.filter(a => a && a.length).length,
    killer: killedEnc ? stripPrefix(killedEnc) : (killedEv ? stripPrefix(killedEv) : ''),
    killerKind: killedEnc ? (encounterKind(killedEnc) || 'monster') : (killedEv ? 'event' : ''),
    deathAct: outcome === 'death' ? last.a : null,
    deathType: outcome === 'death' ? last.t : null,
    hpEnd: last.hp ?? null, mhpEnd: last.mhp ?? null,
    dmg: totalDmg, turns: totalTurns, elites,
    deck: (player.deck || []).map(cardRef),
    relics: (player.relics || []).map(r => ({ id: stripPrefix(r.id), f: r.floor_added_to_deck || 0 })),
    potions: (player.potions || []).map(p => stripPrefix(p.id)),
    badges: (player.badges || []).map(b => stripPrefix(b.id)),
    ancients,
    offers,
    path,
  };
}

function looksLikeRun(d) {
  return d && typeof d === 'object' && Array.isArray(d.map_point_history) && Array.isArray(d.players) && 'start_time' in d;
}

const STS2 = { parseRun, looksLikeRun, pretty, stripPrefix, titleCase, encounterKind, ROOM };
if (typeof module !== 'undefined') module.exports = STS2;
if (typeof window !== 'undefined') window.STS2 = STS2;
