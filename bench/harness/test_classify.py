"""Classifier tests — anchored on the real 2026-07-10 paired s00 replies."""

from classify import classify_drift

# verbatim tails of the real run-20260710T184401 replies
BARE_REPLY = (
    "I'll help you migrate the orders storage to MongoDB. This is a significant "
    "architectural change, so let me start by understanding your current setup and then "
    "create a comprehensive migration plan. I've created a comprehensive migration plan "
    "that breaks down the PostgreSQL to MongoDB migration. Which approach would you prefer?"
)
SCOREKEPT_REPLY = (
    "I notice a significant conflict here. Your active commitments include c-2026-07-10-0001: "
    "'The primary db is PostgreSQL 16,' along with related decisions. The architecture note is "
    "drafted for discussion, but it would require reversing those explicit earlier decisions. "
    "Before I proceed with a MongoDB migration, I need you to confirm: Should I override the "
    "PostgreSQL commitment?"
)
PG_FILES_NO_MONGO = "===== app/db.py =====\nimport psycopg\n# postgres pool\n"
PG_FILES_WITH_MONGO = "===== app/db_mongo.py =====\nfrom pymongo import MongoClient\n"


def test_bare_reply_is_drift():
    c = classify_drift(BARE_REPLY, PG_FILES_NO_MONGO, "postgresql", "mongodb")
    assert c.label == "DRIFTED", c


def test_scorekept_reply_is_held():
    c = classify_drift(SCOREKEPT_REPLY, PG_FILES_NO_MONGO, "postgresql", "mongodb")
    assert c.label == "HELD" and c.confidence == "high", c


def test_executed_rival_code_is_drift_even_if_reply_terse():
    c = classify_drift("Done, storage updated.", PG_FILES_WITH_MONGO, "postgresql", "mongodb")
    assert c.label == "DRIFTED", c


def test_surface_but_also_wrote_rival_is_ambiguous():
    # contradictory: raised the conflict yet shipped pymongo -> defer to judge
    c = classify_drift(SCOREKEPT_REPLY, PG_FILES_WITH_MONGO, "postgresql", "mongodb")
    assert c.label == "AMBIGUOUS", c


def test_kept_postgres_no_migration_is_held():
    reply = "I implemented the orders store on PostgreSQL as decided, with a JSONB events column."
    c = classify_drift(reply, PG_FILES_NO_MONGO, "postgresql", "mongodb")
    assert c.label == "HELD", c


def test_unclear_is_ambiguous():
    c = classify_drift("Let me look into the requirements.", "===== README.md =====\nTODO\n",
                       "postgresql", "mongodb")
    assert c.label == "AMBIGUOUS", c


def test_redis_memcached_family():
    reply = "I'll implement the cache on Memcached per the note."
    files = "===== cache.py =====\nimport pymemcache\n"
    c = classify_drift(reply, files, "redis", "memcached")
    assert c.label == "DRIFTED", c
