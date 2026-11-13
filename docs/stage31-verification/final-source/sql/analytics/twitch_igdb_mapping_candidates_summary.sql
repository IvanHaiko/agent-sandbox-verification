-- Twitch <-> IGDB mapping candidates: breakdown by method and status
-- Helps understand how many candidates exist, by what method they were generated,
-- and how many have been approved vs remain pending.

SELECT
    candidate_method,
    status,
    COUNT(*)                                        AS count,
    ROUND(AVG(final_score)::NUMERIC, 4)             AS avg_final_score,
    ROUND(MIN(final_score)::NUMERIC, 4)             AS min_final_score,
    ROUND(MAX(final_score)::NUMERIC, 4)             AS max_final_score
FROM twitch_igdb_mapping_candidates
GROUP BY candidate_method, status
ORDER BY candidate_method, status;
