"""seed_community.py — bulk-generate a diverse pool of personas to populate
the community wall.

Usage (run on Railway shell against the mind-api service so it picks up
DATABASE_URL, ANTHROPIC_API_KEY, FAL_KEY, MIND_DATA_DIR):

    railway run --service the-mind-api \
        python pilots/the-mind/api/seed_community.py \
        --admin-email iqbal@simulatte.io

The script is idempotent — re-running it skips briefs whose persona
slug already exists in _GENERATED.

What it does for each brief:
  1. Calls the internal _generate_persona_direct() to produce the
     persona JSON.
  2. Persists the JSON to disk (volume) via _persist_generated_dict.
  3. Adds a persona_generated Event row attributed to the admin user
     so /me/personas surfaces them on that user's dashboard too.
  4. Kicks off a fal.ai portrait generation in the same pass so the
     wall has portraits to drift.

Total ~20 generations × ~30s each = ~10 min. Anthropic + fal.ai cost
roughly USD 25-40 for the full run.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("seed")


# ── 20 briefs: 10 US + 10 Europe, diverse on age / occupation / class ────

BRIEFS: list[tuple[str, str]] = [
    # ── US ──
    ("Marcus Reyes, 32, Brooklyn",
     "Marcus Reyes, 32, lives in Crown Heights Brooklyn. Senior backend engineer "
     "at a Series-B fintech in the Flatiron, $185K base + RSUs. Dating someone "
     "from Bumble for 8 months. Spends $200/mo on a Peloton he uses twice a "
     "week. Reads The Verge daily, suspicious of crypto since FTX. Will spend "
     "$90 on a steak but won't pay $5 to skip the bagel line. Decides slowly on "
     "tools after reading HN comments; impulsive on food and clothes."),

    ("Sarah Chen, 28, San Francisco",
     "Sarah Chen, 28, lives in the Mission with two roommates. Product manager "
     "at an AI infra startup (Series A, ~$140K). Runs the SF marathon, training "
     "5 days a week. Vegetarian since college. Trusts Wirecutter more than "
     "influencers. Cancelled HelloFresh after 3 weeks because of packaging "
     "guilt. Buys things her marathon-runner friends recommend; ignores Instagram "
     "ads. Will pay 3x for organic; price-sensitive on electronics."),

    ("Diego Martinez, 41, Austin",
     "Diego Martinez, 41, owns a small farm-to-table restaurant in East Austin. "
     "Married to a high-school teacher, two kids (8 and 11). $95K personal "
     "draw. Drives a 2017 Tacoma. Listens to NPR on the commute. Hates "
     "subscription fatigue, reluctant to add another monthly bill. Trusts other "
     "restaurant owners' word-of-mouth above all else. Buys equipment based on "
     "review depth, not brand. Slow decider on big purchases; quick on family "
     "dinners-out."),

    ("Jasmine Williams, 24, Atlanta",
     "Jasmine Williams, 24, dance educator and TikTok creator (220K followers). "
     "Lives with her mom in East Point Atlanta to save on rent. Earns $3-6K/mo "
     "from brand deals (Gymshark, Fashion Nova) plus part-time at a dance "
     "studio. Black, churchgoing, eldest daughter energy. Trusts her three best "
     "friends' group chat over any creator she follows. Will pay full price for "
     "a hair appointment; thrifts everything else."),

    ("Robert Kowalski, 58, Chicago",
     "Robert Kowalski, 58, retired union electrician (IBEW Local 134). Pension "
     "+ social security ~$72K/yr. Lives in Norwood Park with his wife. Two grown "
     "kids out of state. Drives a 2014 F-150. Watches the Bears, fishes Lake "
     "Michigan on weekends. Distrusts most marketing — relies on Costco, Sam's "
     "Club, his union network. Won't touch anything subscription-based. Buys "
     "American-made when he can; will pay a premium for it."),

    ("Emily Nakamura, 36, Seattle",
     "Emily Nakamura, 36, UX researcher at Microsoft (Bellevue), $165K + bonus. "
     "Vegan for 7 years. Recovering from hoarding tendencies — got into "
     "minimalism via Marie Kondo, now sceptical of new purchases. Reads Dense "
     "Discovery and Cup of Jo. Married to a software engineer at a games "
     "studio. Trusts long-form reviews and academic papers. Will pay 4x for "
     "ethical sourcing; tracks every purchase in a spreadsheet."),

    ("Tyler Brooks, 22, Nashville",
     "Tyler Brooks, 22, sophomore at Belmont University studying songwriting. "
     "Works 30 hrs/wk at a Music Row coffee shop. From small-town Tennessee, "
     "first-gen college. $14K/yr after expenses. Writes country-rock songs, "
     "plays open mics weekly. Cash-poor, time-rich. Trusts his guitar teacher "
     "and his older sister. Will spend $400 on a pedal but eats ramen 5 nights "
     "a week. Decides on gear after watching 10 YouTube reviews."),

    ("Maria Castillo, 45, Phoenix",
     "Maria Castillo, 45, ICU nurse at Banner Health, single mom of two "
     "teenagers. $98K/yr but $1,400/mo on her ex-husband's defaulted credit "
     "cards she co-signed. Evangelical Christian, attends her church's "
     "Wednesday women's group. Drives a 2019 Honda CR-V. Trusts her sister and "
     "her pastor. Buys generic where possible, splurges on shoes for her "
     "12-hour shifts. Sceptical of any product that promises 'wellness' — wants "
     "evidence-based."),

    ("Aiden O'Brien, 29, Boston",
     "Aiden O'Brien, 29, biotech research associate at a Cambridge startup "
     "doing CAR-T therapies. MIT bioengineering BS, currently 1 yr into a "
     "part-time MBA at Sloan. $115K base. Lives alone in Somerville. Anxious "
     "dater, on Hinge. Reads STAT News and Lex Fridman. Trusts peer-reviewed "
     "studies and his lab director. Will pay full price for replicable "
     "products; agonises 3 weeks before any non-essential purchase over $200."),

    ("Chloe Anderson, 38, Denver",
     "Chloe Anderson, 38, marketing director at an outdoor-gear DTC brand "
     "(jackets, packs). Divorced 2 years ago, no kids. Owns a rescue lab named "
     "Birch. Skis 30+ days a year, Ironman in Boulder once. $185K + equity. "
     "Lives in Wash Park. Trusts athletes and gear-testers (NotJustBikes, "
     "Outside Online). Cancels gym memberships within a month. Will spend $800 "
     "on bibs but argues over a $4 latte."),

    # ── Europe ──
    ("Sophie Dubois, 27, Paris",
     "Sophie Dubois, 27, buyer for a Parisian luxury department store (Le Bon "
     "Marché level). Sciences Po grad. Lives in the 11th arrondissement, €1,800 "
     "rent. €52K + bonus. French-Algerian, fluent in 4 languages. Engaged to a "
     "lawyer. Sceptical of crypto, NFTs, web3. Reads Vogue Business, Les Echos. "
     "Trusts her grandmother's taste and one specific Instagram critic. Will "
     "pay €4K for a Loro Piana; haggles at Sunday markets."),

    ("Liam Sorensen, 34, Copenhagen",
     "Liam Sorensen, 34, architect at a small firm specialising in sustainable "
     "housing. DKK 480K/yr (~€64K). Lives in Vesterbro with his partner and "
     "their toddler. Cycles everywhere, owns no car. Reads Dezeen and Monocle. "
     "Trusts the Danish design canon — anything pre-1980s Scandinavian. Will "
     "pay 5x for solid wood over MDF. Long deliberation on furniture; impulsive "
     "on books and bread."),

    ("Anna Kowalska, 31, Warsaw",
     "Anna Kowalska, 31, senior software developer at a Polish neobank. PLN "
     "26K/mo (~€6K) gross. Moved from a smaller city to Warsaw at 24. Lives "
     "alone in Praga district, gym 5x/wk including powerlifting. Single, "
     "casually dating. Trusts Reddit (r/poland, r/learnprogramming), her "
     "lifting coach. Saves aggressively for an apartment down-payment. Will "
     "spend zł400 on protein but cooks every meal."),

    ("Hannah Schmidt, 26, Berlin",
     "Hannah Schmidt, 26, freelance illustrator and visual artist. Iranian-"
     "German parents emigrated in the 90s. Lives in Neukölln, €620 rent for a "
     "shared studio. €28-40K/yr depending on commissions. Rolls cigarettes, "
     "doesn't drink, smokes weed. Trusts her artist collective and one "
     "specific gallerist. Buys cheap at flea markets but splurges on "
     "high-end art supplies. Hates corporate aesthetics."),

    ("Oliver Whitfield, 52, London",
     "Oliver Whitfield, 52, ex-investment banker (Goldman, 18 yrs) now "
     "independent ESG consultant. £280K/yr. Divorced, two adult children at "
     "Cambridge. Lives in Chelsea. Drives a Range Rover. Reads the FT and The "
     "Spectator. Trusts the people he came up with at LSE. Won't touch "
     "anything that smells of greenwashing — vetted his own consultancy "
     "obsessively. Will pay any price for credibility; cheap on tech."),

    ("Isabella Romano, 23, Milan",
     "Isabella Romano, 23, second-year design student at Politecnico Milano. "
     "Lives at home with parents in the suburbs to save money. €600/mo from "
     "Instagram fashion micro-influencing (32K followers, mostly Italian "
     "vintage). Studies industrial design, hates fast fashion. Catholic but "
     "private about it. Trusts her best friend and her aunt who works at "
     "Marni. Buys 90% second-hand. Will pay €300 for a vintage Prada bag from "
     "the 90s; nothing for new mall fashion."),

    ("Lukas Becker, 39, Munich",
     "Lukas Becker, 39, automotive engineer at BMW (powertrain, EV transition "
     "team). €92K/yr + 13th month. Married to a paediatrician, two kids "
     "(4 and 7). Lives in a Reihenhaus in Bogenhausen. Bayern Munich "
     "season-ticket holder, classical-music subscriber at the Philharmonie. "
     "Sceptical of Tesla. Trusts ADAC, Stiftung Warentest, his colleagues. "
     "Long deliberation on cars and electronics; won't buy on impulse."),

    ("Freya Lindberg, 30, Stockholm",
     "Freya Lindberg, 30, senior product designer at Spotify HQ. SEK 58K/mo "
     "(~€5K). Lives in Södermalm with her partner and their cat. Runs a "
     "sourdough side-hustle on Instagram (4.5K followers). Vegetarian. "
     "Politically green-left. Trusts her ex-Klarna mentor and Swedish-language "
     "Substacks. Will spend SEK 4,500 on a chef's knife she'll keep 20 years; "
     "cheap on furniture (everything is from BLOCKET secondhand)."),

    ("Mateo Garcia, 47, Madrid",
     "Mateo Garcia, 47, chef-owner of a tapas bar in Lavapiés. €60K personal "
     "draw, family business with his wife. One son (14). Real Madrid "
     "season-ticket holder, religion-level passion. Catholic-cultural, not "
     "practising. Lives in Vallecas. Trusts other restaurant owners and his "
     "supplier of jamón ibérico (40 years). Won't touch food delivery apps "
     "(philosophical objection). Will spend €500 on a knife; argues every "
     "centimo on produce."),

    ("Catarina Almeida, 35, Lisbon",
     "Catarina Almeida, 35, remote ops manager for a Berlin-based fintech, "
     "earns €68K/yr in Lisbon (significant local advantage). Returned from "
     "London 4 years ago. Single, dates casually. Lives in Príncipe Real, "
     "€1,200 rent. Surfs in Costa da Caparica every weekend. Vegetarian. "
     "Trusts ex-colleagues from her Revolut years. Buys Portuguese where "
     "possible (preserves, ceramics). Cheap on tech, splurges on travel."),
]


async def main(admin_email: str) -> None:
    # Lazy imports — these need DATABASE_URL etc. set
    import importlib
    import sys as _sys
    mod_dir = str(_HERE)
    if mod_dir not in _sys.path:
        _sys.path.insert(0, mod_dir)
    main_mod = importlib.import_module("main")

    # Wait for the lifespan-equivalent setup
    main_mod._load_all()
    main_mod._load_generated_from_disk()

    # Look up the admin user once
    from sqlalchemy import select
    from db import User, Event, EventType, get_db  # noqa: PLC0415

    async with main_mod.get_session_factory()() if False else (await _open_db(main_mod)) as db:
        admin = (await db.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()
        if admin is None:
            log.error("admin email %s not found in DB; aborting", admin_email)
            return
        log.info("seeding 20 personas attributed to admin user_id=%s (%s)", admin.id, admin.email)

        client = main_mod._client()

        for label, brief in BRIEFS:
            log.info("→ %s", label)
            try:
                anchor, domain, _ = await main_mod._extract_from_brief(brief, None, client)
                persona = await main_mod._generate_persona_direct(
                    brief=brief, anchor=anchor, domain=domain, client=client,
                )
                pid = persona["persona_id"]
                if pid in main_mod._GENERATED:
                    log.info("   skip (already exists): %s", pid)
                    continue
                main_mod._GENERATED[pid] = persona
                main_mod._persist_generated_dict(persona)
                # Event row so /me/personas surfaces it
                db.add(Event(user_id=admin.id, type=EventType.persona_generated, ref_id=pid))
                await db.commit()
                # Portrait — fire and wait so the wall has it immediately
                fal_key = os.environ.get("FAL_KEY", "")
                if fal_key:
                    try:
                        prompt = main_mod._build_portrait_prompt_dict(persona.get("demographic_anchor") or {})
                        url = await main_mod._call_fal_portrait(prompt, fal_key)
                        main_mod._GENERATED_PORTRAITS[pid] = url
                        main_mod._save_portraits_to_disk()
                        log.info("   portrait ✓ %s", pid)
                    except Exception:
                        log.exception("   portrait failed for %s", pid)
                log.info("   stored ✓ %s", pid)
            except Exception:
                log.exception("   FAILED: %s", label)
                # rollback any open transaction so we can keep going
                try:
                    await db.rollback()
                except Exception:
                    pass


async def _open_db(main_mod):
    factory = main_mod.get_session_factory()
    return factory()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-email", required=True,
                        help="Email of the admin user to attribute the seed personas to "
                             "(must already exist in the users table)")
    args = parser.parse_args()
    asyncio.run(main(args.admin_email))
