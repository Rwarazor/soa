-- CREATE TABLE IF NOT EXISTS event_queue (
--     user_id_ String,
--     post_id_ String,
--     author_id_ String,
--     type_ String
-- ) ENGINE = Kafka
-- SETTINGS kafka_broker_list = 'stat-kafka:9092',
--     kafka_topic_list = 'events',
--     kafka_group_name = 'group1',
--     kafka_format = 'JSONEachRow';

CREATE TABLE IF NOT EXISTS likes (
    user_id UInt64,
    post_id UInt64,
    author_id UInt64
) ENGINE = ReplacingMergeTree()
ORDER BY (author_id, post_id, user_id);

CREATE TABLE IF NOT EXISTS views (
    user_id UInt64,
    post_id UInt64,
    author_id UInt64
) ENGINE = ReplacingMergeTree()
ORDER BY (author_id, post_id, user_id);


-- CREATE MATERIALIZED VIEW IF NOT EXISTS events_to_likes TO likes AS
-- SELECT
--     toInt64(user_id_) as user_id,
--     toInt64(post_id_) as post_id,
--     toInt64(author_id_) as author_id
-- FROM event_queue
-- WHERE type_ = 'like';

-- CREATE MATERIALIZED VIEW IF NOT EXISTS events_to_views TO views AS
-- SELECT
--     toInt64(user_id_) as user_id,
--     toInt64(post_id_) as post_id,
--     toInt64(author_id_) as author_id
-- FROM event_queue
-- WHERE type_ = 'view';
